# Nexus Nova Quick Start Guide

## 5-Minute Setup

### Install and Run

```bash
# Clone repository
git clone https://github.com/Shendu09/Nexus-nova.git
cd Nexus-nova

# Setup Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r ML_REQUIREMENTS.txt

# Run tests
pytest tests/ -v
```

### Test Locally

```bash
# Test BERT classifier
python -c "
from src.nexus.models.bert_classifier import SeverityClassifier
classifier = SeverityClassifier()
result = classifier.predict('High CPU usage detected')
print(f'Severity: {result.severity}, Confidence: {result.confidence}')
"
# Output: Severity: 2, Confidence: 0.87

# Test forecasting
python -c "
from src.nexus.models.forecaster import ForecastingEngine
engine = ForecastingEngine({'CPU': (85.0, 7)})
forecasts = engine.forecast_all(12)
print(f'CPU breach likelihood: {forecasts[\"CPU\"].breach_probability}')
"

# Test embeddings
python -c "
from src.nexus.models.embeddings import SimCSEEmbedder
embedder = SimCSEEmbedder()
emb = embedder.encode(['error in database connection'])
print(f'Embedding shape: {emb.shape}')
"
```

### First Lambda Deployment

```bash
# Minimal local Lambda environment
pip install aws-lambda-powertools

# Create minimal handler
cat > app.py << 'EOF'
from src.nexus.models.bert_classifier import SeverityClassifier

classifier = SeverityClassifier()

def lambda_handler(event, context):
    """Handle incident logs."""
    logs = event.get('logs', [])
    results = []
    
    for log_text in logs:
        prediction = classifier.predict(log_text)
        results.append({
            'text': log_text,
            'severity': prediction.severity,
            'confidence': float(prediction.confidence)
        })
    
    return {
        'statusCode': 200,
        'body': {'results': results}
    }
EOF

# Test locally
python -c "
from app import lambda_handler
event = {'logs': ['CPU at 95%', 'Memory leak detected']}
result = lambda_handler(event, None)
print(result['body'])
"
# Output: {'results': [{'text': 'CPU at 95%', 'severity': 2, 'confidence': 0.91}, ...]}
```

### Docker Quick Start

```dockerfile
# Dockerfile.quickstart
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0"]
```

```bash
# Build and run
docker build -f Dockerfile.quickstart -t nexus-app .
docker run -p 8000:8000 nexus-app

# Test endpoint
curl http://localhost:8000/classify -X POST \
  -H "Content-Type: application/json" \
  -d '{"text": "Critical error occurred"}'
```

## Core Workflows

### Workflow 1: Severity Classification

```python
from src.nexus.models.bert_classifier import SeverityClassifier

# Initialize
classifier = SeverityClassifier()

# Classify logs
logs = [
    "Starting scheduled backup",
    "WARNING: Connection timeout",
    "CRITICAL: Database service down",
    "HIGH: Memory utilization 92%"
]

for log in logs:
    result = classifier.predict(log)
    severity_map = {0: "INFO", 1: "WARNING", 2: "HIGH", 3: "CRITICAL"}
    print(f"{log} → {severity_map[result.severity]} (confidence: {result.confidence:.2%})")

# Output:
# Starting scheduled backup → INFO (confidence: 95.23%)
# WARNING: Connection timeout → WARNING (confidence: 88.41%)
# CRITICAL: Database service down → CRITICAL (confidence: 96.87%)
# HIGH: Memory utilization 92% → HIGH (confidence: 91.34%)
```

### Workflow 2: Metric Forecasting

```python
from src.nexus.models.forecaster import ForecastingEngine
import pandas as pd

# Initialize with metrics
engine = ForecastingEngine({
    'CPU': (85.0, 7),           # threshold=85%, seasonality=7
    'Memory': (80.0, 7),
    'ErrorRate': (5.0, 7)
})

# Fit models (using demo data)
forecasts = engine.forecast_all(future_hours=24)

# Check breach probabilities
for metric_name, forecast in forecasts.items():
    print(f"{metric_name}:")
    print(f"  Breach probability: {forecast.breach_probability:.1%}")
    print(f"  Estimated breach time: {forecast.estimated_breach_time}")
    
# Output:
# CPU:
#   Breach probability: 23.4%
#   Estimated breach time: 2024-01-15 18:30:00
```

### Workflow 3: Query Recommendation

