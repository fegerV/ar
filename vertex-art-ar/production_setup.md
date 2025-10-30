# Упрощенная настройка Production Environment для Vertex AR

This document describes the simplified steps to set up the production environment for the Vertex AR application based on Stogram approach.

## Отличия от оригинальной версии

- Использование SQLite вместо PostgreSQL
- Локальное файловое хранилище вместо MinIO
- Упрощенная аутентификация
- Меньше зависимостей и внешних сервисов

## Prerequisites

- Ubuntu 22.04 LTS server
- Domain name pointing to the server
- Firewall configured to allow HTTP (80), HTTPS (443), and SSH (22) ports

## 1. Initial Server Setup

### Update System Packages

```bash
sudo apt update && sudo apt upgrade -y
```

### Create Application User

```bash
sudo adduser --system --group --shell /bin/bash vertexart
```

### Configure Firewall

```bash
# Allow SSH, HTTP, and HTTPS
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

## 2. Application Deployment

### Install Python and Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git nginx supervisor curl wget
```

### Clone Repository

```bash
# Switch to application user
sudo su - vertexart

# Clone repository
git clone https://github.com/your-username/vertex-art-ar.git /opt/vertex-art-ar
cd /opt/vertex-art-ar
```

### Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install simplified dependencies
pip install --upgrade pip
pip install -r requirements-simple.txt
```

### Configure Environment Variables

Create a `.env` file in the project directory:

```bash
cat > .env <<EOF
DATABASE_URL=sqlite:///./app_data.db
STORAGE_ROOT=/opt/vertex-art-ar/storage
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secret
SECRET_KEY=your-very-secure-secret-key-here
EOF
```

## 3. Storage Setup (Local File System)

### Create Storage Directories

```bash
# Create storage directories
sudo mkdir -p /opt/vertex-art-ar/storage/ar_content
sudo mkdir -p /opt/vertex-art-ar/storage/nft-markers
sudo mkdir -p /opt/vertex-art-ar/storage/previews

# Set proper ownership
sudo chown -R vertexart:vertexart /opt/vertex-art-ar/storage
```

## 4. Web Server Configuration (Nginx)

### Configure Nginx Site

Create a new site configuration:

```bash
sudo tee /etc/nginx/sites-available/vertex-art-ar > /dev/null <<EOF
server {
    listen 80;
    server_name your-domain.com; # Change to your domain
    
    # Proxy to FastAPI application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Serve static files
    location /static/ {
        alias /opt/vertex-art-ar/static/;
        expires 1y;
        add_header Cache-Control "public";
    }
    
    # Serve uploaded content
    location /storage/ {
        alias /opt/vertex-art-ar/storage/;
        expires 1d;
        add_header Cache-Control "public";
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/vertex-art-ar /etc/nginx/sites-enabled/

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

## 5. Process Management (Supervisor)

### Configure Supervisor

Create a supervisor configuration for the application:

```bash
sudo tee /etc/supervisor/conf.d/vertex-art-ar.conf > /dev/null <<EOF
[program:vertex-art-ar]
command=/opt/vertex-art-ar/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
directory=/opt/vertex-art-ar
user=vertexart
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/vertex-art-ar.log
environment=DATABASE_URL="sqlite:////opt/vertex-art-ar/app_data.db",STORAGE_ROOT="/opt/vertex-art-ar/storage"
EOF

# Reload supervisor configuration
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start vertex-art-ar
```

## 6. SSL Certificate (Let's Encrypt)

### Install Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### Obtain SSL Certificate

```bash
# Replace 'your-domain.com' with your actual domain
sudo certbot --nginx -d your-domain.com
```

## 7. Final Steps

### Set Proper Permissions

```bash
# Set ownership of application files
sudo chown -R vertexart:vertexart /opt/vertex-art-ar

# Create database file with proper permissions
sudo touch /opt/vertex-art-ar/app_data.db
sudo chown vertexart:vertexart /opt/vertex-art-ar/app_data.db
```

### Test Application

```bash
# Check if services are running
sudo systemctl status nginx
sudo supervisorctl status

# Test application accessibility
curl -I http://your-domain.com
```

## 8. Monitoring and Maintenance

### Log Files

- Application logs: `/var/log/vertex-art-ar.log`
- Nginx logs: `/var/log/nginx/`

### Regular Maintenance Tasks

1. Update system packages regularly:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. Monitor disk space usage:
   ```bash
   df -h
   ```

3. Check application health:
   ```bash
   sudo supervisorctl status vertex-art-ar
   ```

4. Backup database regularly:
   ```bash
   cp /opt/vertex-art-ar/app_data.db backup_$(date +%Y%m%d).db
   ```

5. Backup storage directory:
   ```bash
   tar -czf storage_backup_$(date +%Y%m%d).tar.gz /opt/vertex-art-ar/storage
   ```

## 9. Docker Production Setup (Alternative)

Instead of manual installation, you can use Docker for simplified deployment:

### Install Docker

```bash
# Install Docker
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add current user to docker group
sudo usermod -aG docker $USER
```

### Deploy with Docker Compose

```bash
# Clone repository
git clone https://github.com/your-username/vertex-art-ar.git /opt/vertex-art-ar
cd /opt/vertex-art-ar

# Build and start services
docker compose up -d

# Check status
docker compose ps
```

## Conclusion

With these steps, you should have a fully functional production environment for the simplified Vertex AR application. Remember to:

1. Regularly update the system and application
2. Monitor logs for any issues
3. Maintain backups of important data
4. Keep all credentials secure and rotate them periodically
5. The simplified version requires fewer resources and dependencies than the original version