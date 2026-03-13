#!/usr/bin/env python3
"""Cost dashboard helper for Kiro integration."""
import boto3
import os
from datetime import datetime


def get_dashboard_summary():
    region = os.environ.get('AWS_REGION', 'us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name=region)

    resources_table = dynamodb.Table('CostHunterResources')
    actions_table = dynamodb.Table('CostHunterActions')

    # Pending recommendations
    pending_resp = resources_table.scan(
        FilterExpression='#s = :s',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={':s': 'pending_review'}
    )
    pending = pending_resp.get('Items', [])
    total_savings = sum(float(r.get('estimated_savings', 0)) for r in pending)

    # Recent approvals
    approved_resp = actions_table.scan(
        FilterExpression='user_approved = :t',
        ExpressionAttributeValues={':t': True}
    )
    approved = approved_resp.get('Items', [])
    realized_savings = sum(float(a.get('estimated_savings', 0)) for a in approved)

    return {
        'timestamp': datetime.utcnow().isoformat(),
        'pending_recommendations': len(pending),
        'potential_monthly_savings': f'${total_savings:.2f}',
        'approved_actions': len(approved),
        'realized_monthly_savings': f'${realized_savings:.2f}',
        'top_recommendations': sorted(
            pending, key=lambda x: float(x.get('estimated_savings', 0)), reverse=True
        )[:5]
    }


if __name__ == '__main__':
    import json
    print(json.dumps(get_dashboard_summary(), indent=2, default=str))
