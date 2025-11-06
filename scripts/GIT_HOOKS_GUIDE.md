# Git Hooks and Code Formatting Guide

This guide explains the Git hooks and code formatting setup for the Vertex AR project.

## Overview

The Vertex AR project uses pre-commit hooks to ensure code quality and consistency. These hooks automatically run before each commit to:

- Format code with Black
- Sort imports with isort
- Check for common issues (trailing whitespace, merge conflicts, etc.)
- Run linting and security checks
- Execute tests

## Quick Start

### 1. Initial Setup

Run the setup script to configure your development environment:

```bash
./scripts/setup-dev.sh
```

This will:
- Install all development dependencies
- Install pre-commit hooks
- Create configuration files
- Set up helper scripts

### 2. Manual Installation

If you prefer to set up manually:

```bash
# Install development dependencies
pip install -r vertex-ar/requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

## Available Tools

### Code Formatters

#### Black
- **Purpose**: Opinionated code formatter for Python
- **Configuration**: Line length 127, Python 3.11+ target
- **Usage**: `black vertex-ar/ --line-length 127`

#### isort
- **Purpose**: Import statement organizer
- **Configuration**: Black profile, line length 127
- **Usage**: `isort vertex-ar/ --profile black --line-length 127`

### Linters

#### flake8
- **Purpose**: Python code linter
- **Configuration**: Max line length 127, ignores E203 and W503
- **Usage**: `flake8 vertex-ar/ --max-line-length=127 --extend-ignore=E203,W503`

#### mypy
- **Purpose**: Static type checker
- **Configuration**: Ignore missing imports, no strict optional
- **Usage**: `mypy vertex-ar/app/ --ignore-missing-imports --no-strict-optional`

#### bandit
- **Purpose**: Security linter for Python
- **Configuration**: Scans vertex-ar/app/, outputs JSON report
- **Usage**: `bandit -r vertex-ar/app/ -f json -o bandit-report.json`

### Testing

#### pytest
- **Purpose**: Test runner with coverage
- **Configuration**: Coverage for app/, HTML reports, 80% threshold
- **Usage**: `pytest vertex-ar/tests/ --cov=app --cov-report=term-missing --cov-report=html`

### Security

#### safety
- **Purpose**: Check for known security vulnerabilities in dependencies
- **Usage**: `safety check --json`

## Pre-commit Hooks Configuration

The `.pre-commit-config.yaml` file contains the following hooks:

### Basic Hooks
- `trailing-whitespace`: Remove trailing whitespace
- `end-of-file-fixer`: Ensure files end with newline
- `check-yaml`: Validate YAML syntax
- `check-added-large-files`: Prevent large files from being committed
- `check-case-conflict`: Check for case conflicts on case-insensitive filesystems
- `check-merge-conflict`: Check for merge conflict markers
- `debug-statements`: Prevent debug statements from being committed
- `check-docstring-first`: Ensure docstrings come first

### Code Quality Hooks
- `black`: Format Python code
- `isort`: Sort imports
- `flake8`: Lint Python code
- `mypy`: Type checking
- `bandit`: Security scanning

### Local Hooks
- `pytest-check`: Run tests
- `safety-check`: Check dependencies for vulnerabilities

## Usage

### Running Hooks Manually

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run all hooks on staged files
pre-commit run

# Run specific hook
pre-commit run black --all-files

# Run hooks on specific files
pre-commit run --files vertex-ar/app/main.py
```

### Skipping Hooks

If you need to skip hooks (not recommended):

```bash
# Skip all hooks for one commit
git commit --no-verify

# Skip specific hook
SKIP=black git commit
```

## Editor Integration

### VS Code

The project includes VS Code settings in `.vscode/settings.json`:

- Automatic formatting on save
- Black as Python formatter
- Flake8 and MyPy linting enabled
- Import organization on save

### Other Editors

Most editors support pre-commit hooks and can be configured to:

