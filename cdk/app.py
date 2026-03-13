#!/usr/bin/env python3
import aws_cdk as cdk
from aws_cdk import (
    Stack, Duration, RemovalPolicy,
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
)
from constructs import Construct


class CostHunterStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        model_bucket = s3.Bucket(self, 'ModelBucket',
            removal_policy=RemovalPolicy.RETAIN, versioned=True)

        resources_table = dynamodb.Table(self, 'ResourcesTable',
            table_name='CostHunterResources',
            partition_key=dynamodb.Attribute(name='resource_id', type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY)

        actions_table = dynamodb.Table(self, 'ActionsTable',
            table_name='CostHunterActions',
            partition_key=dynamodb.Attribute(name='action_id', type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY)

        config_table = dynamodb.Table(self, 'ConfigTable',
            table_name='CostHunterConfig',
            partition_key=dynamodb.Attribute(name='config_key', type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY)

        env_vars = {'MODEL_BUCKET': model_bucket.bucket_name, 'AWS_REGION': self.region}

        cost_scanner = _lambda.Function(self, 'CostScanner',
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler='cost_scanner.handler',
            code=_lambda.Code.from_asset('../lambda_package'),
            timeout=Duration.minutes(5), memory_size=256, environment=env_vars)
        resources_table.grant_write_data(cost_scanner)
        actions_table.grant_write_data(cost_scanner)
        cost_scanner.add_to_role_policy(iam.PolicyStatement(
            actions=['ec2:DescribeInstances','ec2:DescribeVolumes','cloudwatch:GetMetricStatistics'],
            resources=['*']))

        action_executor = _lambda.Function(self, 'ActionExecutor',
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler='action_executor.handler',
            code=_lambda.Code.from_asset('../lambda_package'),
            timeout=Duration.minutes(10), memory_size=256, environment=env_vars)
        actions_table.grant_read_write_data(action_executor)
        action_executor.add_to_role_policy(iam.PolicyStatement(
            actions=['ec2:StopInstances','ec2:StartInstances','ec2:ModifyInstanceAttribute','ec2:DeleteVolume'],
            resources=['*']))

        feedback_collector = _lambda.Function(self, 'FeedbackCollector',
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler='feedback_collector.handler',
            code=_lambda.Code.from_asset('../lambda_package'),
            timeout=Duration.minutes(5), memory_size=256, environment=env_vars)
        actions_table.grant_read_write_data(feedback_collector)
        feedback_collector.add_to_role_policy(iam.PolicyStatement(
            actions=['cloudwatch:GetMetricStatistics'], resources=['*']))

        rl_trainer = _lambda.Function(self, 'RLTrainer',
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler='rl_trainer.handler',
            code=_lambda.Code.from_asset('../lambda_package'),
            timeout=Duration.minutes(15), memory_size=1024, environment=env_vars)
        actions_table.grant_read_data(rl_trainer)
        config_table.grant_read_write_data(rl_trainer)
        model_bucket.grant_read_write(rl_trainer)

        events.Rule(self, 'DailyScan',
            schedule=events.Schedule.cron(hour='6', minute='0'),
            targets=[targets.LambdaFunction(cost_scanner)])
        events.Rule(self, 'DailyFeedback',
            schedule=events.Schedule.cron(hour='7', minute='0'),
            targets=[targets.LambdaFunction(feedback_collector)])
        events.Rule(self, 'MonthlyTraining',
            schedule=events.Schedule.cron(day='1', hour='2', minute='0'),
            targets=[targets.LambdaFunction(rl_trainer)])

        cloudwatch.Alarm(self, 'CostAlarm',
            metric=cloudwatch.Metric(
                namespace='AWS/Billing', metric_name='EstimatedCharges',
                statistic='Maximum', period=Duration.hours(6)),
            threshold=5, evaluation_periods=1,
            alarm_description='Cost Hunter infrastructure > $5/month')


app = cdk.App()
CostHunterStack(app, 'CostHunterStack')
app.synth()
