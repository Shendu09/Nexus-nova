# Getting Started Guide

## Installation

### Prerequisites
- Python 3.12+
- AWS Account with appropriate permissions
- Docker (for Lambda deployment)

### Setup
```bash
pip install nexus
```

### Configuration
```bash
export AWS_REGION=us-east-1
export LOG_GROUP=my-app-logs
export SNS_TOPIC=arn:aws:sns:...
export DYNAMODB_TABLE=nexus-sessions
export CONNECT_INSTANCE_ID=instance-id
```

## First Steps
1. Configure AWS credentials
2. Set up CloudWatch log groups
3. Create SNS topic for notifications
4. Create DynamoDB tables
5. Configure Amazon Connect (optional)
6. Deploy Lambda function

## Testing
```bash
python -m pytest tests/
```

## Deployment
```bash
docker build -t nexus:latest .
aws lambda create-function ...
```
