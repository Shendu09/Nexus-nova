# Voice Setup Guide

Flare's voice pipeline -- Amazon Connect, Lex V2 with Nova 2 Sonic speech-to-speech, and the contact flow -- is fully automated via CloudFormation. No manual console setup is required.

**Region**: All resources are created in the deployment region. Nova 2 Sonic requires **us-east-1** or **us-west-2**.

**Time estimate**: ~5 minutes (deploy command + wait for provisioning).

---

## Prerequisites

1. **Enable Nova model access in Bedrock**

   Open the [Amazon Bedrock console](https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess) in us-east-1 and enable:
   - Amazon Nova 2 Lite (log analysis)
   - Amazon Nova Multimodal Embeddings (Cordon anomaly detection)
   - Amazon Nova 2 Sonic (voice conversation)

   Click **Save changes** and wait for "Access granted" status.

2. **AWS CLI configured** with credentials that have permissions to create CloudFormation stacks, Connect instances, and Lex bots.

---

## Deploy

```bash
make deploy \
  EMAIL=oncall@example.com \
  LOG_GROUP_PATTERNS="/aws/lambda/*" \
  ENABLE_ALARM=true \
  CONNECT_ENABLED=true \
  ONCALL_PHONE="+15551234567"
```

Or directly with CloudFormation:

```bash
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name flare \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    LogGroupPatterns="/aws/lambda/*" \
    NotificationEmail=oncall@example.com \
    EnableAlarmTrigger=true \
    ConnectEnabled=true \
    OncallPhone="+15551234567"
```

This single command provisions everything:

| Resource | What it creates |
|----------|----------------|
| Amazon Connect instance | Outbound calling enabled, managed identity |
| US DID phone number | Claimed automatically, used as caller ID |
| Lex V2 bot | FlareCommander with Nova 2 Sonic S2S, intents, and utterances |
| Contact flow | Set Voice, Lambda briefing, Polly RCA, Lex handoff, error handling |
| Integration associations | Lambda and Lex bot wired to the Connect instance |
| DynamoDB table | Incident state and pre-fetched investigation cache |

The only user-provided value is `OncallPhone` -- the phone number to call when an incident is detected.

---

## Verify

After deployment, check the stack outputs:

```bash
aws cloudformation describe-stacks \
  --stack-name flare \
  --query 'Stacks[0].Outputs' \
  --output table
```

You should see:
- `FlareConnectInstanceId` -- the provisioned Connect instance
- `FlarePhoneNumberAddress` -- the claimed DID number
- `FlareBotId` -- the Lex bot ID

## Test

Trigger a test call using the stack outputs:

```bash
INSTANCE_ID=$(aws cloudformation describe-stacks --stack-name flare \
  --query 'Stacks[0].Outputs[?OutputKey==`FlareConnectInstanceId`].OutputValue' --output text)

FLOW_ARN=$(aws cloudformation describe-stacks --stack-name flare \
  --query 'Stacks[0].Outputs[?OutputKey==`FlareContactFlowArn`].OutputValue' --output text)

PHONE=$(aws cloudformation describe-stacks --stack-name flare \
  --query 'Stacks[0].Outputs[?OutputKey==`FlarePhoneNumberAddress`].OutputValue' --output text)

aws connect start-outbound-voice-contact \
  --instance-id "$INSTANCE_ID" \
  --contact-flow-id "$FLOW_ARN" \
  --destination-phone-number "+1YOUR_CELL_PHONE" \
  --source-phone-number "$PHONE" \
  --attributes '{"incident_id": "test"}' \
  --region us-east-1
```

For a full end-to-end test, trigger a real alarm or insert a test incident into DynamoDB:

```bash
TABLE=$(aws cloudformation describe-stacks --stack-name flare \
  --query 'Stacks[0].Outputs[?OutputKey==`FlareIncidentsTableName`].OutputValue' --output text)

aws dynamodb put-item \
  --table-name "$TABLE" \
  --item '{
    "incident_id": {"S": "test-001"},
    "rca": {"S": "STATUS: High\nSUMMARY: Connection pool exhaustion on auth-db."},
    "alarm_name": {"S": "test-alarm"},
    "trigger_type": {"S": "alarm"},
    "timestamp": {"S": "2026-02-27T12:00:00Z"},
    "prefetch_status": {"S": "complete"},
    "cached_data": {"S": "{\"metrics\": [], \"logs\": [], \"status\": []}"}
  }' \
  --region us-east-1
```

---

## Teardown

```bash
make teardown
```

This deletes everything: the CloudFormation stack, Connect instance, phone number, Lex bot, DynamoDB table, and all Lambda functions. No lingering charges.

---

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ConnectEnabled` | `false` | Toggle the entire voice pipeline on/off |
| `OncallPhone` | `""` | Engineer's phone number in E.164 format (e.g., `+15551234567`) |

All Connect and Lex resources are provisioned automatically when `ConnectEnabled=true`. No instance IDs, flow IDs, or phone numbers need to be provided.

---

## What Gets Created

When `ConnectEnabled=true`, the template provisions:

- **`FlareConnectInstance`** -- Amazon Connect instance with outbound calling
- **`FlarePhoneNumber`** -- US DID number claimed and attached to the instance
- **`FlareBot`** -- Lex V2 bot with Nova 2 Sonic speech-to-speech, five intents (CheckMetrics, CheckLogs, CheckStatus, Summarize, FallbackIntent), and a "live" alias
- **`FlareContactFlow`** -- Contact flow that reads the RCA via Polly, then hands off to the Lex bot for interactive investigation
- **`FlareLambdaAssociation`** / **`FlareLexAssociation`** -- Integration associations wiring the Lambda and Lex bot to the Connect instance
- **`FlareIncidentsTable`** -- DynamoDB table for incident state and pre-fetched investigation cache

All resources are conditional on `ConnectEnabled` and are fully torn down with `make teardown`.

---

## Troubleshooting

### "CREATE_FAILED on FlareConnectInstance"

- Connect instance creation is rate-limited (limited operations per 30-day window). If you've been creating/deleting instances frequently, wait and retry.
- The instance alias must be globally unique. If `flare-{stack-name}` is taken, change the stack name.

### "CREATE_FAILED on FlarePhoneNumber"

- DID number availability varies by region. The template requests a US DID; if none are available, the stack will roll back. Retry or try a different region.

### "Nova Sonic not working in the Lex bot"

- Ensure Nova 2 Sonic model access is enabled in Bedrock (prerequisite step 1).
- The template sets `UnifiedSpeechSettings.SpeechFoundationModel.ModelArn` to `amazon.nova-2-sonic-v1:0`. If the model ID changes, update the template.

### "Fulfillment Lambda timeout"

- Check that the DynamoDB table has incident records with `prefetch_status: complete`.
- Check CloudWatch Logs for the `flare-voice-*` Lambda for errors.
