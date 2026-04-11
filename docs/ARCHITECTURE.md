# Nexus Nova Architecture Guide

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Incident Input                            │
│              (CloudWatch Logs, Custom Webhooks)                  │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│                   AWS Lambda Handler (3GB Memory)               │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Pre-processing & Feature Extraction                      │  │
│  │ - Log parsing and cleaning                              │  │
│  │ - Context building (service, alert type, severity)      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         │                                       │
│  ┌──────┬──────────┬───┴────┬──────────────┬─────────────┐     │
│  │      │          │        │              │             │     │
│  ▼      ▼          ▼        ▼              ▼             ▼     │
│
│ Module 1    Module 2     Module 3    Module 4      Module 5    │
│ Autoencoder BERT Seg   Prophet     LinUCB RL      RLHF/DPO    │
│ Anomaly    Classifier  Forecasting Query Prefetch Alignment    │
│ Detection                                                       │
│ │      │          │        │              │             │     │
│  └──────┴──────────┴───┬────┴──────────────┴─────────────┘     │
│                        │                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Module 6: Embedding Similarity                   │  │
│  │  Unified representation & semantic search               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                        │                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Response Aggregation & Ranking                          │  │
│  │  - Combine outputs from all modules                      │  │
│  │  - Rank suggestions by confidence                        │  │
│  │  - Format for Nova assistant                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────┬──────────────┬──────────────┬───────────────────────────┘
         │              │              │
         ▼              ▼              ▼
    ┌─────────┐  ┌──────────┐  ┌─────────────────┐
    │SNS      │  │DynamoDB  │  │CloudWatch Logs  │
    │Alerts   │  │Feedback/ │  │& Metrics        │
    │Topic    │  │Metrics   │  │                 │
    └─────────┘  └──────────┘  └─────────────────┘
```

## Module Interaction Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                          Input: Incident Logs                       │
└────────┬─────────────────────────────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────────────────────────┐
    │ Module 1: AUTOENCODER (Anomaly Detection)                  │
    │ Input: Raw log embeddings                                  │
    │ Output: anomaly_score (0-1), is_anomalous (bool)          │
    │ Normal Logs → low score → expected patterns               │
    │ Anomalous Logs → high score → unusual patterns            │
    │ Dependencies: Embeddings (Module 6)                        │
    └─────────┬───────────────────────────────────────────────────┘
              │
              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │ Module 2: BERT CLASSIFIER (Severity Classification)        │
    │ Input: Log text                                            │
    │ Output: severity (0-3), confidence (0-1)                   │
    │ Routing decisions based on severity level                  │
    │ Dependencies: None (standalone)                             │
    └─────────┬───────────────────────────────────────────────────┘
              │
              ├──────────────────────────┬───────────────────────────┐
              │                          │                           │
              ▼                          ▼                           ▼
    ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
    │ Module 3:        │     │ Module 4:        │     │ Module 5:        │
    │ PROPHET          │     │ LinUCB RL        │     │ RLHF/DPO         │
    │ Forecasting      │     │ Query Prefetch   │     │ Alignment        │
    │                  │     │                  │     │                  │
    │ Input: Metrics   │     │ Input: Context   │     │ Input: Text      │
    │ Output: Breach   │     │ Output: Top-K    │     │ Output: Aligned  │
    │ probability      │     │ Queries          │     │ Suggestions      │
    │                  │     │ Dependencies:    │     │ Dependencies:    │
    │ Dependencies:    │     │ None             │     │ None             │
    │ CloudWatch       │     │                  │     │                  │
    │ metrics          │     │                  │     │                  │
    └────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
             │                        │                        │
             └────────────────────────┼────────────────────────┘
                                      │
                                      ▼
                     ┌────────────────────────────────┐
                     │ Module 6: EMBEDDINGS           │
                     │ Semantic Similarity Search     │
                     │                                │
                     │ Input: Query text              │
                     │ Output: Similar incidents      │
                     │ (Cross-module unification)     │
                     └────────────────────────────────┘
                                      │
                                      ▼
                     ┌────────────────────────────────┐
                     │ AGGREGATION & RANKING          │
                     │ - Combine module outputs       │
                     │ - Rank by confidence           │
                     │ - Format response              │
                     └────────────────────────────────┘
```

