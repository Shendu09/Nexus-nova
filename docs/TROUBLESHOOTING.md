# Nexus Nova Troubleshooting Guide

## Common Issues and Solutions

### Module-Specific Issues

#### BERT Severity Classifier

**Issue: Low classification accuracy (< 80%)**
```python
# Problem: Model trained on limited data
# Solution: Add more diverse training examples

# Symptoms:
# - Mislabels "error" as INFO instead of WARNING
# - Low confidence scores (<0.6)

# Fix:
python scripts/extract_training_data.py --days 30 --min_samples 1000
python scripts/finetune_severity.py --num_epochs 10 --learning_rate 1e-5
```

**Issue: Model prediction timeout (>5s)**
```python
# Problem: Large model or insufficient memory
# Solution: Use quantized model

from src.nexus.models.bert_classifier import SeverityClassifier

# Instead of large model
classifier = SeverityClassifier(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Use quantized version
import torch
model = classifier.model
model.half()  # Convert to float16 (50% memory, 2x speed)
```

**Issue: Out of Memory during batch prediction**
```python
# Problem: Batch size too large for available RAM
# Solution: Process in smaller batches

texts = [log for log in large_batch]  # 10,000 logs

# Don't do this:
# predictions = classifier.predict_batch(texts, batch_size=512)

# Do this instead:
BATCH_SIZE = 32
predictions = []
for i in range(0, len(texts), BATCH_SIZE):
    batch_predictions = classifier.predict_batch(
        texts[i:i+BATCH_SIZE],
        batch_size=BATCH_SIZE
    )
    predictions.extend(batch_predictions)
```

#### Time-Series Forecasting (Prophet)

**Issue: Forecast accuracy poor (MAPE > 20%)**
```python
# Problem: Insufficient history or wrong seasonality

from src.nexus.models.forecaster import TimeSeriesForecast

# Solution 1: Use longer history
forecast = TimeSeriesForecast('CPU_Utilization', threshold=85.0)
# train on 60 days instead of 30
forecast.fit(data, periods=60)

# Solution 2: Adjust seasonality
# For metrics with weekly patterns:
forecast.model.add_seasonality(
    name='weekly',
    period=7,
    fourier_order=3
)

# Solution 3: Increase intervals
# More conservative bounds reduce false positives
forecast.model.interval_width = 0.95  # 95% confidence
```

**Issue: Forecast always predicts same value**
```python
# Problem: Model not converging or too much regularization

# Solution:
forecast = TimeSeriesForecast('Memory_Usage', threshold=80.0)
forecast.model.fit(
    df,
    yearly_seasonality=False,  # Disable if <365 days data
    weekly_seasonality=True,
    daily_seasonality=False,   # Only if sub-hourly data
    seasonality_mode='additive', # Try 'multiplicative' for growing trends
    interval_width=0.99  # Wider intervals = higher variance
)
```

**Issue: S3 model loading fails**
```python
# Problem: Model not found or S3 permissions

import boto3
from botocore.exceptions import NoCredentialsError

try:
    s3 = boto3.client('s3')
    s3.head_object(Bucket='nexus-ml-models', Key='forecaster/cpu.pkl')
except NoCredentialsError:
    print("AWS credentials not configured")
    # Solution: export AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
except Exception as e:
    print(f"Model not found: {e}")
    # Solution: train model locally
    from scripts.train_prophet_model import train_forecast_model
    train_forecast_model('CPU_Utilization')
```

#### LinUCB Bandit Agent

**Issue: Agent not improving (reward flat)**
```python
# Problem: Exploration rate too low or poor context representation

from src.nexus.models.rl_prefetch import LinUCBAgent

# Solution 1: Increase exploration bonus
agent = LinUCBAgent(alpha=1.0)  # Increase from 0.5

# Solution 2: Check context features
context = agent.build_context('HighCPU', severity=2)
print(f"Context vector: {context}")
# Expected: [1/8, 2/4, service_idx/100, hour/24, day/7, is_business_hours]

# Solution 3: Verify reward signal
# Make sure rewards correlate with action quality
def get_reward(action, outcome):
    # Don't return 0.0 always!
    if action == 'CPU_Metrics' and outcome == 'found_issue':
        return 1.0
    elif action == 'Logs' and outcome == 'found_issue':
        return 0.8
    else:
        return 0.1  # Small reward for trying
```

