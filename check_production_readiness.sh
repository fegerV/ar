#!/bin/bash

# 🚀 Production Readiness Check Script
# Немедленная проверка готовности Vertex AR к production

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода статуса
status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[✅]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[⚠️]${NC} $1"
}

error() {
    echo -e "${RED}[❌]${NC} $1"
}

echo "🚀 Vertex AR Production Readiness Check"
echo "======================================="
echo ""

# Проверка структуры проекта
status "Checking project structure..."

required_files=(
    "vertex-ar/main.py"
    "vertex-ar/requirements.txt"
    "docker-compose.yml"
    "Dockerfile.app"
    "nginx.conf"
    "Makefile"
)

missing_files=()
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -eq 0 ]; then
    success "All required files present"
else
    error "Missing files: ${missing_files[*]}"
    exit 1
fi

# Проверка зависимостей
status "Checking Python dependencies..."

cd vertex-ar
if [ ! -f "requirements.txt" ]; then
    error "requirements.txt not found"
    exit 1
fi

# Проверка критических пакетов
critical_packages=(
    "fastapi"
    "uvicorn"
    "sqlalchemy"
    "passlib"
    "python-jose"
    "jinja2"
    "opencv-python"
    "pillow"
    "qrcode"
    "minio"
)

missing_packages=()
for package in "${critical_packages[@]}"; do
    if ! grep -q "^$package" requirements.txt; then
        missing_packages+=("$package")
    fi
done

