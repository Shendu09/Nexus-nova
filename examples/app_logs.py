"""Application server log analysis example."""

import novaml

# Application logs
app_logs = [
    "INFO: App starting on port 8080",
    "INFO: Connected to database",
    "ERROR: NullPointerException in UserService",
    "ERROR: Exception in thread 'http-handler'",
    "CRITICAL: Out of heap memory",
    "INFO: Graceful shutdown...",
]

result = novaml.triage(app_logs)
print(f"Severity: {result.severity}")
print(f"Next steps: {result.next_steps}")
