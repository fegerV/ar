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
