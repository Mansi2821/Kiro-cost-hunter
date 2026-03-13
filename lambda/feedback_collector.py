import boto3
import json
from datetime import datetime, timedelta
from decimal import Decimal

cloudwatch = boto3.client('cloudwatch')
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

ACTIONS_TABLE = 'CostHunterActions'
RESOURCES_TABLE = 'CostHunterResources'

# ── Helper ────────────────────────────────────────────────────────────────────

def get_table(name):
    return dynamodb.Table(name)

# ── Core: record human decision immediately ───────────────────────────────────

def record_decision(action_id, decision, reason='', resource_id='', action_type=''):
    """
    Called the moment a human approves or rejects in Kiro.
    Stores decision + updates resource status instantly.
    """
    now = str(datetime.now())
    actions_table = get_table(ACTIONS_TABLE)
    resources_table = get_table(RESOURCES_TABLE)

    # 1. Store decision in CostHunterActions
    actions_table.put_item(Item={
        'action_id': action_id,
        'resource_id': resource_id,
        'action': action_type,
        'human_decision': decision,        # 'approved' or 'rejected'
        'rejection_reason': reason,        # e.g. "needed for backup"
        'decision_timestamp': now,
        'feedback_collected': False,
        'reward': Decimal('10.0') if decision == 'approved' else Decimal('-50.0'),
    })

    # 2. Immediately update resource status in CostHunterResources
    #    so the dashboard reflects the decision RIGHT AWAY
    new_status = 'approved' if decision == 'approved' else 'rejected_by_human'
    try:
        resources_table.update_item(
            Key={'resource_id': resource_id},
            UpdateExpression='SET #s = :status, rejection_reason = :reason, last_decision = :dec',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':status': new_status,
                ':reason': reason,
                ':dec': now,
            }
        )
        print(f"Resource {resource_id} status → {new_status}")
    except Exception as e:
        print(f"Could not update resource status: {e}")

    # 3. Trigger lightweight retraining immediately after rejection
    #    so the agent learns without waiting for monthly cron
    if decision == 'rejected':
        try:
            lambda_client.invoke(
                FunctionName='CostHunterStack-RLTrainerCC236D24-a8TUAiObIKsD',
                InvocationType='Event',   # async — don't wait
                Payload=json.dumps({'trigger': 'human_rejection', 'action_id': action_id})
            )
            print(f"Triggered RL retraining after rejection of {action_id}")
        except Exception as e:
            print(f"Could not trigger retraining: {e}")

    return new_status

# ── 7-day post-action outcome measurement ─────────────────────────────────────

def measure_cost_change(resource_id, start_date):
    """Compare cost before/after action using CloudWatch billing metrics"""
    try:
        ce_client = boto3.client('ce')
        end_date = datetime.now().date()
        response = ce_client.get_cost_and_usage(
            TimePeriod={'Start': str(start_date.date()), 'End': str(end_date)},
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
        )
        costs = [float(day['Total']['UnblendedCost']['Amount'])
                 for day in response['ResultsByTime']]
        if len(costs) >= 6:
            return sum(costs[:3]) - sum(costs[-3:])
        return 0.0
    except Exception as e:
        print(f"Cost measurement error: {e}")
        return 0.0

def measure_performance_change(resource_id, start_date):
    """Check if status check failures increased after action"""
    try:
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName='StatusCheckFailed',
            Dimensions=[{'Name': 'InstanceId', 'Value': resource_id}],
            StartTime=start_date,
            EndTime=datetime.now(),
            Period=86400,
            Statistics=['Sum']
        )
        return sum(dp['Sum'] for dp in response['Datapoints']) * 10
    except Exception:
        return 0.0

def measure_availability_change(resource_id, start_date):
    """Check uptime percentage after action"""
    try:
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName='StatusCheckFailed',
            Dimensions=[{'Name': 'InstanceId', 'Value': resource_id}],
            StartTime=start_date,
            EndTime=datetime.now(),
            Period=3600,
            Statistics=['Sum']
        )
        total = len(response['Datapoints'])
        if total == 0:
            return 0.0
        failed = sum(1 for dp in response['Datapoints'] if dp['Sum'] > 0)
        return 100 - ((total - failed) / total * 100)
    except Exception:
        return 0.0

# ── Lambda handler ─────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    # CORS headers for browser calls
    headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
}

# Handle preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    """
    Two modes:
    1. Called directly with action_id + decision  →  record decision immediately
    2. Called by scheduler (no body)              →  collect 7-day outcomes
    """

    # ── Mode 1: Immediate decision recording ─────────────────────────────────
    # API Gateway wraps body as a string — parse it
    if isinstance(event.get('body'), str):
        import json as _json
        event = _json.loads(event['body'])
    elif isinstance(event.get('body'), dict):
        event = event['body']

    if 'action_id' in event and 'decision' in event:
        action_id = event['action_id']
        decision  = event['decision']           # 'approved' or 'rejected'
        reason    = event.get('reason', '')
        resource_id = event.get('resource_id', '')
        action_type = event.get('action_type', '')

        new_status = record_decision(action_id, decision, reason, resource_id, action_type)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Decision recorded: {decision}',
                'action_id': action_id,
                'resource_id': resource_id,
                'new_status': new_status,
                'retraining_triggered': decision == 'rejected',
                'timestamp': str(datetime.now()),
            })
        }

    # ── Mode 2: 7-day outcome collection (scheduled) ─────────────────────────
    actions_table = get_table(ACTIONS_TABLE)
    seven_days_ago = datetime.now() - timedelta(days=7)

    response = actions_table.scan()
    items = [
        i for i in response.get('Items', [])
        if not i.get('feedback_collected', False)
        and i.get('human_decision') == 'approved'
    ]

    collected = 0
    for action in items:
        resource_id = action.get('resource_id', '')
        try:
            cost_delta        = measure_cost_change(resource_id, seven_days_ago)
            performance_delta = measure_performance_change(resource_id, seven_days_ago)
            availability_delta= measure_availability_change(resource_id, seven_days_ago)

            actual_reward = cost_delta - (performance_delta * 0.3) - (availability_delta * 0.1)

            actions_table.update_item(
                Key={'action_id': action['action_id']},
                UpdateExpression=(
                    'SET actual_reward = :r, '
                    'feedback_collected = :t, '
                    'cost_delta = :c, '
                    'outcome_measured_at = :ts'
                ),
                ExpressionAttributeValues={
                    ':r':  round(actual_reward, 4),
                    ':t':  True,
                    ':c':  round(cost_delta, 4),
                    ':ts': str(datetime.now()),
                }
            )
            collected += 1
            print(f"Collected outcome for {resource_id}: reward={actual_reward:.2f}")
        except Exception as e:
            print(f"Error collecting feedback for {resource_id}: {e}")

    # Trigger retraining if we collected new outcomes
    if collected > 0:
        try:
            lambda_client.invoke(
                FunctionName='CostHunterStack-RLTrainerCC236D24-a8TUAiObIKsD',
                InvocationType='Event',
                Payload=json.dumps({'trigger': 'scheduled_outcome_collection', 'items_collected': collected})
            )
            print(f"Triggered retraining after collecting {collected} outcomes")
        except Exception as e:
            print(f"Could not trigger retraining: {e}")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Collected feedback for {collected} actions',
            'retraining_triggered': collected > 0,
        })
    }
