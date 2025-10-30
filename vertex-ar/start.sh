#!/bin/bash

# Simple AR Backend Startup Script for Vertex-AR (Simplified)
# Based on Stogram approach but maintaining core Vertex-AR functionality

echo "Starting Vertex-AR (Simplified)..."
echo "====================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements-simple.txt

# Create necessary directories
mkdir -p storage/ar_content
mkdir -p storage/previews
mkdir -p storage/nft-markers

# Start the server
echo "Starting server on http://localhost:8000"
uvicorn main:app --host 0.0.0.0 --port 800 --reload