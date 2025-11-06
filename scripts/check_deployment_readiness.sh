#!/bin/bash
# Vertex AR - Deployment Readiness Checker
# This script checks if the application is ready for production deployment

# Don't exit on error - we want to collect all issues
set +e

echo "🔍 Vertex AR - Deployment Readiness Check"
echo "=========================================="
echo ""

ERRORS=0
WARNINGS=0
PASSES=0

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

function pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSES++))
}

function warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

function error() {
    echo -e "${RED}✗${NC} $1"
    ((ERRORS++))
}

echo "1. Checking critical files..."
echo "-------------------------------"

# Check .env.example exists
if [ -f ".env.example" ]; then
    pass ".env.example exists in root"
else
    error ".env.example missing in root"
fi

# Check if .env exists
if [ -f ".env" ]; then
    pass ".env file exists"
else
    warn ".env file not found - will use defaults"
fi

# Check docker-compose.yml
if [ -f "docker-compose.yml" ]; then
    pass "docker-compose.yml exists"
else
    error "docker-compose.yml missing"
fi

# Check backup script
if [ -f "scripts/backup.sh" ]; then
    pass "Backup script exists"
    if [ -x "scripts/backup.sh" ]; then
        pass "Backup script is executable"
    else
        warn "Backup script is not executable (chmod +x scripts/backup.sh)"
    fi
else
    error "Backup script missing"
fi

echo ""
echo "2. Checking Python dependencies..."
echo "-----------------------------------"

if [ -f "vertex-ar/requirements.txt" ]; then
    pass "requirements.txt exists"

    # Check if critical packages are in requirements
    if grep -q "fastapi" vertex-ar/requirements.txt; then
        pass "FastAPI dependency present"
    else
        error "FastAPI missing from requirements.txt"
    fi

    if grep -q "slowapi" vertex-ar/requirements.txt; then
        pass "slowapi (rate limiting) dependency present"
    else
        error "slowapi missing from requirements.txt"
    fi

    if grep -q "structlog" vertex-ar/requirements.txt; then
        pass "structlog (logging) dependency present"
    else
        error "structlog missing from requirements.txt"
    fi

    if grep -q "sentry-sdk" vertex-ar/requirements.txt; then
        pass "sentry-sdk (error tracking) dependency present"
    else
        warn "sentry-sdk missing from requirements.txt"
    fi

    if grep -q "prometheus-fastapi-instrumentator" vertex-ar/requirements.txt; then
        pass "prometheus-fastapi-instrumentator (metrics) dependency present"
    else
        warn "Prometheus metrics missing from requirements.txt"
    fi
else
    error "requirements.txt missing"
fi

echo ""
echo "3. Checking environment configuration..."
echo "-----------------------------------------"

