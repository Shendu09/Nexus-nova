# Deployment Guide

## AWS Lambda Deployment

### Build Docker Image
```bash
docker build -t nexus:latest .
docker tag nexus:latest account.dkr.ecr.region.amazonaws.com/nexus:latest
aws ecr get-login-password | docker login --username AWS --password-stdin account.dkr.ecr.region.amazonaws.com
docker push account.dkr.ecr.region.amazonaws.com/nexus:latest
```

### Create Lambda Function
```bash
aws lambda create-function \
  --function-name nexus-analyzer \
  --role arn:aws:iam::account:role/nexus-role \
  --code ImageUri=account.dkr.ecr.region.amazonaws.com/nexus:latest \
  --timeout 300 \
  --memory-size 1024 \
  --environment Variables={AWS_REGION=us-east-1}
```

### CloudWatch Integration
```bash
# Create subscription filter
aws logs put-subscription-filter \
  --log-group-name /aws/lambda/my-app \
  --filter-name nexus-trigger \
  --filter-pattern "[ERROR]" \
  --destination-arn arn:aws:lambda:...
```

### EventBridge Schedule
```bash
aws events put-rule \
  --name nexus-periodic-check \
  --schedule-expression "rate(1 hour)"
```

## Infrastructure as Code

### CloudFormation Template
```yaml
AWSTemplateFormatVersion: '2010-09-09'

Resources:
  NexusLambda:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: nexus-analyzer
      Runtime: python3.12
      # ... additional properties
```

## Monitoring and Logging

```bash
# View logs
aws logs tail /aws/lambda/nexus-analyzer --follow

# Create CloudWatch dashboard
aws cloudwatch put-dashboard ...
```
