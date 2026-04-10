# Budget API Reference

## Functions

### plan_budget(logs, available_tokens)
Create optimal token budget allocation plan.

**Parameters:**
- `logs` (list): Input logs
- `available_tokens` (int): Available token count

**Returns:**
- `dict`: Budget allocation plan

### estimate_tokens(content)
Estimate token count for content.

**Parameters:**
- `content` (str): Content to estimate

**Returns:**
- `int`: Estimated token count

### optimize_content(logs, token_limit)
Optimize content to fit token limit.

**Parameters:**
- `logs` (list): Full log list
- `token_limit` (int): Maximum tokens

**Returns:**
- `list`: Optimized logs

## Configuration
```python
MIN_LOG_SIZE = 100
MAX_COMPRESSION = 0.8
RESERVE_TOKENS = 500
```
