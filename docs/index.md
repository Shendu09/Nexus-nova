# novaml

[![CI](https://github.com/Shendu09/novaml/actions/workflows/ci.yml/badge.svg)](https://github.com/Shendu09/novaml/actions)
[![Coverage](https://codecov.io/gh/Shendu09/novaml/branch/main/graph/badge.svg)](https://codecov.io/gh/Shendu09/novaml)
[![PyPI version](https://badge.fury.io/py/novaml.svg)](https://badge.fury.io/py/novaml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

**AI-powered log intelligence. Zero cloud. One line.**

```python
import novaml

result = novaml.triage(open("app.log").readlines())
print(result)
```

## Features

- ✅ **Zero cloud dependency** — runs entirely offline
- ✅ **One-line API** — entire library in readable functions
- ✅ **Smart fallbacks** — every component has a rule-based backup
- ✅ **Explainability** — tells you WHY logs are anomalous
- ✅ **Auto-training** — learns your log patterns with zero labels
- ✅ **Production-ready** — Docker, FastAPI, async, tests, type hints

## Quick Start

```bash
pip install novaml
```

## Documentation

- [Quickstart](docs/index.md)
- [API Reference](docs/api_reference.md)
- [Deployment Guide](docs/deployment.md)
- [CLI Usage](docs/cli_guide.md)

## Architecture

- embeddings: `sentence-transformers`
- anomaly detection: `LSTM` + `Autoencoder`
- LLM triage: `Ollama` (local Mistral)
- classification: `DistilBERT`
- forecasting: `Prophet`
- API: `FastAPI`

## License

Apache-2.0
