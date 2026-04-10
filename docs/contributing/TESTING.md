# Testing Guide

## Test Structure

```
tests/
├── unit/
│   ├── test_analyzer.py
│   ├── test_budget.py
│   ├── test_caller.py
│   └── ...
├── integration/
│   ├── test_end_to_end.py
│   └── test_pipeline.py
└── fixtures/
    └── mock_logs.json
```

## Unit Tests

### Analyzer Tests
```python
import pytest
from nexus.analyzer import analyze_logs

def test_analyze_logs_basic():
    logs = [
        {"message": "normal operation"},
        {"message": "error occurred"}
    ]
    result = analyze_logs(logs)
    assert result["status"] == "success"
    assert len(result["anomalies"]) > 0

def test_analyze_logs_empty():
    result = analyze_logs([])
    assert result["status"] == "success"
    assert len(result["anomalies"]) == 0
```

## Integration Tests

```python
def test_end_to_end_pipeline():
    event = {
        "source": "aws.logs",
        "detail": {"logGroup": "test-group"}
    }
    response = handler(event, {})
    assert response["statusCode"] == 200
```

## Mocking AWS Services

```python
from moto import mock_logs
import boto3

@mock_logs
def test_get_logs():
    client = boto3.client("logs")
    client.create_log_group(logGroupName="test")
    # ... test code
```

## Test Coverage

```bash
pytest --cov=src/nexus --cov-report=html
open htmlcov/index.html
```

## Performance Tests

```python
import timeit

def test_analyzer_performance():
    logs = [{"message": f"log {i}"} for i in range(10000)]
    time_taken = timeit.timeit(
        lambda: analyze_logs(logs),
        number=1
    )
    assert time_taken < 30  # Should complete in <30s
```
