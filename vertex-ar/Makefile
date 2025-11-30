# Makefile for Vertex AR development tasks

.PHONY: help install install-dev test test-cov lint format security clean run docker-build docker-run

# Default target
help:
    @echo "Vertex AR Development Commands:"
    @echo ""
    @echo "Setup & Installation:"
    @echo "  install      Install production dependencies"
    @echo "  install-dev  Install development dependencies"
    @echo "  setup        Setup pre-commit hooks"
    @echo ""
    @echo "Development:"
    @echo "  run          Run the application"
    @echo "  format       Format code with black and isort"
    @echo "  lint         Run linting (flake8, mypy)"
    @echo "  test         Run tests"
    @echo "  test-cov     Run tests with coverage"
    @echo ""
    @echo "Quality & Security:"
    @echo "  security     Run security scans (bandit, safety)"
    @echo "  check        Run all quality checks (lint, security, test)"
    @echo ""
    @echo "Docker:"
    @echo "  docker-build Build Docker image"
    @echo "  docker-run   Run with Docker Compose"
    @echo ""
    @echo "Maintenance:"
    @echo "  clean        Clean up temporary files"

# Installation
install:
    pip install -r requirements.txt

install-dev: install
    pip install -r requirements-dev.txt
    pre-commit install

setup: install-dev

# Development
run:
    @echo "Starting Vertex AR in development mode..."
    @echo "Workers: 1 (development mode with --reload)"
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production run (respects env settings)
run-production:
    @echo "Starting Vertex AR in production mode..."
    @echo "Reading configuration from environment..."
    python -m uvicorn app.main:app \
        --host ${APP_HOST:-0.0.0.0} \
        --port ${APP_PORT:-8000} \
        --workers ${UVICORN_WORKERS:-$(python -c "import psutil; print((2 * (psutil.cpu_count() or 1)) + 1)")} \
        --timeout-keep-alive ${UVICORN_TIMEOUT_KEEP_ALIVE:-5} \
        --limit-concurrency ${UVICORN_LIMIT_CONCURRENCY:-0} \
        --backlog ${UVICORN_BACKLOG:-2048} \
        $(if [ "${UVICORN_PROXY_HEADERS:-true}" = "true" ]; then echo "--proxy-headers"; fi) \
        --timeout-graceful-shutdown ${UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN:-30}

# Code formatting
format:
    black --line-length 127 app/ tests/
    isort --profile black --line-length 127 app/ tests/

# Linting
lint:
    @echo "Running flake8..."
    flake8 app/ tests/ --max-line-length=127 --extend-ignore=E203,W503
    @echo "Running mypy..."
    mypy app/ --ignore-missing-imports --no-strict-optional

# Testing
test:
    pytest tests/ -v

test-cov:
    pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

test-integration:
    pytest ../test_*.py -v

test-all: test test-integration

# Security
security:
    @echo "Running bandit security scan..."
    bandit -r app/ -f json -o bandit-report.json || true
    @echo "Running safety dependency check..."
    safety check --json --output safety-report.json || true

# Quality checks
check: lint security test-cov

# Docker
docker-build:
    docker build -f ../Dockerfile.app -t vertex-ar:latest ..

docker-run:
    docker-compose -f ../docker-compose.yml up -d

docker-stop:
    docker-compose -f ../docker-compose.yml down

docker-logs:
    docker-compose -f ../docker-compose.yml logs -f

# Database
db-backup:
    @echo "Creating database backup..."
    cp app_data.db app_data_backup_$$(date +%Y%m%d_%H%M%S).db

db-reset:
    @echo "Resetting database..."
    rm -f app_data.db
    python -c "from app.database import Database; Database('app_data.db')"

# Performance
perf-test:
    @echo "Running performance tests..."
    locust --headless --users 10 --spawn-rate 2 --run-time 60s --host http://localhost:8000

# Documentation
docs:
    @echo "Generating documentation..."
    cd ../docs && make html

docs-serve:
    @echo "Serving documentation..."
    cd ../docs/_build/html && python -m http.server 8080

# Cleanup
clean:
    @echo "Cleaning up..."
    find . -type f -name "*.pyc" -delete
    find . -type d -name "__pycache__" -delete
    find . -type d -name "*.egg-info" -exec rm -rf {} +
    rm -rf .coverage htmlcov/ .pytest_cache/ bandit-report.json safety-report.json
    rm -rf dist/ build/

# Full development workflow
dev: format lint test-cov

# Production deployment
deploy-staging:
    @echo "Deploying to staging..."
    # Add staging deployment commands here

deploy-production:
    @echo "Deploying to production..."
    # Add production deployment commands here

# Version management
version-patch:
    @echo "Bumping patch version..."
    bump2version patch

version-minor:
    @echo "Bumping minor version..."
    bump2version minor

version-major:
    @echo "Bumping major version..."
    bump2version major

# Migration helpers (for future database migrations)
migrate-create:
    @echo "Creating migration file..."
    # Add migration creation commands here

migrate-up:
    @echo "Running database migrations..."
    # Add migration commands here

# Health check
health:
    @echo "Checking application health..."
    curl -f http://localhost:8000/health || echo "Application not running"

# Continuous integration helper
ci: install-dev lint security test-cov
    @echo "All CI checks passed!"