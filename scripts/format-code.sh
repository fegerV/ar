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
