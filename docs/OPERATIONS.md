# Nexus Nova Operations Guide

## Daily Operations

### Health Check Procedure

Run every morning:

```bash
#!/bin/bash
# health_check.sh

echo "=== Nexus Nova Health Check ==="

# 1. Check Lambda function
echo "1. Lambda Function Status..."
aws lambda get-function-configuration \
  --function-name nexus-handler \
  --query 'State' --output text

# 2. Check recent errors
echo "2. Lambda Error Rate (last hour)..."
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=nexus-handler \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum

# 3. Check DynamoDB
echo "3. DynamoDB Tables..."
aws dynamodb describe-table --table-name nexus-ml-config \
  --query 'Table.TableStatus' --output text
aws dynamodb describe-table --table-name nexus-voice-feedback \
  --query 'Table.TableStatus' --output text

# 4. Check S3 models
echo "4. Model S3 Bucket..."
aws s3 ls s3://nexus-ml-models/ --recursive | wc -l

# 5. Check latest logs
echo "5. Recent Log Errors..."
aws logs tail /aws/lambda/nexus-handler --since 1h --follow=false | grep -i error | tail -5

echo "=== Health Check Complete ==="
```

### Weekly Maintenance

```bash
#!/bin/bash
# weekly_maintenance.sh

echo "=== Weekly Maintenance Checklist ==="

# 1. Review performance metrics
echo "1. Reviewing performance metrics..."
python - <<'EOF'
import boto3
cw = boto3.client('cloudwatch')

metrics = ['Duration', 'Errors', 'Throttles', 'ConcurrentExecutions']
for metric in metrics:
    response = cw.get_metric_statistics(
        Namespace='AWS/Lambda',
        MetricName=metric,
        Dimensions=[{'Name': 'FunctionName', 'Value': 'nexus-handler'}],
        StartTime=datetime.utcnow() - timedelta(days=7),
        EndTime=datetime.utcnow(),
        Period=86400,
        Statistics=['Average', 'Maximum']
    )
    print(f"{metric}: Avg={response['Datapoints'][0]['Average']:.2f}, Max={response['Datapoints'][0]['Maximum']:.2f}")
EOF

# 2. Clean up old feedback (exceeds TTL)
echo "2. Cleaning old feedback data..."
aws dynamodb scan --table-name nexus-voice-feedback \
  --filter-expression "attribute_exists(#ttl) AND #ttl < :now" \
  --expression-attribute-names '{"#ttl":"ttl"}' \
  --expression-attribute-values '{":now":{'N':'1704067200'}}' \
  --projection-expression 'feedback_id' | jq -c '.Items[] | .feedback_id.S' | \
  xargs -I {} aws dynamodb delete-item --table-name nexus-voice-feedback --key '{"feedback_id":{"S":"{}"}}'

# 3. Review CloudWatch logs for anomalies
echo "3. Analyzing CloudWatch logs for anomalies..."
aws logs start-query \
  --log-group-name /aws/lambda/nexus-handler \
  --start-time $(date -d '7 days ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @duration | stats avg(@duration)'

# 4. Check S3 bucket size
echo "4. S3 bucket size..."
aws s3 ls s3://nexus-ml-models --recursive --summarize | tail -2

# 5. Run test scenarios
echo "5. Running test scenarios..."
python tests/integration_test.py

echo "=== Weekly Maintenance Complete ==="
```

## Incident Response

### Lambda Function Degradation

**Symptoms**: High error rate, timeouts, memory exhaustion

**Response Steps**:

```bash
# Step 1: Check logs immediately
aws logs tail /aws/lambda/nexus-handler --follow &

# Step 2: Scale up concurrency
aws lambda put-function-concurrency \
  --function-name nexus-handler \
  --reserved-concurrent-executions 100

# Step 3: Increase memory (faster processing)
aws lambda update-function-configuration \
  --function-name nexus-handler \
  --memory-size 3008 \
  --timeout 900

# Step 4: If memory exhaustion, reload models
aws lambda update-function-code \
  --function-name nexus-handler \
  --s3-bucket nexus-ml-models \
  --s3-key latest-lambda.zip

# Step 5: Monitor recovery
watch -n 5 'aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=nexus-handler \
  --start-time $(date -u -d "5 minutes ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum | jq ".Datapoints[0].Sum"'
```

