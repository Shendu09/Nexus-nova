# Handler Function

## Overview
AWS Lambda handler entry point for Nexus.

## Function Signature
```python
def handler(event, context):
    """
    Lambda handler for Nexus log triage.
    
    Args:
        event: Lambda event
        context: Lambda context
    
    Returns:
        Response object with status and results
    """
```

## Processing Flow
1. Parse incoming event
2. Extract CloudWatch logs
3. Analyze for anomalies
4. Generate RCA report
5. Send notifications
6. Optionally initiate voice call

## Response Format
```json
{
  "statusCode": 200,
  "body": {
    "processed": true,
    "anomalies": [...],
    "recommendations": [...]
  }
}
```
