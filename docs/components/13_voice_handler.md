# Voice Investigation Handler

## Overview
Manages real-time voice conversation for interactive investigation.

## Features
- Speech-to-text conversion
- Interactive dialogue
- Context-aware responses
- Real-time data fetching
- Call quality monitoring

## Voice Pipeline
1. Amazon Connect initiates call
2. Nova 2 Sonic handles speech
3. Predict and prefetch data
4. Generate context-aware responses
5. Handle user interruptions
6. Graceful call termination

## Integration Points
- Amazon Connect (voice)
- Nova 2 Sonic (speech model)
- Prefetch system (data)
- DynamoDB (state)

## Configuration
```python
voice_enabled = True
speech_model = "nova-2-sonic"
language = "en-US"
timeout = 600
```

## Error Handling
- Handle connection drops
- Fallback to text mode
- Graceful degradation
