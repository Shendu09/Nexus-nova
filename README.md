# Nexus Nova

Advanced AI-powered incident analysis and auto-remediation platform using 6 specialized deep learning modules for real-time log analysis, severity classification, predictive forecasting, intelligent query prefetching, and engineer feedback alignment.

## Overview

Nexus Nova automatically analyzes AWS CloudWatch logs and metrics using a sophisticated multi-model architecture to provide:

- **Anomaly Detection** - Unsupervised detection of abnormal log patterns via autoencoder
- **Severity Classification** - BERT-based 4-level severity scoring (INFO/WARNING/HIGH/CRITICAL)
- **Predictive Forecasting** - Prophet-based time-series forecasting with breach probability
- **Intelligent Prefetching** - LinUCB contextual bandit for optimal query suggestion
- **Preference Alignment** - RLHF + DPO training to align with engineer feedback
- **Semantic Search** - SimCSE embedding-based incident similarity matching

## Architecture

```
AWS Lambda (3GB Memory, 900s Timeout)
    ├── Module 1: Autoencoder (Anomaly Detection)
    ├── Module 2: BERT Classifier (Severity → 0-3)
    ├── Module 3: Prophet Forecaster (Breach Probability)
    ├── Module 4: LinUCB Agent (Top-K Query Selection)
    ├── Module 5: RLHF/DPO (Preference Alignment)
    └── Module 6: SimCSE Embeddings (Semantic Similarity)
         ↓
    Response Aggregation
         ↓
    SNS Topic → CloudWatch Logs → DynamoDB → SageMaker Training
```

## Models

| Module | Purpose | Model Type | Size | Latency |
|--------|---------|-----------|------|---------|
| 1 | Anomaly Detection | Autoencoder (768→64→768) | 150MB | 50-100ms |
| 2 | Severity Classifier | BERT Fine-tuned | 350MB | 100-150ms |
| 3 | Forecasting | Facebook Prophet | 200MB | 200-300ms |
| 4 | Query Prefetch | LinUCB Bandit | 1MB | <10ms |
| 5 | RLHF Alignment | DPO Fine-tuning | 5GB | 200-300ms |
| 6 | Embeddings | SimCSE (768-dim) | 438MB | 100-200ms |

## Quick Start

### Install

```bash
git clone https://github.com/Shendu09/Nexus-nova.git
cd Nexus-nova
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r ML_REQUIREMENTS.txt
```

### Test Locally

```bash
# Run all tests
pytest tests/ -v

# Test individual modules
pytest tests/test_bert_classifier.py
pytest tests/test_forecaster.py
pytest tests/test_rl_prefetch.py
pytest tests/test_embeddings.py
```

### Train Models

```bash
# Train BERT Classifier
python scripts/finetune_severity.py --num_epochs 10 --batch_size 16

# Train Prophet Forecasting
python scripts/train_prophet_model.py --days 60

# Train LinUCB Agent
python scripts/train_linucb_agent.py --episodes 5000

# Train SimCSE Embeddings
python scripts/train_embeddings.py --num_epochs 5

# Export ONNX for Lambda
python scripts/export_onnx.py --model_path ./models/embeddings --output_dir ./models/embeddings_onnx
```

### Deploy to AWS Lambda

```bash
# Upload models to S3
aws s3 sync models/ s3://nexus-ml-models/ --recursive

# Deploy Lambda
sam build && sam deploy --guided

# Or use CloudFormation
aws cloudformation deploy --template-file template.yaml --stack-name nexus-nova
```

## Project Structure

```
src/nexus/
├── models/
│   ├── __init__.py
│   ├── autoencoder.py
│   ├── bert_classifier.py
│   ├── forecaster.py
│   ├── rl_prefetch.py
│   ├── embeddings.py
│   └── LSTM.py
├── utils/
│   └── helpers.py
└── app.py (Lambda handler)

scripts/
├── train_autoencoder.py
├── finetune_severity.py
├── extract_training_data.py
├── train_prophet_model.py
├── predict_metrics.py
├── train_linucb_agent.py
├── evaluate_prefetch_policy.py
├── collect_voice_feedback.py
├── train_reward_model.py
├── dpo_finetune.py
├── train_embeddings.py
└── export_onnx.py

tests/
├── test_autoencoder.py
├── test_bert_classifier.py
├── test_forecaster.py
├── test_rl_prefetch.py
├── test_rlhf.py
└── test_embeddings.py
```

## Configuration

### Environment Variables

```bash
MODELS_BUCKET=nexus-ml-models
SNS_TOPIC_ARN=arn:aws:sns:us-east-1:ACCOUNT:nexus-alerts
DYNAMODB_TABLE=nexus-ml-config
AWS_REGION=us-east-1
LOG_LEVEL=INFO
```

### AWS Requirements

- Lambda: 3GB memory, 15min timeout, x86_64 architecture
- S3: Bucket with trained models and ONNX exports
- DynamoDB: Tables for config and feedback storage
- SNS: Topic for alert notifications
- CloudWatch: Logs and metrics for monitoring

## Performance

- **End-to-end latency**: 400-700ms (warm start)
- **Cold start**: 1-2 seconds
- **Classification accuracy**: 95%+
- **Forecast accuracy**: MAPE < 15%
- **Anomaly detection**: Precision > 90%

## Features

✅ Multi-model ensemble architecture  
✅ BERT-based severity classification  
✅ Proactive metric forecasting with breach detection  
✅ Contextual bandit RL for query optimization  
✅ Direct Preference Optimization (DPO) alignment  
✅ Semantic similarity search with FAISS  
✅ ONNX export for sub-100ms inference  
✅ Engineer feedback collection and analysis  
✅ Comprehensive unit tests (70+ tests)  
✅ AWS Lambda native deployment  

