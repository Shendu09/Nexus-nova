# Terraform Infrastructure Template

```hcl
# Provider configuration
provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  default = "us-east-1"
}

variable "environment" {
  default = "dev"
}

# IAM Role for Lambda
resource"aws_iam_role" "nexus_role" {
  name = "nexus-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy
resource "aws_iam_role_policy" "nexus_policy" {
  name = "nexus-policy"
  role = aws_iam_role.nexus_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:GetLogEvents",
          "logs:DescribeLogGroups"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = "bedrock:InvokeModel"
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = "dynamodb:*"
        Resource = aws_dynamodb_table.sessions.arn
      },
      {
        Effect = "Allow"
        Action = "sns:Publish"
        Resource = aws_sns_topic.notifications.arn
      }
    ]
  })
}

# DynamoDB Table
resource "aws_dynamodb_table" "sessions" {
  name           = "nexus-sessions-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "session_id"
  range_key      = "created_at"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "N"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

# SNS Topic
resource "aws_sns_topic" "notifications" {
  name = "nexus-notifications-${var.environment}"
}

# Lambda Function
resource "aws_lambda_function" "nexus" {
  filename      = "nexus.zip"
  function_name = "nexus-analyzer-${var.environment}"
  role          = aws_iam_role.nexus_role.arn
  handler       = "nexus.handler.handler"
  runtime       = "python3.12"
  timeout       = 600
  memory_size   = 1024

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.sessions.name
      SNS_TOPIC_ARN  = aws_sns_topic.notifications.arn
    }
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "nexus_logs" {
  name              = "/aws/lambda/nexus-analyzer-${var.environment}"
  retention_in_days = 30
}

# EventBridge Rule
resource "aws_cloudwatch_event_rule" "nexus_schedule" {
  name                = "nexus-periodic-check"
  description         = "Trigger Nexus analysis hourly"
  schedule_expression = "rate(1 hour)"
}

# EventBridge Target
resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.nexus_schedule.name
  target_id = "NexusLambda"
  arn       = aws_lambda_function.nexus.arn
}

# Lambda Permission for EventBridge
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.nexus.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.nexus_schedule.arn
}

# Outputs
output "lambda_arn" {
  value = aws_lambda_function.nexus.arn
}

output "dynamodb_table" {
  value = aws_dynamodb_table.sessions.name
}

output "sns_topic_arn" {
  value = aws_sns_topic.notifications.arn
}
```

## Deployment
```bash
terraform init
terraform plan
terraform apply
```
