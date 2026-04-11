# Contributing

Thank you for your interest in contributing to novaml!

## Development Setup

```bash
git clone https://github.com/Shendu09/novaml.git
cd novaml
pip install -e ".[all,dev]"
```

## Running Tests

```bash
make test
```

## Code Style

We use `ruff` for linting and `mypy` for type checking.

```bash
make lint
make format
```

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat: add new feature`
- `fix: fix a bug`
- `docs: documentation changes`
- `test: add tests`
- `refactor: code restructuring`
- `perf: performance improvements`

## Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests and linting
5. Push and create a PR

## Reporting Issues

Please include:
- Python version
- novaml version
- Steps to reproduce
- Expected vs actual behavior
