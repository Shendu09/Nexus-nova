# Configuration API Reference

## Functions

### load_config(source='env')
Load configuration from specified source.

**Parameters:**
- `source` (str): 'env', 'file', or 'aws_ssm'

**Returns:**
- `Config`: Configuration object

### get_setting(key, default=None)
Retrieve individual setting value.

**Parameters:**
- `key` (str): Setting key (dot notation supported)
- `default`: Default value if not found

**Returns:**
- Value of setting

### validate_config()
Validate all required settings present.

**Raises:**
- `ConfigError`: If required setting missing

## Settings Dict Structure
```python
{
    'aws': {'region': str, 'account_id': str},
    'logging': {'level': str, 'format': str},
    'analysis': {'timeout': int, 'budget': int},
    'notification': {'channels': list},
    'voice': {'enabled': bool, 'timeout': int}
}
```
