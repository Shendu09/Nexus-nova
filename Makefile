.PHONY: install test lint format build serve clean help

help:
	@echo "novaml — AI-powered log intelligence"
	@echo ""
	@echo "Available targets:"
	@echo "  install       Install the package with dev dependencies"
	@echo "  test          Run pytest"
	@echo "  lint          Check with ruff and mypy"
	@echo "  format        Auto-format with ruff and black"
	@echo "  build         Build distribution packages"
	@echo "  serve         Start dev server"
	@echo "  clean         Remove build artifacts and cache"

install:
	pip install -e ".[all,dev]"

test:
	pytest tests/ -v --tb=short --cov=novaml

lint:
	ruff check novaml tests
	mypy novaml 2>/dev/null || true

format:
	ruff check --fix novaml tests
	ruff format novaml tests 2>/dev/null || true

build:
	hatch build

serve:
	python -m novaml.server

clean:
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
