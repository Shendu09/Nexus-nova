# Triage System

## Overview
Root cause analysis and issue triage pipeline.

## Analysis Pipeline
1. Collect normalized logs
2. Send to Nova 2 Lite for analysis
3. Extract RCA findings
4. Generate recommendations
5. Format triage report

## Prompts
- Initial analysis prompt
- Follow-up question generation
- Recommendation synthesis
- Report formatting

## Output Structure
```json
{
  "root_cause": "description",
  "confidence": 0.95,
  "affected_services": ["service1"],
  "timeline": "event sequence",
  "recommendations": ["action1"],
  "severity": "critical"
}
```

## Functions
- `analyze_logs_for_rca()` - Perform RCA
- `generate_questions()` - Generate questions
- `format_report()` - Create final report
- `estimate_impact()` - Estimate severity
