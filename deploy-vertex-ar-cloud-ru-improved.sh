#!/bin/bash

###############################################################################
# Vertex AR Production Deployment Script (Improved Version)
# Target: Ubuntu 22.04/24.04 LTS
# Version: 2.0
# 
# IMPROVEMENTS OVER v1.0:
# - Secure random password generation
# - Pre-flight system checks
# - Backup before deployment
# - Rollback capability
# - Health check verification
# - Trap handlers for cleanup
# - Python 3.10+ verification
# - Modern dependencies (Node.js 20+)
# - Deployment logging
# - Production secrets validation
###############################################################################

set -euo pipefail

# ===== CONFIGURATION =====

# Application Configuration (can be overridden via environment variables)
APP_USER="${APP_USER:-rustadmin}"
APP_GROUP="${APP_GROUP:-$APP_USER}"
APP_HOME="/home/$APP_USER"
APP_DIR="$APP_HOME/vertex-ar-app"
VENV_DIR="$APP_DIR/venv"
APP_PORT="${APP_PORT:-8000}"
DOMAIN="${DOMAIN:-nft.vertex-art.ru}"
LOG_DIR="/var/log/vertex-ar"
BACKUP_BASE_DIR="$APP_HOME/backups"
DEPLOY_LOG="$LOG_DIR/deploy-$(date +%Y%m%d-%H%M%S).log"

# System Requirements
MIN_DISK_GB=5
MIN_MEMORY_GB=2
REQUIRED_PYTHON_VERSION="3.10"
REQUIRED_NODE_VERSION="20"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global Variables
BACKUP_DIR=""
DEPLOYMENT_FAILED=false

# ===== UTILITY FUNCTIONS =====

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$DEPLOY_LOG" 2>/dev/null || echo "$1"
}

# ===== CLEANUP AND TRAP HANDLERS =====

cleanup() {
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -ne 0 ] || [ "$DEPLOYMENT_FAILED" = true ]; then
        print_error "Deployment failed with exit code: $EXIT_CODE"
        log_message "ERROR: Deployment failed with exit code: $EXIT_CODE"
        
        if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR" ]; then
            print_warning "Backup available at: $BACKUP_DIR"
            read -p "Do you want to rollback to previous version? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rollback_deployment
            fi
        fi
    else
        log_message "INFO: Deployment completed successfully"
        print_success "Deployment completed successfully"
    fi
}

trap cleanup EXIT INT TERM

# ===== PRE-FLIGHT CHECKS =====

check_root() {
    print_header "Checking root privileges"
    
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root or with sudo"
        exit 1
    fi
    
    print_success "Running with root privileges"
}

check_os_version() {
    print_header "Checking OS version"
    
    if [ ! -f /etc/os-release ]; then
        print_error "Cannot determine OS version"
        exit 1
    fi
    
    source /etc/os-release
    
    if [[ "$ID" != "ubuntu" ]]; then
        print_error "This script is designed for Ubuntu. Detected: $ID"
        exit 1
    fi
    
    VERSION_NUMBER="${VERSION_ID%.*}"
    
    if [[ "$VERSION_NUMBER" -lt 20 ]]; then
        print_error "Ubuntu $VERSION_ID is too old or EOL. Please use Ubuntu 22.04 LTS or 24.04 LTS"
        exit 1
    fi
    
    print_success "OS: Ubuntu $VERSION_ID"
}

check_system_requirements() {
    print_header "Checking system requirements"
    
    # Check disk space
    AVAILABLE_SPACE=$(df -BG / | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ "$AVAILABLE_SPACE" -lt "$MIN_DISK_GB" ]; then
        print_error "Insufficient disk space: ${AVAILABLE_SPACE}GB (minimum ${MIN_DISK_GB}GB required)"
        exit 1
    fi
    print_success "Disk space: ${AVAILABLE_SPACE}GB available (${MIN_DISK_GB}GB required)"
    
    # Check memory
    AVAILABLE_MEMORY=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$AVAILABLE_MEMORY" -lt "$MIN_MEMORY_GB" ]; then
        print_warning "Low memory: ${AVAILABLE_MEMORY}GB (recommended ${MIN_MEMORY_GB}GB)"
    else
        print_success "Memory: ${AVAILABLE_MEMORY}GB available"
    fi
    
    # Check ports
    for PORT in "$APP_PORT" 80 443; do
        if command -v netstat &> /dev/null && netstat -tuln 2>/dev/null | grep -q ":$PORT "; then
            print_warning "Port $PORT is already in use"
            read -p "Continue anyway? (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    done
    print_success "Required ports available or user accepted"
}

check_app_user() {
    print_header "Checking application user"
    
    if ! id "$APP_USER" &>/dev/null; then
        print_warning "User $APP_USER does not exist"
        print_warning "Creating user $APP_USER..."
        
        useradd -m -s /bin/bash "$APP_USER"
        print_success "User $APP_USER created"
    else
        print_success "User $APP_USER exists"
    fi
}

