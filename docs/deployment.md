"""Deployment guide."""

# novaml Deployment Guide

## Local Development

```bash
make install
make test
novaml serve
```

## Docker Deployment

```bash
docker-compose up --build
# API available at http://localhost:8000
```

## Production Checklist

- [ ] Change API_SECRET_KEY in .env
- [ ] Setup Ollama with mistral model
- [ ] Configure log storage
- [ ] Setup monitoring/alerts
- [ ] Use HTTPS/TLS
- [ ] Configure rate limiting
- [ ] Setup model versioning
- [ ] Configure backup models