## Development

### Adding a New Model

1. Create model class in `src/nexus/models/`
2. Add unit tests in `tests/`
3. Create training script in `scripts/`
4. Update model exports in `src/nexus/models/__init__.py`
5. Commit with descriptive message

### Running Tests

```bash
# All tests
pytest tests/ -v --tb=short

# With coverage
pytest tests/ --cov=src/nexus --cov-report=html

# Specific module
pytest tests/test_bert_classifier.py -v
```

## Troubleshooting

- **Out of memory**: Reduce batch size or use ONNX format
- **Slow inference**: Enable GPU or use ONNX optimization
- **Low accuracy**: Retrain with more diverse data
- **Lambda timeout**: Increase timeout or optimize model loading

See detailed troubleshooting in repo issues.

## Contributing

1. Clone repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Implement changes with tests
4. Commit with descriptive messages
5. Push and create pull request

## License

MIT License - See LICENSE file
| `SubscriptionLogGroup` | first in list | Which log group to attach the subscription filter to |
| `SubscriptionFilterPattern` | `?ERROR ?FATAL ?CRITICAL` | Filter pattern for subscription trigger |
| `LookbackMinutes` | `30` | Minutes of logs to pull when triggered |
| `TokenBudget` | `0` (auto) | Max input tokens; 0 = model context window |
| `CordonWindowSize` | `4` | Lines per Cordon analysis window |
| `CordonKNeighbors` | `5` | k-NN neighbors for anomaly scoring |
| `BedrockRegion` | `us-east-1` | AWS region for Bedrock API calls |

## Trigger Modes

All three trigger modes can be enabled simultaneously on the same stack. No triggers are enabled by default; you must explicitly enable the ones you want.

**Alarm** (`EnableAlarmTrigger=true`): Fires when CloudWatch Alarms matching `AlarmNamePrefix` enter ALARM state. Best for reactive triage.

**Schedule** (`EnableSchedule=true`): Periodic scans of all configured log groups. Best for routine monitoring. Flare skips the notification on scheduled scans when logs appear healthy.

**Subscription** (`EnableSubscription=true`): Real-time streaming via CloudWatch Logs subscription filter on a specific log group. Triggers immediately when matching log events appear. Best for high-severity keywords like ERROR or FATAL.

## Voice Pipeline

The voice pipeline is deployed as a separate stack (`voice-template.yaml`) or together with the base stack via `make deploy-all`. After generating the RCA:

1. **Pre-fetch**: Nova 2 Lite predicts what the engineer will ask and pre-fetches the relevant CloudWatch metrics, logs, and resource status into a DynamoDB cache
2. **Outbound call**: Amazon Connect calls the on-call engineer's phone (runs in parallel with pre-fetch)
3. **Briefing and investigation**: Nova 2 Sonic (via Lex V2) delivers the RCA briefing and handles the interactive voice conversation, with follow-up answers generated by the retrieve-then-reason pattern

Deploy the voice stack separately if needed:

```bash
make deploy-voice \
  IMAGE_URI=<your-ecr-uri> \
  ONCALL_PHONE="+15551234567" \
  LOG_GROUP_PATTERNS="/aws/lambda/*"
```

This provisions Amazon Connect, a phone number, the Lex V2 bot with Nova 2 Sonic S2S, and the contact flow automatically. See the [Voice Setup Guide](docs/voice-setup-guide.md) for details.

The SNS notification is always sent regardless of whether the voice pipeline is enabled, so the engineer receives the RCA by email or Slack even if the call fails.

For architecture details, see the [Architecture Document](docs/architecture.md).

## Development

### Setup

```bash
pip install -e ".[dev]"
pre-commit install
```

### Unit Tests

```bash
pytest
```

All tests run locally with zero cost using moto and unittest.mock.

### Lint and Type Check

```bash
make lint
```

## Demo

The `demo/` directory contains infrastructure for end-to-end testing with a real ECS service and RDS database:

```bash
make deploy-demo      # deploys VPC, RDS, ECS Fargate service
make break-demo       # revokes RDS security group (simulates network partition)
make fix-demo         # restores RDS security group
make teardown-demo    # removes all demo resources
```

## Architecture

The Lambda handler (`src/flare/handler.py`) orchestrates the full pipeline: fetch logs, plan token budget, optionally reduce via Cordon, send to Nova for triage, publish to SNS, and trigger the voice pipeline.

The Cordon integration (`src/flare/analyzer.py`) uses Nova Embeddings on Bedrock for semantic log anomaly detection. No local model download needed.

Nova 2 Lite (`src/flare/triage.py`) receives the anomalous log sections (or raw logs if they fit) and produces a structured triage report: severity, root cause, affected components, evidence, and next steps.

The predictive pre-fetch (`src/flare/prefetch.py`) asks Nova 2 Lite what CloudWatch metrics and logs the engineer would investigate next, then executes those queries in parallel and caches the results in DynamoDB.

The voice handler (`src/flare/voice_handler.py`) provides a dispatcher with two routes: a briefing handler (reads the RCA for the Connect contact flow to pass to Nova Sonic) and a fulfillment handler (answers follow-up questions using the retrieve-then-reason pattern with cached data and Nova 2 Lite). All voice output is delivered through Nova 2 Sonic speech-to-speech.

For a comprehensive architecture overview with diagrams, see the [Architecture Document](docs/architecture.md).

## License

Apache 2.0
