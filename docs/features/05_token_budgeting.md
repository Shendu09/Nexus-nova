# Token Budget Optimization

## Feature Overview
Intelligently manages token usage across the analysis pipeline.

## Budget Allocation Strategy

### Strategy 1: Raw (Default)
- Include all logs in analysis
- Best when: <2000 logs, <100KB
- Cost: High
- Quality: Highest

### Strategy 2: Selective
- Include top anomalies only
- Best when: 2000-10000 logs
- Cost: Medium
- Quality: High

### Strategy 3: Reduced
- Cordon pre-filtering + top selection
- Best when: >10000 logs
- Cost: Low
- Quality: Good

## Budget Calculation
```
Available = 5000 tokens (default)
Reserve = 1000 (for RCA response)
Usable = 4000 for logs
Per-log = 50 tokens average
Max-logs = 4000 / 50 = 80 logs
```

## Tuning
- Adjust base budget in environment
- Set minimum log requirements
- Configure compression ratios
- Fine-tune thresholds
