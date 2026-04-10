# Logs API Reference

## Functions

### get_logs(log_group, start_time, end_time)
Retrieve logs from CloudWatch.

**Parameters:**
- `log_group` (str): Log group name
- `start_time` (int): Unix timestamp (ms)
- `end_time` (int): Unix timestamp (ms)

**Returns:**
- `list`: List of log events

### filter_logs(logs, pattern, include=True)
Apply pattern-based filtering to logs.

**Parameters:**
- `logs` (list): Input logs
- `pattern` (str): Filter pattern
- `include` (bool): Include/exclude matching

**Returns:**
- `list`: Filtered logs

### parse_log_events(raw_events)
Parse raw CloudWatch events.

**Parameters:**
- `raw_events` (list): Raw events from API

**Returns:**
- `list`: Parsed event objects

### batch_get_logs(log_group, time_ranges)
Retrieve logs in time batches.

**Parameters:**
- `log_group` (str): Log group
- `time_ranges` (list): List of (start, end) tuples

**Returns:**
- `list`: Combined logs from all ranges

## Exceptions
- `LogGroupNotFound`
- `AccessDenied`
- `ThrottlingException`
