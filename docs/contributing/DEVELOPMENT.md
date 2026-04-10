# Contributing to Nexus

## Getting Started

### Prerequisites
- Python 3.12+
- AWS Account
- Git

### Setup Development Environment
```bash
git clone https://github.com/shendu09/Nexus-nova.git
cd Nexus-nova
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

## Code Style

### Python Style Guide
- Follow PEP 8
- Use type hints
- Max line length: 88 (Black)
- Use type checker: mypy

```python
def analyze_logs(logs: list[dict], budget: int = 5000) -> dict:
    """Analyze logs for anomalies.
    
    Args:
        logs: List of log events
        budget: Token budget for analysis
        
    Returns:
        Analysis results
    """
    pass
```

### Commit Messages
- Use conventional commits
- Format: type: description
- Types: feat, fix, docs, test, refactor, perf, chore

## Testing

### Run Tests
```bash
pytest tests/
pytest tests/ --cov=src/nexus
```

### Write Tests
```python
def test_analyze_logs():
    logs = [{"message": "error occurred"}]
    result = analyze_logs(logs)
    assert result["anomalies"] > 0
```

## Pull Request Process

1. Fork repository
2. Create feature branch: `git checkout -b feat/feature-name`
3. Make changes and commit
4. Push to fork
5. Create pull request
6. Address review comments
7. Merge when approved

## Code Review Guidelines

- Ensure tests pass
- Maintain code coverage >80%
- Follow style guide
- Include documentation
- Add CHANGELOG entry

## Bug Reports

Include:
- Python version
- AWS region
- Log group size
- Error message
- Steps to reproduce
- Expected vs actual behavior
