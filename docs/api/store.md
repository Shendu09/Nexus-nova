# Store API Reference

## Functions

### create_session(session_data)
Create new session record.

**Parameters:**
- `session_data` (dict): Session information

**Returns:**
- `str`: Session ID

### update_session(session_id, updates)
Update existing session.

**Parameters:**
- `session_id` (str): Session ID
- `updates` (dict): Fields to update

**Returns:**
- `bool`: Update success

### get_session(session_id)
Retrieve session by ID.

**Parameters:**
- `session_id` (str): Session ID

**Returns:**
- `dict`: Session object

### cache_result(cache_key, data, ttl=3600)
Store temporary analysis result.

**Parameters:**
- `cache_key` (str): Cache key
- `data` (dict): Data to cache
- `ttl` (int): Time to live

**Returns:**
- `bool`: Cache success

### delete_session(session_id)
Delete session and associated data.

**Parameters:**
- `session_id` (str): Session ID

**Returns:**
- `bool`: Deletion success

## Tables
- `nexus-sessions` - Active sessions
- `nexus-cache` - Temporary cache
- `nexus-metrics` - Performance metrics
