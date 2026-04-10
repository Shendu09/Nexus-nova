# Usage Examples

## Basic Event Handling

```python
from nexus.handler import handler

event = {
    "source": "aws.cloudwatch",
    "detail-type": "CloudWatch Alarm State Change",
    "detail": {
        "alarmName": "my-alarm",
        "state": {"value": "ALARM"}
    }
}

response = handler(event, {})
print(response)
```

## Direct Analysis

```python
from nexus.analyzer import analyze_logs
from nexus.logs import get_logs

# Fetch logs
logs = get_logs(log_group="my-app", minutes=60)

# Analyze for anomalies
analysis = analyze_logs(logs, token_budget=5000)
print(analysis)
```

## Notifications

```python
from nexus.notifier import send_notification

notification = {
    "type": "rca_report",
    "title": "Critical Issue RCA",
    "body": "Root cause identified...",
    "severity": "critical"
}

send_notification(notification, channels=["email", "slack"])
```

## Voice Callout

```python
from nexus.caller import initiate_call

call_details = {
    "phone_number": "+1234567890",
    "rca_brief": "Issue analyzed...",
    "session_id": "session-123"
}

call_result = initiate_call(call_details)
```