# ===== BACKUP AND ROLLBACK =====

backup_before_deploy() {
    print_header "Creating backup before deployment"
    
    BACKUP_DIR="$BACKUP_BASE_DIR/pre-deploy-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    local BACKUP_CREATED=false
    
    # Backup database
    if [ -f "$APP_DIR/vertex-ar/app_data.db" ]; then
        cp "$APP_DIR/vertex-ar/app_data.db" "$BACKUP_DIR/"
        print_success "Database backed up"
        BACKUP_CREATED=true
    fi
    
    # Backup storage
    if [ -d "$APP_DIR/vertex-ar/storage" ]; then
        cp -r "$APP_DIR/vertex-ar/storage" "$BACKUP_DIR/"
        print_success "Storage files backed up"
        BACKUP_CREATED=true
    fi
    
    # Backup .env
    if [ -f "$APP_DIR/vertex-ar/.env" ]; then
        cp "$APP_DIR/vertex-ar/.env" "$BACKUP_DIR/.env.backup"
        print_success "Configuration backed up"
        BACKUP_CREATED=true
    fi
    
    if [ "$BACKUP_CREATED" = true ]; then
        echo "$BACKUP_DIR" > /tmp/vertex-ar-last-backup.txt
        chown "$APP_USER:$APP_GROUP" "$BACKUP_DIR" -R
        print_success "Backup created: $BACKUP_DIR"
        log_message "INFO: Backup created at $BACKUP_DIR"
    else
        print_warning "No existing installation found - skipping backup"
    fi
}

rollback_deployment() {
    print_header "Rolling back to previous version"
    
    if [ -z "$BACKUP_DIR" ] || [ ! -d "$BACKUP_DIR" ]; then
        if [ -f /tmp/vertex-ar-last-backup.txt ]; then
            BACKUP_DIR=$(cat /tmp/vertex-ar-last-backup.txt)
        fi
    fi
    
    if [ -z "$BACKUP_DIR" ] || [ ! -d "$BACKUP_DIR" ]; then
        print_error "No backup found, rollback impossible"
        return 1
    fi
    
    # Stop application
    if command -v supervisorctl &> /dev/null; then
        supervisorctl stop vertex-ar 2>/dev/null || true
    fi
    
    # Restore database
    if [ -f "$BACKUP_DIR/app_data.db" ]; then
        cp "$BACKUP_DIR/app_data.db" "$APP_DIR/vertex-ar/"
        print_success "Database restored"
    fi
    
    # Restore storage
    if [ -d "$BACKUP_DIR/storage" ]; then
        rm -rf "$APP_DIR/vertex-ar/storage"
        cp -r "$BACKUP_DIR/storage" "$APP_DIR/vertex-ar/"
        print_success "Storage files restored"
    fi
    
    # Restore .env
    if [ -f "$BACKUP_DIR/.env.backup" ]; then
        cp "$BACKUP_DIR/.env.backup" "$APP_DIR/vertex-ar/.env"
        print_success "Configuration restored"
    fi
    
    # Fix permissions
    chown -R "$APP_USER:$APP_GROUP" "$APP_DIR/vertex-ar/"
    
    # Restart application
    if command -v supervisorctl &> /dev/null; then
        supervisorctl start vertex-ar
    fi
    
    print_success "Rollback completed"
    log_message "INFO: Rollback completed from $BACKUP_DIR"
}

# ===== INSTALLATION FUNCTIONS =====

update_system() {
    print_header "Updating system packages"
    
    apt update -qq
    apt upgrade -y -qq
    
    print_success "System updated"
}

install_dependencies() {
    print_header "Installing system dependencies"
    
    apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        git \
        wget \
        curl \
        nano \
        supervisor \
        nginx \
        sqlite3 \
        libssl-dev \
        libffi-dev \
        python3-dev \
        build-essential \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 \
        libgl1-mesa-glx \
        net-tools \
        software-properties-common
    
    print_success "Dependencies installed"
}

