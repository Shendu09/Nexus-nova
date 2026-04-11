"""CLI usage guide."""

# Full triage
novaml triage --file my_logs.txt --output json

# Just detect anomalies
novaml detect --file my_logs.txt

# Train a model
novaml train --log-file healthy_logs.txt --save-dir ./models

# Start REST API server
novaml serve --host 0.0.0.0 --port 8000

# Show version
novaml version
