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

# Load environment variables if .env file exists
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    export $(grep -v '^#' .env | xargs)
fi

# Calculate default workers based on CPU count
DEFAULT_WORKERS=$(python3 -c "import psutil; print((2 * (psutil.cpu_count() or 1)) + 1)")
WORKERS=${UVICORN_WORKERS:-$DEFAULT_WORKERS}

# Start the server with tuned settings
echo "Starting server on http://localhost:${APP_PORT:-8000}"
echo "Workers: $WORKERS"
echo "Keep-alive timeout: ${UVICORN_TIMEOUT_KEEP_ALIVE:-5}s"
echo "Graceful shutdown timeout: ${UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN:-30}s"

# Build uvicorn command with optional flags
UVICORN_CMD="uvicorn main:app --host ${APP_HOST:-0.0.0.0} --port ${APP_PORT:-8000}"

# Add production settings if not in development mode
if [ "${ENVIRONMENT:-development}" != "development" ]; then
    UVICORN_CMD="$UVICORN_CMD --workers $WORKERS"
    UVICORN_CMD="$UVICORN_CMD --timeout-keep-alive ${UVICORN_TIMEOUT_KEEP_ALIVE:-5}"
    
    if [ "${UVICORN_LIMIT_CONCURRENCY:-0}" != "0" ]; then
        UVICORN_CMD="$UVICORN_CMD --limit-concurrency ${UVICORN_LIMIT_CONCURRENCY}"
    fi
    
    UVICORN_CMD="$UVICORN_CMD --backlog ${UVICORN_BACKLOG:-2048}"
    
    if [ "${UVICORN_PROXY_HEADERS:-true}" = "true" ]; then
        UVICORN_CMD="$UVICORN_CMD --proxy-headers"
    fi
    
    UVICORN_CMD="$UVICORN_CMD --timeout-graceful-shutdown ${UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN:-30}"
else
    # Development mode with reload
    UVICORN_CMD="$UVICORN_CMD --reload"
    echo "Development mode: using --reload (single worker)"
fi

echo "Running: $UVICORN_CMD"
exec $UVICORN_CMD