check_and_install_python() {
    print_header "Checking Python version"
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 not found"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
    
    REQUIRED_MAJOR=$(echo "$REQUIRED_PYTHON_VERSION" | cut -d. -f1)
    REQUIRED_MINOR=$(echo "$REQUIRED_PYTHON_VERSION" | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -lt "$REQUIRED_MAJOR" ] || \
       { [ "$PYTHON_MAJOR" -eq "$REQUIRED_MAJOR" ] && [ "$PYTHON_MINOR" -lt "$REQUIRED_MINOR" ]; }; then
        print_warning "Python $PYTHON_VERSION is too old. Required: $REQUIRED_PYTHON_VERSION+"
        print_warning "Installing Python $REQUIRED_PYTHON_VERSION..."
        
        add-apt-repository ppa:deadsnakes/ppa -y
        apt update -qq
        apt install -y "python${REQUIRED_PYTHON_VERSION}" \
                       "python${REQUIRED_PYTHON_VERSION}-venv" \
                       "python${REQUIRED_PYTHON_VERSION}-dev"
        
        update-alternatives --install /usr/bin/python3 python3 "/usr/bin/python${REQUIRED_PYTHON_VERSION}" 1
        
        print_success "Python $REQUIRED_PYTHON_VERSION installed"
    else
        print_success "Python $PYTHON_VERSION (meets requirement: $REQUIRED_PYTHON_VERSION+)"
    fi
}

install_nodejs() {
    print_header "Installing Node.js"
    
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
        if [ "$NODE_VERSION" -ge "$REQUIRED_NODE_VERSION" ]; then
            print_success "Node.js v$(node -v) already installed"
            return
        else
            print_warning "Node.js v$(node -v) is outdated. Upgrading to v${REQUIRED_NODE_VERSION}+"
        fi
    fi
    
    # Install Node.js 20.x LTS
    curl -fsSL "https://deb.nodesource.com/setup_${REQUIRED_NODE_VERSION}.x" | bash -
    apt install -y nodejs
    
    print_success "Node.js v$(node -v) installed"
}

clone_or_update_repository() {
    print_header "Setting up repository"
    
    if [ ! -d "$APP_DIR" ]; then
        mkdir -p "$APP_DIR"
        print_success "Directory created: $APP_DIR"
    fi
    
    if [ ! -d "$APP_DIR/.git" ]; then
        print_warning "Repository not found"
        echo ""
        echo "Please clone the repository manually:"
        echo "  git clone https://github.com/fegerV/AR.git $APP_DIR"
        echo ""
        echo "OR download and extract:"
        echo "  wget -O /tmp/vertex-ar.zip https://github.com/fegerV/AR/archive/refs/heads/main.zip"
        echo "  unzip /tmp/vertex-ar.zip -d /tmp/"
        echo "  mv /tmp/AR-main/* $APP_DIR/"
        echo ""
        read -p "Press Enter after cloning the repository, or Ctrl+C to exit..."
        
        if [ ! -d "$APP_DIR/.git" ] && [ ! -f "$APP_DIR/vertex-ar/main.py" ]; then
            print_error "Repository still not found. Please clone and run script again."
            exit 1
        fi
    else
        print_success "Repository exists"
        
        # Optionally update
        read -p "Update from git repository? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cd "$APP_DIR"
            sudo -u "$APP_USER" git pull
            print_success "Repository updated"
        fi
    fi
    
    # Change ownership
    chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"
}

create_virtualenv() {
    print_header "Creating Python virtual environment"
    
    if [ -d "$VENV_DIR" ]; then
        print_warning "Virtual environment exists"
        read -p "Recreate virtual environment? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$VENV_DIR"
        else
            print_success "Using existing virtual environment"
            return
        fi
    fi
    
    sudo -u "$APP_USER" python3 -m venv "$VENV_DIR"
    print_success "Virtual environment created"
}

install_python_dependencies() {
    print_header "Installing Python dependencies"
    
    cd "$APP_DIR/vertex-ar"
    
    # Activate venv
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    if ! pip install --upgrade pip setuptools wheel; then
        print_error "Failed to upgrade pip/setuptools/wheel"
        exit 1
    fi
    
    # Install requirements
    if [ -f "requirements-simple.txt" ]; then
        if ! pip install -r requirements-simple.txt; then
            print_error "Failed to install dependencies from requirements-simple.txt"
            pip install -r requirements-simple.txt 2>&1 | tail -20
            exit 1
        fi
        print_success "Dependencies installed (requirements-simple.txt)"
    elif [ -f "requirements.txt" ]; then
        if ! pip install -r requirements.txt; then
            print_error "Failed to install dependencies from requirements.txt"
            exit 1
        fi
        print_success "Dependencies installed (requirements.txt)"
    else
        print_error "No requirements file found in $APP_DIR/vertex-ar"
        exit 1
    fi
    
    deactivate
}

run_database_migrations() {
    print_header "Running database migrations"
    
    cd "$APP_DIR/vertex-ar"
    
    if [ -d "alembic" ]; then
        source "$VENV_DIR/bin/activate"
        
        if alembic upgrade head; then
            print_success "Database migrations applied"
        else
            print_warning "Database migrations failed or not needed"
        fi
        
        deactivate
    else
        print_warning "No alembic directory found - skipping migrations"
    fi
}

