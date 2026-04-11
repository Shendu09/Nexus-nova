"""Train on your own logs example."""

import novaml

# Load your normal logs
with open("my_healthy_logs.txt") as f:
    healthy_logs = f.readlines()

# Train the anomaly detector
print("Training anomaly detector...")
stats = novaml.train(healthy_logs, save_dir="./my_models")

print(f"Model saved: {stats['model_path']}")
print(f"Threshold: {stats.get('threshold', 'N/A')}")

# Now triage new logs
new_logs = ["ERROR: Unexpected behavior detected"]
result = novaml.triage(new_logs)
print(f"Severity: {result.severity}")
