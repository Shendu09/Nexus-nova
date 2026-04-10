# Budget Management

## Overview
Manages token budget allocation and optimization across the pipeline.

## Strategies
- Raw log inclusion when budget allows
- Selective reduction when needed
- Cordon-based anomaly pre-filtering

## Configuration
```python
token_budget = 5000
strategy = "optimize"
```

## Methods
- `plan_budget()` - Create budget allocation plan
- `estimate_tokens()` - Estimate token usage
- `optimize_content()` - Reduce content optimally
