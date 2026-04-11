"""Kubernetes log analysis example."""

import novaml

# Example Kubernetes logs
k8s_logs = [
    "INFO: Pod started",
    "INFO: Container ready",
    "ERROR: Liveness probe failed",
    "ERROR: CrashLoopBackOff - restarting",
    "CRITICAL: OOMKilled by Kubernetes",
    "ERROR: Back-off restarting failed container",
]

result = novaml.triage(k8s_logs)
print(f"Severity: {result.severity}")
print(f"Root cause: {result.root_cause}")
