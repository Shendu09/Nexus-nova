# Triage API Reference

## Functions

### analyze_logs_for_rca(logs, token_budget)
Perform root cause analysis on logs.

**Parameters:**
- `logs` (list): Parsed log events
- `token_budget` (int): Available tokens

**Returns:**
- `dict`: RCA analysis result

**Result Structure:**
```python
{
    "root_cause": "description",
    "confidence": 0.95,
    "affected_services": ["service1", "service2"],
    "timeline": "event sequence",
    "contributing_factors": [...],
    "recommendations": [...],
    "severity": "critical"
}
```

### generate_questions(analysis)
Generate follow-up questions for investigation.

**Parameters:**
- `analysis` (dict): RCA analysis

**Returns:**
- `list`: Question strings

### format_report(analysis)
Create human-readable RCA report.

**Parameters:**
- `analysis` (dict): RCA analysis

**Returns:**
- `str`: Formatted report

### estimate_impact(analysis)
Estimate business impact of issue.

**Parameters:**
- `analysis` (dict): RCA analysis

**Returns:**
- `dict`: Impact assessment

## Response Codes
- `HIGH_CONFIDENCE` - 0.9+
- `MEDIUM_CONFIDENCE` - 0.6-0.9
- `LOW_CONFIDENCE` - <0.6