```python
from src.nexus.models.rl_prefetch import RLPrefetchStrategy

# Initialize strategy
strategy = RLPrefetchStrategy()

# Get recommendations for incident
incident_type = "HighCPU"
severity = 2

recommendations = strategy.plan_prefetch(incident_type, severity)

print(f"Recommended queries for {incident_type} (severity {severity}):")
for i, query in enumerate(recommendations, 1):
    print(f"  {i}. {query}")

# Output:
# Recommended queries for HighCPU (severity 2):
#   1. CPU Metrics
#   2. Process List
#   3. Historical CPU Trends
#   4. Correlated Alerts
```

### Workflow 4: Feedback Collection

```python
from scripts.collect_voice_feedback import VoiceFeedback, VoiceFeedbackCollector
from datetime import datetime

# Initialize collector (uses local JSONL by default)
collector = VoiceFeedbackCollector()

# Record feedback after voice call
feedback = VoiceFeedback(
    suggestion_id="sugg-12345",
    quality_score=8,
    relevance_score=0.9,
    was_helpful=True,
    satisfaction=9,
    timestamp=datetime.now()
)

feedback_id = collector.record_feedback(feedback)
print(f"Feedback recorded: {feedback_id}")

# Analyze trends
analyzer = collector.get_analyzer()
trends = analyzer.get_trending_suggestions(days=7)
print(f"Top suggestions this week: {trends}")
```

### Workflow 5: Embedding Similarity Search

```python
from src.nexus.models.embeddings import SimCSEEmbedder, LogEmbeddingStore

# Initialize embedder
embedder = SimCSEEmbedder()
store = LogEmbeddingStore(embedder)

# Add logs to store
logs = [
    ("log-1", "Database connection timeout after 30s"),
    ("log-2", "Connection refused on port 5432"),
    ("log-3", "Memory usage at 95% capacity"),
    ("log-4", "CPU temperature critical warning")
]

for log_id, text in logs:
    embedding = embedder.encode_single(text)
    store.add(log_id, embedding)

# Find similar logs
query = "Database connection failed"
query_emb = embedder.encode_single(query)
similar = store.get_most_similar(query_emb, top_k=2)

print(f"Similar to '{query}':")
for log_id in similar:
    print(f"  - {log_id}")

# Output:
# Similar to 'Database connection failed':
#   - log-1
#   - log-2
```

## Environment Configuration

### Local Development

```bash
# Create .env file
cat > .env << 'EOF'
# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=default

# Model Configuration
MODEL_CACHE_DIR=./models
CACHE_SIZE_GB=10

# Inference Settings
BATCH_SIZE=32
INFERENCE_TIMEOUT=60

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=json
EOF

# Load environment
export $(cat .env | xargs)
```

### AWS Credentials

```bash
# Configure AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_REGION=us-east-1
```

## Common Tasks

### Training Models

```bash
# Train all models (takes ~30 minutes)
./scripts/train_all_models.sh

# Or individual models
python scripts/finetune_severity.py --num_epochs 10 --batch_size 16
python scripts/train_prophet_model.py --days 60 --output_dir ./models
python scripts/train_linucb_agent.py --episodes 5000
python scripts/train_embeddings.py --num_epochs 5
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific tests
pytest tests/test_bert_classifier.py -v
pytest tests/test_forecaster.py -v
pytest tests/test_rl_prefetch.py -v

# Generate coverage report
pytest tests/ --cov=src/nexus --cov-report=html
open htmlcov/index.html
```

### Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with debug prints
python -u scripts/train_prophet_model.py --debug

# Attach debugger
python -m pdb scripts/train_embeddings.py

# Profile performance
python -m cProfile -s cumulative scripts/train_severity.py
```

## Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| Out of memory | Reduce batch_size by 50% |
| Slow inference | Use ONNX format for embeddings |
| Model not found | Check MODELS_BUCKET env var |
| Lambda timeout | Increase timeout from 300s to 900s |
| Low accuracy | Retrain with more data |
| GPU not detected | Install CUDA 11.8 + PyTorch GPU |

## Next Steps

1. **Read** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for production setup
2. **Study** [API_REFERENCE.md](API_REFERENCE.md) for detailed APIs
3. **Review** [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for module integration
4. **Check** [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
5. **Explore** examples in `demo/` directory

## Need Help?

- GitHub Issues: https://github.com/Shendu09/Nexus-nova/issues
- Documentation: https://github.com/Shendu09/Nexus-nova/tree/main/docs
- Examples: https://github.com/Shendu09/Nexus-nova/tree/main/demo

Happy analyzing! 🚀
