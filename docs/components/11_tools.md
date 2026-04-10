# Utility Tools

## Overview
Common utilities and helper functions used throughout Nexus.

## Modules
- `text_processing` - String manipulation
- `time_utils` - Timestamp handling
- `json_utils` - JSON serialization
- `aws_utils` - AWS service helpers
- `error_utils` - Error handling

## Common Functions
- `format_timestamp()` - Timestamp formatting
- `truncate_text()` - Safe string truncation
- `merge_dicts()` - Deep dictionary merge
- `retry_with_backoff()` - Retry decorator
- `parse_lambda_event()` - Event parsing

## Decorators
- `@timed` - Function timing
- `@cached` - Result caching
- `@retry` - Automatic retry
- `@validate` - Input validation
