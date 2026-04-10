# Caller API Reference

## Functions

### initiate_call(phone_number, rca_brief, session_id)
Initiate outbound call with on-call engineer.

**Parameters:**
- `phone_number` (str): Target phone number
- `rca_brief` (str): RCA briefing content
- `session_id` (str): Session identifier

**Returns:**
- `dict`: Call initiation result with call ID

### transfer_call(call_id, target_queue)
Transfer active call to another queue.

**Parameters:**
- `call_id` (str): Current call ID
- `target_queue` (str): Target queue name

**Returns:**
- `bool`: Transfer success status

### end_call(call_id)
Terminate active call.

**Parameters:**
- `call_id` (str): Call ID to terminate

**Returns:**
- `bool`: Termination success

## Events
- `call_initiated`
- `call_connected`
- `call_disconnected`
- `call_transferred`
