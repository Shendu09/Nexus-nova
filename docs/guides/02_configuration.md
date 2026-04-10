# Configuration Guide

## Environment Setup

### AWS Configuration
```bash
# Core services
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789

# CloudWatch
LOG_GROUP=/aws/lambda/my-app
LOG_STREAM_PREFIX=nexus

# DynamoDB
DYNAMODB_TABLE=nexus-sessions
SESSION_TTL=86400

# SNS
SNS_TOPIC=arn:aws:sns:region:account:topic-name

# Bedrock
BEDROCK_REGION=us-east-1
BEDROCK_MODEL_EMBEDDINGS=amazon.nova-embed-text-v1
BEDROCK_MODEL_LITE=amazon.nova-lite
BEDROCK_MODEL_SONIC=amazon.nova-sonic
```

### Optional Configuration
```bash
# Amazon Connect
CONNECT_INSTANCE_ID=instance-id
CONNECT_PHONE_NUMBER=+1234567890

# Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
PAGERDUTY_TOKEN=token
```

## Configuration File
Create `config.yaml`:
```yaml
logging:
  level: INFO
  format: json

analysis:
  timeout: 300
  max_logs: 10000
  
voice:
  enabled: true
  timeout: 600
```
