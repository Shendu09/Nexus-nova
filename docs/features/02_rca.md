# Root Cause Analysis Feature

## Overview
Generates intelligent root cause analysis using Nova 2 Lite reasoning model.

## Analysis Process
1. **Log Preprocessing**: Normalize and structure anomalous logs
2. **Context Extraction**: Gather surrounding logs and metrics
3. **Model Invocation**: Send to Nova 2 Lite for analysis
4. **Result Parsing**: Extract findings and recommendations
5. **Report Generation**: Format for consumption

## RCA Report Contents
- Root cause description
- Confidence level (0.0-1.0)
- Affected services
- Event timeline
- Contributing factors
- Recommended actions
- Estimated severity

## Customization
- Custom prompt templates
- Industry-specific analysis modes
- Configurable recommendation type
- Multi-step investigation support
