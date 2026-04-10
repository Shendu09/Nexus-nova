# Monitoring and Metrics

## Key Metrics to Track

### Analysis Metrics
- Log volume processed
- Anomalies detected count
- Analysis confidence average
- Analysis latency (p50, p99)

### Call Metrics (voice)
- Calls initiated count
- Call duration average
- Call success rate
- Voice response latency

### Notification Metrics
- Notifications sent count
- Delivery success rate
- Delivery latency
- Failed notifications count

### System Metrics
- Lambda invocations
- Lambda duration
- Lambda errors
- Cold start frequency
- DynamoDB read/write units

## CloudWatch Dashboard

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Invocations"],
          ["AWS/Lambda", "Duration"],
          ["AWS/Lambda", "Errors"]
        ],
        "period": 300,
        "stat": "Average"
      }
    }
  ]
}
```

## Alarms

### Critical Alarms
- Lambda error rate > 1%
- RCA analysis failure
- Notification delivery failure
- DynamoDB throttling

### Warning Alarms
- P99 latency > 60s
- Cold start rate > 10%
- Cache miss rate > 30%

## Logging Config

```yaml
logging:
  level: INFO
  format: json
  handlers:
    - cloudwatch
    - stderr
```

## Performance Baselines
- Normal analysis: 5-15s
- Large logs: 15-30s
- Voice call: 2-5 minutes
- Notification delivery: <10s
