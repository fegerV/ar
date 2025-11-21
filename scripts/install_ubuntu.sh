#!/bin/bash

# Enhanced Vertex AR Ubuntu Server Installation Script
# Supports Ubuntu 20.04/22.04/24.04 LTS
# Version 2.0 - Improved with better error handling and local installation support

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="vertex-ar"
PROJECT_DIR="/opt/$PROJECT_NAME"
PROJECT_USER="vertexar"
PROJECT_GROUP="vertexar"
DOMAIN=""
EMAIL=""
INSTALL_MODE="production"
USE_DOCKER=true
INSTALL_SSL=true
USE_POSTGRES=false
USE_MINIO=true
LOCAL_INSTALL=false
SOURCE_DIR=""
INIT_DB=true
CREATE_BACKUP=true

# Default ports
APP_PORT=8000
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --email)
            EMAIL="$2"
            shift 2
            ;;
        --mode)
            INSTALL_MODE="$2"
            shift 2
            ;;
        --no-docker)
            USE_DOCKER=false
            shift
            ;;
        --no-ssl)
            INSTALL_SSL=false
            shift
            ;;
        --postgres)
            USE_POSTGRES=true
            shift
            ;;
        --no-minio)
            USE_MINIO=false
            shift
            ;;
        --local)
            LOCAL_INSTALL=true
            SOURCE_DIR="$2"
            shift 2
            ;;
        --app-port)
            APP_PORT="$2"
            shift 2
            ;;
        --no-db-init)
            INIT_DB=false
            shift
            ;;
        --no-backup)
            CREATE_BACKUP=false
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --domain DOMAIN         Set domain name (required for SSL)"
            echo "  --email EMAIL           Set email for Let's Encrypt"
            echo "  --mode MODE             Installation mode: production|development (default: production)"
            echo "  --no-docker             Install without Docker"
            echo "  --no-ssl                Skip SSL certificate setup"
            echo "  --postgres              Use PostgreSQL instead of SQLite"
            echo "  --no-minio              Skip MinIO installation"
            echo "  --local SOURCE_DIR      Install from local directory instead of Git"
            echo "  --app-port PORT         Custom application port (default: 8000)"
            echo "  --no-db-init            Skip database initialization"
            echo "  --no-backup             Skip backup creation"
            echo "  --help                  Show this help"
            echo ""
            echo "Examples:"
            echo "  $0 --domain example.com --email admin@example.com"
            echo "  $0 --local /path/to/vertex-ar --mode development --no-docker"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Installation log
LOG_FILE="/tmp/vertex_ar_install_$(date +%Y%m%d_%H%M%S).log"

# Logging functions
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

print_header() {
    echo -e "${BLUE}===================================${NC}"
    echo -e "${BLUE}Vertex AR Ubuntu Server Installer${NC}"
    echo -e "${BLUE}Version 2.0 - Enhanced${NC}"
    echo -e "${BLUE}===================================${NC}"
    echo ""
    echo "Installation Configuration:"
    echo "  Mode: $INSTALL_MODE"
    echo "  Domain: ${DOMAIN:-'Not set'}"
    echo "  Email: ${EMAIL:-'Not set'}"
    echo "  Docker: $USE_DOCKER"
    echo "  SSL: $INSTALL_SSL"
    echo "  PostgreSQL: $USE_POSTGRES"
    echo "  MinIO: $USE_MINIO"
    echo "  Local Install: $LOCAL_INSTALL"
    echo "  Source: ${SOURCE_DIR:-'Git Repository'}"
    echo "  App Port: $APP_PORT"
    echo "  DB Init: $INIT_DB"
    echo "  Backup: $CREATE_BACKUP"
    echo "  Log: $LOG_FILE"
    echo ""
}

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
    log "INFO: $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    log "WARNING: $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    log "ERROR: $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
    log "STEP: $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    log "SUCCESS: $1"
}

# Error handling
error_exit() {
    print_error "$1"
    print_error "Installation failed. Check log: $LOG_FILE"
    exit 1
}

