"""Configuration guide."""

# Configuration

All configuration via environment variables:

```bash
# LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral

# Embeddings
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIM=384

# Anomaly Detection
ANOMALY_THRESHOLD=0.75
LSTM_WINDOW_SIZE=16
LSTM_STRIDE=4

# API
API_HOST=0.0.0.0
API_PORT=8000
API_SECRET_KEY=your-secret-key

# Paths
MODELS_DIR=~/.novaml/models
LOGS_DIR=~/.novaml/logs
```