create_env_file() {
    print_header "Creating/updating .env configuration"
    
    ENV_FILE="$APP_DIR/vertex-ar/.env"
    
    if [ -f "$ENV_FILE" ]; then
        print_warning ".env file already exists"
        read -p "Overwrite existing .env file? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_success "Using existing .env file"
            return
        fi
        
        # Backup existing .env
        cp "$ENV_FILE" "$ENV_FILE.backup-$(date +%Y%m%d-%H%M%S)"
        print_success "Existing .env backed up"
    fi
    
    # Generate strong random values
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    ADMIN_PASSWORD=$(python3 -c "import secrets, string; chars=string.ascii_letters+string.digits+string.punctuation.replace('\"', '').replace(\"'\", '').replace('\\$', ''); print(''.join(secrets.choice(chars) for _ in range(24)))")
    
    # Display generated credentials
    print_header "SAVE THESE CREDENTIALS SECURELY"
    echo ""
    echo "Admin Username: superar"
    echo "Admin Password: $ADMIN_PASSWORD"
    echo ""
    echo "Store these credentials in a secure password manager NOW!"
    echo ""
    read -p "Press Enter after saving credentials..."
    
    # Create full .env file
    cat > "$ENV_FILE" << EOF
# ============================================
# Vertex AR Production Configuration
# Generated: $(date)
# ============================================

# Application Settings
DEBUG=False
SECRET_KEY=$SECRET_KEY
APP_HOST=127.0.0.1
APP_PORT=$APP_PORT
BASE_URL=https://$DOMAIN
INTERNAL_HEALTH_URL=http://127.0.0.1:$APP_PORT
ENVIRONMENT=production

# Database Settings
DATABASE_URL=sqlite:///./app_data.db

# Storage Settings
STORAGE_TYPE=local
STORAGE_PATH=./storage

# Security Settings
CORS_ORIGINS=https://$DOMAIN,https://www.$DOMAIN
SESSION_TIMEOUT_MINUTES=30
AUTH_MAX_ATTEMPTS=5
AUTH_LOCKOUT_MINUTES=15
TOKEN_EXPIRATION_HOURS=24
BCRYPT_ROUNDS=12

# Admin Credentials
DEFAULT_ADMIN_USERNAME=superar
DEFAULT_ADMIN_PASSWORD=$ADMIN_PASSWORD
DEFAULT_ADMIN_EMAIL=admin@$DOMAIN
DEFAULT_ADMIN_FULL_NAME=Super Administrator

# Rate Limiting
RATE_LIMIT_ENABLED=true
GLOBAL_RATE_LIMIT=100/minute
AUTH_RATE_LIMIT=5/minute
UPLOAD_RATE_LIMIT=10/minute

# Logging
LOG_LEVEL=INFO
JSON_LOGS=true

# File Upload Limits
MAX_IMAGE_SIZE_MB=10
MAX_VIDEO_SIZE_MB=50
ALLOWED_IMAGE_FORMATS=jpg,jpeg,png
ALLOWED_VIDEO_FORMATS=mp4,webm

# NFT Marker Generation
NFT_FEATURE_DENSITY=high
NFT_PYRAMID_LEVELS=3
NFT_TARGET_DPI=150

# Monitoring and Alerting
ALERTING_ENABLED=true
CPU_THRESHOLD=80.0
MEMORY_THRESHOLD=85.0
DISK_THRESHOLD=90.0
HEALTH_CHECK_INTERVAL=60

# Monitoring Alert Stabilization
MONITORING_CONSECUTIVE_FAILURES=3
MONITORING_DEDUP_WINDOW=300

# Video Scheduler
VIDEO_SCHEDULER_ENABLED=true
VIDEO_SCHEDULER_CHECK_INTERVAL=300
VIDEO_SCHEDULER_ROTATION_INTERVAL=3600
VIDEO_SCHEDULER_ARCHIVE_AFTER_HOURS=168
VIDEO_SCHEDULER_NOTIFICATIONS_ENABLED=true

# Lifecycle Scheduler
LIFECYCLE_SCHEDULER_ENABLED=true
LIFECYCLE_CHECK_INTERVAL_SECONDS=3600
LIFECYCLE_NOTIFICATIONS_ENABLED=true

# Backup Settings
BACKUP_DESTINATION=local
BACKUP_RETENTION_DAYS=7

# Telegram Notifications (Optional - configure if needed)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Email Notifications (Optional - configure if needed)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
EMAIL_FROM=
ADMIN_EMAILS=

# Sentry Error Tracking (Optional - configure if needed)
SENTRY_DSN=
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1

# MinIO/S3 Settings (if STORAGE_TYPE=minio)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_BUCKET=vertex-ar
MINIO_SECURE=True
MINIO_PUBLIC_URL=

# Redis (Optional)
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=

# Uvicorn Runtime Tuning
# Auto-calculated workers: (2 * CPU cores) + 1
# UVICORN_WORKERS=$NUM_WORKERS
UVICORN_KEEPALIVE_TIMEOUT=5
UVICORN_TIMEOUT_KEEP_ALIVE=5
UVICORN_LIMIT_CONCURRENCY=0
UVICORN_BACKLOG=2048
UVICORN_PROXY_HEADERS=true
UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=30

# Web Server Health Check Tuning
WEB_HEALTH_CHECK_TIMEOUT=5
WEB_HEALTH_CHECK_USE_HEAD=false
WEB_HEALTH_CHECK_COOLDOWN=30
EOF
    
    # Set secure permissions
    chown "$APP_USER:$APP_GROUP" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    
    print_success ".env file created with secure permissions (600)"
    log_message "INFO: .env file created with generated credentials and uvicorn tuning"
}

