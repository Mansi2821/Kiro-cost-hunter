# Cost Hunter Deployment Guide

## Prerequisites

### 1. Install AWS CLI
Download and install from: https://aws.amazon.com/cli/

Or use pip:
```bash
pip install awscli
```

### 2. Configure AWS Credentials
```bash
aws configure
```
You'll need:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., us-east-1)

### 3. Install Node.js (for CDK)
Download from: https://nodejs.org/ (version 18+)

### 4. Install AWS CDK
```bash
npm install -g aws-cdk
```

## Deployment Steps

### Step 1: Create S3 Bucket for Models
```bash
aws s3 mb s3://cost-hunter-models-YOUR-ACCOUNT-ID
```

### Step 2: Upload Trained Model
```bash
aws s3 cp models/ppo_agent_baseline.zip s3://cost-hunter-models-YOUR-ACCOUNT-ID/ppo_agent.zip
```

### Step 3: Bootstrap CDK (First Time Only)
```bash
cd cdk
cdk bootstrap
```

### Step 4: Deploy Infrastructure
```bash
cdk deploy
```

This will create:
- 4 Lambda functions (scanner, executor, trainer, feedback collector)
- 3 DynamoDB tables (resources, actions, config)
- 1 S3 bucket (cost data)
- EventBridge rules (daily scan, feedback, monthly training)
- CloudWatch alarm (cost monitoring)

### Step 5: Test in Kiro

Once deployed, use these commands in Kiro chat:
- "Show me my cost dashboard"
- "What are the top wasteful resources?"
- "Approve action [action_id]"
- "Prioritize cost savings"

## Demo Mode (Without AWS)

If you don't have AWS credentials yet, you can test locally:

```bash
python demo/local_demo.py
```

This simulates the entire system locally with mock data.
