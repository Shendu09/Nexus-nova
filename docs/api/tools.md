# Tools API Reference

## Text Processing

### truncate_text(text, max_length, suffix="...")
Truncate text safely.

**Parameters:**
- `text` (str): Input text
- `max_length` (int): Maximum length
- `suffix` (str): Truncation suffix

**Returns:**
- `str`: Truncated text

### format_json(obj, pretty=True)
Format object as JSON string.

**Parameters:**
- `obj` (dict): Object to format
- `pretty` (bool): Pretty print

**Returns:**
- `str`: JSON string

## Time Utilities

### get_timestamp()
Get current Unix timestamp.

**Returns:**
- `int`: Unix timestamp (ms)

### format_timestamp(ts, format_str=None)
Format timestamp as string.

**Parameters:**
- `ts` (int): Unix timestamp
- `format_str` (str): Format string

**Returns:**
- `str`: Formatted timestamp

## AWS Utilities

### retry_with_backoff(func, max_attempts=3)
Decorator for automatic retry with backoff.

**Parameters:**
- `func`: Function to retry
- `max_attempts`: Maximum retry attempts

**Returns:**
- `object`: Function result

## Decorators
- `@cached` - Cache function results
- `@timed` - Log execution time
- `@validate` - Validate inputs
