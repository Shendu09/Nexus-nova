# Notifier API Reference

## Functions

### send_notification(notification, channels=None)
Send notification to configured channels.

**Parameters:**
- `notification` (dict): Notification content
- `channels` (list): Target channels

**Returns:**
- `dict`: Delivery status per channel

**Notification Structure:**
```python
{
    "type": "alert|rca_report|voice_confirmation",
    "title": "string",
    "body": "string",
    "severity": "info|warning|critical",
    "metadata": {...}
}
```

### format_message(notification, channel)
Format notification for specific channel.

**Parameters:**
- `notification` (dict): Notification object
- `channel` (str): Target channel

**Returns:**
- `str`: Formatted message

### retry_failed(notification_id)
Retry sending failed notification.

**Parameters:**
- `notification_id` (str): Notification ID

**Returns:**
- `bool`: Retry status

## Supported Channels
- `email` - SNS email
- `slack` - Slack webhook
- `pagerduty` - PagerDuty API
- `sms` - SNS SMS
- `webhook` - Custom webhook
