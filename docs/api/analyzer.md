# Analyzer API Reference

## Functions

### analyze_logs(logs, budget=5000)
Perform semantic anomaly analysis on CloudWatch logs.

**Parameters:**
- `logs` (list): List of log events
- `budget` (int): Token budget for analysis

**Returns:**
- `dict`: Analysis results with anomalies and scores

**Example:**
```python
results = analyze_logs(logs, token_budget=5000)
```

### calculate_anomaly_score(log_entry)
Calculate anomaly score for individual log entry.

**Parameters:**
- `log_entry` (dict): Single log event

**Returns:**
- `float`: Anomaly score (0.0-1.0)

### extract_context(logs, anomaly_indices)
Extract relevant context around anomalies.

**Parameters:**
- `logs` (list): Full log list
- `anomaly_indices` (list): Indices of anomalies

**Returns:**
- `list`: Context segments

## Exceptions

- `InvalidLogFormat`: Malformed log input
- `BudgetExceeded`: Token budget exceeded
- `AnalysisTimeout`: Analysis took too long
