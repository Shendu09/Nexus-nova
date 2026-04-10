# Performance Tuning

## Lambda Optimization

### Memory Configuration
- Minimum: 512MB (slower Python startup)
- Recommended: 1024MB (good balance)
- Maximum: 10240MB (overkill for most cases)

### Trade-offs
```
More Memory = More CPU = Faster Execution = Lower Duration Cost
But: Fixed timeout still applies
```

### Code Optimization
1. Lazy import heavy libraries
2. Connection pooling for AWS APIs
3. Batch CloudWatch Logs calls
4. Cache frequently accessed data

### Monitoring Code Performance
```python
import time

start = time.time()
result = expensive_operation()
duration = time.time() - start
print(f"Operation took {duration}s")
```

## DynamoDB Optimization

### Provisioning
- Use on-demand for unpredictable workloads
- Use provisioned for steady-state
- Monitor consumed capacity

### Query Optimization
- Use partition key in queries
- Minimize returned attributes
- Use batch operations
- Index frequently queried attributes

### TTL Configuration
```python
# DynamoDB TTL for automatic cleanup
session_ttl = int(time.time()) + 86400  # 24 hours
```

## API Call Batching

### CloudWatch Logs
- Max 150 events per request
- Batch similar queries together

### Bedrock Invocation
- Process multiple logs in single invocation
- Optimize prompt size

## Caching Strategy

### Application-level Cache
- Session data in memory
- Prefetched data in DynamoDB
- 1-hour TTL for metrics

### Resultant Cache
- Store RCA results for duplicate events
- Avoid reanalysis of same logs

## Memory Usage Monitoring

```python
import tracemalloc

tracemalloc.start()
# ... operation ...
current, peak = tracemalloc.get_traced_memory()
print(f"Peak memory: {peak / 1024 / 1024:.2f}MB")
```
