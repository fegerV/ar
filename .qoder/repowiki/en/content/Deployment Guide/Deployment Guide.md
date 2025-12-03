# Deployment Guide

<cite>
**Referenced Files in This Document**   
- [docker-compose.yml](file://docker-compose.yml)
- [nginx.conf](file://nginx.conf)
- [vertex-ar/.env.example](file://vertex-ar/.env.example)
- [vertex-ar/.env.production.example](file://vertex-ar/.env.production.example)
- [vertex-ar/systemd/vertex-ar-backup.service](file://vertex-ar/systemd/vertex-ar-backup.service)
- [vertex-ar/systemd/vertex-ar-backup.timer](file://vertex-ar/systemd/vertex-ar-backup.timer)
- [vertex-ar/start.sh](file://vertex-ar/start.sh)
- [scripts/deploy-vertex-ar-cloud-ru.sh](file://scripts/deploy-vertex-ar-cloud-ru.sh)
- [docs/deployment/cloud-ru.md](file://docs/deployment/cloud-ru.md)
- [docs/deployment/production-setup.md](file://docs/deployment/production-setup.md)
- [docs/deployment/nginx-ssl-setup.md](file://docs/deployment/nginx-ssl-setup.md)
- [docs/deployment/uvicorn-tuning.md](file://docs/deployment/uvicorn-tuning.md)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Environment Configuration](#environment-configuration)
4. [Docker-Based Deployment](#docker-based-deployment)
5. [Systemd Backup Management](#systemd-backup-management)
6. [Nginx Reverse Proxy and SSL Setup](#nginx-reverse-proxy-and-ssl-setup)
7. [Cloud-Specific Deployment (cloud.ru)](#cloud-specific-deployment-cloudru)
8. [Performance Tuning (Uvicorn)](#performance-tuning-uvicorn)
9. [Startup Procedures](#startup-procedures)
10. [Verification and Troubleshooting](#verification-and-troubleshooting)

## Introduction
This deployment guide provides comprehensive instructions for deploying the AR backend application in a production environment. The guide covers Docker-based deployment using docker-compose, systemd service management for backup processes, Nginx reverse proxy configuration with SSL termination, environment variable configuration from .env files, and cloud-specific deployment guidance for cloud.ru. The documentation includes step-by-step procedures for production deployment, performance tuning recommendations, and solutions for common deployment issues.

## Prerequisites
Before beginning the deployment process, ensure the following prerequisites are met:

- **Server Requirements**: Ubuntu 18.04 or later with at least 512MB RAM and 2GB disk space
- **Domain Configuration**: Domain name configured with DNS records pointing to the server IP
- **SSL Certificate**: Access to SSL certificate files or ability to generate them via Let's Encrypt
- **Dependencies**: Python 3.8+, pip, git, Docker, and Docker Compose installed on the target system
- **User Permissions**: Root or sudo access to the deployment server
- **Network Configuration**: Firewall configured to allow HTTP (port 80) and HTTPS (port 443) traffic

For cloud.ru deployments specifically, ensure Cpanel access is available for SSL certificate management and domain configuration.

**Section sources**
- [docs/deployment/cloud-ru.md](file://docs/deployment/cloud-ru.md#-requirements)
- [docs/deployment/production-setup.md](file://docs/deployment/production-setup.md#-1-under-server-preparation)

## Environment Configuration
The AR backend application uses environment variables for configuration, with different .env files for various deployment scenarios.

### Environment Files
Two primary environment configuration files are provided:

- **.env.example**: Template for development and testing environments
- **.env.production.example**: Template for production deployments with remote storage

### Key Configuration Parameters
The following environment variables must be configured for production deployment:

**Application Settings**
```
DEBUG=False
SECRET_KEY=secure-random-key
APP_HOST=0.0.0.0
APP_PORT=8000
BASE_URL=https://yourdomain.com
```

**Storage Configuration**
For local storage:
```
STORAGE_TYPE=local
STORAGE_PATH=./storage
```

For remote MinIO/S3 storage:
```
STORAGE_TYPE=minio
MINIO_ENDPOINT=your-minio-endpoint:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_BUCKET=vertex-ar-production
MINIO_SECURE=True
```

**Security Parameters**
```
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
TOKEN_EXPIRATION_HOURS=24
BCRYPT_ROUNDS=12
RATE_LIMIT_ENABLED=True
RATE_LIMIT_AUTH=100
RATE_LIMIT_ANON=20
```

**Database Connection**
```
DATABASE_URL=sqlite:///./app_data.db
# For PostgreSQL: postgresql://user:password@localhost:5432/vertex_ar
```

**Monitoring and Analytics**
```
ANALYTICS_ENABLED=True
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

### Configuration Process
1. Copy the appropriate .env template to create a .env file
2. Update all placeholder values with production-specific configurations
3. Set appropriate file permissions (chmod 600 .env)
4. Ensure sensitive credentials are not committed to version control

**Section sources**
- [vertex-ar/.env.example](file://vertex-ar/.env.example)
- [vertex-ar/.env.production.example](file://vertex-ar/.env.production.example)
- [docs/deployment/production-setup.md](file://docs/deployment/production-setup.md#-4-environment-configuration)

## Docker-Based Deployment
The AR backend application can be deployed using Docker Compose for containerized deployment.

### Docker Compose Configuration
The primary docker-compose.yml file defines two services:

```yaml
version: '3.8'
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.app
    container_name: vertex_ar_app_simplified
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./app_data.db
      - STORAGE_ROOT=/app/storage
      - ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
      - SECRET_KEY=${SECRET_KEY}
      - BASE_URL=${BASE_URL:-http://localhost:8000}
      - CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:8000}
      - RATE_LIMIT_ENABLED=${RATE_LIMIT_ENABLED:-true}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - SENTRY_DSN=${SENTRY_DSN:-}
      - ENVIRONMENT=${ENVIRONMENT:-production}
    volumes:
      - ./storage:/app/storage
      - ./app_data:/app/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: vertex_ar_nginx_simplified
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - nginx_logs:/var/log/nginx
    depends_on:
      - app
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "sh", "-c", "curl -f http://localhost/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  nginx_logs:
```

### Remote MinIO Configuration
For deployments using remote MinIO storage, use the docker-compose.minio-remote.yml file:

```yaml
version: '3.8'
services:
  vertex-ar:
    build:
      context: .
      dockerfile: Dockerfile.app
    container_name: vertex-ar
    ports:
      - "8000:8000"
    environment:
      - BASE_URL=http://localhost:8000
      - SECRET_KEY=${SECRET_KEY:-change-this-in-production}
      - STORAGE_TYPE=minio
      - MINIO_ENDPOINT=${MINIO_ENDPOINT:-minio.example.com:9000}
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-your-access-key}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-your-secret-key}
      - MINIO_BUCKET=${MINIO_BUCKET:-vertex-ar}
      - MINIO_SECURE=${MINIO_SECURE:-true}
      - MINIO_PUBLIC_URL=${MINIO_PUBLIC_URL:-}
      - LOG_LEVEL=INFO
    volumes:
      - ./vertex-ar/app_data.db:/app/app_data.db
      - ./vertex-ar/templates:/app/templates
      - ./vertex-ar/static:/app/static
    restart: unless-stopped
    networks:
      - vertex-ar-network

networks:
  vertex-ar-network:
    driver: bridge
```

### Deployment Steps
1. Ensure Docker and Docker Compose are installed
2. Copy the appropriate .env file to the vertex-ar directory
3. Update environment variables in the .env file
4. Run `docker-compose up -d` to start the services
5. Verify container status with `docker-compose ps`

**Section sources**
- [docker-compose.yml](file://docker-compose.yml)
- [docker-compose.minio-remote.yml](file://docker-compose.minio-remote.yml)
- [vertex-ar/.env.example](file://vertex-ar/.env.example)

## Systemd Backup Management
The AR backend includes systemd service and timer files for automated backup management.

### Backup Service Configuration
The vertex-ar-backup.service file defines the backup process:

```ini
[Unit]
Description=Vertex AR Backup Service
After=network.target

[Service]
Type=oneshot
User=vertex-ar
Group=vertex-ar
WorkingDirectory=/opt/vertex-ar
Environment="PATH=/opt/vertex-ar/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/vertex-ar/.venv/bin/python /opt/vertex-ar/backup_cli.py create full
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vertex-ar-backup

[Install]
WantedBy=multi-user.target
```

### Backup Timer Configuration
The vertex-ar-backup.timer file schedules the backup execution:

```ini
[Unit]
Description=Vertex AR Daily Backup Timer
Requires=vertex-ar-backup.service

[Timer]
# Run daily at 2:00 AM
OnCalendar=daily
OnCalendar=02:00
# If the system was down at the scheduled time, run on next boot
Persistent=true

[Install]
WantedBy=timers.target
```

### Setup Procedure
1. Copy service and timer files to /etc/systemd/system/
2. Reload systemd configuration: `sudo systemctl daemon-reload`
3. Enable the timer: `sudo systemctl enable vertex-ar-backup.timer`
4. Start the timer: `sudo systemctl start vertex-ar-backup.timer`
5. Verify status: `sudo systemctl status vertex-ar-backup.timer`

The backup process runs daily at 2:00 AM and creates a full backup of the application data.

**Section sources**
- [vertex-ar/systemd/vertex-ar-backup.service](file://vertex-ar/systemd/vertex-ar-backup.service)
- [vertex-ar/systemd/vertex-ar-backup.timer](file://vertex-ar/systemd/vertex-ar-backup.timer)

## Nginx Reverse Proxy and SSL Setup
Nginx is used as a reverse proxy to handle HTTP/HTTPS traffic and forward requests to the AR backend application.

### Nginx Configuration
The nginx.conf file provides the base configuration:

```nginx
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log warn;

    resolver 127.0.0.11 8.8.8.8 valid=10s ipv6=off;

    server {
        listen 80;
        server_name localhost nft.vertex-art.ru;

        client_max_body_size 500M;
        client_body_timeout 300s;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;

        location / {
            set $upstream_app app;
            set $upstream_port 8000;
            proxy_pass http://$upstream_app:$upstream_port;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-Port $server_port;
            
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        location /storage/ {
            set $upstream_app app;
            set $upstream_port 8000;
            proxy_pass http://$upstream_app:$upstream_port/storage/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health {
            set $upstream_app app;
            set $upstream_port 8000;
            proxy_pass http://$upstream_app:$upstream_port/health;
            access_log off;
        }
    }
}
```

### SSL Configuration
The SSL setup is initially disabled to prevent container startup failures. To enable SSL:

1. Obtain SSL certificates (Let's Encrypt, self-signed, or purchased)
2. Place certificates in the ssl directory
3. Uncomment the HTTPS server block in nginx.conf
4. Update certificate paths in the configuration
5. Uncomment the SSL volume mount in docker-compose.yml
6. Restart the nginx container

For Let's Encrypt certificates:
```bash
sudo certbot certonly --standalone -d yourdomain.com --email your-email@example.com --agree-tos
```

### Configuration Steps
1. Copy nginx.conf to the server
2. Configure domain name in server_name directive
3. Adjust client_max_body_size based on upload requirements
4. Set appropriate proxy timeouts for long-running requests
5. Test configuration: `nginx -t`
6. Reload Nginx: `sudo systemctl reload nginx`

**Section sources**
- [nginx.conf](file://nginx.conf)
- [docs/deployment/nginx-ssl-setup.md](file://docs/deployment/nginx-ssl-setup.md)

## Cloud-Specific Deployment (cloud.ru)
The deployment process for cloud.ru hosting involves specific steps and configurations.

### Automated Deployment Script
The deploy-vertex-ar-cloud-ru.sh script automates the deployment process:

```bash
#!/bin/bash
# Vertex AR Deployment Script for cloud.ru
# Ubuntu 18.04 + Cpanel

set -e

# Configuration
APP_USER="rustadmin"
APP_GROUP="rustadmin"
APP_HOME="/home/rustadmin"
APP_DIR="$APP_HOME/vertex-ar-app"
VENV_DIR="$APP_DIR/venv"
APP_PORT=8000
DOMAIN="nft.vertex-art.ru"
LOG_DIR="/var/log/vertex-ar"

# Main execution
main() {
    check_root
    update_system
    install_dependencies
    install_nodejs
    clone_repository
    create_virtualenv
    install_python_dependencies
    create_env_file
    create_log_directory
    setup_supervisor
    setup_nginx
    setup_ssl_certificates
    create_backup_script
    setup_logrotate
    print_final_info
}

main
```

### Deployment Steps
1. Connect to the server via SSH
2. Download the deployment script:
   ```bash
   wget https://raw.githubusercontent.com/fegerV/AR/master/scripts/deploy-vertex-ar-cloud-ru.sh
   ```
3. Make the script executable:
   ```bash
   chmod +x deploy-vertex-ar-cloud-ru.sh
   ```
4. Run the script with sudo:
   ```bash
   sudo ./deploy-vertex-ar-cloud-ru.sh
   ```
5. Follow the SSL certificate setup instructions
6. Complete post-deployment configuration

### Post-Deployment Configuration
After running the deployment script:
1. Install SSL certificates through Cpanel
2. Copy PEM certificate to /etc/ssl/certs/nft.vertex-art.ru.crt
3. Copy private key to /etc/ssl/private/nft.vertex-art.ru.key
4. Restart Nginx: `sudo systemctl restart nginx`
5. Change the default admin password in the .env file

**Section sources**
- [scripts/deploy-vertex-ar-cloud-ru.sh](file://scripts/deploy-vertex-ar-cloud-ru.sh)
- [docs/deployment/cloud-ru.md](file://docs/deployment/cloud-ru.md)

## Performance Tuning (Uvicorn)
The AR backend application uses Uvicorn as the ASGI server, with extensive performance tuning options.

### Uvicorn Configuration
Configuration is managed through environment variables in the .env file:

```bash
# Worker Configuration
UVICORN_WORKERS=9  # (2 × CPU cores) + 1

# Connection Management
UVICORN_TIMEOUT_KEEP_ALIVE=5
UVICORN_LIMIT_CONCURRENCY=0  # 0 = unlimited
UVICORN_BACKLOG=2048
UVICORN_PROXY_HEADERS=true
UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=30

# Health Check Tuning
WEB_HEALTH_CHECK_TIMEOUT=5
WEB_HEALTH_CHECK_USE_HEAD=false
WEB_HEALTH_CHECK_COOLDOWN=30
```

### Worker Sizing
The default worker count follows the formula: `(2 × CPU_cores) + 1`

| CPU Cores | Default Workers | Memory Usage (est.) |
|-----------|----------------|---------------------|
| 1 | 3 | ~600 MB |
| 2 | 5 | ~1 GB |
| 4 | 9 | ~1.8 GB |
| 8 | 17 | ~3.4 GB |
| 16 | 33 | ~6.6 GB |

### Tuning Scenarios
**High-Traffic Production (1000+ req/sec)**
```bash
UVICORN_WORKERS=17
UVICORN_LIMIT_CONCURRENCY=1000
UVICORN_BACKLOG=8192
UVICORN_KEEPALIVE_TIMEOUT=15
WEB_HEALTH_CHECK_USE_HEAD=true
WEB_HEALTH_CHECK_COOLDOWN=60
```

**Memory-Constrained (< 2 GB RAM)**
```bash
UVICORN_WORKERS=3
UVICORN_LIMIT_CONCURRENCY=100
UVICORN_BACKLOG=512
UVICORN_KEEPALIVE_TIMEOUT=2
WEB_HEALTH_CHECK_COOLDOWN=60
```

**Long-Running Requests**
```bash
UVICORN_WORKERS=5
UVICORN_LIMIT_CONCURRENCY=50
UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=120
UVICORN_KEEPALIVE_TIMEOUT=30
WEB_HEALTH_CHECK_TIMEOUT=15
```

### Startup Script Integration
The start.sh script automatically applies Uvicorn settings:

```bash
#!/bin/bash
# Calculate default workers based on CPU count
DEFAULT_WORKERS=$(python3 -c "import psutil; print((2 * (psutil.cpu_count() or 1)) + 1)")
WORKERS=${UVICORN_WORKERS:-$DEFAULT_WORKERS}

# Build uvicorn command with optional flags
UVICORN_CMD="uvicorn main:app --host ${APP_HOST:-0.0.0.0} --port ${APP_PORT:-8000}"

# Add production settings
if [ "${ENVIRONMENT:-development}" != "development" ]; then
    UVICORN_CMD="$UVICORN_CMD --workers $WORKERS"
    UVICORN_CMD="$UVICORN_CMD --timeout-keep-alive ${UVICORN_TIMEOUT_KEEP_ALIVE:-5}"
    # Additional production flags...
fi
```

**Section sources**
- [vertex-ar/start.sh](file://vertex-ar/start.sh)
- [docs/deployment/uvicorn-tuning.md](file://docs/deployment/uvicorn-tuning.md)

## Startup Procedures
The deployment process follows a standardized startup procedure to ensure consistent operation.

### Manual Startup
1. Navigate to the application directory:
   ```bash
   cd /path/to/vertex-ar
   ```
2. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```
3. Start the application:
   ```bash
   ./start.sh
   ```

### Docker Compose Startup
1. Ensure the .env file is properly configured
2. Start services in detached mode:
   ```bash
   docker-compose up -d
   ```
3. Verify service status:
   ```bash
   docker-compose ps
   ```

### Systemd Service Startup
For systemd-managed deployments:
1. Start the application service:
   ```bash
   sudo systemctl start vertex-ar.service
   ```
2. Enable auto-start on boot:
   ```bash
   sudo systemctl enable vertex-ar.service
   ```
3. Check service status:
   ```bash
   sudo systemctl status vertex-ar.service
   ```

### Supervisor Startup
For Supervisor-managed deployments:
1. Start the application:
   ```bash
   sudo supervisorctl start vertex-ar
   ```
2. Check status:
   ```bash
   sudo supervisorctl status vertex-ar
   ```

**Section sources**
- [vertex-ar/start.sh](file://vertex-ar/start.sh)
- [docs/deployment/production-setup.md](file://docs/deployment/production-setup.md#-5-uvicorn-runtime-configuration)
- [scripts/deploy-vertex-ar-cloud-ru.sh](file://scripts/deploy-vertex-ar-cloud-ru.sh)

## Verification and Troubleshooting
After deployment, verify the application is functioning correctly and address common issues.

### Verification Steps
1. **Check Service Status**:
   ```bash
   docker-compose ps
   ```
2. **Test Health Endpoint**:
   ```bash
   curl http://localhost:8000/health
   ```
3. **Verify Nginx Configuration**:
   ```bash
   nginx -t
   ```
4. **Check Application Logs**:
   ```bash
   docker-compose logs app
   ```
5. **Test External Access**:
   Open https://yourdomain.com/admin in a web browser

### Common Issues and Solutions
**Nginx Fails to Start**
- Check SSL certificate files exist
- Verify file permissions (600 for key, 644 for certificate)
- Test Nginx configuration: `nginx -t`

**Application Not Responding**
- Check if the app container is running: `docker-compose ps`
- Verify port mappings in docker-compose.yml
- Check application logs for errors

**SSL Certificate Issues**
- Ensure certificates are in the correct location
- Verify domain name matches certificate
- Check certificate expiration date

**Database Connection Errors**
- Verify DATABASE_URL in .env file
- Check database file permissions
- Ensure database directory exists

**Backup Failures**
- Verify systemd service and timer are enabled
- Check backup script permissions
- Verify storage space availability

### Monitoring Commands
```bash
# Check container status
docker-compose ps

# View application logs
docker-compose logs app

# Monitor Nginx logs
docker-compose logs nginx

# Check system resources
htop

# Test health endpoint
curl -I http://localhost:8000/health
```

**Section sources**
- [docs/deployment/nginx-ssl-setup.md](file://docs/deployment/nginx-ssl-setup.md#-troubleshooting)
- [docs/deployment/uvicorn-tuning.md](file://docs/deployment/uvicorn-tuning.md#-troubleshooting)
- [scripts/deploy-vertex-ar-cloud-ru.sh](file://scripts/deploy-vertex-ar-cloud-ru.sh)