### Model Accuracy Drop

**Symptoms**: Low confidence scores, wrong classifications, poor recommendations

**Response**:

```bash
# Check if model was updated
aws s3api head-object --bucket nexus-ml-models --key severity/model.pkl

# Compare with backup
aws s3 cp s3://nexus-ml-models/backups/severity-v1.tar.gz ./
tar -xzf severity-v1.tar.gz

# Run validation tests
pytest tests/test_bert_classifier.py::test_accuracy -v

# If accuracy low, retrain
python scripts/finetune_severity.py \
  --output_dir /tmp/severity_new \
  --num_epochs 10 \
  --learning_rate 1e-5

# A/B test new model
python tests/integration_test.py --compare-models

# If better, deploy
aws s3 cp /tmp/severity_new/model.pkl s3://nexus-ml-models/severity/model.pkl
aws lambda update-environment-variables \
  --function-name nexus-handler \
  --environment Variables="{MODEL_VERSION=severity-v2}"
```

## Scaling Operations

### Peak Traffic Handling

```bash
#!/bin/bash
# handle_peak.sh - Called during high traffic periods

# 1. Increase Lambda provisioned concurrency
aws lambda put-provisioned-concurrent-executions \
  --function-name nexus-handler \
  --provisioned-concurrent-executions 500

# 2. Enable DynamoDB auto-scaling
aws appautoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/nexus-voice-feedback \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --min-capacity 10 \
  --max-capacity 1000

# 3. Pre-warm Lambda instances
for i in {1..10}; do
  aws lambda invoke \
    --function-name nexus-handler \
    --payload '{"action":"healthcheck"}' \
    /dev/null &
done
wait

# 4. Monitor metrics
aws cloudwatch describe-alarms \
  --alarm-names nexus-lambda-errors nexus-lambda-duration

# 5. Scale down after peak
# (Run after 2 hours of normal traffic)
aws lambda delete-provisioned-concurrent-executions \
  --function-name nexus-handler
```

## Backup & Recovery

### Automated Backups

```bash
#!/bin/bash
# backup_daily.sh - Run via AWS Lambda scheduled event

# 1. Export Lambda function
FUNCTION_VERSION=$(date +%s)
aws lambda publish-version \
  --function-name nexus-handler \
  --description "Backup $FUNCTION_VERSION"

# 2. Backup models from S3
aws s3 sync s3://nexus-ml-models s3://nexus-ml-backups/models-$FUNCTION_VERSION/

# 3. Backup DynamoDB
aws dynamodb create-backup \
  --table-name nexus-voice-feedback \
  --backup-name nexus-feedback-backup-$FUNCTION_VERSION
aws dynamodb create-backup \
  --table-name nexus-ml-config \
  --backup-name nexus-config-backup-$FUNCTION_VERSION

# 4. Export to S3
aws dynamodb export-table-to-point-in-time \
  --table-arn arn:aws:dynamodb:us-east-1:ACCOUNT:table/nexus-voice-feedback \
  --s3-bucket nexus-ml-backups \
  --s3-prefix feedback-export-$FUNCTION_VERSION

# 5. Upload function code
aws lambda get-function \
  --function-name nexus-handler \
  --query 'Code.Location' | xargs curl -o /tmp/lambda-$FUNCTION_VERSION.zip
aws s3 cp /tmp/lambda-$FUNCTION_VERSION.zip s3://nexus-ml-backups/lambda-$FUNCTION_VERSION.zip

echo "Backup complete: $FUNCTION_VERSION"
```

### Disaster Recovery