## Data Flow

### 1. Incident Arrival
```
Event → Lambda Trigger → Payload Validation → Context Extraction
```

### 2. Processing Pipeline
```
Input Text
    ↓
[Autoencoder] → Anomaly Score
    ↓
[BERT] → Severity (INFO/WARNING/HIGH/CRITICAL)
    ↓
[Prophet] → Forecast Breach Probability (if metrics available)
    ↓
[LinUCB] → Recommended Queries [Top-3]
    ↓
[RLHF] → Refined Suggestions (if alignment model loaded)
    ↓
[Embeddings] → Similar Incidents [Top-5]
    ↓
Aggregation → Final Recommendations
```

### 3. Feedback Loop
```
Engineer Reviews Suggestion
    ↓
Records Feedback (quality, helpfulness, satisfaction)
    ↓
[Stored in DynamoDB] → nexus-voice-feedback table
    ↓
Weekly SageMaker Job
    ↓
[Reward Model] Trains on feedback → Predicts suggestion quality
[DPO Trainer] Fine-tunes model → Aligns with engineer preferences
    ↓
[Updated weights] Deployed to Lambda
```

## Storage Architecture

### DynamoDB Tables

**nexus-ml-config**
- Purpose: Model configuration and thresholds
- Primary Key: config_key (String)
- Example items:
  - `severity_threshold_high`: 0.8
  - `forecast_breach_threshold_cpu`: 85.0
  - `linucb_alpha`: 0.5

**nexus-voice-feedback**
- Purpose: Engineer feedback from voice calls
- Primary Key: feedback_id (String)
- Sort Key: timestamp (Number)
- TTL: 90 days (auto-cleanup)
- Data: quality_score, relevance, helpfulness, satisfaction

### S3 Buckets

