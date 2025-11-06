#!/bin/bash
# Run tests with coverage

echo "🧪 Running tests..."

cd vertex-ar
python -m pytest tests/ --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=80

echo "✅ Tests complete! Check htmlcov/index.html for detailed coverage report."
