#!/bin/bash

# Vertex AR Development Environment Setup Script
# This script sets up the development environment with Git hooks and code formatting

set -e  # Exit on any error

echo "🚀 Setting up Vertex AR development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "vertex-ar/app/main.py" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    print_error "Python 3.11+ is required. Found Python $python_version"
    exit 1
fi

print_success "Python version check passed: $python_version"

# Check if virtual environment is active
if [[ "$VIRTUAL_ENV" == "" ]]; then
    print_warning "No virtual environment detected. Creating one..."

    # Create virtual environment
    python3 -m venv .venv
    source .venv/bin/activate
    print_success "Virtual environment created and activated"
else
    print_success "Virtual environment is active: $VIRTUAL_ENV"
fi

# Upgrade pip
print_status "Upgrading pip..."
pip install --break-system-packages --upgrade pip

# Install development dependencies
print_status "Installing development dependencies..."
if [ -f "vertex-ar/requirements-dev.txt" ]; then
    pip install --break-system-packages -r vertex-ar/requirements-dev.txt
    print_success "Development dependencies installed"
else
    print_error "Development requirements file not found"
    exit 1
fi

# Install main dependencies
print_status "Installing main dependencies..."
if [ -f "vertex-ar/requirements.txt" ]; then
    pip install --break-system-packages -r vertex-ar/requirements.txt
    print_success "Main dependencies installed"
else
    print_error "Main requirements file not found"
    exit 1
fi

# Install pre-commit hooks
print_status "Installing pre-commit hooks..."
pre-commit install
print_success "Pre-commit hooks installed"

# Create scripts directory if it doesn't exist
mkdir -p scripts

# Create helper scripts
print_status "Creating helper scripts..."

# Format code script
cat > scripts/format-code.sh << 'EOF'
#!/bin/bash
# Format code with Black and isort

echo "🎨 Formatting code..."

# Run Black
echo "Running Black..."
black vertex-ar/ --line-length=127

# Run isort
echo "Running isort..."
isort vertex-ar/ --profile=black --line-length=127

echo "✅ Code formatting complete!"
EOF

# Lint code script
cat > scripts/lint-code.sh << 'EOF'
#!/bin/bash
# Run linting tools

echo "🔍 Running linting tools..."

# Run flake8
echo "Running flake8..."
flake8 vertex-ar/ --max-line-length=127 --extend-ignore=E203,W503 || echo "⚠️  flake8 found issues"

# Run mypy
echo "Running mypy..."
mypy vertex-ar/app/ --ignore-missing-imports --no-strict-optional || echo "⚠️  mypy found issues"

# Run bandit
echo "Running bandit..."
bandit -r vertex-ar/app/ -f json -o bandit-report.json || echo "⚠️  bandit found issues"

echo "✅ Linting complete! Check reports for details."
EOF

# Run tests script
cat > scripts/run-tests.sh << 'EOF'
#!/bin/bash
# Run tests with coverage

echo "🧪 Running tests..."

cd vertex-ar
python -m pytest tests/ --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=80

echo "✅ Tests complete! Check htmlcov/index.html for detailed coverage report."
EOF

# Update pre-commit script
cat > scripts/update-pre-commit.sh << 'EOF'
#!/bin/bash
# Update pre-commit hooks

echo "🔄 Updating pre-commit hooks..."

pre-commit autoupdate

echo "✅ Pre-commit hooks updated!"
EOF

# Make scripts executable
chmod +x scripts/*.sh

print_success "Helper scripts created in scripts/"

# Create .editorconfig if it doesn't exist
if [ ! -f ".editorconfig" ]; then
    print_status "Creating .editorconfig..."
    cat > .editorconfig << 'EOF'
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.py]
indent_style = space
indent_size = 4
max_line_length = 127

[*.{yml,yaml}]
indent_style = space
indent_size = 2

[*.{json,js,html,css}]
indent_style = space
indent_size = 2

[Makefile]
indent_style = tab
EOF
    print_success ".editorconfig created"
fi

# Create VS Code settings if directory exists
if [ -d ".vscode" ]; then
    print_status "Updating VS Code settings..."
    cat > .vscode/settings.json << 'EOF'
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "python.linting.flake8Args": [
        "--max-line-length=127",
        "--extend-ignore=E203,W503"
    ],
    "python.linting.mypyArgs": [
        "--ignore-missing-imports",
        "--no-strict-optional"
    ],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".pytest_cache": true,
        ".mypy_cache": true,
        ".coverage": true,
        "htmlcov": true,
        ".DS_Store": true
    }
}
EOF
    print_success "VS Code settings updated"
fi

# Run initial formatting
print_status "Running initial code formatting..."
./scripts/format-code.sh

# Test pre-commit hooks
print_status "Testing pre-commit hooks..."
if pre-commit run --all-files; then
    print_success "Pre-commit hooks are working correctly!"
else
    print_warning "Some pre-commit hooks had issues. Check the output above."
fi

# Create development documentation
print_status "Creating development documentation..."
cat > DEVELOPMENT.md << 'EOF'
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
EOF

print_success "Development documentation created"

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Make your changes in the vertex-ar/ directory"
echo "2. Use the helper scripts in scripts/ to format and test"
echo "3. Commit your changes - hooks will run automatically"
echo ""
echo "Available commands:"
echo "  ./scripts/format-code.sh    - Format code"
echo "  ./scripts/lint-code.sh      - Run linting"
echo "  ./scripts/run-tests.sh      - Run tests"
echo "  ./scripts/update-pre-commit.sh - Update hooks"
echo ""
echo "📚 See DEVELOPMENT.md for more information"
echo "📚 See scripts/GIT_HOOKS_GUIDE.md for detailed documentation"