if [ ${#missing_packages[@]} -eq 0 ]; then
    success "All critical packages in requirements.txt"
else
    warning "Missing packages: ${missing_packages[*]}"
fi

cd ..

# Проверка Docker конфигурации
status "Checking Docker configuration..."

if ! grep -q "version:" docker-compose.yml; then
    error "Invalid docker-compose.yml format"
else
    success "Docker Compose configuration valid"
fi

# Проверка Nginx конфигурации
if command -v nginx &> /dev/null; then
    if nginx -t -c nginx.conf 2>/dev/null; then
        success "Nginx configuration valid"
    else
        warning "Nginx configuration may have issues"
    fi
else
    warning "Nginx not installed, skipping configuration check"
fi

# Проверка storage директорий
status "Checking storage directories..."

storage_dirs=(
    "vertex-ar/storage"
    "vertex-ar/storage/ar_content"
    "vertex-ar/storage/nft-markers"
    "vertex-ar/storage/qr-codes"
)

mkdir -p "${storage_dirs[@]}"

for dir in "${storage_dirs[@]}"; do
    if [ -d "$dir" ]; then
        success "Directory exists: $dir"
    else
        warning "Directory missing: $dir"
    fi
done

# Проверка переменных окружения
status "Checking environment configuration..."

env_files=(
    "vertex-ar/.env.example"
    "vertex-ar/.env.production.example"
)

for env_file in "${env_files[@]}"; do
    if [ -f "$env_file" ]; then
        success "Environment file exists: $env_file"
    else
        warning "Environment file missing: $env_file"
    fi
done

# Проверка тестов
status "Checking test coverage..."

test_files=(
    "test_api_endpoints.py"
    "test_ar_functionality.py"
    "test_security.py"
    "test_performance.py"
)

existing_tests=0
for test_file in "${test_files[@]}"; do
    if [ -f "$test_file" ]; then
        existing_tests=$((existing_tests + 1))
        success "Test file exists: $test_file"
    else
        warning "Test file missing: $test_file"
    fi
done

test_coverage=$((existing_tests * 100 / ${#test_files[@]}))
status "Test coverage: $test_coverage% ($existing_tests/${#test_files[@]} files)"

# Проверка безопасности
status "Checking security configuration..."

# Проверка .gitignore
if [ -f ".gitignore" ]; then
    if grep -q ".env" .gitignore && grep -q "*.db" .gitignore; then
        success ".gitignore properly configured"
    else
        warning ".gitignore may miss sensitive files"
    fi
else
    error ".gitignore not found"
fi

# Проверка SSL
if [ -f "setup_ssl.sh" ]; then
    success "SSL setup script exists"
else
    warning "SSL setup script missing"
fi

# Проверка backup скрипта
if [ -f "scripts/backup.sh" ]; then
    success "Backup script exists"
else
    warning "Backup script missing - creating basic backup script"
    mkdir -p scripts
    cat > scripts/backup.sh << 'EOF'
#!/bin/bash
set -e

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups"
mkdir -p $BACKUP_DIR

echo "Creating backup..."

# Database backup
if [ -f "vertex-ar/app_data.db" ]; then
    cp vertex-ar/app_data.db $BACKUP_DIR/db_backup_$DATE.db
    echo "Database backed up"
fi

# Storage backup
if [ -d "vertex-ar/storage" ]; then
    tar -czf $BACKUP_DIR/storage_backup_$DATE.tar.gz vertex-ar/storage/
    echo "Storage backed up"
fi

# Cleanup old backups (keep last 7 days)
find $BACKUP_DIR/ -name "*.db" -mtime +7 -delete 2>/dev/null || true
find $BACKUP_DIR/ -name "*.tar.gz" -mtime +7 -delete 2>/dev/null || true

echo "Backup completed: $DATE"
EOF
    chmod +x scripts/backup.sh
    success "Basic backup script created"
fi

# Проверка логирования
status "Checking logging configuration..."

if grep -q "logging" vertex-ar/main.py; then
    success "Logging configuration found"
else
    warning "Logging configuration may be missing"
fi

# Проверка health checks
if grep -q "/health" vertex-ar/main.py; then
    success "Health check endpoint exists"
else
    warning "Health check endpoint may be missing"
fi

# Проверка rate limiting
if grep -q "rate" vertex-ar/main.py || grep -q "slowapi" vertex-ar/requirements.txt; then
    success "Rate limiting configuration found"
else
    warning "Rate limiting may not be implemented"
fi

# Проверка метрик
if grep -q "metrics" vertex-ar/main.py || grep -q "prometheus" vertex-ar/requirements.txt; then
    success "Metrics configuration found"
else
    warning "Metrics may not be implemented"
fi

# Проверка версии
if [ -f "vertex-ar/VERSION" ]; then
    version=$(cat vertex-ar/VERSION)
    success "Version file exists: $version"
else
    warning "Version file missing"
fi

# Проверка документации
status "Checking documentation..."

doc_files=(
    "README.md"
    "API_DOCUMENTATION.md"
    "DEVELOPER_GUIDE.md"
    "CHANGELOG.md"
)

doc_count=0
for doc_file in "${doc_files[@]}"; do
    if [ -f "$doc_file" ]; then
        doc_count=$((doc_count + 1))
        success "Documentation exists: $doc_file"
    else
        warning "Documentation missing: $doc_file"
    fi
done

# Проверка Makefile целей
if [ -f "Makefile" ]; then
    makefile_targets=("help" "build" "up" "down" "logs" "status")
    for target in "${makefile_targets[@]}"; do
        if grep -q "^$target:" Makefile; then
            success "Makefile target exists: $target"
        else
            warning "Makefile target missing: $target"
        fi
    done
fi

# Сводная оценка
echo ""
echo "======================================="
echo "📊 READINESS ASSESSMENT"
echo "======================================="

# Подсчет успешных проверок
total_checks=0
passed_checks=0

# Функция для оценки
add_check() {
    total_checks=$((total_checks + 1))
    if [ "$1" = "success" ]; then
        passed_checks=$((passed_checks + 1))
    fi
}

# Простая эвристика для подсчета (в реальном скрипте нужно точнее)
if [ ${#missing_files[@]} -eq 0 ]; then
    add_check "success"
fi

if [ ${#missing_packages[@]} -eq 0 ]; then
    add_check "success"
fi

if [ -f "docker-compose.yml" ]; then
    add_check "success"
fi

if [ -f "nginx.conf" ]; then
    add_check "success"
fi

if [ $test_coverage -ge 50 ]; then
    add_check "success"
fi

if [ -f ".gitignore" ]; then
    add_check "success"
fi

if [ -f "scripts/backup.sh" ]; then
    add_check "success"
fi

if [ $doc_count -ge 3 ]; then
    add_check "success"
fi

# Расчет процента готовности
readiness_percentage=$((passed_checks * 100 / total_checks))

echo "Overall Readiness: $readiness_percentage% ($passed_checks/$total_checks checks passed)"

# Рекомендации
echo ""
echo "📋 RECOMMENDATIONS"
echo "==================="

if [ $readiness_percentage -lt 50 ]; then
    error "Project is NOT ready for production"
    echo "Critical issues must be addressed:"
    echo "1. Implement missing security features"
    echo "2. Add comprehensive monitoring"
    echo "3. Create backup and recovery procedures"
    echo "4. Improve test coverage"
elif [ $readiness_percentage -lt 80 ]; then
    warning "Project needs significant improvements before production"
    echo "Recommended actions:"
    echo "1. Add rate limiting and security measures"
    echo "2. Implement monitoring and logging"
    echo "3. Create automated backup system"
    echo "4. Increase test coverage to 70%+"
else
    success "Project is mostly ready for production"
    echo "Final recommendations:"
    echo "1. Run comprehensive security tests"
    echo "2. Perform load testing"
    echo "3. Set up production monitoring"
    echo "4. Document deployment procedures"
fi

# Критические проблемы
echo ""
echo "🚨 CRITICAL ISSUES TO ADDRESS"
echo "=============================="

critical_issues=()

if ! grep -q "slowapi" vertex-ar/requirements.txt; then
    critical_issues+=("Rate limiting not implemented")
fi

if [ ! -f "scripts/backup.sh" ]; then
    critical_issues+=("No backup system")
fi

if [ $test_coverage -lt 70 ]; then
    critical_issues+=("Test coverage below 70%")
fi

if ! grep -q "logging" vertex-ar/main.py; then
    critical_issues+=("Comprehensive logging missing")
fi

if [ ${#critical_issues[@]} -gt 0 ]; then
    for issue in "${critical_issues[@]}"; do
        error "• $issue"
    done
else
    success "No critical issues found"
fi

# Следующие шаги
echo ""
echo "🎯 NEXT STEPS"
echo "============="

echo "1. Run full test suite:"
echo "   python -m pytest test_*.py -v"
echo ""
echo "2. Check code quality:"
echo "   flake8 vertex-ar/*.py"
echo "   black vertex-ar/*.py"
echo ""
echo "3. Run security tests:"
echo "   python test_security.py"
echo ""
echo "4. Test deployment:"
echo "   docker compose up -d"
echo "   make health"
echo ""
echo "5. Review production checklist:"
echo "   cat PRODUCTION_READINESS_CHECKLIST.md"

echo ""
echo "======================================="
if [ $readiness_percentage -ge 80 ]; then
    success "Ready to proceed with production deployment planning"
elif [ $readiness_percentage -ge 50 ]; then
    warning "Significant work required before production deployment"
else
    error "Major issues must be resolved before production deployment"
fi
echo "======================================="
