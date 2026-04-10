# Cloud Infrastructure

## AWS Services Used

### Compute
- **AWS Lambda**: Main execution runtime (Python 3.12)
- **Container Image**: ECR for Lambda container

### Logs & Monitoring
- **CloudWatch Logs**: Source data for analysis
- **CloudWatch Metrics**: Custom metrics for monitoring
- **X-Ray**: Distributed tracing

### Data Storage
- **DynamoDB**: Sessions, cache, metrics
- **S3**: Backup and archived analyses

### AI/ML
- **Amazon Bedrock**: For Amazon Nova models
  - Nova Embeddings: Semantic analysis
  - Nova 2 Lite: RCA reasoning
  - Nova 2 Sonic: Voice conversation

### Communications
- **SNS**: Email notifications
- **Amazon Connect**: Voice calls
- **SQS**: Message queuing (optional)

### Event Management
- **EventBridge**: Scheduled triggers
- **CloudWatch Alarms**: Direct triggers

### Security
- **IAM**: Authentication and authorization
- **Secrets Manager**: Credential storage
- **VPC**: Network isolation

## Infrastructure Deployment Options

### Option 1: AWS SAM
```yaml
Functions:
  NexusHandler:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: src/
      Handler: nexus.handler.handler
      Runtime: python3.12
      Timeout: 600
```

### Option 2: Terraform
```hcl
resource "aws_lambda_function" "nexus" {
  filename         = "nexus.zip"
  function_name    = "nexus-analyzer"
  role            = aws_iam_role.nexus_role.arn
  handler         = "nexus.handler.handler"
  runtime         = "python3.12"
}
```

### Option 3: CloudFormation
- Native AWS IaC format
- Template validation
- Change sets for safe updates

## Scaling Considerations
- Lambda: Automatic, timeout 15 minutes max
- DynamoDB: On-demand or provisioned
- Bedrock: Model throughput quotas
- CloudWatch: Log retention window
- Connect: Concurrent call limits

## High Availability
- Multi-region deployment (optional)
- DynamoDB global tables
- Lambda across availability zones
- Cross-region SNS topics