**Issue: Agent design matrix singular/non-invertible**
```python
# Problem: Context vectors too similar or all zeros

# Solution 1: Add feature normalization
import numpy as np
from src.nexus.models.rl_prefetch import ContextFeatures

context = ContextFeatures(alarm_type=0, severity=0, service=0, hour=0, day=0, is_business_hours=0)
# Better:
context = ContextFeatures(alarm_type=0/8, severity=0/4, service=0/100, hour=0/24, day=0/7, is_business_hours=0)

# Solution 2: Add regularization
agent = LinUCBAgent(alpha=0.5, lambda_reg=1.0)  # Add lambda_reg parameter if not present

# Solution 3: Reset agent if matrices become singular
if np.linalg.cond(agent.A[action_id]) > 1e10:
    print(f"Action {action_id} matrix singular, resetting")
    agent.A[action_id] = np.eye(6)
    agent.b[action_id] = np.zeros(6)
```

#### RLHF Feedback & Preference Learning

**Issue: Reward model not learning (loss not decreasing)**
```python
# Problem: Target labels inconsistent or wrong normalization

from scripts.train_reward_model import RewardModel, SuggestionRewardDataset

# Solution 1: Check target normalization
# Targets should be between 0 and 1, not raw scores
dataset = SuggestionRewardDataset()
sample_target = next(iter(dataset))[1]
assert 0.0 <= sample_target <= 1.0, f"Target out of range: {sample_target}"

# Solution 2: Verify dataset balancing
# Don't have all high or all low quality examples
from collections import Counter
targets = [dataset[i][1] for i in range(len(dataset))]
print(f"Target distribution: {Counter(targets)}")
# Expected: Spread across 0-1, not skewed to one end

# Solution 3: Reduce learning rate
# DPO is sensitive to learning rate
from scripts.dpo_finetune import DPOTrainer
trainer = DPOTrainer(learning_rate=1e-6)  # Reduce from 5e-5
```

**Issue: DPO training diverging (loss increasing)**
```python
# Problem: Preference pairs conflicting or beta too high

# Solution 1: Use smaller beta
from scripts.dpo_finetune import DPOTrainer
trainer = DPOTrainer(beta=0.1)  # Reduce from 0.5

# Solution 2: Verify preference labels
# Check that preferred > dispreferred in quality
from scripts.dpo_finetune import DPODataset
dataset = DPODataset()
for i in range(10):
    preferred, dispreferred, _ = dataset[i]
    # Debug: preferred should be higher quality
    print(f"Preferred quality: {preferred['quality']}, Dispreferred: {dispreferred['quality']}")
```

#### Embeddings Fine-tuning

**Issue: Embeddings not semantically similar**
```python
# Problem: Model not properly fine-tuned or wrong data

from src.nexus.models.embeddings import SimCSEEmbedder

embedder = SimCSEEmbedder()

# Test semantic similarity
emb1 = embedder.encode_single("Database connection timeout")
emb2 = embedder.encode_single("Connection refused on port 5432")
emb3 = embedder.encode_single("CPU utilization high")

sim_12 = embedder.get_similarity(emb1.reshape(1, -1), emb2.reshape(1, -1))[0, 0]
sim_13 = embedder.get_similarity(emb1.reshape(1, -1), emb3.reshape(1, -1))[0, 0]

print(f"DB similarity: {sim_12:.3f}")  # Should be > 0.8
print(f"CPU similarity: {sim_13:.3f}") # Should be < 0.5

# If not, retrain
from scripts.train_embeddings import LogDataGenerator
gen = LogDataGenerator()
logs = gen.generate_logs(num_incidents=500, logs_per_incident=20)
embedder.train(logs, num_epochs=5)
```

**Issue: ONNX export fails**
```python
# Problem: Model architecture incompatible with ONNX

from scripts.export_onnx import ONNXExporter

# Solution: Use fallback
exporter = ONNXExporter()
try:
    exporter.export_optimum()  # Try optimum first
except Exception as e:
    print(f"Optimum export failed: {e}")
    exporter.export_torch_onnx()  # Fallback to torch.onnx

# Verify export
import onnxruntime
session = onnxruntime.InferenceSession('model.onnx')
print(f"ONNX model loaded successfully")
```

### AWS & Lambda Issues