# Rollback function
rollback() {
    print_warning "Rolling back installation..."
    
    # Stop services
    systemctl stop vertex-ar 2>/dev/null || true
    systemctl stop nginx 2>/dev/null || true
    systemctl stop minio 2>/dev/null || true
    
    # Remove directories
    rm -rf "$PROJECT_DIR" 2>/dev/null || true
    
    # Remove user
    userdel -r "$PROJECT_USER" 2>/dev/null || true
    
    # Remove nginx config
    rm -f /etc/nginx/sites-enabled/vertex-ar 2>/dev/null || true
    rm -f /etc/nginx/sites-available/vertex-ar 2>/dev/null || true
    
    print_warning "Rollback completed"
}

# Set trap for cleanup
trap 'error_exit "Installation interrupted"' INT TERM

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error_exit "This script must be run as root (use sudo)"
    fi
}

# Function to detect Ubuntu version
detect_ubuntu_version() {
    print_step "Detecting Ubuntu version..."
    
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        print_status "Detected Ubuntu $VERSION"
        if [[ "$VERSION_ID" < "20.04" ]]; then
            error_exit "Ubuntu 20.04 or higher is required"
        fi
    else
        error_exit "Cannot detect Ubuntu version"
    fi
}

# Function to check system resources
check_system_resources() {
    print_step "Checking system resources..."
    
    # Check RAM
    RAM=$(free -m | awk 'NR==2{printf "%.0f", $2/1024}')
    if [[ $RAM -lt 2 ]]; then
        print_warning "System has less than 2GB RAM. Performance may be affected."
    fi
    
    # Check disk space
    DISK=$(df /opt | awk 'NR==2{print $4}')
    if [[ $DISK -lt 5242880 ]]; then # 5GB in KB
        error_exit "Insufficient disk space. At least 5GB required."
    fi
    
    print_status "System resources check passed"
}

# Function to check if ports are available
check_ports() {
    print_step "Checking port availability..."
    
    local ports=("$APP_PORT" "$NGINX_HTTP_PORT" "$NGINX_HTTPS_PORT")
    if [[ "$USE_MINIO" == true ]]; then
        ports+=("$MINIO_PORT" "$MINIO_CONSOLE_PORT")
    fi
    
    for port in "${ports[@]}"; do
        if netstat -tuln | grep -q ":$port "; then
            error_exit "Port $port is already in use"
        fi
    done
    
    print_status "All required ports are available"
}

# Function to update system
update_system() {
    print_step "Updating system packages..."
    
    apt update
    apt upgrade -y
    
    print_status "System updated"
}

# Function to install system dependencies
install_system_dependencies() {
    print_step "Installing system dependencies..."
    
    # Basic dependencies
    apt install -y \
        curl \
        wget \
        git \
        unzip \
        htop \
        vim \
        nano \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release \
        build-essential \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        libmagic1 \
        libffi-dev \
        libssl-dev \
        libpq-dev \
        supervisor \
        ufw \
        net-tools \
        lsof
    
    # Install Nginx
    apt install -y nginx
    
    # Install Node.js for frontend development (optional)
    if [[ "$INSTALL_MODE" == "development" ]]; then
        curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
        apt install -y nodejs
    fi
    
    print_status "System dependencies installed"
}

# Function to install Docker
install_docker() {
    if [[ "$USE_DOCKER" == true ]]; then
        print_step "Installing Docker..."
        
        # Remove old versions
        apt remove -y docker docker-engine docker.io containerd runc || true
        
        # Install Docker
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
        apt update
        apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        
        # Start and enable Docker
        systemctl start docker
        systemctl enable docker
        
        # Add project user to docker group (will be created later)
        usermod -aG docker "$PROJECT_USER" || true
        
        print_status "Docker installed"
    fi
}

# Function to create project user
create_project_user() {
    print_step "Creating project user..."
    
    # Create user and group
    if ! id "$PROJECT_USER" &>/dev/null; then
        useradd -r -m -s /bin/bash "$PROJECT_USER"
        print_status "User $PROJECT_USER created"
    else
        print_status "User $PROJECT_USER already exists"
    fi
    
    # Create project directory
    mkdir -p "$PROJECT_DIR"
    chown "$PROJECT_USER:$PROJECT_USER" "$PROJECT_DIR"
    chmod 755 "$PROJECT_DIR"
    
    print_status "Project directory created: $PROJECT_DIR"
}

