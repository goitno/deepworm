# Contributing to deepworm

Thanks for your interest in contributing to deepworm!

## Development Setup

```bash
git clone https://github.com/bysiber/deepworm.git
cd deepworm
pip install -e "."
pip install pytest
```

## Running Tests

```bash
pytest tests/ -v
```

## Making Changes

1. Fork the repo
2. Create a branch from `main`
3. Make your changes
4. Add tests if applicable
5. Run tests to make sure nothing is broken
6. Submit a PR

## Code Style

- Use type hints
- Keep functions focused and small
- Follow existing patterns in the codebase
- Docstrings for public functions

## Reporting Bugs

Open an issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Python version and OS

## Feature Requests

Open an issue describing the feature and why it would be useful. For larger features, it's worth discussing before starting implementation.
