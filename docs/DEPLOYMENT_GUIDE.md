# Nexus Nova Deployment Guide

## Quick Start Deployment

### Prerequisites

- AWS Account with IAM permissions for Lambda, DynamoDB, S3, CloudWatch
- Python 3.10+, pip, git
- AWS CLI configured with credentials
- Docker (optional, for local testing)

### Step 1: Clone and Setup

```bash
git clone https://github.com/Shendu09/Nexus-nova.git
cd Nexus-nova
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r ML_REQUIREMENTS.txt
```

### Step 2: Build Models

```bash
# Create models directory
mkdir -p models/{autoencoder,severity,forecasts,linucb,embeddings,embeddings_onnx}

# Train each module (or download pre-trained)
python scripts/train_autoencoder.py --output_dir models/autoencoder --epochs 10
python scripts/finetune_severity.py --output_dir models/severity --epochs 5
python scripts/train_prophet_model.py --output_dir models/forecasts --days 30
python scripts/train_linucb_agent.py --output_dir models/linucb --episodes 1000
python scripts/train_embeddings.py --output_dir models/embeddings --epochs 3
python scripts/export_onnx.py --model_path models/embeddings --output_dir models/embeddings_onnx
```

### Step 3: Upload Models to S3

```bash
aws s3 mb s3://nexus-ml-models-$(date +%s) --region us-east-1
export MODELS_BUCKET=nexus-ml-models-$(date +%s)

# Upload all models
aws s3 sync models/ s3://$MODELS_BUCKET/ --recursive

# Verify
aws s3 ls s3://$MODELS_BUCKET/
```

### Step 4: Deploy Lambda Function

#### Option A: Using AWS SAM

```yaml
# template.yaml (partial)
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Parameters:
  ModelsBucket:
    Type: String
    Description: S3 bucket with trained models

Resources:
  NexusHandlerFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: app.lambda_handler
      Runtime: python3.10
      Timeout: 900
      MemorySize: 3008
      CodeUri: ./
      Environment:
        Variables:
          MODELS_BUCKET: !Ref ModelsBucket
          SNS_TOPIC_ARN: !Ref AlertTopic
          DYNAMODB_TABLE: nexus-ml-config
      Policies:
        - S3CrudPolicy:
            BucketName: !Ref ModelsBucket
        - DynamoDBCrudPolicy:
            TableName: nexus-ml-config
        - SNSPublishMessagePolicy:
            TopicName: !GetAtt AlertTopic.TopicName

  AlertTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: nexus-alerts
      DisplayName: Nexus Incident Alerts

  MLConfigTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: nexus-ml-config
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: config_key
          AttributeType: S
      KeySchema:
        - AttributeName: config_key
          KeyType: HASH

Outputs:
  LambdaFunctionArn:
    Value: !GetAtt NexusHandlerFunction.Arn
  SNSTopicArn:
    Value: !Ref AlertTopic
```

Deploy with SAM:
```bash
sam build
sam deploy --guided \
  --parameter-overrides ModelsBucket=$MODELS_BUCKET \
  --stack-name nexus-novo \
  --region us-east-1
```

#### Option B: Manual Lambda Deployment

```bash
# Package function
zip -r lambda-package.zip \
  src/ scripts/ models/ \
  -x "*.git*" "tests/*" "*.pyc" "*.pth" "*.pkl" "__pycache__/*"

# Create Lambda execution role
aws iam create-role --role-name nexus-lambda-role \
  --assume-role-policy-document file://trust-policy.json

# Attach policies
aws iam attach-role-policy --role-name nexus-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/AWSLambdaFullAccess
aws iam attach-role-policy --role-name nexus-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess

# Create Lambda function
aws lambda create-function \
  --function-name nexus-handler \
  --runtime python3.10 \
  --role arn:aws:iam::ACCOUNT_ID:role/nexus-lambda-role \
  --handler app.lambda_handler \
  --zip-file fileb://lambda-package.zip \
  --timeout 900 \
  --memory-size 3008 \
  --environment Variables="{MODELS_BUCKET=$MODELS_BUCKET,SNS_TOPIC_ARN=arn:aws:sns:us-east-1:ACCOUNT_ID:nexus-alerts,DYNAMODB_TABLE=nexus-ml-config}"
```

### Step 5: Configure Triggers

#### EventBridge Rule for Periodic Forecasting

```bash
# Create rule
aws events put-rule \
  --name nexus-forecast-schedule \
  --schedule-expression 'rate(1 hour)'

# Set Lambda as target
aws events put-targets \
  --rule nexus-forecast-schedule \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:ACCOUNT_ID:function:nexus-handler","RoleArn"="arn:aws:iam::ACCOUNT_ID:role/nexus-eventbridge-role"
```

