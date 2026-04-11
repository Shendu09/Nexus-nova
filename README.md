"""README for novaml library."""

# novaml

**AI-powered log intelligence. Zero cloud. One line.**

```bash
pip install novaml
```

```python
import novaml

result = novaml.triage(open("app.log").readlines())
print(result)
```

```
┌─────────────────── novaml triage report ───────────────────┐
│ CRITICAL  confidence: 94%                                    │
│                                                              │
│ Root cause: Database connection pool exhausted after OOM     │
│                                                              │
│ Next steps:                                                  │
│   1. Restart the connection pool manager                     │
│   2. Check available heap memory                             │
│   3. Review recent deployments                               │
│                                                              │
│ Anomalous lines: 23/847 | 1,240ms | mistral                 │
└─────────────────────────────────────────────────────────────┘
```

## Why novaml?

| Feature | novaml | Datadog | Elastic | Splunk |
|---------|--------|---------|---------|--------|
| Free | ✅ | ❌ | ❌ | ❌ |
| No cloud | ✅ | ❌ | ❌ | ❌ |
| One-line API | ✅ | ❌ | ❌ | ❌ |
| Explainability | ✅ | partial | ❌ | ❌ |
| Auto-trains on your logs | ✅ | ❌ | ❌ | ❌ |
| pip install | ✅ | ❌ | ❌ | ❌ |

## Install

```bash
# Core
pip install novaml

# With forecasting
pip install "novaml[forecast]"

# With REST API server
pip install "novaml[server]"

# Everything
pip install "novaml[all]"
```

## Train on your logs

```python
# No labels needed — unsupervised
novaml.train(open("my_normal_logs.txt").readlines())
```

## Serve as REST API

```python
novaml.serve()  # → http://localhost:8000/triage
```

## Setup

Before using novaml, install Ollama and pull the Mistral model:

```bash
# Install Ollama (one time)
curl -fsSL https://ollama.com/install.sh | sh

# Pull Mistral model
ollama pull mistral

# Try it
ollama serve  # runs on localhost:11434
```

## Features

- **Zero cloud dependency** — runs entirely offline on your machine
- **One-line API** — entire library compressed into readable functions
- **Smart fallbacks** — every component has a rule-based backup
- **Explainability** — tells you WHY logs are anomalous, not just THAT they are
- **Auto-training** — learns your log patterns with zero labeling effort
- **Production-ready** — Docker, FastAPI, async, type hints, comprehensive tests

## API Functions

- `novaml.triage(logs)` — Full AI triage with root cause + next steps
- `novaml.detect(logs)` — Anomaly detection only
- `novaml.explain(logs)` — Why is this anomalous?
- `novaml.forecast(metric_df)` — Time-series anomaly forecast
- `novaml.train(logs)` — Train on your own logs
- `novaml.serve()` — Start REST API server

## License

Apache-2.0