```bash
#!/bin/bash
# disaster_recovery.sh - Full system restore

BACKUP_ID=$1  # e.g., 1704067200

echo "Restoring from backup: $BACKUP_ID"

# 1. Restore DynamoDB from backup
for TABLE in nexus-voice-feedback nexus-ml-config; do
  BACKUP_ARN=$(aws dynamodb list-backups \
    --table-name $TABLE \
    --query "Backups[?BackupName=='nexus-${TABLE##*-}-backup-$BACKUP_ID'].BackupArn" \
    --output text)
  
  if [ -n "$BACKUP_ARN" ]; then
    aws dynamodb restore-table-from-backup \
      --target-table-name $TABLE-restored \
      --backup-arn $BACKUP_ARN
    echo "Restored $TABLE"
  fi
done

# 2. Restore models from S3
aws s3 sync s3://nexus-ml-backups/models-$BACKUP_ID/ s3://nexus-ml-models/

# 3. Update Lambda to restored code
aws s3 cp s3://nexus-ml-backups/lambda-$BACKUP_ID.zip /tmp/lambda-restored.zip
aws lambda update-function-code \
  --function-name nexus-handler \
  --zip-file fileb:///tmp/lambda-restored.zip

# 4. Verify restoration
pytest tests/integration_test.py

echo "Disaster recovery complete!"
```

## Cost Management

### Monthly Cost Estimation

```python
import boto3

def estimate_monthly_costs():
    """Estimate Nexus monthly AWS costs."""
    ce = boto3.client('ce')
    
    response = ce.get_cost_and_usage(
        TimePeriod={
            'Start': '2024-01-01',
            'End': '2024-02-01'
        },
        Granularity='MONTHLY',
        Metrics=['UnblendedCost'],
        Filter={
            'Tags': {
                'Key': 'Project',
                'Values': ['Nexus-Nova']
            }
        },
        GroupBy=[
            {
                'Type': 'DIMENSION',
                'Key': 'SERVICE'
            }
        ]
    )
    
    total = 0
    for group in response['ResultsByTime'][0]['Groups']:
        service = group['Keys'][0]
        cost = float(group['Metrics']['UnblendedCost']['Amount'])
        total += cost
        print(f"{service}: ${cost:.2f}")
    
    print(f"Total: ${total:.2f}")
    print(f"Projected Monthly: ${total * 30:.2f}")

estimate_monthly_costs()
```

### Cost Optimization Tips

1. **Lambda**
   - Use ONNX instead of PyTorch (30% faster = less runtime)
   - Enable Lambda Insights for tracing
   - Reserved concurrency for baseline

2. **DynamoDB**
   - Use on-demand billing for variable workloads
   - Enable point-in-time recovery only when needed
   - Archive old feedback to S3 Glacier

3. **S3**
   - Enable versioning only on production bucket
   - Lifecycle policies to move old models to Glacier
   - Use S3 Intelligent-Tiering

4. **SageMaker**
   - Use on-demand training (not reserved)
   - Spot Instances for training (70% savings)
   - Stop instances after training

## Service Level Objectives (SLOs)

| Metric | Target | Warning |
|--------|--------|---------|
| Availability | 99.9% | < 99.5% |
| Latency (p50) | 500ms | > 800ms |
| Latency (p99) | 2s | > 3s |
| Error Rate | < 0.1% | > 0.5% |
| Classification Accuracy | 95% | < 90% |
| Model Training Cadence | Weekly | > 2 weeks |

## Metrics to Monitor

```python
# CloudWatch alarms to set up
alarms = [
    ('nexus-errors-high', 'AWS/Lambda', 'Errors > 10 in 5min'),
    ('nexus-duration-high', 'AWS/Lambda', 'Duration > 5s in 5min'),
    ('nexus-throttles', 'AWS/Lambda', 'Throttles > 0 in 5min'),
    ('nexus-dynamodb-write', 'AWS/DynamoDB', 'ConsumedWriteUnits > 1000'),
    ('nexus-forecast-fail', 'Custom', 'ForecastError > 20%'),
    ('nexus-accuracy-drop', 'Custom', 'Accuracy < 90%'),
]
```
