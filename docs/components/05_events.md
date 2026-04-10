# Event Processing

## Overview
Handles various AWS event sources that trigger the Nexus pipeline.

## Supported Events
- CloudWatch Alarms
- EventBridge Scheduled Rules
- SNS Subscriptions
- Direct Lambda Invocations

## Event Structure
```json
{
  "source": "aws.cloudwatch",
  "detail-type": "CloudWatch Alarm",
  "detail": {
    "alarmName": "my-alarm",
    "state": {"value": "ALARM"}
  }
}
```

## Processing Functions
- `parse_event()` - Parse incoming event
- `extract_logs()` - Extract log group info
- `route_event()` - Route to appropriate handler