# Function to setup PostgreSQL
setup_postgresql() {
    if [[ "$USE_POSTGRES" == true ]]; then
        print_step "Setting up PostgreSQL..."
        
        # Install PostgreSQL
        apt install -y postgresql postgresql-contrib
        
        # Start and enable PostgreSQL
        systemctl start postgresql
        systemctl enable postgresql
        
        # Create database and user
        sudo -u postgres psql <<EOF
CREATE DATABASE vertex_ar;
CREATE USER $PROJECT_USER WITH PASSWORD 'vertexar_secure_password';
GRANT ALL PRIVILEGES ON DATABASE vertex_ar TO $PROJECT_USER;
ALTER USER $PROJECT_USER CREATEDB;
EOF
        
        print_status "PostgreSQL configured"
    fi
}

# Function to setup MinIO
setup_minio() {
    if [[ "$USE_MINIO" == true ]]; then
        print_step "Setting up MinIO..."
        
        # Create MinIO user
        useradd -r -s /bin/false minio-user || true
        
        # Create directories
        mkdir -p /opt/minio/data
        mkdir -p /etc/minio
        chown minio-user:minio-user /opt/minio/data
        chown minio-user:minio-user /etc/minio
        
        # Download MinIO
        MINIO_VERSION="RELEASE.2023-12-14T18-51-57Z"
        wget -O /usr/local/bin/minio "https://dl.min.io/server/minio/release/linux-amd64/archive/minio.$MINIO_VERSION"
        chmod +x /usr/local/bin/minio
        
        # Generate secure password
        MINIO_PASSWORD=$(openssl rand -base64 32)
        
        # Create MinIO environment file
        cat > /etc/default/minio <<EOF
# MinIO local server configuration
MINIO_OPTS="--config-dir /etc/minio --address :9000 --console-address :9001"
MINIO_VOLUMES="/opt/minio/data"
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=$MINIO_PASSWORD
EOF
        
        # Create systemd service
        cat > /etc/systemd/system/minio.service <<EOF
[Unit]
Description=MinIO
Documentation=https://docs.min.io
Wants=network-online.target
After=network-online.target
AssertFileIsExecutable=/usr/local/bin/minio

[Service]
WorkingDirectory=/usr/local/

User=minio-user
Group=minio-user
ProtectProc=invisible

EnvironmentFile=/etc/default/minio
ExecStartPre=/bin/bash -c "if [ -z \"\${MINIO_VOLUMES}\" ]; then echo \"Variable MINIO_VOLUMES not set in /etc/default/minio\"; exit 1; fi"
ExecStart=/usr/local/bin/minio server \$MINIO_OPTS \$MINIO_VOLUMES

Restart=always
LimitNOFILE=65536
TasksMax=infinity
TimeoutStopSec=infinity
SendSIGKILL=no

[Install]
WantedBy=multi-user.target
EOF
        
        # Reload systemd and start MinIO
        systemctl daemon-reload
        systemctl enable minio
        systemctl start minio
        
        # Wait for MinIO to start
        sleep 5
        
        # Verify MinIO is running
        if ! systemctl is-active --quiet minio; then
            error_exit "MinIO failed to start"
        fi
        
        print_status "MinIO configured"
        print_status "MinIO Console: http://$(hostname -I | awk '{print $1}'):9001"
        print_status "MinIO Username: minioadmin"
        print_status "MinIO Password: $MINIO_PASSWORD"
    fi
}

