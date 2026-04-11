# Nexus Nova Deep Learning Integration Guide

## Overview

This guide covers the integration and deployment of all 7 deep learning modules for Nexus Nova's advanced incident analysis platform.

## Modules Summary

### Module 1: Autoencoder-Based Anomaly Detection (✅ Complete)
- **Purpose**: Unsupervised detection of anomalous log patterns
- **Architecture**: 768→256→64→256→768 autoencoder
- **Status**: Production-ready
- **Commit**: ml: implement BERT severity classifier model

### Module 2: BERT Severity Classification (✅ Complete)
- **Purpose**: Classify incident severity (INFO/WARNING/HIGH/CRITICAL)
- **Architecture**: sentence-transformers/all-MiniLM-L6-v2 fine-tuned
- **Status**: Production-ready
- **Performance**: 4-class classification with confidence scoring

### Module 3: Time-Series Forecasting (✅ Complete)
- **Purpose**: Proactive metric forecasting to predict capacity breaches
- **Architecture**: Facebook Prophet with seasonality modeling
- **Status**: Production-ready
- **Metrics**: CPU, Memory, Error Rate, Latency, RPS

### Module 4: RL-Based Query Pre-fetching (✅ Complete)
- **Purpose**: Learn optimal query selection for incident investigation
- **Algorithm**: LinUCB contextual bandit (8 actions)
- **Status**: Production-ready
- **Actions**: CPU metrics, memory, logs, dependencies, database, DynamoDB, etc.

### Module 5: RLHF Feedback Loop (✅ Complete)
- **Purpose**: Align Nova suggestions with engineer preferences
- **Training**: DPO fine-tuning with voice call feedback
- **Status**: Production-ready
- **Deployment**: Weekly SageMaker training jobs

### Module 6: Neural Embedding Fine-tuning (✅ Complete)
- **Purpose**: Optimize embeddings for anomaly detection
- **Method**: SimCSE contrastive learning
- **Status**: Production-ready
- **Output**: ONNX format for Lambda (sub-100ms)

## Deployment Architecture

```
AWS Lambda (Nova Handler)
    ↓
├── Autoencoder (anomaly scoring)
├── BERT Classifier (severity classification)
├── Prophet Forecaster (breach probability)
├── LinUCB Agent (prefetch selection)
└── Embeddings (semantic similarity)
    ↓
CloudWatch Logs (results)
DynamoDB (metrics, feedback)
SNS (alerts)
```

## Module Interdependencies

- **Embeddings** → Used by Autoencoder for feature representation
- **BERT Classifier** → Uses Embeddings for text encoding
- **Prophet** → Predicts metrics for prefetch agent
- **LinUCB** → Selects top queries based on context
- **RLHF** → Improves Nova's suggestions over time

## Performance Targets

| Module | Latency | Memory | Model Size |
|--------|---------|--------|-----------|
| Autoencoder | 50-100ms | 256MB | 150MB |
| BERT Classifier | 100-150ms | 512MB | 350MB |
| Prophet | 200-300ms | 1GB | 200MB |
| LinUCB | <10ms | 50MB | 1MB |
| RLHF | Variable | 2GB+ | 1-5GB |
| Embeddings | 100-200ms | 512MB | 438MB |

## Quick Start

### 1. Deploy Core Models
```bash
# Autoencoder
python scripts/train_autoencoder.py --output_dir ./models/autoencoder

# BERT Classifier
python scripts/finetune_severity.py --output_dir ./models/severity

# Prophet Forecasts
python scripts/train_prophet_model.py --output_dir ./models/forecasts

# LinUCB Agent
python scripts/train_linucb_agent.py --output_dir ./models/linucb

# Embeddings
python scripts/train_embeddings.py --output_dir ./models/embeddings

# ONNX Export
python scripts/export_onnx.py --model_path ./models/embeddings --output_dir ./models/embeddings_onnx
```

### 2. Set AWS Environment Variables
```bash
export MODELS_BUCKET=nexus-ml-models
export SNS_TOPIC_ARN=arn:aws:sns:us-east-1:ACCOUNT:nexus-alerts
export DYNAMODB_TABLE=nexus-ml-config
```

### 3. Deploy to Lambda
```bash
# Package Lambda function
zip -r lambda.zip . -x "*.git*" "tests/*" "*.pth" "*.pkl"

# Upload and update function
aws lambda update-function-code --function-name nexus-handler --zip-file fileb://lambda.zip
```

## Configuration Files

Key configuration files:
- `pyproject.toml` - Dependencies
- `.env.example` - Environment variables
- `serverless.yml` - Serverless deployment
- `docker-compose.yml` - Local testing

## Monitoring and Observability

### CloudWatch Metrics
- Autoencoder reconstruction error
- BERT classification confidence
- Prophet forecast accuracy
- LinUCB reward rates
- Vector embedding quality

### DynamoDB Tables
- `nexus-ml-config` - Model configurations
- `nexus-voice-feedback` - Engineer feedback
- `nexus-forecast-alerts` - Prediction alerts

### Logging
- All module inference latencies logged
- Error rates and exceptions tracked
- Training job progress monitored

## Testing

Run comprehensive test suite:
```bash
pytest tests/ -v --tb=short

# Specific module tests
pytest tests/test_autoencoder.py
pytest tests/test_bert_classifier.py
pytest tests/test_forecaster.py
pytest tests/test_rl_prefetch.py
pytest tests/test_rlhf.py
pytest tests/test_embeddings.py
```

## Troubleshooting

### Out of Memory Errors
- Reduce batch size (32 → 16)
- Enable Lambda Insights
- Check provisioned concurrency

### Slow Inference
- Use ONNX format for embeddings
- Enable GPU acceleration
- Consider SageMaker endpoints

### Model Drift
- Re-train monthly
- Monitor performance metrics
- Compare A/B test results

## Next Steps

1. Deploy Module 1 (Autoencoder) to production
2. Run feedback collection for Module 5
3. Monitor Module 3 forecast accuracy
4. Iterate on Module 6 embeddings
5. Scale to multi-region deployment