**nexus-ml-models/**
```
├── autoencoder/
│   ├── model.pt (150MB)
│   ├── config.json
│   └── vocabulary.pkl
├── severity/
│   ├── pytorch_model.bin (350MB)
│   ├── tokenizer.json
│   └── config.json
├── forecasts/
│   ├── cpu_prophet.pkl (200MB)
│   ├── memory_prophet.pkl
│   └── error_rate_prophet.pkl
├── linucb/
│   ├── agent_state.pkl (1MB)
│   └── context_encoder.pkl (5MB)
├── embeddings/
│   ├── pytorch_model.bin (438MB)
│   ├── tokenizer.json
│   └── config.json
└── embeddings_onnx/
    ├── model.onnx (200MB)  # Optimized for Lambda
    ├── tokenizer.json
    └── config.json
```

## Computational Requirements

### Lambda Function Configuration

```
Memory: 3008 MB (maximum for standard Lambda)
Timeout: 900 seconds (15 minutes)
Architecture: x86_64
Storage: 10.24 GB (ephemeral - cleaned up after execution)

Layer: python-dependencies (50MB)
├── torch
├── transformers
├── prophet
├── faiss-cpu
└── boto3
```

### Per-Module Latency Budget

| Module | Cold Start | Warm Start | Budget |
|--------|-----------|-----------|--------|
| Autoencoder | 100ms | 50ms | 100ms |
| BERT Classifier | 150ms | 100ms | 150ms |
| Prophet Forecasting | 50ms | 30ms | 200ms |
| LinUCB Agent | 10ms | 5ms | 10ms |
| RLHF/DPO | 200ms | 100ms | 200ms |
| Embeddings | 150ms | 100ms | 150ms |
| Aggregation | 50ms | 20ms | 50ms |
| **Total** | **710ms** | **405ms** | **860ms** |

## Deployment Topology

### Single Region (us-east-1)

```
┌─────────────────────────────────────────┐
│         AWS Region: us-east-1            │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │ Lambda: nexus-handler            │  │
│  │ Concurrent: 100                  │  │
│  │ Reserved: 10                     │  │
│  └──────────────────────────────────┘  │
│           │         │         │        │
│           ▼         ▼         ▼        │
│  ┌───────────┐ ┌────────┐ ┌───────┐  │
│  │S3 Models  │ │DynamoDB│ │SNS    │  │
│  │           │ │Tables  │ │Topics │  │
│  └───────────┘ └────────┘ └───────┘  │
│           │         │         │        │
│           ▼         ▼         ▼        │
│  ┌──────────────────────────────────┐  │
│  │ CloudWatch Logs & Metrics         │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │ SageMaker Training Jobs           │  │
│  │ (Weekly: Reward Model, DPO)      │  │
│  └──────────────────────────────────┘  │
│                                         │
└─────────────────────────────────────────┘
```

### Multi-Region (Future)

```
┌──────────────────────────────────────────┐
│         AWS Region: us-east-1             │
│  [Primary - Active Lambda + Full Models]  │
└──────────────────────────────────────────┘
              │                 │
    ┌─────────┘                 └──────────┐
    │                                       │
    ▼                                       ▼
┌──────────────────────────────────────────┐
│      AWS Region: eu-west-1                │
│ [Standby - Lambda + Model Replicas]      │
└──────────────────────────────────────────┘

Model Replication: S3 Cross-Region (1h RTO)
Feedback Sync: DynamoDB Global Tables (real-time)
```

## Security Architecture

### Network

- VPC Endpoint: S3, DynamoDB (private access)
- Lambda: Private subnets (optional)
- IAM Roles: Least privilege per Lambda function

### Data Protection

- Encryption at rest: S3 (KMS), DynamoDB (KMS)
- Encryption in transit: TLS 1.2+
- Secrets: AWS Secrets Manager for API keys
- Audit logging: CloudTrail for all API calls

### Access Control

```
┌─────────────────────────────────────────────┐
│        IAM Role: LambdaExecutionRole        │
│                                             │
│ Permissions:                                │
│ - s3:GetObject on nexus-ml-models/*        │
│ - dynamodb:GetItem on nexus-*              │
│ - dynamodb:PutItem on nexus-*              │
│ - sns:Publish on nexus-alerts              │
│ - cloudwatch:PutMetricData                 │
│ - logs:CreateLogGroup                      │
│ - logs:CreateLogStream                     │
│ - logs:PutLogEvents                        │
│                                             │
└─────────────────────────────────────────────┘
```

## Monitoring & Observability

### Key Metrics

1. **Latency Metrics**
   - End-to-end inference time
   - Per-module breakdown
   - Cold start duration

2. **Quality Metrics**
   - Classification accuracy
   - Forecast MAPE
   - Anomaly detection precision/recall

3. **Operational Metrics**
   - Error rate (%)
   - Throttle count
   - DynamoDB consumed capacity

4. **Cost Metrics**
   - Lambda invocations
   - Processing minutes
   - Estimated monthly cost

### Dashboards

- **Operational**: Latency, errors, throttles, cold starts
- **Quality**: Model accuracy, forecast error, detection metrics
- **Cost**: Per-module cost breakdown, resource efficiency
- **Business**: Incidents analyzed, suggestions adopted, feedback score

## Scaling Considerations

### Horizontal Scaling

- Lambda concurrency: Auto-scale from 10 to 1000
- DynamoDB: On-demand billing (auto-scales)
- S3: Unlimited (no configuration needed)

### Vertical Scaling

- Model optimization: ONNX format (10x faster, 50% smaller)
- Quantization: INT8 (25% smaller, minimal accuracy loss)
- Pruning: Remove low-weight connections (20% reduction)

### Caching Strategies

- Model caching: Models stay in Lambda memory (warm start)
- Prediction caching: Redis/ElastiCache for similar incidents
- Embedding caching: FAISS index in DynamoDB for similarity

## Disaster Recovery

### Backup

- Models: S3 versioning + cross-region backup
- Feedback: DynamoDB point-in-time recovery
- Configuration: CloudFormation templates in Git

### Recovery Procedures

| Scenario | RTO | RPO | Procedure |
|----------|-----|-----|-----------|
| Model corruption | 5 min | 1 hour | Restore from S3 previous version |
| DynamoDB failure | 1 min | 1 sec | Failover to replica region |
| Lambda failure | 1 sec | 0 sec | Auto-redeployment |

