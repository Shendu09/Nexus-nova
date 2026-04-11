"""Troubleshooting guide."""

# FAQ & Troubleshooting

## Q: Ollama not found

Install Ollama: https://ollama.com

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull mistral
```

## Q: Out of memory

Reduce batch_size and window_size in config.

## Q: Slow inference

Use CPU-optimized PyTorch or ONNX export.

## Q: Model not updating

Clear model cache: `rm -rf ~/.novaml/models`

## Q: API authentication failing

Check X-API-Key header and API_SECRET_KEY setting.
