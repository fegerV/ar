# Vertex AR Installation Examples

This document provides practical examples for installing Vertex AR using the Ubuntu installation scripts.

## Quick Start Examples

### Example 1: Basic Production Installation
```bash
# Install with domain and SSL
sudo ./install_ubuntu.sh --domain ar.example.com --email admin@example.com
```

### Example 2: Quick Installation
```bash
# Using the quick installer
sudo ./quick_install.sh ar.example.com admin@example.com

# Or without domain
sudo ./quick_install.sh
```

### Example 3: Development Setup
```bash
# Development mode without Docker
sudo ./install_ubuntu.sh --mode development --no-docker --no-ssl
```

## Advanced Installation Scenarios

### Scenario 1: Local Development from Source
```bash
# Install from local directory for development
sudo ./install_ubuntu.sh --local ./vertex-ar --mode development --no-docker --no-ssl
```

### Scenario 2: Production with PostgreSQL
```bash
# Full production setup with PostgreSQL
sudo ./install_ubuntu.sh \
    --domain ar.company.com \
    --email it@company.com \
    --postgres \
    --app-port 8080
```

### Scenario 3: High-Performance Setup
```bash
# Production with custom configuration
sudo ./install_ubuntu.sh \
    --domain ar.enterprise.com \
    --email devops@enterprise.com \
    --postgres \
    --app-port 9000
```

### Scenario 4: Minimal Installation
```bash
# Minimal setup without extra services
sudo ./install_ubuntu.sh \
    --no-docker \
    --no-minio \
    --no-ssl \
    --mode development
```

### Scenario 5: Docker-Only Installation
```bash
# Docker setup with MinIO but no SSL
sudo ./install_ubuntu.sh \
    --no-ssl \
    --postgres
```

## Environment-Specific Examples

### Development Environment
```bash
# Full development stack
sudo ./install_ubuntu.sh \
    --mode development \
    --no-docker \
    --no-ssl \
    --no-minio \
    --app-port 8000
```

**Features:**
- Debug mode enabled
- Verbose logging
- Node.js installed
- Local storage
- SQLite database

### Staging Environment
```bash
# Staging with production-like setup
sudo ./install_ubuntu.sh \
    --domain staging.ar.example.com \
    --email staging@example.com \
    --mode development \
    --postgres
```

**Features:**
- Domain with SSL
- PostgreSQL database
- Debug mode enabled
- Production-like services

### Production Environment
```bash
# Full production deployment
sudo ./install_ubuntu.sh \
    --domain ar.production.com \
    --email ops@production.com \
    --postgres \
    --app-port 8000
```

**Features:**
- Full SSL setup
- PostgreSQL database
- MinIO storage
- Production optimizations
- Rate limiting

## Special Configurations

### Custom Port Installation
```bash
# Install on custom port
sudo ./install_ubuntu.sh \
    --domain ar.example.com \
    --email admin@example.com \
    --app-port 8080
```

### No Database Initialization
```bash
# Skip database initialization (manual setup)
sudo ./install_ubuntu.sh \
    --domain ar.example.com \
    --email admin@example.com \
    --no-db-init
```

### No Backup Creation
```bash
# Skip backup creation (faster install)
sudo ./install_ubuntu.sh \
    --domain ar.example.com \
    --email admin@example.com \
    --no-backup
```

## Multi-Server Setup Examples

### Application Server
```bash
# Application server with PostgreSQL
sudo ./install_ubuntu.sh \
    --domain app.ar.example.com \
    --email app@example.com \
    --postgres \
    --no-minio
```

### Storage Server
```bash
# Dedicated MinIO storage server
sudo ./install_ubuntu.sh \
    --domain storage.ar.example.com \
    --email storage@example.com \
    --no-docker \
    --postgres
```

## Testing and Validation

### Test Installation
```bash
# Quick test installation
sudo ./install_ubuntu.sh \
    --mode development \
    --no-ssl \
    --no-docker \
    --no-minio \
    --app-port 8001
```

### Validation Commands
```bash
# Check service status
sudo systemctl status vertex-ar
sudo systemctl status nginx
sudo systemctl status postgresql  # if enabled
sudo systemctl status minio        # if enabled

# Check application health
curl http://localhost:8000/health

# Check logs
sudo journalctl -u vertex-ar -f
```

## Migration Examples

### Migrate from Local to Docker
```bash
# Stop existing services
sudo systemctl stop vertex-ar

# Install with Docker
sudo ./install_ubuntu.sh \
    --domain ar.example.com \
    --email admin@example.com

# Migrate data manually
sudo cp /opt/vertex-ar/app_data.db /opt/vertex-ar/data/
```

