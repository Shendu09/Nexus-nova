# Prefetch API Reference

## Functions

### predict_questions(rca_analysis)
Predict follow-up questions based on analysis.

**Parameters:**
- `rca_analysis` (dict): Root cause analysis

**Returns:**
- `list`: Predicted question strings

### prefetch_data(predictions, session_id)
Pre-fetch data for predicted questions.

**Parameters:**
- `predictions` (list): List of predicted questions
- `session_id` (str): Session ID

**Returns:**
- `dict`: Pre-fetched data

### cache_results(data, session_id, ttl=3600)
Store prefetched data in cache.

**Parameters:**
- `data` (dict): Data to cache
- `session_id` (str): Session ID
- `ttl` (int): Cache TTL in seconds

**Returns:**
- `bool`: Cache success

### get_prefetched(session_id, key=None)
Retrieve cached prefetched data.

**Parameters:**
- `session_id` (str): Session ID
- `key` (str): Specific data key (optional)

**Returns:**
- `dict`: Cached data

## Cache Keys
- `metrics` - CloudWatch metrics
- `logs` - Related logs
- `errors` - Error patterns
- `configurations` - Service configs
