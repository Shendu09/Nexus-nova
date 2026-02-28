# Flare Setup Guide

This guide walks through deploying Flare and configuring triggers for common AWS monitoring scenarios.

## Prerequisites

- An AWS account with [Amazon Bedrock access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) enabled for Amazon Nova models in your region
- AWS CLI installed and configured (`aws configure`)
- The CloudWatch Log Groups you want to monitor must already exist (Flare reads from them, it doesn't create them)

## Step 1: Deploy Flare

Deploy with at least one trigger enabled. This example enables the alarm trigger for alarms prefixed with `prod-`:

```bash
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name flare \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    LogGroupPatterns="/aws/lambda/*" \
    NotificationEmail=you@example.com \
    EnableAlarmTrigger=true \
    AlarmNamePrefix=prod-
```

After deploying, check your email and **confirm the SNS subscription**. You won't receive any notifications until you do.

**Important:** No triggers are enabled by default. You must explicitly enable at least one, otherwise Flare deploys but never runs. This is intentional -- you control exactly when Flare analyzes your logs.

## Step 2: Choose Your Triggers

Flare supports three trigger modes. You can enable any combination.

### CloudWatch Alarm Trigger

Flare analyzes logs when specific CloudWatch Alarms fire. Use `AlarmNamePrefix` to scope which alarms Flare reacts to.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `EnableAlarmTrigger` | `false` | Turn alarm-driven analysis on/off |
| `AlarmNamePrefix` | `""` | Only react to alarms whose name starts with this prefix |

**Example: react to production alarms only:**

```bash
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name flare \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    LogGroupPatterns="/aws/lambda/*,/aws/ecs/*" \
    NotificationEmail=you@example.com \
    EnableAlarmTrigger=true \
    AlarmNamePrefix=prod-
```

When a matching alarm transitions to ALARM state, Flare pulls logs from all configured log groups and analyzes them. The notification includes the alarm name and details.

**How it works:** Flare doesn't create alarms -- you create them separately through CloudWatch for whatever metrics matter to you (CPU utilization, error count, latency, etc.). Name them with a consistent prefix (e.g., `prod-cpu-high`, `prod-error-rate`) so Flare can filter to just the alarms you care about.

If `AlarmNamePrefix` is empty, Flare reacts to *all* alarms in your account, which is usually too broad.

### Scheduled Scans

Flare runs on a timer and scans all log groups matching your patterns. Useful for routine monitoring.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `EnableSchedule` | `false` | Turn scheduled scans on/off |
| `ScheduleExpression` | `rate(1 hour)` | How often to scan |
| `LookbackMinutes` | `30` | How far back to pull logs per scan |

**Example: scan every 30 minutes, looking back 15 minutes each time:**

```bash
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name flare \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    LogGroupPatterns="/aws/lambda/*" \
    NotificationEmail=you@example.com \
    EnableSchedule=true \
    ScheduleExpression="rate(30 minutes)" \
    LookbackMinutes=15
```

Schedule expressions follow [EventBridge syntax](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schedule-expressions.html):
- `rate(1 hour)` -- every hour
- `rate(30 minutes)` -- every 30 minutes
- `cron(0 9 * * ? *)` -- daily at 9 AM UTC

**Note:** On scheduled scans, if Flare determines the logs are healthy, it skips the notification. You only get emailed when something is worth investigating.

### Subscription Filter Trigger (Real-Time)

Flare can react immediately when specific patterns appear in a log group. CloudWatch Logs streams matching events directly to Flare with no delay.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `EnableSubscription` | `false` | Turn subscription filter on/off |
| `SubscriptionLogGroup` | first in `LogGroupPatterns` | Which log group to attach the filter to |
| `SubscriptionFilterPattern` | `?ERROR ?FATAL ?CRITICAL` | What log patterns to match |

**Example: trigger immediately when ERROR or FATAL appears in your app's logs:**

```bash
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name flare \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    LogGroupPatterns="/aws/lambda/*" \
    NotificationEmail=you@example.com \
    EnableSubscription=true \
    SubscriptionLogGroup=/aws/lambda/my-critical-app \
    SubscriptionFilterPattern="?ERROR ?FATAL ?CRITICAL"
```

Filter patterns follow [CloudWatch Logs filter syntax](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntax.html):
- `?ERROR ?FATAL` -- matches lines containing ERROR *or* FATAL
- `"OutOfMemoryError"` -- matches the exact string
- `{ $.level = "ERROR" }` -- JSON pattern matching (for structured logs)
- `""` (empty string) -- matches everything (not recommended, very noisy)

**Limitation:** CloudFormation supports one subscription filter per stack. If you need filters on multiple log groups, deploy multiple stacks with different names:

```bash
# Stack for API logs
aws cloudformation deploy --stack-name flare-api \
  --template-file template.yaml --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    LogGroupPatterns="/aws/lambda/api-*" \
    NotificationEmail=api-team@example.com \
    EnableSubscription=true \
    SubscriptionLogGroup=/aws/lambda/api-gateway

# Stack for worker logs
aws cloudformation deploy --stack-name flare-workers \
  --template-file template.yaml --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    LogGroupPatterns="/aws/ecs/workers/*" \
    NotificationEmail=platform-team@example.com \
    EnableSubscription=true \
    SubscriptionLogGroup=/aws/ecs/workers/processor
```

## Step 3: Configure Log Group Patterns

The `LogGroupPatterns` parameter accepts exact names and prefix patterns (trailing `*`):

| Pattern | What it matches |
|---------|----------------|
| `/aws/lambda/*` | All Lambda function log groups |
| `/aws/ecs/my-cluster/*` | All ECS tasks in a specific cluster |
| `/aws/rds/*` | All RDS instance log groups |
| `/my-app/api` | One specific log group (exact match) |
| `/aws/lambda/*,/aws/ecs/*` | All Lambda and ECS log groups |

Patterns are resolved at invocation time, so new log groups that match are automatically picked up without redeploying.

**Common AWS log group naming conventions:**

| Service | Log group pattern |
|---------|-------------------|
| Lambda | `/aws/lambda/<function-name>` |
| ECS | `/aws/ecs/<cluster-name>/<service-name>` |
| RDS | `/aws/rds/instance/<instance-id>/<log-type>` |
| API Gateway | `/aws/apigateway/<api-id>/<stage>` |
| CloudTrail | `aws-cloudtrail-logs-<account-id>-<id>` |
| VPC Flow Logs | `/aws/vpc/flowlogs` |
| AppRunner | `/aws/apprunner/<service-name>/<service-id>` |

## Step 4: Notifications

Flare publishes analysis results to an SNS topic. By default it creates an email subscription, but SNS supports many delivery methods.

### Email (default)

Set `NotificationEmail` in your deploy command. Confirm the subscription via the email you receive.

### Slack

After deploying, add an SNS subscription for your Slack webhook:

```bash
TOPIC_ARN=$(aws cloudformation describe-stacks \
  --stack-name flare \
  --query 'Stacks[0].Outputs[?OutputKey==`FlareSNSTopicArn`].OutputValue' \
  --output text)

aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol https \
  --notification-endpoint https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

### PagerDuty

Use PagerDuty's [SNS integration](https://support.pagerduty.com/main/docs/aws-cloudwatch-integration-guide):

```bash
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol https \
  --notification-endpoint https://events.pagerduty.com/integration/YOUR_KEY/enqueue
```

### Multiple Channels

You can add as many subscriptions to the SNS topic as you want. For example, email for the on-call engineer and Slack for the team channel.

## Tuning

### Token Budget

By default, Flare uses the full model context window. If you want to reduce Bedrock costs, set a token budget:

```bash
--parameter-overrides TokenBudget=100000  # 100K tokens max
```

When logs exceed the budget, Cordon automatically reduces them to the most anomalous sections. When they fit, Cordon is skipped entirely (faster and cheaper).

### Cordon Parameters

| Parameter | Default | When to change |
|-----------|---------|----------------|
| `CordonWindowSize` | `4` | Increase to 8-10 for verbose logs with long stack traces |
| `CordonKNeighbors` | `5` | Increase for very large log files (10K+ lines) for better anomaly detection |

### Healthy Scan Suppression

On scheduled scans, if Flare determines the logs are healthy, it skips the notification. You only get emailed when something is worth investigating. Alarm and subscription triggers always notify, since those fired for a reason.

## Updating

To change configuration, re-run the deploy command with new parameters. CloudFormation updates the stack in place:

```bash
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name flare \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    LogGroupPatterns="/aws/lambda/*,/aws/ecs/*" \
    NotificationEmail=you@example.com \
    ScheduleExpression="rate(15 minutes)" \
    EnableAlarmTrigger=true
```

## Step 5: Voice Pipeline (Optional)

Flare can call the on-call engineer by phone when an incident is detected, deliver the RCA briefing via Nova 2 Sonic speech-to-speech, and support interactive voice investigation -- all powered by Nova Sonic.

The voice pipeline is deployed as a separate CloudFormation stack. First deploy the base stack (Step 1), then deploy the voice stack:

```bash
make deploy-voice \
  ONCALL_PHONE="+15551234567" \
  LOG_GROUP_PATTERNS="/aws/lambda/*"
```

This provisions Amazon Connect (instance + phone number), a Lex V2 bot with Nova 2 Sonic S2S, a contact flow, and a DynamoDB table for incident state and pre-fetched investigation data. The Makefile also configures Nova Sonic on the bot and wires up the fulfillment Lambda automatically.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ONCALL_PHONE` | *required* | On-call engineer's phone number (E.164 format, e.g., `+15551234567`) |
| `LOG_GROUP_PATTERNS` | *required* | Must match the base stack's log group patterns |
| `CONNECT_INSTANCE_ID` | `""` | Reuse an existing Connect instance (leave empty to create one) |

The only prerequisite beyond the base stack is enabling Nova 2 Sonic model access in Bedrock. See the [Voice Setup Guide](voice-setup-guide.md) for details.

The SNS notification is always sent regardless of whether the voice pipeline is enabled.

## Teardown

```bash
make teardown-all    # tears down voice stack first, then base stack
```

Or individually:

```bash
make teardown-voice  # voice stack only (Connect, Lex, DynamoDB)
make teardown        # base stack only (Lambda, SNS, EventBridge rules)
```

This removes all Flare resources including the Connect instance, phone number, Lex bot, Lambda functions, DynamoDB table, and IAM roles. It does not affect your log groups or alarms.
