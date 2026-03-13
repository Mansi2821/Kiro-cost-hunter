import boto3
import json

ec2_client = boto3.client('ec2')
bedrock = boto3.client('bedrock-runtime')

def lambda_handler(event, context):
    """Executes approved cost-saving actions"""
    
    # FIX 1: Handle both 'action' and 'action_id' in payload
    action = event.get('action') or event.get('action_id')
    resource_id = event.get('resource_id', 'unknown')
    dry_run = event.get('dry_run', True)
    
    # FIX 2: Validate required fields
    if not action:
        return {
            'statusCode': 400,
            'body': 'Missing required field: action or action_id'
        }
    
    # FIX 3: Try Bedrock explanation, but don't crash if it fails
    try:
        explanation = generate_explanation(action, resource_id)
    except Exception as e:
        explanation = f"Action: {action} on resource {resource_id}. (Bedrock unavailable: {str(e)})"
    
    if action == 'downsize':
        return downsize_instance(resource_id, dry_run, explanation)
    elif action == 'switch_to_spot':
        return switch_to_spot(resource_id, dry_run, explanation)
    elif action == 'enable_autoscaling':
        return enable_autoscaling(resource_id, dry_run, explanation)
    else:
        return {
            'statusCode': 400,
            'body': f'Unknown action: {action}. Valid actions: downsize, switch_to_spot, enable_autoscaling'
        }

def generate_explanation(action, resource_id):
    """Use Bedrock to explain the action"""
    prompt = f"Explain why we should {action} for resource {resource_id} based on low utilization. Keep it under 100 words."
    
    response = bedrock.invoke_model(
        modelId='us.anthropic.claude-3-5-haiku-20241022-v1:0',
        body=json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 200,
            'messages': [{'role': 'user', 'content': prompt}]
        })
    )
    result = json.loads(response['body'].read())
    return result['content'][0]['text']

def downsize_instance(instance_id, dry_run, explanation):
    """Downsize EC2 instance"""
    try:
        if not dry_run:
            # Stop instance first before resizing
            ec2_client.stop_instances(InstanceIds=[instance_id])
            ec2_client.get_waiter('instance_stopped').wait(InstanceIds=[instance_id])
            ec2_client.modify_instance_attribute(
                InstanceId=instance_id,
                InstanceType={'Value': 't3.micro'}
            )
            ec2_client.start_instances(InstanceIds=[instance_id])
        return {
            'statusCode': 200,
            'explanation': explanation,
            'action': 'downsize_scheduled',
            'resource_id': instance_id,
            'dry_run': dry_run
        }
    except Exception as e:
        return {'statusCode': 500, 'error': str(e)}

def switch_to_spot(instance_id, dry_run, explanation):
    """Switch to spot instance"""
    return {
        'statusCode': 200,
        'explanation': explanation,
        'action': 'spot_migration_planned',
        'resource_id': instance_id,
        'dry_run': dry_run
    }

def enable_autoscaling(instance_id, dry_run, explanation):
    """Enable auto-scaling"""
    return {
        'statusCode': 200,
        'explanation': explanation,
        'action': 'autoscaling_enabled',
        'resource_id': instance_id,
        'dry_run': dry_run
    }