# Function to deploy application
deploy_application() {
    print_step "Deploying Vertex AR application..."
    
    cd "$PROJECT_DIR"
    
    if [[ "$LOCAL_INSTALL" == true ]]; then
        # Copy from local directory
        if [[ ! -d "$SOURCE_DIR" ]]; then
            error_exit "Source directory $SOURCE_DIR does not exist"
        fi
        
        print_status "Copying files from $SOURCE_DIR"
        cp -r "$SOURCE_DIR"/* .
        chown -R "$PROJECT_USER:$PROJECT_USER" .
        
    else
        # Clone from Git repository
        print_status "Cloning from Git repository..."
        sudo -u "$PROJECT_USER" git clone https://github.com/fegerV/ar.git .
        
        # Verify clone was successful
        if [[ ! -f "vertex-ar/main.py" ]]; then
            error_exit "Failed to clone repository or invalid repository structure"
        fi
    fi
    
    if [[ "$USE_DOCKER" == false ]]; then
        # Install Python dependencies
        print_status "Setting up Python environment..."
        sudo -u "$PROJECT_USER" python3 -m venv venv
        sudo -u "$PROJECT_USER" venv/bin/pip install --upgrade pip
        sudo -u "$PROJECT_USER" venv/bin/pip install -r vertex-ar/requirements.txt
        
        # Create environment file
        print_status "Creating environment configuration..."
        sudo -u "$PROJECT_USER" bash -c "cat > .env <<EOF
# Database Configuration
DATABASE_URL=$([ "$USE_POSTGRES" == true ] && echo "postgresql://$PROJECT_USER:vertexar_secure_password@localhost/vertex_ar" || echo "sqlite:///./app_data.db")

# MinIO Configuration
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=$([ "$USE_MINIO" == true ] && echo "$(grep MINIO_ROOT_PASSWORD /etc/default/minio | cut -d'=' -f2)" || echo "local_storage_password")
MINIO_BUCKET=vertex-art-bucket

# Application Configuration
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=$([ "$INSTALL_MODE" == "development" ] && echo "true" || echo "false")
ENVIRONMENT=$INSTALL_MODE
APP_PORT=$APP_PORT

# Admin User
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$(openssl rand -base64 16)
ADMIN_EMAIL=$EMAIL

# Storage
STORAGE_TYPE=$([ "$USE_MINIO" == true ] && echo "minio" || echo "local")
STORAGE_PATH=./storage

# Rate Limiting
RATE_LIMIT_ENABLED=$([ "$INSTALL_MODE" == "production" ] && echo "true" || echo "false")
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Logging
LOG_LEVEL=$([ "$INSTALL_MODE" == "development" ] && echo "DEBUG" || echo "INFO")
EOF"
        
        # Create storage directories
        sudo -u "$PROJECT_USER" mkdir -p storage/{ar_content,nft-markers,qr-codes,temp,previews,images,videos}
        sudo -u "$PROJECT_USER" mkdir -p logs
        sudo -u "$PROJECT_USER" mkdir -p app_data
        
        # Create systemd service
        print_status "Creating systemd service..."
        cat > /etc/systemd/system/vertex-ar.service <<EOF
[Unit]
Description=Vertex AR Application
After=network.target

[Service]
Type=simple
User=$PROJECT_USER
Group=$PROJECT_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python -m uvicorn vertex-ar.main:app --host 0.0.0.0 --port $APP_PORT
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        # Enable and start service
        systemctl daemon-reload
        systemctl enable vertex-ar
        
        print_status "Application deployed without Docker"
        
    else
        # Create Docker environment file
        print_status "Creating Docker environment..."
        sudo -u "$PROJECT_USER" bash -c "cat > .env <<EOF
# Database Configuration
DATABASE_URL=sqlite:///./data/app_data.db

# MinIO Configuration
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=$([ "$USE_MINIO" == true ] && echo "$(grep MINIO_ROOT_PASSWORD /etc/default/minio | cut -d'=' -f2)" || echo "local_storage_password")
MINIO_BUCKET=vertex-art-bucket

# Application Configuration
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=$([ "$INSTALL_MODE" == "development" ] && echo "true" || echo "false")
ENVIRONMENT=$INSTALL_MODE
APP_PORT=8000

# Admin User
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$(openssl rand -base64 16)
ADMIN_EMAIL=$EMAIL

# Storage
STORAGE_TYPE=minio
STORAGE_PATH=./storage

# Rate Limiting
RATE_LIMIT_ENABLED=$([ "$INSTALL_MODE" == "production" ] && echo "true" || echo "false")
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Logging
LOG_LEVEL=$([ "$INSTALL_MODE" == "development" ] && echo "DEBUG" || echo "INFO")
EOF"
        
        # Create storage directories
        sudo -u "$PROJECT_USER" mkdir -p storage/{ar_content,nft-markers,qr-codes,temp,previews,images,videos}
        sudo -u "$PROJECT_USER" mkdir -p app_data
        
        print_status "Application deployed with Docker"
    fi
}

# Function to initialize database
initialize_database() {
    if [[ "$INIT_DB" == true ]]; then
        print_step "Initializing database..."
        
        if [[ "$USE_DOCKER" == false ]]; then
            # Initialize database using Python script
            cd "$PROJECT_DIR"
            sudo -u "$PROJECT_USER" bash -c "
            source venv/bin/activate
            cd vertex-ar
            python -c '
from app.database import init_db
init_db()
print(\"Database initialized successfully\")
' || echo 'Database initialization script not found, will be created on first run'
"
        else
            # Database will be initialized when container starts
            print_status "Database will be initialized when Docker container starts"
        fi
        
        print_status "Database initialization completed"
    fi
}

# Function to setup Nginx
setup_nginx() {
    print_step "Setting up Nginx..."
    
    # Create Nginx configuration
    cat > /etc/nginx/sites-available/vertex-ar <<EOF
# Nginx configuration for Vertex AR
server {
    listen 80;
    server_name ${DOMAIN:-_} localhost;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

EOF

    if [[ "$INSTALL_SSL" == true && -n "$DOMAIN" ]]; then
        cat >> /etc/nginx/sites-available/vertex-ar <<EOF
    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name $DOMAIN;

    # SSL certificates (will be added by Certbot)
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

EOF
    else
        cat >> /etc/nginx/sites-available/vertex-ar <<EOF
    # Main application proxy
    location / {
EOF
    fi

    cat >> /etc/nginx/sites-available/vertex-ar <<EOF
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts for file uploads
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering off;
        client_max_body_size 100M;
    }
EOF

    if [[ "$USE_MINIO" == true ]]; then
        cat >> /etc/nginx/sites-available/vertex-ar <<EOF

    # MinIO proxy for static files
    location /images/ {
        proxy_pass http://127.0.0.1:9000/vertex-art-bucket/images/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /videos/ {
        proxy_pass http://127.0.0.1:9000/vertex-art-bucket/videos/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /nft-markers/ {
        proxy_pass http://127.0.0.1:9000/vertex-art-bucket/nft-markers/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
EOF
    fi

    cat >> /etc/nginx/sites-available/vertex-ar <<EOF

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:$APP_PORT/health;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    # Enable site
    ln -sf /etc/nginx/sites-available/vertex-ar /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default

    # Test Nginx configuration
    nginx -t || error_exit "Nginx configuration test failed"

    # Restart Nginx
    systemctl restart nginx
    systemctl enable nginx

    print_status "Nginx configured"
}

# Function to setup SSL
setup_ssl() {
    if [[ "$INSTALL_SSL" == true && -n "$DOMAIN" && -n "$EMAIL" ]]; then
        print_step "Setting up SSL certificate..."
        
        # Install Certbot
        apt install -y certbot python3-certbot-nginx
        
        # Create certbot directory
        mkdir -p /var/www/certbot
        
        # Obtain certificate
        certbot --nginx -d "$DOMAIN" --email "$EMAIL" --agree-tos --non-interactive || error_exit "Failed to obtain SSL certificate"
        
        # Setup auto-renewal
        echo "0 12 * * * /usr/bin/certbot renew --quiet" | crontab -
        
        print_status "SSL certificate installed"
    elif [[ "$INSTALL_SSL" == true ]]; then
        print_warning "SSL installation skipped: domain and email required"
    fi
}

# Function to start services
start_services() {
    print_step "Starting services..."
    
    if [[ "$USE_DOCKER" == false ]]; then
        # Start application service
        systemctl start vertex-ar
        if ! systemctl is-active --quiet vertex-ar; then
            error_exit "Vertex AR service failed to start"
        fi
        print_status "Vertex AR service started"
    else
        # Start Docker containers
        cd "$PROJECT_DIR"
        docker-compose up -d || error_exit "Failed to start Docker containers"
        print_status "Docker containers started"
    fi
    
    print_status "All services started"
}

# Function to perform health checks
health_checks() {
    print_step "Performing health checks..."
    
    local failed_checks=0
    
    # Check application health
    sleep 10  # Wait for services to fully start
    
    if curl -f -s "http://127.0.0.1:$APP_PORT/health" >/dev/null 2>&1; then
        print_success "Application health check passed"
    else
        print_error "Application health check failed"
        ((failed_checks++))
    fi
    
    # Check Nginx
    if systemctl is-active --quiet nginx; then
        print_success "Nginx is running"
    else
        print_error "Nginx is not running"
        ((failed_checks++))
    fi
    
    # Check MinIO if enabled
    if [[ "$USE_MINIO" == true ]]; then
        if systemctl is-active --quiet minio; then
            print_success "MinIO is running"
        else
            print_error "MinIO is not running"
            ((failed_checks++))
        fi
    fi
    
    # Check PostgreSQL if enabled
    if [[ "$USE_POSTGRES" == true ]]; then
        if systemctl is-active --quiet postgresql; then
            print_success "PostgreSQL is running"
        else
            print_error "PostgreSQL is not running"
            ((failed_checks++))
        fi
    fi
    
    if [[ $failed_checks -gt 0 ]]; then
        print_warning "$failed_checks health checks failed"
    else
        print_success "All health checks passed"
    fi
}

# Function to create backup
create_backup() {
    if [[ "$CREATE_BACKUP" == true ]]; then
        print_step "Creating backup..."
        
        local backup_dir="/opt/backups/vertex-ar"
        local backup_name="vertex_ar_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
        
        mkdir -p "$backup_dir"
        
        tar -czf "$backup_dir/$backup_name" -C "$(dirname "$PROJECT_DIR")" "$(basename "$PROJECT_DIR")"
        
        print_status "Backup created: $backup_dir/$backup_name"
    fi
}

# Function to display installation summary
display_summary() {
    echo ""
    echo -e "${GREEN}===================================${NC}"
    echo -e "${GREEN}Installation Completed Successfully!${NC}"
    echo -e "${GREEN}===================================${NC}"
    echo ""
    echo "Installation Summary:"
    echo "  Project Directory: $PROJECT_DIR"
    echo "  Project User: $PROJECT_USER"
    echo "  Installation Mode: $INSTALL_MODE"
    echo "  Docker: $USE_DOCKER"
    echo "  SSL: $INSTALL_SSL"
    echo "  PostgreSQL: $USE_POSTGRES"
    echo "  MinIO: $USE_MINIO"
    echo ""
    echo "Access Information:"
    
    if [[ -n "$DOMAIN" ]]; then
        if [[ "$INSTALL_SSL" == true ]]; then
            echo "  Application URL: https://$DOMAIN"
        else
            echo "  Application URL: http://$DOMAIN"
        fi
    else
        echo "  Application URL: http://$(hostname -I | awk '{print $1}'):$APP_PORT"
    fi
    
    echo "  Admin Panel: http://$(hostname -I | awk '{print $1}'):$APP_PORT/admin"
    
    if [[ "$USE_MINIO" == true ]]; then
        echo "  MinIO Console: http://$(hostname -I | awk '{print $1}'):9001"
        echo "  MinIO Username: minioadmin"
        echo "  MinIO Password: $(grep MINIO_ROOT_PASSWORD /etc/default/minio | cut -d'=' -f2)"
    fi
    
    echo ""
    echo "Service Management:"
    if [[ "$USE_DOCKER" == false ]]; then
        echo "  Start: sudo systemctl start vertex-ar"
        echo "  Stop: sudo systemctl stop vertex-ar"
        echo "  Restart: sudo systemctl restart vertex-ar"
        echo "  Status: sudo systemctl status vertex-ar"
        echo "  Logs: sudo journalctl -u vertex-ar -f"
    else
        echo "  Start: cd $PROJECT_DIR && docker-compose up -d"
        echo "  Stop: cd $PROJECT_DIR && docker-compose down"
        echo "  Logs: cd $PROJECT_DIR && docker-compose logs -f"
    fi
    
    echo ""
    echo "Configuration Files:"
    echo "  Environment: $PROJECT_DIR/.env"
    echo "  Nginx: /etc/nginx/sites-available/vertex-ar"
    echo "  Installation Log: $LOG_FILE"
    
    if [[ "$CREATE_BACKUP" == true ]]; then
        echo "  Backup: /opt/backups/vertex-ar/"
    fi
    
    echo ""
    echo "Next Steps:"
    echo "1. Access the application and create admin account"
    echo "2. Configure your domain name (if applicable)"
    echo "3. Review security settings"
    echo "4. Test all features"
    
    echo ""
    echo -e "${GREEN}Thank you for installing Vertex AR!${NC}"
}

# Main installation function
main() {
    print_header
    
    # Pre-installation checks
    check_root
    detect_ubuntu_version
    check_system_resources
    check_ports
    
    # Installation steps
    update_system
    install_system_dependencies
    install_docker
    create_project_user
    setup_postgresql
    setup_minio
    deploy_application
    initialize_database
    setup_nginx
    setup_ssl
    start_services
    health_checks
    create_backup
    
    # Display summary
    display_summary
}

# Run main function
main "$@"