- Run Black on save
- Sort imports automatically
- Show linting errors
- Integrate with Git hooks

## Configuration Files

### `.pre-commit-config.yaml`
Main configuration for pre-commit hooks.

### `pyproject.toml`
Configuration for Black, isort, mypy, and pytest.

### `.editorconfig`
Editor-agnostic configuration for consistent formatting.

## Helper Scripts

The project includes several helper scripts in `scripts/`:

### `setup-dev.sh`
Initial development environment setup.

### `format-code.sh`
Format all code with Black and isort.

### `lint-code.sh`
Run all linters and security checks.

### `run-tests.sh`
Run tests with coverage reporting.

## Best Practices

### 1. Commit Workflow
1. Make your changes
2. Stage files with `git add`
3. Commit with `git commit` (hooks run automatically)
4. If hooks fail, fix the issues and try again

### 2. Code Style
- Follow Black formatting (no manual formatting needed)
- Let isort handle import organization
- Keep lines under 127 characters
- Use type hints where possible

### 3. Testing
- Write tests for new features
- Ensure all tests pass before committing
- Maintain code coverage above 80%

### 4. Security
- Run bandit security checks regularly
- Keep dependencies updated
- Review safety reports for vulnerabilities

## Troubleshooting

### Common Issues

#### Hooks Not Running
```bash
# Reinstall hooks
pre-commit install

# Check hook status
pre-commit run --all-files
```

#### Formatting Issues
```bash
# Format manually
./scripts/format-code.sh

# Check specific file
black --check vertex-ar/app/main.py
```

#### Import Sorting Issues
```bash
# Sort imports manually
isort vertex-ar/app/main.py

# Check specific file
isort --check-only vertex-ar/app/main.py
```

#### Type Checking Issues
```bash
# Run mypy manually
mypy vertex-ar/app/

# Ignore specific errors
mypy vertex-ar/app/ --ignore-missing-imports
```

### Updating Hooks

```bash
# Update to latest versions
pre-commit autoupdate

# Run updated hooks
pre-commit run --all-files
```

## Contributing

When contributing to the project:

1. Follow the existing code style (enforced by hooks)
2. Write tests for new functionality
3. Ensure all hooks pass before submitting PRs
4. Update documentation as needed
5. Consider adding new hooks if they improve code quality

## Configuration Customization

### Adding New Hooks

Edit `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/example/hook-repo
    rev: v1.0.0
    hooks:
      - id: hook-name
        args: [--option, value]
```

### Modifying Existing Hooks

Update the `args` section for any hook in `.pre-commit-config.yaml`.

### Excluding Files

Add `exclude` patterns to hook configurations:

```yaml
- id: black
  exclude: ^vertex-ar/app/legacy/.*\.py$
```

## Performance

### Optimizing Hook Performance

1. Use `pass_filenames: false` for hooks that scan the entire project
2. Limit `always_run: true` hooks
3. Use appropriate file exclusions
4. Cache dependencies where possible

### Running Hooks Selectively

```bash
# Run only on changed files
pre-commit run

# Run only specific hooks
pre-commit run black isort

# Run on specific directory
pre-commit run --files vertex-ar/app/*.py
```

## Security Considerations

- Pre-commit hooks run with your user permissions
- Review hook repositories before adding them
- Keep hook versions updated
- Use HTTPS URLs for hook repositories
- Review hook output for sensitive information

## Resources

- [Pre-commit Documentation](https://pre-commit.com/)
- [Black Documentation](https://black.readthedocs.io/)
- [isort Documentation](https://isort.readthedocs.io/)
- [flake8 Documentation](https://flake8.pycqa.org/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [bandit Documentation](https://bandit.readthedocs.io/)

## Support

If you encounter issues:

1. Check this documentation first
2. Run `pre-commit run --all-files` to see detailed output
3. Check the `.pre-commit-cache` directory for cached issues
4. Ask in the project discussions or issues
5. Review the pre-commit documentation at https://pre-commit.com/