validate_production_secrets() {
    print_header "Validating production configuration"
    
    ENV_FILE="$APP_DIR/vertex-ar/.env"
    
    if [ ! -f "$ENV_FILE" ]; then
        print_error ".env file not found"
        exit 1
    fi
    
    # Source .env
    set +u  # Temporarily allow unset variables
    source "$ENV_FILE"
    set -u
    
    # Validate DEBUG is False
    if [ "$DEBUG" != "False" ]; then
        print_error "DEBUG must be False in production (currently: $DEBUG)"
        exit 1
    fi
    print_success "DEBUG is False"
    
    # Validate SECRET_KEY is not default
    if [[ "$SECRET_KEY" == *"CHANGE_ME"* ]]; then
        print_error "SECRET_KEY contains CHANGE_ME - must be a secure random value"
        exit 1
    fi
    print_success "SECRET_KEY is set"
    
    # Validate ADMIN_PASSWORD is not default
    if [[ "$DEFAULT_ADMIN_PASSWORD" == "CHANGE_ME_IMMEDIATELY" ]] || \
       [[ "$DEFAULT_ADMIN_PASSWORD" == "ffE48f0ns@HQ" ]]; then
        print_error "DEFAULT_ADMIN_PASSWORD is still using default value"
        exit 1
    fi
    print_success "DEFAULT_ADMIN_PASSWORD is unique"
    
    # Validate ENVIRONMENT is production
    if [ "$ENVIRONMENT" != "production" ]; then
        print_warning "ENVIRONMENT is not 'production' (currently: $ENVIRONMENT)"
    else
        print_success "ENVIRONMENT is production"
    fi
    
    print_success "Production configuration validated"
}

create_log_directory() {
    print_header "Creating log directory"
    
    mkdir -p "$LOG_DIR"
    chown "$APP_USER:$APP_GROUP" "$LOG_DIR"
    chmod 755 "$LOG_DIR"
    
    print_success "Log directory created: $LOG_DIR"
}

setup_ssl_certificates() {
    print_header "Setting up SSL certificates"
    
    CERT_FILE="/etc/ssl/certs/$DOMAIN.crt"
    KEY_FILE="/etc/ssl/private/$DOMAIN.key"
    
    # Check if real certificates exist
    if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
        print_success "SSL certificates found"
        
        # Verify certificate
        if openssl x509 -in "$CERT_FILE" -noout -text &>/dev/null; then
            CERT_EXPIRY=$(openssl x509 -in "$CERT_FILE" -noout -enddate | cut -d= -f2)
            print_success "Certificate valid until: $CERT_EXPIRY"
        else
            print_error "Certificate appears to be invalid"
            exit 1
        fi
        
        # Set correct permissions
        chmod 400 "$KEY_FILE"
        chmod 644 "$CERT_FILE"
        print_success "Certificate permissions set"
        
        return
    fi
    
    # No real certificates - create self-signed for initial setup
    print_warning "SSL certificates not found"
    print_warning "Creating self-signed certificate for initial setup..."
    print_warning "IMPORTANT: Replace with real certificates before going live!"
    
    mkdir -p /etc/ssl/private
    chmod 700 /etc/ssl/private
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$KEY_FILE" \
        -out "$CERT_FILE" \
        -subj "/C=RU/ST=Moscow/L=Moscow/O=Vertex AR/CN=$DOMAIN" \
        2>/dev/null
    
    chmod 400 "$KEY_FILE"
    chmod 644 "$CERT_FILE"
    
    print_warning "Self-signed certificate created (valid for 365 days)"
    print_warning "Replace with Let's Encrypt or purchased certificate:"
    echo ""
    echo "For Let's Encrypt:"
    echo "  apt install -y certbot python3-certbot-nginx"
    echo "  certbot --nginx -d $DOMAIN"
    echo ""
    echo "Or manually copy certificates:"
    echo "  Certificate: $CERT_FILE"
    echo "  Private Key: $KEY_FILE"
    echo ""
}

