# Events API Reference

## Functions

### parse_event(event)
Parse and normalize incoming AWS event.

**Parameters:**
- `event` (dict): Lambda event

**Returns:**
- `ParsedEvent`: Normalized event object

### extract_log_info(event)
Extract log group and stream from event.

**Parameters:**
- `event` (dict): Lambda event

**Returns:**
- `tuple`: (log_group, log_stream)

### route_event(event)
Determine event handler based on source.

**Parameters:**
- `event` (dict): Lambda event

**Returns:**
- `str`: Handler function name

## Supported Sources
- `aws.cloudwatch` - CloudWatch alarms
- `aws.events` - EventBridge rules
- `aws.logs` - CloudWatch Logs subscriptions
- `direct` - Direct Lambda invocations
