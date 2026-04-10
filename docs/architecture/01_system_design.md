# System Architecture

## Overview
Nexus is a serverless, event-driven log analysis and remediation system built on AWS.

## Architecture Diagram
```
┌─────────────────────────────────────────────────────┐
│ Event Sources                                       │
├─────────────────────────────────────────────────────┤
│ • CloudWatch Alarms    • EventBridge           │
│ • Log Subscriptions     • Direct Invocations    │
└────────────────┬────────────────────────────────────┘
                 │
                 v
         ┌──────────────────┐
         │  Lambda Handler  │
         │   (Nexus Main)   │
         └─────────┬────────┘
                   │
            ┌──────┴──────────────────┐
            │                         │
            v                         v
    ┌──────────────────┐    ┌──────────────────┐
    │ CloudWatch Logs  │    │  Analyzer        │
    │ (Log Retrieval)  │    │  (Cordon + Nova) │
    └──────────────────┘    └────────┬─────────┘
                                     │
                            ┌────────v─────────┐
                            │ Triage System    │
                            │ (RCA via Nova 2) │
                            └────────┬─────────┘
                                     │
            ┌────────────┬───────────┼───────────┬─────────┐
            │            │           │           │         │
            v            v           v           v         v
        SNS         PagerDuty    Slack      DynamoDB   Connect
      (Email)    (Incidents)   (Webhook)   (Cache)   (Voice)
```

## Components

### Lambda Function
- Entry point for all events
- Orchestrates pipeline
- Error handling and retries

### Log Analysis
- CloudWatch Logs integration
- Token budget optimization
- Semantic anomaly detection via Cordon

### RCA Engine
- Nova 2 Lite reasoning model
- Root cause identification
- Recommendation generation

### Voice System
- Amazon Connect integration
- Nova 2 Sonic for speech
- Interactive investigation

### Notification Hub
- Multi-channel distribution
- SNS, Slack, PagerDuty, SMS
- Delivery tracking

### Data Layer
- DynamoDB for session storage
- Cache for prefetched data
- Metrics and analytics

## Data Flow

### Normal Execution
1. Event arrives (CloudWatch, EventBridge)
2. Lambda function invoked
3. Extract logs from CloudWatch
4. Plan token budget
5. Analyze with Cordon/Nova Embeddings
6. Send anomalous sections to Nova 2 Lite
7. Generate RCA report
8. Send notifications
9. Optional: Initiate voice callout

### Voice Investigation Flow
1. Prefetch system prepares likely answers
2. Amazon Connect initiates call
3. Engineer receives briefing
4. Nova 2 Sonic handles conversation
5. Retrieve prefetched or fresh data
6. Generate voice responses
7. End call, store session

## Scalability
- Serverless: Auto-scales with demand
- Databases: DynamoDB on-demand billing
- Log processing: Batch and parallel where possible
- Voice: Multiple concurrent calls supported

## Security
- IAM roles and policies
- Encryption in transit (TLS)
- VPC private endpoints (optional)
- CloudTrail logging
- Secrets Manager for sensitive data

## Cost Optimization
- Lambda: Efficient code, proper timeouts
- DynamoDB: On-demand billing
- Bedrock: Pay-per-token for models
- CloudWatch: Log retention policies
