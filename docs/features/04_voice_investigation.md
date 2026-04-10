# Interactive Voice Investigation

## Feature Overview
Enables on-call engineers to investigate issues through natural voice conversation.

## Capabilities
- **Speech Recognition**: AWS transcription of engineer queries
- **Intelligent Responses**: Nova 2 Sonic generates natural responses
- **Context Awareness**: References RCA and prefetched data
- **Follow-up Handling**: Addresses sequential questions
- **Data Integration**: Fetches real-time metrics and logs
- **Call Recording**: Stores conversation for audit

## Voice Pipeline
1. Amazon Connect initiates call
2. Briefing delivered via text-to-speech
3. Engineer asks questions
4. System processes query
5. Fetches relevant data
6. Generates response
7. Text-to-speech delivery
8. Repeat until call ends

## Supported Questions
- "What services are affected?"
- "When did it start?"
- "What caused this?"
- "What are the recommendations?"
- "Pull up error logs for service X"

## Requirements
- Enterprise Amazon Connect setup
- On-call engineer phone number
- Voice-enabled event configuration
