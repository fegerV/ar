# Vertex AR Installation Cheatsheet

## Quick Reference

### 🚀 One-Command Installation

```bash
# Production with SSL
sudo ./quick_install.sh yourdomain.com admin@yourdomain.com

# Development without SSL
sudo ./quick_install.sh

# Advanced options
sudo ./install_ubuntu.sh --help
```

### 📋 Common Installation Scenarios

| Scenario | Command |
|----------|---------|
| **Basic Production** | `sudo ./install_ubuntu.sh --domain example.com --email admin@example.com` |
| **Development** | `sudo ./install_ubuntu.sh --mode development --no-docker --no-ssl` |
| **Local Source** | `sudo ./install_ubuntu.sh --local ./vertex-ar --mode development` |
| **With PostgreSQL** | `sudo ./install_ubuntu.sh --domain example.com --email admin@example.com --postgres` |
| **Custom Port** | `sudo ./install_ubuntu.sh --domain example.com --email admin@example.com --app-port 8080` |

## 🔧 Command Options

### Essential Options
```bash
--domain DOMAIN        # Domain for SSL certificates
--email EMAIL          # Email for Let's Encrypt
--mode MODE           # production|development
--no-docker          # Install without Docker
--no-ssl             # Skip SSL setup
--postgres           # Use PostgreSQL instead of SQLite
--no-minio           # Skip MinIO installation
```

### Advanced Options
```bash
--local SOURCE_DIR    # Install from local directory
--app-port PORT       # Custom application port (default: 8000)
--no-db-init         # Skip database initialization
--no-backup          # Skip backup creation
--help               # Show all options
```

## 🌐 Access URLs

| Service | URL | Default Port |
|---------|-----|--------------|
| **Main App** | `http://IP:8000` or `https://domain.com` | 8000 |
| **Admin Panel** | `http://IP:8000/admin` | 8000 |
| **MinIO Console** | `http://IP:9001` | 9001 |
| **Health Check** | `http://IP:8000/health` | 8000 |

## 🔐 Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| **Admin** | `admin` | *Generated during install* |
| **MinIO** | `minioadmin` | *Generated during install* |

## 🛠️ Service Management

### Docker Installation
```bash
cd /opt/vertex-ar
docker-compose up -d      # Start
docker-compose down        # Stop
docker-compose logs -f     # Logs
docker-compose restart     # Restart
```

### Native Installation
```bash
sudo systemctl start vertex-ar     # Start
sudo systemctl stop vertex-ar      # Stop
sudo systemctl restart vertex-ar   # Restart
sudo systemctl status vertex-ar    # Status
sudo journalctl -u vertex-ar -f    # Logs
```

## 📁 Important Files

| Path | Description |
|------|-------------|
| `/opt/vertex-ar/.env` | Environment configuration |
| `/etc/nginx/sites-available/vertex-ar` | Nginx configuration |
| `/tmp/vertex_ar_install_*.log` | Installation log |
| `/opt/backups/vertex-ar/` | Backup directory |

## 🔍 Troubleshooting

### Quick Commands
```bash
# Check service status
sudo systemctl status vertex-ar nginx postgresql minio

# Check ports
sudo netstat -tuln | grep -E ':(80|443|8000|9000|9001)'

# Check logs
sudo journalctl -u vertex-ar -f
tail -f /var/log/nginx/error.log

# Test application
curl -f http://localhost:8000/health
```

### Common Issues

**Port Already in Use**
```bash
sudo lsof -i :8000
sudo kill -9 <PID>
```

**Service Won't Start**
```bash
sudo systemctl status vertex-ar
sudo journalctl -u vertex-ar -n 50
```

**SSL Issues**
```bash
sudo certbot certificates
sudo nginx -t
```

## 🔄 Maintenance Commands

### Updates
```bash
# System updates
sudo apt update && sudo apt upgrade -y

# Application updates (native)
cd /opt/vertex-ar
sudo -u vertexar git pull
sudo systemctl restart vertex-ar

# Application updates (Docker)
cd /opt/vertex-ar
git pull
docker-compose build
docker-compose up -d
```

### Backup
```bash
# Complete backup
sudo tar -czf vertex_ar_backup_$(date +%Y%m%d).tar.gz /opt/vertex-ar

# Database backup (SQLite)
sudo cp /opt/vertex-ar/app_data.db /tmp/backup_$(date +%Y%m%d).db

# Database backup (PostgreSQL)
sudo -u postgres pg_dump vertex_ar > backup.sql
```

## 🔧 Configuration Examples

### Production .env
```bash
DATABASE_URL=postgresql://vertexar:password@localhost/vertex_ar
MINIO_ENDPOINT=localhost:9000
SECRET_KEY=your-secure-secret-key
DEBUG=false
ENVIRONMENT=production
STORAGE_TYPE=minio
RATE_LIMIT_ENABLED=true
LOG_LEVEL=INFO
```

### Development .env
```bash
DATABASE_URL=sqlite:///./app_data.db
SECRET_KEY=dev-secret-key
DEBUG=true
ENVIRONMENT=development
STORAGE_TYPE=local
RATE_LIMIT_ENABLED=false
LOG_LEVEL=DEBUG
```

## 🛡️ Security Commands

### Firewall Setup
```bash
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
sudo ufw status
```

### Password Changes
```bash
# Change PostgreSQL password
sudo -u postgres psql -c "ALTER USER vertexar PASSWORD 'new_password';"

# Change MinIO password (edit /etc/default/minio)
sudo nano /etc/default/minio
sudo systemctl restart minio
```

## 📊 Monitoring

### System Resources
```bash
htop                    # CPU/Memory usage
df -h                   # Disk space
free -h                 # Memory usage
sudo journalctl -f       # System logs
```

### Application Health
```bash
curl http://localhost:8000/health
sudo systemctl status vertex-ar
docker ps               # If using Docker
```

## 🚀 Quick Deployment Script

```bash
#!/bin/bash
# deploy.sh
DOMAIN="yourdomain.com"
EMAIL="admin@yourdomain.com"

# Install
sudo ./install_ubuntu.sh --domain $DOMAIN --email $EMAIL

# Configure firewall
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw --force enable

echo "Deployment completed!"
echo "Access: https://$DOMAIN"
echo "Admin: https://$DOMAIN/admin"
```

## 📞 Getting Help

1. **Installation Log**: `cat /tmp/vertex_ar_install_*.log`
2. **Application Logs**: `sudo journalctl -u vertex-ar -f`
3. **Documentation**: `UBUNTU_INSTALL_GUIDE.md`
4. **Examples**: `INSTALLATION_EXAMPLES.md`

---

**Save this cheatsheet for quick reference during installation and maintenance!** 🚀