if [ -f ".env" ]; then
    # Check if SECRET_KEY is set and not default
    if grep -q "SECRET_KEY=" .env; then
        SECRET_KEY=$(grep "SECRET_KEY=" .env | cut -d'=' -f2)
        if [[ "$SECRET_KEY" == *"CHANGE_ME"* ]] || [[ "$SECRET_KEY" == *"your-super-secret"* ]]; then
            error "SECRET_KEY still has default value - MUST be changed!"
        elif [ ${#SECRET_KEY} -lt 32 ]; then
            error "SECRET_KEY is too short (min 32 characters)"
        else
            pass "SECRET_KEY is configured (not default)"
        fi
    else
        error "SECRET_KEY not found in .env"
    fi

    # Check if ADMIN_PASSWORD is set and not default
    if grep -q "ADMIN_PASSWORD=" .env; then
        ADMIN_PASS=$(grep "ADMIN_PASSWORD=" .env | cut -d'=' -f2)
        if [[ "$ADMIN_PASS" == *"CHANGE_ME"* ]] || [[ "$ADMIN_PASS" == "secret" ]]; then
            error "ADMIN_PASSWORD still has default value - MUST be changed!"
        else
            pass "ADMIN_PASSWORD is configured (not default)"
        fi
    else
        error "ADMIN_PASSWORD not found in .env"
    fi

    # Check CORS_ORIGINS
    if grep -q "CORS_ORIGINS=" .env; then
        CORS=$(grep "CORS_ORIGINS=" .env | cut -d'=' -f2)
        if [[ "$CORS" == "*" ]]; then
            error "CORS_ORIGINS is set to * - SECURITY RISK!"
        else
            pass "CORS_ORIGINS is configured (not wildcard)"
        fi
    else
        warn "CORS_ORIGINS not found in .env - will use localhost"
    fi

    # Check if DEBUG is disabled
    if grep -q "DEBUG=False" .env; then
        pass "DEBUG mode is disabled"
    elif grep -q "DEBUG=True" .env; then
        error "DEBUG mode is enabled - MUST be False in production!"
    else
        warn "DEBUG setting not found in .env"
    fi

    # Check if RATE_LIMIT_ENABLED
    if grep -q "RATE_LIMIT_ENABLED=true" .env; then
        pass "Rate limiting is enabled"
    elif grep -q "RATE_LIMIT_ENABLED=false" .env; then
        error "Rate limiting is disabled - MUST be enabled in production!"
    else
        warn "RATE_LIMIT_ENABLED not found in .env"
    fi
else
    warn ".env file not found - using defaults (not recommended for production)"
fi

echo ""
echo "4. Checking code quality..."
echo "---------------------------"

# Check if logging_setup.py has the correct syntax
if [ -f "vertex-ar/logging_setup.py" ]; then
    if grep -q "TimeStamper" vertex-ar/logging_setup.py; then
        pass "logging_setup.py uses correct TimeStamper syntax"
    elif grep -q "add_timestamp" vertex-ar/logging_setup.py; then
        error "logging_setup.py uses deprecated add_timestamp - FIX IMMEDIATELY!"
    else
        warn "Cannot verify logging_setup.py timestamp configuration"
    fi
fi

# Check main.py for CORS configuration
if [ -f "vertex-ar/main.py" ]; then
    if grep -q 'allow_origins=\["?\*"?\]' vertex-ar/main.py; then
        error "main.py has CORS allow_origins=['*'] - SECURITY RISK!"
    else
        pass "main.py CORS configuration looks safe"
    fi
fi

echo ""
echo "5. Checking Docker configuration..."
echo "------------------------------------"

# Check if docker-compose.yml has hardcoded secrets
if [ -f "docker-compose.yml" ]; then
    if grep -q "SECRET_KEY=your-super-secret" docker-compose.yml; then
        error "docker-compose.yml has hardcoded SECRET_KEY"
    elif grep -q "ADMIN_PASSWORD=secret" docker-compose.yml; then
        error "docker-compose.yml has hardcoded ADMIN_PASSWORD"
    else
        pass "docker-compose.yml uses environment variables (no hardcoded secrets)"
    fi
fi

echo ""
echo "6. Checking application structure..."
echo "-------------------------------------"

# Check critical directories
if [ -d "vertex-ar/templates" ]; then
    pass "Templates directory exists"
else
    error "Templates directory missing"
fi

if [ -d "vertex-ar/static" ] || [ -d "vertex-ar/storage" ]; then
    pass "Static/Storage directories exist"
else
    warn "Static/Storage directories may need to be created"
fi

# Check if main.py exists
if [ -f "vertex-ar/main.py" ]; then
    pass "main.py exists"
else
    error "main.py missing - cannot run application!"
fi

echo ""
echo "7. Checking backup configuration..."
echo "------------------------------------"

# Check if backups directory exists
if [ -d "backups" ]; then
    pass "Backups directory exists"
else
    warn "Backups directory doesn't exist (will be created by backup.sh)"
fi

# Check if systemd timer or cron is configured
if systemctl list-timers 2>/dev/null | grep -q "backup"; then
    pass "Systemd timer for backups is configured"
elif crontab -l 2>/dev/null | grep -q "backup.sh"; then
    pass "Cron job for backups is configured"
else
    error "No automated backup schedule found - CRITICAL!"
fi

echo ""
echo "=========================================="
echo "Results:"
echo "=========================================="
echo -e "${GREEN}✓ Passed:${NC} $PASSES"
echo -e "${YELLOW}⚠ Warnings:${NC} $WARNINGS"
echo -e "${RED}✗ Errors:${NC} $ERRORS"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}🎉 All checks passed! Application is ready for deployment.${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  All critical checks passed, but there are warnings.${NC}"
    echo "   Review warnings before deploying to production."
    exit 0
else
    echo -e "${RED}❌ Deployment readiness check FAILED!${NC}"
    echo "   Fix all errors before deploying to production."
    echo ""
    echo "For detailed deployment checklist, see:"
    echo "   - DEPLOYMENT_READINESS_REVIEW.md"
    echo "   - PRODUCTION_READINESS_CHECKLIST.md"
    exit 1
fi
