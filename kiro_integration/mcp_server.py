#!/usr/bin/env python3
"""
MCP Server for Kiro Cost Hunter integration
Exposes tools for cost monitoring and action approval in Kiro chat
"""

import json
import sys
import os

if 'AWS_REGION' not in os.environ:
    os.environ['AWS_REGION'] = 'us-east-1'

_dynamodb = None
_lambda_client = None

def get_dynamodb():
    global _dynamodb
    if _dynamodb is None:
        import boto3
        _dynamodb = boto3.resource('dynamodb')
    return _dynamodb

def get_lambda_client():
    global _lambda_client
    if _lambda_client is None:
        import boto3
        _lambda_client = boto3.client('lambda')
    return _lambda_client

from datetime import datetime

TOOLS = [
    {
        "name": "get_cost_dashboard",
        "description": "Get current AWS cost metrics and wasteful resources",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "approve_action",
        "description": "Approve a cost-saving action recommended by the agent",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_id": {"type": "string", "description": "ID of the action to approve"}
            },
            "required": ["action_id"]
        }
    },
    {
        "name": "reject_action",
        "description": "Reject a cost-saving action with optional reason",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_id": {"type": "string"},
                "reason": {"type": "string", "description": "Why this action was rejected"}
            },
            "required": ["action_id"]
        }
    },
    {
        "name": "adjust_optimization_priority",
        "description": "Adjust agent's cost vs performance trade-off",
        "inputSchema": {
            "type": "object",
            "properties": {
                "priority": {
                    "type": "string",
                    "enum": ["cost", "balanced", "performance"],
                    "description": "Optimization priority"
                }
            },
            "required": ["priority"]
        }
    },
    {
        "name": "explain_recommendation",
        "description": "Get detailed explanation for a specific recommendation",
        "inputSchema": {
            "type": "object",
            "properties": {"action_id": {"type": "string"}},
            "required": ["action_id"]
        }
    }
]

def handle_tool_call(tool_name, arguments):
    if tool_name == "get_cost_dashboard":
        return get_cost_dashboard()
    elif tool_name == "approve_action":
        return approve_action(arguments['action_id'])
    elif tool_name == "reject_action":
        return reject_action(arguments['action_id'], arguments.get('reason', ''))
    elif tool_name == "adjust_optimization_priority":
        return adjust_priority(arguments['priority'])
    elif tool_name == "explain_recommendation":
        return explain_recommendation(arguments['action_id'])
    return {"error": "Unknown tool"}

def get_cost_dashboard():
    dynamodb = get_dynamodb()
    table = dynamodb.Table('CostHunterResources')
    response = table.scan(
        FilterExpression='#status = :status',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={':status': 'pending_review'}
    )
    pending_actions = response['Items']
    total_potential_savings = sum(float(a.get('estimated_savings', 0)) for a in pending_actions)
    return {
        "pending_actions": len(pending_actions),
        "potential_monthly_savings": f"${total_potential_savings:.2f}",
        "top_recommendations": pending_actions[:5]
    }

def approve_action(action_id):
    dynamodb = get_dynamodb()
    lambda_client = get_lambda_client()
    table = dynamodb.Table('CostHunterActions')
    table.update_item(
        Key={'action_id': action_id},
        UpdateExpression='SET user_approved = :true, execution_date = :date',
        ExpressionAttributeValues={':true': True, ':date': str(datetime.now().date())}
    )
    import json as _json
    lambda_client.invoke(
        FunctionName='ActionExecutor',
        InvocationType='Event',
        Payload=_json.dumps({'action_id': action_id, 'dry_run': False})
    )
    return {"status": "approved", "message": "Action will execute within 5 minutes"}

def reject_action(action_id, reason):
    dynamodb = get_dynamodb()
    table = dynamodb.Table('CostHunterActions')
    table.update_item(
        Key={'action_id': action_id},
        UpdateExpression='SET user_approved = :false, rejection_reason = :reason, actual_reward = :reward',
        ExpressionAttributeValues={':false': False, ':reason': reason, ':reward': -50}
    )
    return {"status": "rejected", "message": "Agent will learn from this feedback"}

def adjust_priority(priority):
    dynamodb = get_dynamodb()
    weights = {
        'cost':        {'cost': 0.8, 'performance': 0.15, 'availability': 0.05},
        'balanced':    {'cost': 0.6, 'performance': 0.30, 'availability': 0.10},
        'performance': {'cost': 0.3, 'performance': 0.60, 'availability': 0.10}
    }
    table = dynamodb.Table('CostHunterConfig')
    table.put_item(Item={'config_key': 'reward_weights', **weights[priority]})
    return {"status": "updated", "weights": weights[priority]}

def explain_recommendation(action_id):
    dynamodb = get_dynamodb()
    table = dynamodb.Table('CostHunterActions')
    response = table.get_item(Key={'action_id': action_id})
    action = response['Item']
    return {
        "action": action['action_type'],
        "resource": action['resource_id'],
        "explanation": action.get('explanation', 'No explanation available'),
        "estimated_savings": f"${float(action.get('estimated_savings', 0)):.2f}/month",
        "risk_level": action.get('risk_level', 'low')
    }

def handle_mcp_request(request):
    method = request.get('method')
    if method == 'tools/list':
        return {'tools': TOOLS}
    elif method == 'tools/call':
        tool_name = request['params']['name']
        arguments = request['params'].get('arguments', {})
        result = handle_tool_call(tool_name, arguments)
        return {'content': [{'type': 'text', 'text': json.dumps(result, indent=2)}]}
    elif method == 'initialize':
        return {
            'protocolVersion': '2024-11-05',
            'capabilities': {'tools': {}},
            'serverInfo': {'name': 'cost-hunter', 'version': '1.0.0'}
        }
    return {'error': 'Unknown method'}

def main():
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = handle_mcp_request(request)
            print(json.dumps(response), flush=True)
        except Exception as e:
            print(json.dumps({'error': {'code': -32603, 'message': str(e)}}), flush=True)

if __name__ == '__main__':
    main()
