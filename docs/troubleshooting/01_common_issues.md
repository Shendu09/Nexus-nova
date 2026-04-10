# Troubleshooting Common Issues

## Log Retrieval Failures

### Error: "Log Group Not Found"
**Cause**: CloudWatch log group doesn't exist or wrong region

**Solutions**:
1. Verify log group exists: `aws logs describe-log-groups`
2. Check AWS region configuration
3. Verify Lambda IAM permissions

### Error: "Access Denied on Logs API"
**Cause**: Missing IAM permissions

**Solution**:
```json
{
  "Effect": "Allow",
  "Action": [
    "logs:GetLogEvents",
    "logs:DescribeLogGroups",
    "logs:DescribeLogStreams"
  ],
  "Resource": "arn:aws:logs:*:*:*"
}
```

## Analysis Timeouts

### Error: "Analysis Took Too Long"
**Cause**: Too many logs or complex patterns

**Solutions**:
1. Increase Lambda timeout (max 15min)
2. Reduce looked-back time window
3. Adjust token budget lower

### Symptom: Partial Results
**Cause**: Timeout occurred during processing

**Solutions**:
1. Check CloudWatch logs for timing
2. Optimize log volume
3. Consider concurrent processing

## Notification Issues

### Error: "SNS Publish Failed"
**Cause**: Topic doesn't exist or permissions missing

**Solutions**:
1. Verify SNS topic ARN
2. Check topic access policy
3. Verify email subscription confirmed

### Error: "Slack Webhook Invalid"
**Cause**: Webhook URL expired or incorrect

**Solutions**:
1. Regenerate Slack webhook
2. Update environment variable
3. Test webhook manually

## Voice Call Issues

### Error: "Amazon Connect Call Failed"
**Cause**: Instance unavailable or phone invalid

**Solutions**:
1. Verify instance is active
2. Check phone number format
3. Ensure service quota not exceeded

### Symptom: "Voice Garbled or Unclear"
**Cause**: Network latency or speech model issues

**Solutions**:
1. Check network connectivity
2. Monitor latency metrics
3. Consider disabling voice for heavy load

## Performance Issues

### Symptom: "Lambda Execution Slow"
**Diagnosis**:
```bash
# Check CloudWatch duration metric
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --statistics Average,Maximum
```

**Solutions**:
1. Increase Lambda memory (improves CPU)
2. Optimize code hot paths
3. Cache frequently accessed data
4. Consider Lambda layers

### Symptom: "High DynamoDB Costs"
**Cause**: Excessive read/write units

**Solutions**:
1. Enable DynamoDB autoscaling
2. Use appropriate provisioned capacity
3. Cache results locally
4. Batch operations where possible

## Debugging

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### CloudWatch Insights Query
```
fields @timestamp, @message, @duration
| stats count() by ispublic
| sort count() desc
```

### X-Ray Tracing
```bash
aws xray get-trace-summaries \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T12:00:00Z
```
