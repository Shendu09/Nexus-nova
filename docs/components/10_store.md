# Data Storage

## Overview
DynamoDB integration for session management and state persistence.

## Tables
- `nexus-sessions` - Session state and history
- `nexus-cache` - Cached analysis results
- `nexus-metrics` - Performance metrics

## Schema
```python
sessions = {
    "session_id": "string",
    "alarm_id": "string",
    "created_at": "timestamp",
    "status": "enum",
    "logs": "string",
    "analysis": "json",
    "voice_state": "json"
}
```

## Operations
- `create_session()` - Initialize new session
- `update_session()` - Update session state
- `get_session()` - Retrieve session
- `cache_result()` - Store temporary results

## TTL Management
- Sessions: 24 hours
- Cache: 1 hour
- Metrics: 30 days
