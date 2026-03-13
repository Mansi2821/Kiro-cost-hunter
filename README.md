# Kiro Cost Hunter - RL-Powered AWS Cost Optimizer

Autonomous agent that learns optimal AWS resource allocation using reinforcement learning, reducing cloud bills by 20-40%.

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
npm install -g aws-cdk
```

2. Train baseline agent locally (10-15 minutes):
```bash
python scripts/train_baseline.py
```

3. Configure AWS credentials:
```bash
aws configure
```

4. Deploy infrastructure:
```bash
cd cdk
cdk bootstrap  # First time only
cdk deploy
```

5. Upload trained model:
```bash
aws s3 cp models/ppo_agent_baseline.zip s3://cost-hunter-models/ppo_agent.zip
```

6. Open Kiro and use Cost Hunter commands:
- "Show me my cost dashboard"
- "What are the top wasteful resources?"
- "Approve action [action_id]"
- "Prioritize cost savings" or "Prioritize performance"

## Architecture

- **RL Agent**: PPO algorithm learns cost/performance trade-offs
- **Lambda Functions**: Daily scanning, action execution, monthly retraining
- **DynamoDB**: Resource inventory + action history
- **Bedrock**: Generates human-readable explanations
- **Kiro Integration**: Approval workflow in chat interface

## Kiro Integration

Cost Hunter integrates with Kiro via MCP server. Available commands:

- `get_cost_dashboard` - View current spending and recommendations
- `approve_action <id>` - Execute a cost-saving action
- `reject_action <id>` - Reject with feedback for learning
- `adjust_optimization_priority` - Balance cost vs performance
- `explain_recommendation <id>` - Get detailed reasoning

The agent appears in Kiro chat and proactively suggests optimizations.

## Safety Guardrails

- Dry-run mode by default
- Actions <$100/month auto-approved, larger require human sign-off
- 7-day monitoring after each action with automatic rollback if issues detected
- Human override always available
- Infrastructure cost alarm at $5/month

## Learning & Feedback

- Agent learns from every approval/rejection
- Monthly retraining incorporates real outcomes
- Multi-objective optimization balances cost, performance, availability
- Explainable AI via Bedrock provides reasoning for every action

## Cost

Runs entirely on AWS free tier for <100 resources:
- Lambda: ~30 invocations/month (1M free)
- DynamoDB: <1GB storage (25GB free)
- S3: <1GB storage (5GB free)
- Bedrock: ~$0.30/month for explanations

Total: <$1/month for typical usage
