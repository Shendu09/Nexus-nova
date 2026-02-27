# Voice Setup Guide

Step-by-step instructions for the manual AWS console work required by Phase 0 (Prerequisites) and Phase 2a (Lex Bot + Nova Sonic). These steps cannot be automated via SAM/CloudFormation and must be done through the AWS console.

**Region**: All resources must be created in **us-east-1** (N. Virginia). Nova 2 Sonic and Connect's native Nova Sonic integration are only available in us-east-1 and us-west-2.

**Time estimate**: 1-2 hours for Phase 0, 2-3 hours for Phase 2a.

---

## Phase 0: Prerequisites

### 0.1 Request Hackathon Credits

1. Go to the [Amazon Nova AI Hackathon](https://amazon-nova.devpost.com/) Devpost page
2. Follow the instructions to request $100 in AWS credits (deadline: March 13, 2026)
3. Apply the credits to your AWS account via the [AWS Credits page](https://console.aws.amazon.com/billing/home#/credits)

### 0.2 Enable Nova Model Access in Bedrock

1. Open the [Amazon Bedrock console](https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess) in us-east-1
2. Click **Manage model access** (or **Model access** in the left nav)
3. Enable these models (check the box next to each, then click **Save changes**):
   - `Amazon Nova 2 Lite` -- required for log analysis
   - `Amazon Nova Multimodal Embeddings` -- already enabled for Cordon
   - `Amazon Nova 2 Sonic` -- **new, required for voice**
4. Wait for status to show "Access granted" (usually instant, can take up to a few minutes)

### 0.3 Create an Amazon Connect Instance

1. Open the [Amazon Connect console](https://console.aws.amazon.com/connect/home?region=us-east-1)
2. Click **Create instance**
3. Configure the instance:
   - **Identity management**: Select **Store users within Amazon Connect**
   - **Instance alias**: Enter `flare-voice` (or any unique name)
   - Click **Next**
4. **Administrator**:
   - Enter your name, username, password, and email
   - Click **Next**
5. **Telephony**:
   - Check **I want to handle incoming calls with Amazon Connect** (needed for the contact flow)
   - Check **I want to make outbound calls with Amazon Connect** (critical for our use case)
   - Click **Next**
6. **Data storage**: Leave defaults, click **Next**
7. **Review and create**: Verify settings, click **Create instance**
8. Wait 1-3 minutes for the instance to be created

Record these values -- you'll need them for `template.yaml` parameters:
- **Instance ID**: Found in the instance overview page URL, e.g., `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **Instance ARN**: Shown on the instance overview page

### 0.4 Enable Lex Bot Management in Connect

1. From the Amazon Connect console, click your instance alias
2. In the left nav, go to **Flows**
3. Under **Amazon Lex**, check:
   - **Enable Lex Bot Management in Amazon Connect**
   - **Enable Bot Analytics and Transcripts in Amazon Connect** (optional but useful for debugging)
4. Click **Save**

### 0.5 Claim a Phone Number

1. Log in to your Connect instance by clicking the **Access URL** (e.g., `https://flare-voice.my.connect.aws/`)
2. In the Connect admin site left nav, go to **Channels** > **Phone numbers**
3. Click **Claim a number**
4. Select the **DID (Direct Inward Dialing)** tab
5. Select **United States (+1)** as the country
6. Optionally enter an area code to filter results
7. Select any available number from the list
8. Enter description: `Flare outbound calling`
9. For **Flow / IVR**, select `Default customer queue` (we'll change this later)
10. Click **Save**

Record the phone number you claimed (E.164 format, e.g., `+12025551234`). This becomes the `ConnectPhoneNumber` parameter.

### 0.6 Create a Basic Test Contact Flow

1. In the Connect admin site, go to **Routing** > **Flows**
2. Click **Create flow**
3. Name it: `Flare Test Flow`
4. In the flow designer:
   - Drag a **Set voice** block onto the canvas
     - Configure: Voice = **Matthew**, Language = **English (US)**
     - Connect the Entry block to this
   - Drag a **Play prompt** block
     - Configure: Text-to-speech = `Hello, this is a test call from Flare. Goodbye.`
     - Connect the Set voice block's Success output to this
   - Drag a **Disconnect** block
     - Connect the Play prompt block's Ok output to this
5. Click **Save**, then **Publish**
6. Note the **Contact Flow ID** from the URL or the "Show additional flow information" dropdown:
   - Format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

### 0.7 Associate the Phone Number with the Test Flow

1. Go to **Channels** > **Phone numbers**
2. Click the phone number you claimed
3. Change the **Flow / IVR** dropdown to `Flare Test Flow`
4. Click **Save**

### 0.8 Test Outbound Calling

Test from the AWS CLI (not the Connect console) to verify the API path works:

```bash
aws connect start-outbound-voice-contact \
  --instance-id "YOUR_INSTANCE_ID" \
  --contact-flow-id "YOUR_TEST_FLOW_ID" \
  --destination-phone-number "+1YOUR_CELL_PHONE" \
  --source-phone-number "+1YOUR_CLAIMED_DID" \
  --region us-east-1
```

Replace the placeholder values:
- `YOUR_INSTANCE_ID`: From step 0.3
- `YOUR_TEST_FLOW_ID`: From step 0.6
- `+1YOUR_CELL_PHONE`: Your personal phone number in E.164 format
- `+1YOUR_CLAIMED_DID`: The Connect DID from step 0.5

**Expected result**: Your phone rings. When you answer, you hear "Hello, this is a test call from Flare. Goodbye." and the call disconnects.

If this works, Phase 0 is complete. You now have a working Connect instance with outbound calling.

### 0.9 Associate Lambda Functions with Connect

Before the Lambda functions can be invoked from a contact flow, they must be registered with the Connect instance:

1. Open the [Amazon Connect console](https://console.aws.amazon.com/connect/home?region=us-east-1)
2. Click your instance alias
3. In the left nav, go to **Flows**
4. Scroll down to **AWS Lambda**
5. In the **Function** dropdown, search for and select `flare-voice-YOUR_STACK_NAME` (the voice handler Lambda deployed by SAM)
6. Click **+ Add Lambda Function**

This grants Connect permission to invoke the Lambda. You can do this step after deploying the SAM stack (Phase 1), but it must be done before Phase 2.

### 0.10 Deploy the Flare Stack with Voice Enabled

Now deploy (or update) the Flare SAM stack with the Connect parameters:

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
    AlarmNamePrefix=prod- \
    ConnectEnabled=true \
    ConnectInstanceId="YOUR_INSTANCE_ID" \
    ConnectContactFlowId="YOUR_CONTACT_FLOW_ID" \
    ConnectPhoneNumber="+1YOUR_CLAIMED_DID" \
    OncallPhone="+1YOUR_CELL_PHONE"
```

After deployment, go back to step 0.9 and associate the newly created voice handler Lambda with Connect.

---

## Phase 2a: Create the Lex Bot with Nova 2 Sonic

### 2a.1 Create the Conversational AI Bot

1. Log in to your Connect instance admin site
2. In the left nav, go to **Bots**
3. Click **+ Add bot**
4. Configure:
   - **Bot name**: `FlareCommander`
   - **Description**: `Voice incident commander for Flare`
   - **Session timeout**: `5 minutes` (enough for an incident investigation)
   - **COPPA**: Select `No` (not directed at children)
5. Click **Create**

### 2a.2 Configure Nova 2 Sonic Speech-to-Speech

1. In the bot, go to the **Configuration** tab
2. Click the **English (US)** locale (or create it if it doesn't exist)
3. In the **Speech model** section, click **Edit**
4. In the Speech model modal:
   - Open the **Model type** dropdown and select **Speech-to-Speech**
   - Open the **Voice provider** dropdown and select **Amazon Nova Sonic**
5. Click **Confirm**
6. The Speech model card should now show: `Speech-to-Speech: Amazon Nova Sonic`

### 2a.3 Configure the System Prompt

1. Still in the bot's locale configuration, find the **System prompt** section
2. Enter the following system prompt (or similar):

```
You are Flare, an AI incident commander helping an on-call engineer investigate an active infrastructure incident. The engineer has just been briefed on the initial analysis.

Be conversational and concise. Speak in short, clear sentences. When reporting metrics or data, lead with the key finding, then give supporting details only if asked. Use natural phrasing like "looks like" and "here's what I see" rather than formal language.

When the engineer asks about a resource, metric, or service, use the appropriate tool to retrieve data. If you don't have data for something, say so honestly.

All operations are read-only. You can investigate but not take remediation actions. If asked to fix something, explain that you're designed for investigation only as a safety feature.
```

### 2a.4 Create Intents

Create the following intents in the bot. For each one, add 10-15 sample utterances that an engineer might say.

#### Intent: CheckMetrics

Sample utterances:
- Check the metrics for {resource}
- What are the error rates?
- How's the CPU looking on {resource}?
- Show me the connection count for {resource}
- What's the latency on {resource}?
- Does {resource} look overwhelmed?
- Are there any metric spikes?
- Check {metric} for {resource}
- How's {resource} performing?
- What do the metrics show?
- Pull up the {metric} data
- Is {resource} under heavy load?

Slots:
- `resource` (Type: `AMAZON.AlphaNumeric`, Prompt: "Which resource should I check?", Required: No)
- `metric` (Type: `AMAZON.AlphaNumeric`, Prompt: "Which metric?", Required: No)

Fulfillment: **Active** -- select the `flare-voice-*` Lambda function.

#### Intent: CheckLogs

Sample utterances:
- Show me recent logs for {service}
- Any errors in the logs?
- What do the {service} logs show?
- Pull up the logs for {service}
- Are there error logs?
- Check the {log_group} logs
- What errors are showing up?
- Show me what's in the logs
- Any connection errors in the logs?
- What's the log output for {service}?

Slots:
- `service` (Type: `AMAZON.AlphaNumeric`, Prompt: "Which service's logs?", Required: No)
- `log_group` (Type: `AMAZON.AlphaNumeric`, Required: No)

Fulfillment: **Active** -- select the `flare-voice-*` Lambda function.

#### Intent: CheckStatus

Sample utterances:
- Is {resource} healthy?
- What's the status of {resource}?
- Is {resource} running?
- Check if {resource} is up
- How's {resource} doing?
- Is the {resource} instance OK?
- What's the health of {resource}?
- Is {resource} responding?
- Check the status of {resource}

Slots:
- `resource` (Type: `AMAZON.AlphaNumeric`, Prompt: "Which resource?", Required: No)
- `resource_type` (Type: `AMAZON.AlphaNumeric`, Required: No)

Fulfillment: **Active** -- select the `flare-voice-*` Lambda function.

#### Intent: Summarize

Sample utterances:
- Give me a summary
- What do we know so far?
- Summarize the situation
- What's the current status?
- Walk me through what happened
- Recap the incident
- What's the big picture?
- Give me the rundown

Slots: None required.

Fulfillment: **Active** -- select the `flare-voice-*` Lambda function.

#### FallbackIntent (built-in)

1. Select the built-in **FallbackIntent**
2. Enable fulfillment: **Active** -- select the `flare-voice-*` Lambda function
3. This is critical: any question that doesn't match a specific intent will still be sent to the fulfillment Lambda with all cached data, letting Nova Lite reason about it

### 2a.5 Build the Bot

1. After creating all intents, click **Build** in the top right
2. Wait for the build to complete (usually 30-60 seconds)
3. The status should show "Built" with a green check

### 2a.6 Create a Bot Version and Alias

1. Go to the **Versions** tab, click **Create version**
2. Enter description: `v1 - initial release`, click **Create**
3. Go to the **Aliases** tab, click **Create alias**
4. Name: `live`
5. Select the version you just created
6. Check **Enable for use in flow and flow modules** (critical for Connect integration)
7. Under **Lambda function**, select the `flare-voice-*` Lambda for the English (US) locale
8. Click **Create**

### 2a.7 Create the Production Contact Flow

Now create the real contact flow that reads the RCA and hands off to the Lex bot.

1. In the Connect admin site, go to **Routing** > **Flows**
2. Click **Create flow**
3. Name it: `Flare Incident Commander`
4. Build the flow with these blocks connected in sequence:

**Block 1: Set voice**
- Voice: **Matthew**
- Language: **English (US)**
- Speaking style: **Generative** (under Override speaking style)

**Block 2: Invoke AWS Lambda** (briefing)
- Function: `flare-voice-YOUR_STACK_NAME`
- Function input parameters: Add an attribute:
  - Destination key: `handler`
  - Value: Set manually, value = `briefing`
- Set the Contact Attribute mapping for the response:
  - After the Lambda block, add a **Set contact attributes** block
  - Map `$.External.rca_summary` to user-defined attribute `rca_summary`
  - Map `$.External.severity` to user-defined attribute `severity`
  - Map `$.External.affected` to user-defined attribute `affected`

**Block 3: Play prompt** (RCA briefing)
- Text-to-speech (SSML):

```xml
<speak>
  Hi, this is Flare, your incident commander.
  <break time="500ms"/>
  We detected a <emphasis level="strong">$.Attributes.severity</emphasis> severity incident
  affecting $.Attributes.affected.
  <break time="300ms"/>
  $.Attributes.rca_summary
  <break time="500ms"/>
  I'm available to help investigate. What would you like to know?
</speak>
```

Note: Replace `$.Attributes.*` with the actual Connect attribute reference syntax in the flow designer. Use "Interpret as" > SSML.

**Block 4: Get customer input** (Lex bot)
- Select **Amazon Lex**
- Bot: `FlareCommander`
- Alias: `live`
- Session attributes:
  - Key: `incident_id`, Value: `$.Attributes.incident_id` (from the initial contact attributes passed by StartOutboundVoiceContact)

**Block 5: Error handling**
- Connect the Error outputs from the Lambda block and the Get Customer Input block to a Play prompt:
  - Text: `Sorry, I encountered a technical issue. The incident analysis has been sent to your email.`
- Then connect to a **Disconnect** block

**Block 6: Disconnect**
- Connect the Get Customer Input "Default" and "Timeout" outputs here

5. Click **Save**, then **Publish**
6. Note the new Contact Flow ID

### 2a.8 Update the Phone Number Flow Assignment

1. Go to **Channels** > **Phone numbers**
2. Click your claimed phone number
3. Change **Flow / IVR** to `Flare Incident Commander`
4. Click **Save**

### 2a.9 Update the SAM Stack with the Production Flow ID

If the contact flow ID changed from the test flow:

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
    AlarmNamePrefix=prod- \
    ConnectEnabled=true \
    ConnectInstanceId="YOUR_INSTANCE_ID" \
    ConnectContactFlowId="YOUR_NEW_FLOW_ID" \
    ConnectPhoneNumber="+1YOUR_CLAIMED_DID" \
    OncallPhone="+1YOUR_CELL_PHONE"
```

### 2a.10 Test the Full Voice Flow

Test via CLI:

```bash
aws connect start-outbound-voice-contact \
  --instance-id "YOUR_INSTANCE_ID" \
  --contact-flow-id "YOUR_PRODUCTION_FLOW_ID" \
  --destination-phone-number "+1YOUR_CELL_PHONE" \
  --source-phone-number "+1YOUR_CLAIMED_DID" \
  --attributes '{"incident_id": "TEST_INCIDENT_ID"}' \
  --region us-east-1
```

For this to work, you need a test incident in DynamoDB. Either trigger a real alarm or insert a test record:

```bash
aws dynamodb put-item \
  --table-name flare-incidents-YOUR_STACK_NAME \
  --item '{
    "incident_id": {"S": "TEST_INCIDENT_ID"},
    "rca": {"S": "STATUS: High\nSUMMARY: Connection pool exhaustion on auth-db.\nAFFECTED COMPONENTS: auth-service, api-gateway"},
    "alarm_name": {"S": "test-alarm"},
    "trigger_type": {"S": "alarm"},
    "timestamp": {"S": "2026-02-27T12:00:00Z"},
    "prefetch_status": {"S": "complete"},
    "cached_data": {"S": "{\"metrics\": [{\"query_key\": \"Test metric\", \"datapoints\": [{\"value\": 95}]}], \"logs\": [], \"status\": []}"}
  }' \
  --region us-east-1
```

**Expected result**: Your phone rings. You hear Flare read the RCA briefing. Then you can ask follow-up questions and Nova Sonic responds using the Lex bot with the fulfillment Lambda.

---

## Teardown

When you're done with the hackathon, tear down Connect resources to stop charges:

```bash
# Delete the Connect instance (removes phone number, flows, bots)
aws connect delete-instance \
  --instance-id "YOUR_INSTANCE_ID" \
  --region us-east-1

# Delete the Flare stack
aws cloudformation delete-stack \
  --stack-name flare \
  --region us-east-1
```

The DID phone number charge ($0.03/day) stops immediately when the instance is deleted. Nova Sonic charges are included in Connect's per-minute pricing, so there are no lingering Bedrock costs.

---

## Troubleshooting

### "Nova Sonic not available in Speech model dropdown"

- Ensure your instance is in **us-east-1** or **us-west-2**
- Ensure Nova 2 Sonic model access is enabled in Bedrock (step 0.2)
- Try refreshing the page or logging out and back in
- If still not visible, the feature may require an AWS support request for your account

### "StartOutboundVoiceContact returns AccessDeniedException"

- Verify the Lambda execution role has `connect:StartOutboundVoiceContact` permission
- Verify the phone number is claimed and associated with the correct Connect instance
- Verify the contact flow is published (not just saved)

### "Lambda not appearing in Connect's Lambda dropdown"

- The Lambda must be in the same region as the Connect instance (us-east-1)
- The Lambda function must have a resource-based policy allowing Connect to invoke it -- the SAM template handles this via `FlareVoiceHandlerConnectPermission`

### "Lex bot not responding / silent after RCA briefing"

- Check that the bot is built (not in "Unbuilt changes" state)
- Check that the alias has "Enable for use in flow and flow modules" checked
- Verify the flow uses the correct bot name and alias
- Check that the Set voice block uses **Generative** speaking style (required for Nova Sonic)
- Check CloudWatch Logs for the voice handler Lambda for errors

### "Fulfillment Lambda timeout"

- Check that `incident_id` is being passed via session attributes in the Get Customer Input block
- Verify the DynamoDB table name matches the `INCIDENTS_TABLE_NAME` environment variable
- Check if cached_data is populated (prefetch_status = "complete") in DynamoDB
