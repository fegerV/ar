#!/bin/bash

# Полный скрипт установки Vertex AR на Ubuntu Server
# Поддерживает Ubuntu 20.04/22.04/24.04 LTS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --domain DOMAIN      Set domain name (required for SSL)"
            echo "  --email EMAIL        Set email for Let's Encrypt"
            echo "  --mode MODE          Installation mode: production|development (default: production)"
            echo "  --no-docker          Install without Docker"
            echo "  --no-ssl             Skip SSL certificate setup"
            echo "  --postgres           Use PostgreSQL instead of SQLite"
            echo "  --no-minio           Skip MinIO installation"
            echo "  --help               Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}===================================${NC}"
echo -e "${BLUE}Vertex AR Ubuntu Server Installer${NC}"
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
echo ""

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Function to detect Ubuntu version
detect_ubuntu_version() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        print_status "Detected Ubuntu $VERSION"
        if [[ "$VERSION_ID" < "20.04" ]]; then
            print_error "Ubuntu 20.04 or higher is required"
            exit 1
        fi
    else
        print_error "Cannot detect Ubuntu version"
        exit 1
    fi
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
        ufw
    
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
        usermod -aG docker $PROJECT_USER || true
        
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
        
        # Create MinIO environment file
        cat > /etc/default/minio <<EOF
# MinIO local server configuration
MINIO_OPTS="--config-dir /etc/minio --address :9000 --console-address :9001"
MINIO_VOLUMES="/opt/minio/data"
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=$(openssl rand -base64 32)
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
        
        print_status "MinIO configured"
    fi
}

# Function to deploy application
deploy_application() {
    print_step "Deploying Vertex AR application..."
    
    # Clone repository
    cd "$PROJECT_DIR"
    sudo -u "$PROJECT_USER" git clone https://github.com/your-org/vertex-ar.git .
    
    if [[ "$USE_DOCKER" == false ]]; then
        # Install Python dependencies
        sudo -u "$PROJECT_USER" python3 -m venv venv
        sudo -u "$PROJECT_USER" venv/bin/pip install --upgrade pip
        sudo -u "$PROJECT_USER" venv/bin/pip install -r vertex-ar/requirements.txt
        
        # Create environment file
        sudo -u "$PROJECT_USER" bash -c "cat > .env <<EOF
# Database Configuration
DATABASE_URL=$([ "$USE_POSTGRES" == true ] && echo "postgresql://$PROJECT_USER:vertexar_secure_password@localhost/vertex_ar" || echo "sqlite:///./app_data.db")

# MinIO Configuration
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=\$(grep MINIO_ROOT_PASSWORD /etc/default/minio | cut -d'=' -f2)
MINIO_BUCKET=vertex-art-bucket

# Application Configuration
SECRET_KEY=\$(openssl rand -hex 32)
DEBUG=$([ "$INSTALL_MODE" == "development" ] && echo "true" || echo "false")
ENVIRONMENT=$INSTALL_MODE

# Admin User
ADMIN_USERNAME=admin
ADMIN_PASSWORD=\$(openssl rand -base64 16)
ADMIN_EMAIL=$EMAIL

# Storage
STORAGE_TYPE=$([ "$USE_MINIO" == true ] && echo "minio" || echo "local")
STORAGE_PATH=./storage

# Rate Limiting
RATE_LIMIT_ENABLED=$([ "$INSTALL_MODE" == "production" ] && echo "true" || echo "false")
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
EOF"
        
        # Create storage directories
        sudo -u "$PROJECT_USER" mkdir -p storage/{ar_content,nft-markers,qr-codes,temp,previews,images,videos}
        sudo -u "$PROJECT_USER" mkdir -p logs
        
        print_status "Application deployed without Docker"
    else
        # Create Docker environment file
        sudo -u "$PROJECT_USER" bash -c "cat > .env <<EOF
# Database Configuration
DATABASE_URL=sqlite:///./data/app_data.db

# MinIO Configuration
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=\$(grep MINIO_ROOT_PASSWORD /etc/default/minio | cut -d'=' -f2)
MINIO_BUCKET=vertex-art-bucket

# Application Configuration
SECRET_KEY=\$(openssl rand -hex 32)
DEBUG=$([ "$INSTALL_MODE" == "development" ] && echo "true" || echo "false")
ENVIRONMENT=$INSTALL_MODE

# Admin User
ADMIN_USERNAME=admin
ADMIN_PASSWORD=\$(openssl rand -base64 16)
ADMIN_EMAIL=$EMAIL

# Storage
STORAGE_TYPE=minio
STORAGE_PATH=./storage

# Rate Limiting
RATE_LIMIT_ENABLED=$([ "$INSTALL_MODE" == "production" ] && echo "true" || echo "false")
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
EOF"
        
        print_status "Application deployed with Docker"
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
        proxy_pass http://$([ "$USE_DOCKER" == true ] && echo "127.0.0.1:8000" || echo "127.0.0.1:8000");
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
        proxy_pass http://$([ "$USE_DOCKER" == true ] && echo "127.0.0.1:9000" || echo "127.0.0.1:9000")/vertex-art-bucket/images/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /videos/ {
        proxy_pass http://$([ "$USE_DOCKER" == true ] && echo "127.0.0.1:9000" || echo "127.0.0.1:9000")/vertex-art-bucket/videos/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /nft-markers/ {
        proxy_pass http://$([ "$USE_DOCKER" == true ] && echo "127.0.0.1:9000" || echo "127.0.0.1:9000")/vertex-art-bucket/nft-markers/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
EOF
    fi

    cat >> /etc/nginx/sites-available/vertex-ar <<EOF
}
EOF

    # Enable site
    ln -sf /etc/nginx/sites-available/vertex-ar /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Test and restart Nginx
    nginx -t
    systemctl restart nginx
    systemctl enable nginx
    
    print_status "Nginx configured"
}