setup_supervisor() {
    print_header "Setting up Supervisor"
    
    SUPERVISOR_CONF="/etc/supervisor/conf.d/vertex-ar.conf"
    
    # Load .env to get tuning settings
    ENV_FILE="$APP_DIR/vertex-ar/.env"
    if [ -f "$ENV_FILE" ]; then
        set +u
        source "$ENV_FILE"
        set -u
    fi
    
    # Determine number of workers (defaults to 2x CPU cores + 1 if not set in .env)
    if [ -z "${UVICORN_WORKERS:-}" ]; then
        NUM_WORKERS=$(( $(nproc) * 2 + 1 ))
        # Cap at 8 workers to prevent resource exhaustion on large machines
        if [ "$NUM_WORKERS" -gt 8 ]; then
            NUM_WORKERS=8
        fi
    else
        NUM_WORKERS="$UVICORN_WORKERS"
    fi
    
    # Get other uvicorn settings from .env or use defaults
    KEEPALIVE_TIMEOUT="${UVICORN_TIMEOUT_KEEP_ALIVE:-5}"
    LIMIT_CONCURRENCY="${UVICORN_LIMIT_CONCURRENCY:-0}"
    BACKLOG="${UVICORN_BACKLOG:-2048}"
    PROXY_HEADERS="${UVICORN_PROXY_HEADERS:-true}"
    GRACEFUL_SHUTDOWN="${UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN:-30}"
    
    # Build uvicorn command with tuning flags
    UVICORN_CMD="$VENV_DIR/bin/uvicorn app.main:app --host 127.0.0.1 --port $APP_PORT"
    UVICORN_CMD="$UVICORN_CMD --workers $NUM_WORKERS"
    UVICORN_CMD="$UVICORN_CMD --timeout-keep-alive $KEEPALIVE_TIMEOUT"
    UVICORN_CMD="$UVICORN_CMD --backlog $BACKLOG"
    
    if [ "$LIMIT_CONCURRENCY" != "0" ]; then
        UVICORN_CMD="$UVICORN_CMD --limit-concurrency $LIMIT_CONCURRENCY"
    fi
    
    if [ "$PROXY_HEADERS" = "true" ]; then
        UVICORN_CMD="$UVICORN_CMD --proxy-headers"
    fi
    
    UVICORN_CMD="$UVICORN_CMD --timeout-graceful-shutdown $GRACEFUL_SHUTDOWN"
    
    cat > "$SUPERVISOR_CONF" << EOF
[program:vertex-ar]
directory=$APP_DIR/vertex-ar
command=$UVICORN_CMD
user=$APP_USER
autostart=true
autorestart=true
stderr_logfile=$LOG_DIR/error.log
stdout_logfile=$LOG_DIR/access.log
environment=PATH="$VENV_DIR/bin",HOME="$APP_HOME"
numprocs=1
priority=999
stopwaitsecs=$GRACEFUL_SHUTDOWN
killasgroup=true
stopasgroup=true

[group:vertex-ar]
programs=vertex-ar
EOF
    
    # Reload and start supervisor
    supervisorctl reread
    supervisorctl update
    
    # Give it a moment to start
    sleep 3
    
    # Start if not running
    if ! supervisorctl status vertex-ar | grep -q "RUNNING"; then
        supervisorctl start vertex-ar
        sleep 3
    fi
    
    # Check status
    if supervisorctl status vertex-ar | grep -q "RUNNING"; then
        print_success "Supervisor configured and application running"
        print_success "Workers: $NUM_WORKERS, Keep-alive: ${KEEPALIVE_TIMEOUT}s, Backlog: $BACKLOG"
    else
        print_error "Application failed to start"
        print_error "Check logs: tail -f $LOG_DIR/error.log"
        DEPLOYMENT_FAILED=true
        exit 1
    fi
}

