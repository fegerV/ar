# Development Guide

This guide helps you set up and work with the Vertex AR development environment.

## Quick Start

1. Run the setup script:
   ```bash
   ./scripts/setup-dev.sh
   ```

2. Make your changes:
   ```bash
   # Edit files in vertex-ar/
   ```

3. Commit your changes:
   ```bash
   git add .
   git commit -m "Your commit message"
   ```

   The pre-commit hooks will automatically format and check your code.

## Available Scripts

- `./scripts/format-code.sh` - Format code with Black and isort
- `./scripts/lint-code.sh` - Run linting tools
- `./scripts/run-tests.sh` - Run tests with coverage
- `./scripts/update-pre-commit.sh` - Update pre-commit hooks

## Manual Commands

### Formatting
```bash
black vertex-ar/ --line-length=127
isort vertex-ar/ --profile=black --line-length=127
```

### Linting
```bash
flake8 vertex-ar/ --max-line-length=127 --extend-ignore=E203,W503
mypy vertex-ar/app/ --ignore-missing-imports --no-strict-optional
bandit -r vertex-ar/app/
```

### Testing
```bash
cd vertex-ar
pytest tests/ --cov=app --cov-report=term-missing
```

## Troubleshooting

If hooks fail:
1. Check the error messages
2. Fix the reported issues
3. Try committing again

To skip hooks (not recommended):
```bash
git commit --no-verify
```

For more details, see `scripts/GIT_HOOKS_GUIDE.md`.
