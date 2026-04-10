# Analyzer Component

## Overview
The analyzer module provides semantic anomaly detection capabilities for CloudWatch logs.

## Features
- Token budget optimization
- Semantic analysis via Nova Embeddings
- Anomaly score calculation
- Context extraction

## Usage
```python
from nexus.analyzer import analyze_logs
results = analyze_logs(logs, budget=5000)
```

## Key Functions
- `analyze_logs()` - Primary analysis function
- `calculate_anomaly_score()` - Score anomalies
- `extract_context()` - Extract relevant context