setup_nginx() {
    print_header "Setting up Nginx"
    
    NGINX_CONF="/etc/nginx/sites-available/vertex-ar"
    NGINX_ENABLED="/etc/nginx/sites-enabled/vertex-ar"
    
    cat > "$NGINX_CONF" << EOF
# Rate limiting zones
limit_req_zone \$binary_remote_addr zone=general:10m rate=100r/m;
limit_req_zone \$binary_remote_addr zone=auth:10m rate=5r/m;
limit_req_zone \$binary_remote_addr zone=upload:10m rate=10r/m;

upstream vertex_ar {
    server 127.0.0.1:$APP_PORT;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    # Allow Let's Encrypt challenges
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;
    
    # SSL certificates
    ssl_certificate /etc/ssl/certs/$DOMAIN.crt;
    ssl_certificate_key /etc/ssl/private/$DOMAIN.key;
    
    # SSL parameters (modern configuration)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Logs
    access_log /var/log/nginx/vertex-ar-access.log;
    error_log /var/log/nginx/vertex-ar-error.log;
    
    # File upload size
    client_max_body_size 50M;
    
    # Auth endpoints (strict rate limiting)
    location /api/auth/ {
        limit_req zone=auth burst=10 nodelay;
        limit_req_status 429;
        
        proxy_pass http://vertex_ar;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Upload endpoints (moderate rate limiting)
    location ~ ^/api/.*/upload {
        limit_req zone=upload burst=5 nodelay;
        limit_req_status 429;
        
        proxy_pass http://vertex_ar;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        proxy_http_version 1.1;
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }
    
    # Static files
    location /static/ {
        alias $APP_DIR/vertex-ar/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # All other locations (general rate limiting)
    location / {
        limit_req zone=general burst=20 nodelay;
        limit_req_status 429;
        
        proxy_pass http://vertex_ar;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF
    
    # Enable site
    if [ ! -L "$NGINX_ENABLED" ]; then
        ln -s "$NGINX_CONF" "$NGINX_ENABLED"
    fi
    
    # Remove default site if exists
    if [ -L "/etc/nginx/sites-enabled/default" ]; then
        rm -f "/etc/nginx/sites-enabled/default"
    fi
    
    # Test configuration
    if nginx -t 2>&1 | grep -q "successful"; then
        print_success "Nginx configuration valid"
    else
        print_error "Nginx configuration has errors"
        nginx -t
        DEPLOYMENT_FAILED=true
        exit 1
    fi
    
    # Restart nginx
    systemctl restart nginx
    print_success "Nginx configured and restarted"
}

verify_application_health() {
    print_header "Verifying application health"
    
    local MAX_RETRIES=15
    local RETRY_COUNT=0
    local HEALTH_URL="http://127.0.0.1:$APP_PORT/health"
    
    print_warning "Waiting for application to be ready..."
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -s -f "$HEALTH_URL" | grep -q "ok" 2>/dev/null; then
            print_success "Application health check passed"
            
            # Additional checks
            if curl -s -f "http://127.0.0.1:$APP_PORT/api/monitoring/health" >/dev/null 2>&1; then
                print_success "Monitoring endpoint accessible"
            fi
            
            return 0
        fi
        
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo -n "."
        sleep 2
    done
    
    echo ""
    print_error "Application health check failed after $MAX_RETRIES attempts"
    print_error "Check logs: tail -f $LOG_DIR/error.log"
    print_error "Check supervisor: supervisorctl status vertex-ar"
    
    DEPLOYMENT_FAILED=true
    exit 1
}

create_backup_script() {
    print_header "Creating backup script"
    
    BACKUP_SCRIPT="$APP_DIR/vertex-ar/backup.cron.sh"
    
    cat > "$BACKUP_SCRIPT" << 'BACKUP_EOF'
#!/bin/bash
set -e

# Configuration
APP_DIR="/home/rustadmin/vertex-ar-app/vertex-ar"
VENV_DIR="/home/rustadmin/vertex-ar-app/venv"
LOG_FILE="/var/log/vertex-ar/backup.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Change to app directory
cd "$APP_DIR" || {
    log "ERROR: Failed to change directory to $APP_DIR"
    exit 1
}

# Activate virtual environment
source "$VENV_DIR/bin/activate" || {
    log "ERROR: Failed to activate virtual environment"
    exit 1
}

# Check if backup CLI exists
if [ ! -f "backup_cli.py" ]; then
    log "ERROR: backup_cli.py not found"
    exit 1
fi

# Create backup
log "INFO: Starting backup..."
if python3 backup_cli.py create; then
    log "INFO: Backup created successfully"
else
    log "ERROR: Backup creation failed"
    exit 1
fi

# Cleanup old backups (keep last 7)
log "INFO: Cleaning up old backups..."
python3 << 'PYEOF'
import os
import sys
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

try:
    backup_dir = Path('./backups')
    if backup_dir.exists():
        backups = sorted(backup_dir.glob('*.zip'), key=os.path.getctime, reverse=True)
        deleted_count = 0
        for backup in backups[7:]:
            backup.unlink()
            logger.info(f'Deleted old backup: {backup.name}')
            deleted_count += 1
        
        if deleted_count > 0:
            logger.info(f'Cleaned up {deleted_count} old backups')
        else:
            logger.info('No old backups to clean up')
    else:
        logger.warning('Backup directory does not exist')
except Exception as e:
    logger.error(f'Error during backup cleanup: {e}')
    sys.exit(1)
PYEOF

log "INFO: Backup process completed successfully"
deactivate
BACKUP_EOF
    
    chmod +x "$BACKUP_SCRIPT"
    chown "$APP_USER:$APP_GROUP" "$BACKUP_SCRIPT"
    
    # Configure cron job
    CRON_JOB="0 2 * * * $BACKUP_SCRIPT >> $LOG_DIR/backup.log 2>&1"
    
    # Remove old vertex-ar backup jobs
    crontab -u "$APP_USER" -l 2>/dev/null | grep -v "vertex-ar" | grep -v "backup.cron.sh" | crontab -u "$APP_USER" - 2>/dev/null || true
    
    # Add new job
    (crontab -u "$APP_USER" -l 2>/dev/null; echo "$CRON_JOB") | crontab -u "$APP_USER" -
    
    print_success "Backup script created and scheduled (daily at 2:00 AM)"
}

setup_logrotate() {
    print_header "Setting up log rotation"
    
    LOGROTATE_CONF="/etc/logrotate.d/vertex-ar"
    
    cat > "$LOGROTATE_CONF" << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 $APP_USER $APP_GROUP
    sharedscripts
    postrotate
        /usr/bin/supervisorctl restart vertex-ar > /dev/null 2>&1 || true
    endscript
}
EOF
    
    print_success "Log rotation configured (14 days retention)"
}

print_final_info() {
    print_header "Deployment Complete!"
    
    echo ""
    echo -e "${GREEN}✓ Vertex AR has been successfully deployed!${NC}"
    echo ""
    echo "📍 Application URL: https://$DOMAIN/admin"
    echo "🔐 Admin Username: superar"
    echo "🔐 Admin Password: [CHECK YOUR SAVED CREDENTIALS]"
    echo ""
    echo "📊 Monitoring & Management:"
    echo "  • Application logs: tail -f $LOG_DIR/error.log"
    echo "  • Access logs: tail -f $LOG_DIR/access.log"
    echo "  • Nginx logs: tail -f /var/log/nginx/vertex-ar-error.log"
    echo "  • Service status: supervisorctl status vertex-ar"
    echo "  • Health check: curl http://127.0.0.1:$APP_PORT/health"
    echo "  • Monitoring: https://$DOMAIN/api/monitoring/metrics"
    echo ""
    echo "🔧 Service Management:"
    echo "  • Restart app: supervisorctl restart vertex-ar"
    echo "  • Stop app: supervisorctl stop vertex-ar"
    echo "  • Start app: supervisorctl start vertex-ar"
    echo "  • Restart nginx: systemctl restart nginx"
    echo ""
    echo "💾 Backup:"
    echo "  • Backup location: $BACKUP_BASE_DIR"
    echo "  • Latest backup: $(cat /tmp/vertex-ar-last-backup.txt 2>/dev/null || echo 'none')"
    echo "  • Scheduled: Daily at 2:00 AM"
    echo ""
    echo -e "${YELLOW}⚠️  Important Next Steps:${NC}"
    echo "  1. Test application: https://$DOMAIN/admin"
    echo "  2. Upload test portrait and video"
    echo "  3. Verify AR viewer works"
    echo "  4. Configure monitoring alerts (Telegram/Email in .env)"
    echo "  5. Set up Let's Encrypt for production SSL (if using self-signed)"
    echo "  6. Test backup restoration procedure"
    echo "  7. Configure firewall rules (ufw/iptables)"
    echo "  8. Review security best practices"
    echo ""
    echo "📚 Documentation:"
    echo "  • Deployment checklist: DEPLOY_CHECKLIST.md"
    echo "  • Audit report: DEPLOY_SCRIPT_AUDIT_REPORT.md"
    echo "  • Main README: README.md"
    echo ""
    
    log_message "INFO: Deployment completed successfully. Application available at https://$DOMAIN"
}

# ===== MAIN EXECUTION =====

main() {
    # Setup logging
    mkdir -p "$LOG_DIR" 2>/dev/null || true
    
    print_header "Vertex AR Production Deployment v2.0"
    echo "Domain: $DOMAIN"
    echo "User: $APP_USER"
    echo "App Directory: $APP_DIR"
    echo "Log File: $DEPLOY_LOG"
    echo ""
    
    log_message "INFO: Starting deployment for $DOMAIN"
    
    # Pre-flight checks
    check_root
    check_os_version
    check_system_requirements
    check_app_user
    
    # Backup existing installation
    if [ -d "$APP_DIR/vertex-ar" ]; then
        print_warning "Existing installation detected"
        backup_before_deploy
    fi
    
    # System setup
    update_system
    install_dependencies
    check_and_install_python
    install_nodejs
    
    # Application setup
    clone_or_update_repository
    create_virtualenv
    install_python_dependencies
    run_database_migrations
    
    # Configuration
    create_env_file
    validate_production_secrets
    create_log_directory
    
    # Services
    setup_ssl_certificates
    setup_supervisor
    setup_nginx
    
    # Verification
    verify_application_health
    
    # Post-deployment
    create_backup_script
    setup_logrotate
    
    # Final information
    print_final_info
}

# Run main
main "$@"
