# Handler API Reference

## Function Signature

### handler(event, context)
AWS Lambda handler for Nexus.

**Parameters:**
- `event` (dict): Lambda event object
- `context` (LambdaContext): Lambda context object

**Returns:**
- `dict`: Response with statusCode and body

**Response Format:**
```json
{
    "statusCode": 200,
    "body": {
        "status": "success",
        "sessionId": "session-id",
        "anomalies": [...],
        "rca": {...},
        "voiceCallInitiated": false
    }
}
```

**Error Responses:**
- 400: Bad request (invalid event)
- 403: Unauthorized (missing permissions)
- 500: Internal server error
- 503: Service unavailable

## Processing Steps
1. Parse event
2. Extract logs
3. Initialize session
4. Analyze anomalies
5. Generate RCA
6. Send notifications
7. Optional: Initiate voice call
8. Return response
