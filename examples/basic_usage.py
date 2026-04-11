"""Basic usage example."""

import novaml

# Example logs
logs = [
    "INFO: Application started",
    "INFO: Processing request",
    "ERROR: Connection timeout",
    "ERROR: Failed to reach database",
    "CRITICAL: Out of memory error",
    "ERROR: Stack trace follows",
]

# Full triage
result = novaml.triage(logs)
print(result)

# Just detect anomalies
anomalies = novaml.detect(logs)
print(f"Found {len(anomalies.anomalous_indices)} anomalies")

# Explain why
explanation = novaml.explain(logs)
print(f"Top signals: {explanation.top_signals}")
