# Configuration Module

## Overview
Centralized configuration management for Nexus environment.

## Environment Variables
- `BEDROCK_REGION` - AWS region
- `LOG_GROUP` - CloudWatch log group
- `DYNAMODB_TABLE` - Session storage table
- `SNS_TOPIC` - Notification topic
- `CONNECT_INSTANCE_ID` - Amazon Connect instance

## Settings
```python
DEBUG = False
TIMEOUT = 300
MAX_LOGS = 10000
```

## Configuration Methods
- `load_from_env()` - Load from environment
- `load_from_file()` - Load from config file
- `validate()` - Validate configuration