**Issue: Lambda function timeout (execution > 900s)**
```python
# Problem: Models too large or inference too slow

# Solution 1: Increase Lambda memory for faster CPU
aws lambda update-function-configuration \
  --function-name nexus-handler \
  --memory-size 3008 \
  --timeout 900

# Solution 2: Use ONNX format (10x faster)
from scripts.export_onnx import ONNXExporter
exporter = ONNXExporter()
exporter.export_optimum()  # ~100ms vs ~1000ms per embedding

# Solution 3: Split into multiple Lambda functions
# Instead of all modules in one function, create separate:
# - nexus-severity-classifier (300s)
# - nexus-forecaster (600s)
# - nexus-embedding-search (300s)
```

**Issue: Lambda unable to load models from S3**
```python
# Problem: Permissions or network issue

import boto3
s3 = boto3.client('s3')

# Solution 1: Check IAM permissions
# Lambda role needs: s3:GetObject on nexus-ml-models bucket
# See: https://docs.aws.amazon.com/lambda/latest/dg/access-control-resource-based.html

# Solution 2: Verify S3 bucket exists
try:
    s3.head_bucket(Bucket='nexus-ml-models')
    print("Bucket accessible")
except Exception as e:
    print(f"Bucket error: {e}")
    # Solution: Create bucket or fix MODELS_BUCKET env var

# Solution 3: Check object key
try:
    s3.head_object(Bucket='nexus-ml-models', Key='severity/model.pkl')
    print("Model file found")
except Exception as e:
    print(f"Model not found: {e}")
    # Solution: Upload model with correct key
    s3.upload_file('severity_model.pkl', 'nexus-ml-models', 'severity/model.pkl')
```

**Issue: DynamoDB throttling**
```python
# Problem: High write rate exceeds provisioned capacity

import boto3
dynamodb = boto3.client('dynamodb')

# Solution 1: Use on-demand billing
dynamodb.update_table(
    TableName='nexus-voice-feedback',
    BillingMode='PAY_PER_REQUEST'
)

# Solution 2: Enable auto-scaling
# See AWS DynamoDB docs for capacity plans

# Solution 3: Batch writes
# Group multiple feedback items into one batch
from boto3.dynamodb.conditions import Key
items = [item1, item2, ...]
with dynamodb.batch_write_item() as batch:
    for item in items:
        batch.put_item(Item=item)
```

### Performance Issues

**Issue: Inference latency too high (>5s)**
```bash
# Profile where time is spent
python -m cProfile -s cumulative app.py 2>&1 | head -20

# Expected breakdown:
# - BERT inference: 100-200ms
# - Prophet forecast: 200-300ms
# - Embeddings: 100-200ms
# - Total: 400-700ms

# If >1000ms:
# 1. Check CPU throttling: watch -n 1 'top -b | head -5'
# 2. Reduce batch size
# 3. Use ONNX for embeddings
# 4. Enable GPU: nvidia-smi
```

**Issue: Memory usage increasing over time (memory leak)**
```python
# Profile memory usage
import tracemalloc
tracemalloc.start()

# Run inference multiple times
for i in range(100):
    classifier.predict(log_text)

current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 1024 / 1024:.1f}MB, Peak: {peak / 1024 / 1024:.1f}MB")

# Solution: Release model from GPU memory
import torch
torch.cuda.empty_cache()

# Or recreate model each request (slower but safe)
classifier = SeverityClassifier()
```

## Debug Commands

```bash
# Check AWS credentials
aws sts get-caller-identity

# List Lambda functions
aws lambda list-functions --region us-east-1

# View Lambda logs
aws logs tail /aws/lambda/nexus-handler --follow

# Check DynamoDB tables
aws dynamodb list-tables

# Download Lambda function code
aws lambda get-function --function-name nexus-handler --query 'Code.Location' | xargs curl -o lambda.zip

# Test Lambda locally
sam local invoke nexus-handler -e events/test-event.json
```

## Getting Help

1. Check CloudWatch logs: `aws logs tail /aws/lambda/nexus-handler`
2. Enable DEBUG logging: `export LOG_LEVEL=DEBUG`
3. File GitHub issue: https://github.com/Shendu09/Nexus-nova/issues
4. Check existing docs: See INTEGRATION_GUIDE.md, API_REFERENCE.md
