# Voice Handler API Reference

## Functions

### start_voice_session(call_id, rca_brief)
Initialize voice investigation session.

**Parameters:**
- `call_id` (str): Amazon Connect call ID
- `rca_brief` (str): Initial briefing

**Returns:**
- `dict`: Session object

### process_voice_input(session_id, user_input)
Process user voice input and generate response.

**Parameters:**
- `session_id` (str): Session ID
- `user_input` (str): User's spoken input

**Returns:**
- `str`: Voice response text

### get_voice_data(session_id, key)
Retrieve prefetched data for voice call.

**Parameters:**
- `session_id` (str): Session ID
- `key` (str): Data key

**Returns:**
- `dict`: Data for voice response

### end_voice_session(session_id)
Terminate voice session.

**Parameters:**
- `session_id` (str): Session ID

**Returns:**
- `dict`: Session summary

## Voice Pipeline
- Recognition → Processing → Prefetch → Response → Speech

## Supported Actions
- Get metrics
- Get related logs
- Get error details
- Get service status
- Get remediation steps
