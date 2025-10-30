#!/bin/bash

# Deployment script for Vertex AR application

# Exit on any error
set -e

# Configuration
PROJECT_DIR="/opt/vertex-art-ar"
VENV_DIR="$PROJECT_DIR/venv"
USER="vertexart"
GROUP="vertexart"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root. Please run as a regular user with sudo privileges."
        exit 1
    fi
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    
    # Update package list
    sudo apt update
    
    # Install required packages
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        postgresql-contrib \
        nginx \
        supervisor \
        git \
        curl \
        wget
    
    log "System dependencies installed successfully."
}

# Setup PostgreSQL database
setup_database() {
    log "Setting up PostgreSQL database..."
    
    # Start PostgreSQL service
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
    
    # Create database and user
    sudo -u postgres psql <<EOF
CREATE DATABASE vertex_art_ar;
CREATE USER vertexart WITH PASSWORD 'vertexart_password';
GRANT ALL PRIVILEGES ON DATABASE vertex_art_ar TO vertexart;
EOF
    
    # Verify database creation
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw vertex_art_ar; then
        log "Database 'vertex_art_ar' created successfully"
    else
        error "Failed to create database 'vertex_art_ar'"
        exit 1
    fi
    
    log "PostgreSQL database setup completed."
}

# Setup MinIO storage
setup_minio() {
    log "Setting up MinIO storage..."
    
    # Create MinIO user and group
    sudo useradd -r -s /bin/false minio-user || true
    
    # Create data directory for MinIO
    sudo mkdir -p /opt/minio/data
    sudo chown minio-user:minio-user /opt/minio/data
    
    # Download MinIO server
    sudo wget -O /usr/local/bin/minio https://dl.min.io/server/minio/release/linux-amd64/minio
    sudo chmod +x /usr/local/bin/minio
    
    # Create MinIO configuration directory
    sudo mkdir -p /etc/minio
    sudo chown minio-user:minio-user /etc/minio
    
    # Create MinIO environment file
    sudo tee /etc/default/minio > /dev/null <<EOF
# MinIO local server configuration
MINIO_OPTS="--config-dir /etc/minio --address :9000"
MINIO_VOLUMES="/opt/minio/data"
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
EOF
    
    # Create systemd service file
    sudo tee /etc/systemd/system/minio.service > /dev/null <<EOF
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

# Let systemd restart this service always
Restart=always

# Specifies the maximum file descriptor number that can be opened by this process
LimitNOFILE=65536

# Specifies the maximum number of threads this process can create
TasksMax=infinity

# Disable timeout logic and wait until process is stopped
TimeoutStopSec=infinity
SendSIGKILL=no

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and start MinIO service
    sudo systemctl daemon-reload
    sudo systemctl enable minio
    sudo systemctl start minio
    
    log "MinIO storage setup completed."
}

# Deploy application
deploy_application() {
    log "Deploying application..."
    
    # Create project directory
    sudo mkdir -p $PROJECT_DIR
    sudo chown $USER:$GROUP $PROJECT_DIR || true
    
    # Clone or update repository
    if [ -d "$PROJECT_DIR/.git" ]; then
        cd $PROJECT_DIR
        git pull
    else
        git clone https://github.com/your-username/vertex-art-ar.git $PROJECT_DIR
        cd $PROJECT_DIR
    fi
    
    # Create virtual environment
    python3 -m venv $VENV_DIR
    source $VENV_DIR/bin/activate
    
    # Install Python dependencies
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        cat > .env <<EOF
DATABASE_URL=postgresql://vertexart:vertexart_password@localhost/vertex_art_ar
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=vertex-art-bucket
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password_here
SECRET_KEY=$(openssl rand -hex 32)
EOF
        log ".env file created with secure defaults"
    else
        log ".env file already exists, skipping creation"
    fi
    
    log "Application deployed successfully."
}

# Setup Nginx
setup_nginx() {
    log "Setting up Nginx..."
    
    # Create Nginx configuration
    sudo tee /etc/nginx/sites-available/vertex-art-ar > /dev/null <<EOF
server {
    listen 80;
    server_name _; # Accept any domain, change to your domain in production
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # Main application proxy
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Increase timeouts for file uploads
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering off;
    }
    
    # MinIO proxy for static files
    location /images/ {
        proxy_pass http://localhost:9000/vertex-art-bucket/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /videos/ {
        proxy_pass http://localhost:9000/vertex-art-bucket/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /nft-markers/ {
        proxy_pass http://localhost:9000/vertex-art-bucket/nft-markers/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /previews/ {
        proxy_pass http://localhost:9000/vertex-art-bucket/previews/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    
    # Enable site
    sudo ln -sf /etc/nginx/sites-available/vertex-art-ar /etc/nginx/sites-enabled/
    
    # Remove default site
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test Nginx configuration
    sudo nginx -t
    
    # Restart Nginx
    sudo systemctl restart nginx
    
    log "Nginx setup completed."
}

# Setup Supervisor for application management
setup_supervisor() {
    log "Setting up Supervisor..."
    
    # Create Supervisor configuration
    sudo tee /etc/supervisor/conf.d/vertex-art-ar.conf > /dev/null <<EOF
[program:vertex-art-ar]
command=$VENV_DIR/bin/uvicorn main:app --host 127.0.0.1 --port 8000
directory=$PROJECT_DIR
user=$USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/vertex-art-ar.log
EOF
    
    # Reload Supervisor configuration
    sudo supervisorctl reread
    sudo supervisorctl update
    sudo supervisorctl start vertex-art-ar
    
    log "Supervisor setup completed."
}

# Setup SSL certificate with Let's Encrypt
setup_ssl() {
    log "Setting up SSL certificate with Let's Encrypt..."
    
    # Install Certbot
    sudo apt install -y certbot python3-certbot-nginx
    
    # Obtain SSL certificate
    # Note: You need to replace 'your-domain.com' with your actual domain
    read -p "Enter your domain name (e.g., example.com): " domain_name
    
    if [ -z "$domain_name" ]; then
        warn "No domain provided, skipping SSL setup"
        return
    fi
    
    sudo certbot --nginx -d $domain_name
    
    # Setup auto-renewal
    sudo crontab -l | { cat; echo "0 12 * * * /usr/bin/certbot renew --quiet"; } | sudo crontab -
    
    log "SSL certificate setup completed for $domain_name"
}

# Main deployment function
main() {
    log "Starting deployment of Vertex AR application..."
    
    check_root
    install_dependencies
    setup_database
    setup_minio
    deploy_application
    setup_nginx
    setup_supervisor
    
    log "Deployment completed successfully!"
    log "Please note:"
    log "1. Replace 'your-domain.com' with your actual domain in Nginx configuration"
    log "2. Obtain SSL certificate with Let's Encrypt by running 'setup_ssl' function"
    log "3. Update .env file with your actual credentials"
    log "4. Configure firewall to allow HTTP (80), HTTPS (443), and SSH (22) ports"
}

# Run main function
main "$@"