### Migrate from SQLite to PostgreSQL
```bash
# Backup existing data
sudo cp /opt/vertex-ar/app_data.db /tmp/backup.db

# Reinstall with PostgreSQL
sudo ./install_ubuntu.sh \
    --domain ar.example.com \
    --email admin@example.com \
    --postgres

# Migrate data (manual process required)
# Use pgloader or similar tools
```

## Troubleshooting Examples

### Reinstall with Clean State
```bash
# Remove existing installation
sudo systemctl stop vertex-ar
sudo rm -rf /opt/vertex-ar
sudo userdel -r vertexar
sudo rm -f /etc/nginx/sites-enabled/vertex-ar

# Reinstall
sudo ./install_ubuntu.sh --domain ar.example.com --email admin@example.com
```

### Fix Port Conflicts
```bash
# Install on different port
sudo ./install_ubuntu.sh \
    --domain ar.example.com \
    --email admin@example.com \
    --app-port 8080
```

### Debug Installation Issues
```bash
# Install with verbose logging
bash -x ./install_ubuntu.sh --domain ar.example.com --email admin@example.com

# Check installation log
tail -f /tmp/vertex_ar_install_*.log
```

## Automation Examples

### Automated Deployment Script
```bash
#!/bin/bash
# deploy.sh

DOMAIN="ar.example.com"
EMAIL="admin@example.com"

# Update system
sudo apt update && sudo apt upgrade -y

# Install Vertex AR
sudo ./install_ubuntu.sh --domain $DOMAIN --email $EMAIL

# Post-install configuration
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow ssh
sudo ufw --force enable

echo "Deployment completed successfully!"
```

### CI/CD Pipeline Example
```bash
#!/bin/bash
# ci-deploy.sh

set -e

DOMAIN="$1"
EMAIL="$2"

if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
    echo "Usage: $0 <domain> <email>"
    exit 1
fi

# Install dependencies
sudo apt-get update
sudo apt-get install -y git curl

# Clone repository
git clone https://github.com/fegerV/ar.git /tmp/vertex-ar
cd /tmp/vertex-ar

# Run installation
sudo ./install_ubuntu.sh --domain $DOMAIN --email $EMAIL

# Health check
sleep 30
curl -f http://localhost:8000/health || exit 1

echo "Deployment successful!"
```

## Configuration Examples

### Production Environment File
```bash
# /opt/vertex-ar/.env
DATABASE_URL=postgresql://vertexar:password@localhost/vertex_ar
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=your-secure-password
MINIO_BUCKET=vertex-art-bucket
SECRET_KEY=your-very-secure-secret-key
DEBUG=false
ENVIRONMENT=production
APP_PORT=8000
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure-admin-password
ADMIN_EMAIL=admin@example.com
STORAGE_TYPE=minio
STORAGE_PATH=./storage
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
LOG_LEVEL=INFO
```

### Development Environment File
```bash
# /opt/vertex-ar/.env
DATABASE_URL=sqlite:///./app_data.db
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=vertex-art-bucket
SECRET_KEY=dev-secret-key
DEBUG=true
ENVIRONMENT=development
APP_PORT=8000
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
ADMIN_EMAIL=dev@example.com
STORAGE_TYPE=local
STORAGE_PATH=./storage
RATE_LIMIT_ENABLED=false
LOG_LEVEL=DEBUG
```

## Best Practices

### Security Best Practices
```bash
# Always use SSL in production
sudo ./install_ubuntu.sh --domain ar.example.com --email admin@example.com

# Change default passwords after installation
sudo chpasswd <<EOF
vertexar:new-secure-password
EOF

# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### Performance Best Practices
```bash
# Use PostgreSQL for better performance
sudo ./install_ubuntu.sh --domain ar.example.com --email admin@example.com --postgres

# Use SSD storage for better I/O performance
# Configure proper logging levels
LOG_LEVEL=WARNING  # in production
```

### Backup Best Practices
```bash
# Create regular backups
echo "0 2 * * * tar -czf /opt/backups/vertex_ar_$(date +\%Y\%m\%d).tar.gz /opt/vertex-ar" | sudo crontab -

# Test backup restoration
sudo tar -xzf /opt/backups/vertex_ar_latest.tar.gz -C /tmp/
```

---

These examples cover most common installation scenarios. Choose the one that best fits your requirements and customize as needed.