#### CloudWatch Logs Subscription

```bash
# Subscribe Lambda to log group
aws logs put-subscription-filter \
  --log-group-name /aws/lambda/incident-logs \
  --filter-name nexus-filter \
  --filter-pattern "[...]" \
  --destination-arn arn:aws:lambda:us-east-1:ACCOUNT_ID:function:nexus-handler
```

### Step 6: Set Up DynamoDB Tables

```bash
# Feedback table
aws dynamodb create-table \
  --table-name nexus-voice-feedback \
  --attribute-definitions AttributeName=feedback_id,AttributeType=S \
  --key-schema AttributeName=feedback_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --time-to-live-specification AttributeName=ttl,Enabled=true

# Config table
aws dynamodb create-table \
  --table-name nexus-ml-config \
  --attribute-definitions AttributeName=config_key,AttributeType=S \
  --key-schema AttributeName=config_key,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### Step 7: Verify Deployment

```bash
# Test Lambda
aws lambda invoke \
  --function-name nexus-handler \
  --payload '{"source": "test"}' \
  response.json

# Check DynamoDB
aws dynamodb scan --table-name nexus-ml-config

# Verify S3 upload
aws s3 ls s3://$MODELS_BUCKET/ --recursive

# Check CloudWatch logs
aws logs tail /aws/lambda/nexus-handler --follow
```

## Production Deployment Checklist

- [ ] All models tested locally with pytest
- [ ] Models uploaded to S3 with versioning
- [ ] Lambda function size < 250MB (use layers for dependencies)
- [ ] Timeout set appropriately (min 300s for large models)
- [ ] Memory configured (min 1024MB for BERT, 3008MB recommended)
- [ ] IAM roles with least privilege
- [ ] CloudWatch alarms configured
- [ ] DynamoDB tables created with TTL
- [ ] SNS topics for alerts
- [ ] EventBridge rules for scheduled inference
- [ ] Monitoring dashboard created
- [ ] Logging configured with retention policies
- [ ] VPC endpoints if running in private VPC
- [ ] KMS encryption for at-rest data

## Monitoring & Debugging

### CloudWatch Dashboard

```python
import boto3
cw = boto3.client('cloudwatch')

cw.put_metric_dashboard(
    DashboardName='nexus-ml-pipeline',
    DashboardBody=json.dumps({
        'widgets': [
            {
                'type': 'metric',
                'properties': {
                    'metrics': [
                        ['AWS/Lambda', 'Duration', {'stat': 'Average'}],
                        ['AWS/Lambda', 'Errors', {'stat': 'Sum'}],
                        ['AWS/Lambda', 'Throttles', {'stat': 'Sum'}]
                    ],
                    'period': 300,
                    'stat': 'Average',
                    'region': 'us-east-1',
                    'title': 'Lambda Performance'
                }
            }
        ]
    })
)
```

### Alarms

```bash
# Error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name nexus-lambda-errors \
  --alarm-description "Alert on Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:nexus-alerts

# Timeout alarm
aws cloudwatch put-metric-alarm \
  --alarm-name nexus-lambda-duration \
  --alarm-description "Alert on Lambda timeout" \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --statistic Maximum \
  --period 300 \
  --threshold 800000 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:nexus-alerts
```

### Local Testing

```bash
# Test with SAM local
sam local start-api

# Invoke function
curl http://localhost:3000/incidents -X POST -d '{"logs": ["error happened"]}'

# Debug with container
docker build -t nexus-handler .
docker run -p 9000:8080 nexus-handler
```

## Rollback Procedures

### Function Rollback
```bash
# List versions
aws lambda list-versions-by-function --function-name nexus-handler

# Publish version
aws lambda publish-version --function-name nexus-handler

# Set alias to previous version
aws lambda update-alias \
  --function-name nexus-handler \
  --name prod \
  --function-version 5
```

### Model Rollback
```bash
# Restore model from S3 backup
aws s3 cp s3://nexus-ml-models/backups/severity-v1.tar.gz ./
tar -xzf severity-v1.tar.gz

# Update Lambda environment
aws lambda update-function-configuration \
  --function-name nexus-handler \
  --environment Variables="{MODEL_VERSION=v1}"
```

## Cost Optimization

- Use Lambda provisioned concurrency for consistent performance
- Enable Lambda Insights for better observability
- Archive old feedback to S3 Glacier
- Use SageMaker Batch Transform for bulk inference
- Consider GPU Lambda for heavy models
- Use AWS Lambda@Edge for lower latency
