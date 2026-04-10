# Nexus Project - Commit History

## Project Overview
Nexus is an AI-powered log triage and voice assistant for AWS.

## Core Components

### Analysis Module (analyzer.py)
- Semantic anomaly detection
- Token budget optimization
- Log analysis pipeline

### Budget System (budget.py)
- Token budget planning
- Cost optimization
- Resource allocation

### Voice Integration (caller.py, voice_handler.py)
- Amazon Connect integration
- Speech-to-speech voice conversation
- Interactive voice investigation

### Configuration (config.py)
- Environment settings
- AWS credentials
- Nova model configuration

### Event Handling (events.py)
- CloudWatch event processing
- EventBridge schedule support
- Subscription filter handling

### Handler (handler.py)
- Lambda function entry point
- Request routing
- Response formatting

### Log Processing (logs.py)
- CloudWatch Logs integration
- Log retrieval and parsing
- Anomaly detection pipeline

### Notification System (notifier.py)
- SNS integration
- Email notifications
- Slack integration
- PagerDuty support

### Prefetch (prefetch.py)
- Predictive data fetching
- Follow-up question handling
- Performance optimization

### Data Storage (store.py)
- DynamoDB integration
- Session management
- State persistence

### Utility Tools (tools.py)
- Helper functions
- Common utilities
- Formatting functions

### Triage System (triage.py)
- Root cause analysis
- Issue classification
- Report generation

## Features
- Real-time log analysis
- Anomaly detection
- Root cause analysis
- Voice-based investigation
- Multi-channel notifications
- Token budget optimization

## Technologies
- Amazon Nova models (Embeddings, Lite, Sonic)
- AWS Lambda
- CloudWatch Logs
- DynamoDB
- Amazon Connect
- SNS

## Deployment
- Docker container support
- AWS Lambda container image
- Infrastructure as Code templates
- CloudFormation support

## Testing
- Comprehensive test suite
- Mocking AWS services
- Unit and integration tests
- Type checking with mypy

## Development
- Python 3.12+
- Pre-commit hooks
- Code formatting with ruff
- Type annotations