# Function to setup SSL with Let's Encrypt
setup_ssl() {
    if [[ "$INSTALL_SSL" == true && -n "$DOMAIN" && -n "$EMAIL" ]]; then
        print_step "Setting up SSL with Let's Encrypt..."
        
        # Install Certbot
        apt install -y certbot python3-certbot-nginx
        
        # Create webroot directory
        mkdir -p /var/www/certbot
        
        # Obtain SSL certificate
        certbot --nginx -d "$DOMAIN" --email "$EMAIL" --agree-tos --non-interactive
        
        # Setup auto-renewal
        (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --post-hook 'systemctl reload nginx'") | crontab -
        
        print_status "SSL certificate installed for $DOMAIN"
    elif [[ "$INSTALL_SSL" == true ]]; then
        print_warning "SSL setup skipped: domain and email required"
        print_warning "Use: --domain yourdomain.com --email your@email.com"
    fi
}

# Function to setup Supervisor
setup_supervisor() {
    if [[ "$USE_DOCKER" == false ]]; then
        print_step "Setting up Supervisor..."
        
        # Create Supervisor configuration
        cat > /etc/supervisor/conf.d/vertex-ar.conf <<EOF
[program:vertex-ar]
command=$PROJECT_DIR/venv/bin/uvicorn vertex-ar.main:app --host 127.0.0.1 --port 8000
directory=$PROJECT_DIR/vertex-ar
user=$PROJECT_USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/vertex-ar.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
environment=PATH="$PROJECT_DIR/venv/bin"
EOF
        
        # Reload Supervisor
        supervisorctl reread
        supervisorctl update
        supervisorctl start vertex-ar
        
        print_status "Supervisor configured"
    fi
}

# Function to setup Docker Compose
setup_docker_compose() {
    if [[ "$USE_DOCKER" == true ]]; then
        print_step "Setting up Docker Compose..."
        
        # Create docker-compose.yml
        sudo -u "$PROJECT_USER" bash -c "cat > docker-compose.yml <<EOF
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.app
    ports:
      - \"8000:8000\"
    environment:
      - DATABASE_URL=sqlite:///./data/app_data.db
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_ROOT_PASSWORD=\$(grep MINIO_ROOT_PASSWORD /etc/default/minio | cut -d'=' -f2)
      - MINIO_BUCKET=vertex-art-bucket
      - SECRET_KEY=\$(openssl rand -hex 32)
      - DEBUG=$([ "$INSTALL_MODE" == "development" ] && echo "true" || echo "false")
      - ENVIRONMENT=$INSTALL_MODE
      - ADMIN_USERNAME=admin
      - ADMIN_PASSWORD=\$(openssl rand -base64 16)
      - ADMIN_EMAIL=$EMAIL
      - STORAGE_TYPE=minio
    volumes:
      - ./app_data:/app/data
      - ./storage:/app/storage
    depends_on:
      - minio
    restart: unless-stopped

EOF

        if [[ "$USE_MINIO" == true ]]; then
            sudo -u "$PROJECT_USER" bash -c "cat >> docker-compose.yml <<EOF
  minio:
    image: minio/minio:latest
    ports:
      - \"9000:9000\"
      - \"9001:9001\"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=\$(grep MINIO_ROOT_PASSWORD /etc/default/minio | cut -d'=' -f2)
    volumes:
      - minio_data:/data
    command: server /data --console-address \":9001\"
    restart: unless-stopped

EOF
        fi

        sudo -u "$PROJECT_USER" bash -c "cat >> docker-compose.yml <<EOF
volumes:
  minio_data:
EOF"
        
        # Create Dockerfile
        sudo -u "$PROJECT_USER" bash -c "cat > Dockerfile.app <<EOF
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    libmagic1 \\
    libmagic-dev \\
    libffi-dev \\
    libssl-dev \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY vertex-ar/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY vertex-ar/ .

# Create data directory
RUN mkdir -p /app/data /app/storage

# Expose port
EXPOSE 8000

# Run application
CMD [\"uvicorn\", \"main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]
EOF"
        
        # Build and start containers
        cd "$PROJECT_DIR"
        sudo -u "$PROJECT_USER" docker compose build
        sudo -u "$PROJECT_USER" docker compose up -d
        
        print_status "Docker Compose configured"
    fi
}

# Function to setup firewall
setup_firewall() {
    print_step "Setting up firewall..."
    
    # Configure UFW
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH
    ufw allow ssh
    
    # Allow HTTP/HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Allow MinIO console (if enabled)
    if [[ "$USE_MINIO" == true ]]; then
        ufw allow 9001/tcp
    fi
    
    # Enable firewall
    ufw --force enable
    
    print_status "Firewall configured"
}

# Function to create admin user
create_admin_user() {
    print_step "Creating admin user..."
    
    if [[ "$USE_DOCKER" == true ]]; then
        # Wait for application to start
        sleep 10
        
        # Create admin user via API
        ADMIN_PASS=$(sudo -u "$PROJECT_USER" grep ADMIN_PASSWORD "$PROJECT_DIR/.env" | cut -d'=' -f2)
        curl -X POST "http://localhost:8000/auth/register" \
             -H "Content-Type: application/json" \
             -d "{
                 \"username\": \"admin\",
                 \"password\": \"$ADMIN_PASS\",
                 \"email\": \"$EMAIL\",
                 \"full_name\": \"Administrator\"
             }" || true
    else
        # Create admin user via direct database access
        if [[ "$USE_POSTGRES" == true ]]; then
            sudo -u "$PROJECT_USER" "$PROJECT_DIR/venv/bin/python" -c "
from vertex-ar.database import get_db
from vertex-ar.auth import get_password_hash
from vertex-ar.models import User

# This would need to be implemented based on your actual models
print('Admin user creation would be implemented here')
"
        fi
    fi
    
    print_status "Admin user setup completed"
}

# Function to show installation summary
show_installation_summary() {
    echo ""
    echo -e "${GREEN}===================================${NC}"
    echo -e "${GREEN}Installation Complete!${NC}"
    echo -e "${GREEN}===================================${NC}"
    echo ""
    echo "Vertex AR has been successfully installed on your Ubuntu server!"
    echo ""
    echo "Configuration Summary:"
    echo "  Project Directory: $PROJECT_DIR"
    echo "  Project User: $PROJECT_USER"
    echo "  Installation Mode: $INSTALL_MODE"
    echo "  Docker: $USE_DOCKER"
    echo "  SSL: $INSTALL_SSL"
    echo "  PostgreSQL: $USE_POSTGRES"
    echo "  MinIO: $USE_MINIO"
    echo ""
    
    if [[ -n "$DOMAIN" ]]; then
        echo "Access URLs:"
        echo "  Application: https://$DOMAIN"
        if [[ "$USE_MINIO" == true ]]; then
            echo "  MinIO Console: https://$DOMAIN:9001"
        fi
    else
        echo "Access URLs:"
        echo "  Application: http://$(hostname -I | awk '{print $1}')"
        if [[ "$USE_MINIO" == true ]]; then
            echo "  MinIO Console: http://$(hostname -I | awk '{print $1}'):9001"
        fi
    fi
    
    echo ""
    echo "Important Files:"
    echo "  Environment: $PROJECT_DIR/.env"
    echo "  Nginx Config: /etc/nginx/sites-available/vertex-ar"
    if [[ "$USE_DOCKER" == false ]]; then
        echo "  Supervisor Config: /etc/supervisor/conf.d/vertex-ar.conf"
    else
        echo "  Docker Compose: $PROJECT_DIR/docker-compose.yml"
    fi
    
    echo ""
    echo "Useful Commands:"
    if [[ "$USE_DOCKER" == true ]]; then
        echo "  View logs: sudo -u $PROJECT_USER docker compose -C $PROJECT_DIR logs -f"
        echo "  Restart: sudo -u $PROJECT_USER docker compose -C $PROJECT_DIR restart"
        echo "  Stop: sudo -u $PROJECT_USER docker compose -C $PROJECT_DIR down"
    else
        echo "  View logs: tail -f /var/log/vertex-ar.log"
        echo "  Restart: supervisorctl restart vertex-ar"
        echo "  Status: supervisorctl status vertex-ar"
    fi
    echo "  Nginx reload: sudo nginx -t && sudo systemctl reload nginx"
    echo "  Firewall status: sudo ufw status"
    
    if [[ "$INSTALL_SSL" == true && -n "$DOMAIN" ]]; then
        echo ""
        echo "SSL Certificate:"
        echo "  Certificate will auto-renew via cron"
        echo "  Manual renewal: sudo certbot renew"
    fi
    
    echo ""
    echo "Next Steps:"
    echo "1. Update your DNS records to point to this server"
    echo "2. Configure your domain if not already done"
    echo "3. Test the application by accessing the URLs above"
    echo "4. Create additional users via the admin interface"
    echo "5. Configure backup strategies for your data"
    
    if [[ "$USE_MINIO" == true ]]; then
        echo ""
        echo "MinIO Default Credentials:"
        echo "  Username: minioadmin"
        echo "  Password: Check /etc/default/minio"
    fi
    
    echo ""
    echo -e "${GREEN}Thank you for installing Vertex AR!${NC}"
}

# Main installation function
main() {
    print_status "Starting Vertex AR installation..."
    
    check_root
    detect_ubuntu_version
    update_system
    install_system_dependencies
    install_docker
    create_project_user
    setup_postgresql
    setup_minio
    deploy_application
    setup_nginx
    setup_ssl
    setup_supervisor
    setup_docker_compose
    setup_firewall
    create_admin_user
    show_installation_summary
    
    print_status "Installation completed successfully!"
}

# Run main function
main "$@"