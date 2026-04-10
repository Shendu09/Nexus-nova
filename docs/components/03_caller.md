# Caller Module

## Overview
Handles Amazon Connect integration for voice communication.

## Capabilities
- On-call engineer notification
- Voice briefing delivery
- Interactive investigation support
- Call routing and management

## Configuration
```python
connect_instance = "your-instance-id"
phone_number = "+1234567890"
```

## Methods
- `initiate_call()` - Start outbound call
- `transfer_call()` - Transfer between agents
- `end_call()` - Terminate call
