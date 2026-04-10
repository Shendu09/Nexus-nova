# Data Flow Specification

## Event Processing Pipeline

### Stage 1: Event Ingestion
```
Input: Lambda Event
├─ Parse event source
├─ Extract log group/stream
├─ Validate permissions
└─ Output: ParsedEvent
```

### Stage 2: Log Retrieval
```
Input: ParsedEvent
├─ Determine time window
├─ Call CloudWatch Logs API
├─ Handle pagination
├─ Apply initial filters
└─ Output: RawLogEvents
```

### Stage 3: Budget Planning
```
Input: RawLogEvents
├─ Estimate content size
├─ Account for model overhead
├─ Determine strategy (raw/reduce)
├─ Reserve tokens for RCA
└─ Output: BudgetPlan
```

### Stage 4: Content Optimization
```
Input: RawLogEvents, BudgetPlan
├─ If raw: Pass through
├─ If reduce: Use Cordon + embeddings
├─ Priority ranking
├─ Select top anomalies
└─ Output: OptimizedLogs
```

### Stage 5: RCA Analysis
```
Input: OptimizedLogs
├─ Send to Nova 2 Lite
├─ Parse response
├─ Extract findings
├─ Generate questions
└─ Output: RCAAnalysis
```

### Stage 6: Notification
```
Input: RCAAnalysis
├─ Format for channels
├─ Send via SNS/APIs
├─ Track delivery
└─ Output: NotificationResult
```

### Stage 7: Voice Pipeline (Optional)
```
Input: RCAAnalysis
├─ Prefetch likely data
├─ Initiate Connect call
├─ Manage conversation
├─ Record session
└─ Output: VoiceSessionData
```

## Error Handling
- Retry policies at each stage
- Fallback mechanisms
- Partial success handling
- Complete failure notifications
