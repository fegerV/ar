# Vertex AR Ubuntu Installation Guide

## Overview

This guide provides comprehensive instructions for installing Vertex AR on Ubuntu servers using the enhanced installation script.

## System Requirements

### Minimum Requirements
- **OS**: Ubuntu 20.04 LTS or higher
- **RAM**: 2GB (4GB+ recommended)
- **Storage**: 5GB free space (10GB+ recommended)
- **Network**: Internet connection for package downloads

### Recommended Requirements
- **OS**: Ubuntu 22.04 LTS or 24.04 LTS
- **RAM**: 4GB or more
- **Storage**: 20GB+ SSD storage
- **CPU**: 2+ cores

## Installation Options

### Option 1: Quick Production Installation
```bash
# Basic production installation with domain
sudo ./install_ubuntu.sh --domain yourdomain.com --email admin@yourdomain.com
```

### Option 2: Development Installation
```bash
# Development mode without SSL
sudo ./install_ubuntu.sh --mode development --no-ssl --no-docker
```

### Option 3: Local Development from Source
```bash
# Install from local directory
sudo ./install_ubuntu.sh --local /path/to/vertex-ar --mode development --no-docker
```

### Option 4: Full Production with PostgreSQL
```bash
# Full production setup with PostgreSQL and custom port
sudo ./install_ubuntu.sh --domain yourdomain.com --email admin@yourdomain.com --postgres --app-port 8080
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--domain DOMAIN` | Set domain name for SSL | None |
| `--email EMAIL` | Email for Let's Encrypt certificates | None |
| `--mode MODE` | Installation mode (production/development) | production |
| `--no-docker` | Install without Docker | false |
| `--no-ssl` | Skip SSL certificate setup | false |
| `--postgres` | Use PostgreSQL instead of SQLite | false |
| `--no-minio` | Skip MinIO installation | false |
| `--local SOURCE_DIR` | Install from local directory | Git repository |
| `--app-port PORT` | Custom application port | 8000 |
| `--no-db-init` | Skip database initialization | false |
| `--no-backup` | Skip backup creation | false |
| `--help` | Show help information | - |

## Installation Modes

### Production Mode (Default)
- Optimized for production deployment
- SSL certificates enabled (if domain provided)
- Rate limiting enabled
- Debug mode disabled
- Security headers configured
- Performance optimizations

### Development Mode
- Debug mode enabled
- Verbose logging
- Node.js installed for frontend development
- SSL disabled by default
- Hot reload capabilities

## Database Options

### SQLite (Default)
- File-based database
- No additional services required
- Suitable for small to medium deployments
- Easy backup and migration

### PostgreSQL
- Production-grade database
- Better performance for large datasets
- Advanced features (replication, clustering)
- Requires additional configuration

## Storage Options

### Local Storage
- Files stored on local filesystem
- No additional services required
- Simple backup strategy
- Limited scalability

### MinIO (Default)
- S3-compatible object storage
- Scalable and reliable
- Built-in web console
- Supports distributed deployment

## SSL Configuration

### Automatic SSL Setup
```bash
# Requires domain and email
sudo ./install_ubuntu.sh --domain example.com --email admin@example.com
```

### Manual SSL Setup
```bash
# Skip SSL during installation
sudo ./install_ubuntu.sh --no-ssl

# Configure SSL later
sudo certbot --nginx -d example.com
```

## Post-Installation Configuration

### Accessing the Application

1. **Main Application**: `http://your-server-ip:8000` or `https://yourdomain.com`
2. **Admin Panel**: `http://your-server-ip:8000/admin`
3. **MinIO Console**: `http://your-server-ip:9001` (if MinIO enabled)

### Default Credentials

- **Admin Username**: `admin`
- **Admin Password**: Generated during installation (check log)
- **MinIO Username**: `minioadmin`
- **MinIO Password**: Generated during installation

### Service Management

#### Docker Installation
```bash
# Start services
cd /opt/vertex-ar
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Restart services
docker-compose restart
```

#### Native Installation
```bash
# Start service
sudo systemctl start vertex-ar

# Stop service
sudo systemctl stop vertex-ar

# Restart service
sudo systemctl restart vertex-ar

# View status
sudo systemctl status vertex-ar

# View logs
sudo journalctl -u vertex-ar -f
```

## Configuration Files

### Environment Configuration
```bash
# Main configuration file
/opt/vertex-ar/.env

# Database settings
DATABASE_URL=sqlite:///./app_data.db

# MinIO settings
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=your-secret-key

# Application settings
SECRET_KEY=your-secret-key
DEBUG=false
ENVIRONMENT=production
```

### Nginx Configuration
```bash
# Nginx site configuration
/etc/nginx/sites-available/vertex-ar

# Test Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

## Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Check what's using the port
sudo netstat -tuln | grep :8000

# Kill the process
sudo kill -9 <PID>
```

#### Service Won't Start
```bash
# Check service status
sudo systemctl status vertex-ar

# View detailed logs
sudo journalctl -u vertex-ar -n 50

# Check configuration
sudo nginx -t
```

#### Database Connection Issues
```bash
# Check database file permissions
ls -la /opt/vertex-ar/app_data.db

# Test database connection
cd /opt/vertex-ar
source venv/bin/activate
python -c "from app.database import engine; print(engine.url)"
```

#### SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Renew certificate manually
sudo certbot renew

# Check Nginx SSL configuration
sudo nginx -t
```

### Log Files

#### Installation Log
```bash
# Installation log location
/tmp/vertex_ar_install_*.log

# View recent logs
tail -f /tmp/vertex_ar_install_*.log
```

#### Application Logs
```bash
# Native installation
sudo journalctl -u vertex-ar -f

# Docker installation
cd /opt/vertex-ar
docker-compose logs -f app
```

#### Nginx Logs
```bash
# Access logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log
```

## Maintenance

### Regular Updates

#### System Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Docker images (if using Docker)
cd /opt/vertex-ar
docker-compose pull
docker-compose up -d
```

#### Application Updates
```bash
# Native installation
cd /opt/vertex-ar
sudo -u vertexar git pull
source venv/bin/activate
pip install -r vertex-ar/requirements.txt
sudo systemctl restart vertex-ar

# Docker installation
cd /opt/vertex-ar
git pull
docker-compose build
docker-compose up -d
```

### Backup Strategy

#### Database Backup
```bash
# SQLite backup
sudo cp /opt/vertex-ar/app_data.db /opt/backups/vertex_ar_db_$(date +%Y%m%d).db

# PostgreSQL backup
sudo -u postgres pg_dump vertex_ar > /opt/backups/vertex_ar_db_$(date +%Y%m%d).sql
```

#### Application Backup
```bash
# Complete application backup
sudo tar -czf /opt/backups/vertex_ar_complete_$(date +%Y%m%d).tar.gz /opt/vertex-ar

# Storage backup (if using local storage)
sudo tar -czf /opt/backups/vertex_ar_storage_$(date +%Y%m%d).tar.gz /opt/vertex-ar/storage
```

### Monitoring

#### Health Checks
```bash
# Application health
curl http://localhost:8000/health

# Nginx status
sudo systemctl status nginx

# Disk space
df -h /opt/vertex-ar

# Memory usage
free -h
```

#### Performance Monitoring
```bash
# System resources
htop

# Network connections
sudo netstat -tuln

# Docker containers (if applicable)
docker stats
```

## Security Considerations

### Firewall Configuration
```bash
# Enable UFW firewall
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow application port (if not behind Nginx)
sudo ufw allow 8000

# Allow MinIO console (if enabled)
sudo ufw allow 9001
```

### Security Hardening

1. **Change Default Passwords**
   - Admin password
   - MinIO password
   - Database passwords

2. **SSL/TLS Configuration**
   - Use strong SSL ciphers
   - Enable HSTS headers
   - Regular certificate renewal

3. **Access Control**
   - Limit SSH access
   - Use key-based authentication
   - Implement fail2ban

4. **Regular Updates**
   - System patches
   - Application updates
   - Security advisories

## Support

### Getting Help

1. **Check Logs**: Review installation and application logs
2. **Documentation**: Refer to project documentation
3. **Community**: Check GitHub issues and discussions
4. **Health Checks**: Run built-in health checks

### Reporting Issues

When reporting issues, include:
- Installation log (`/tmp/vertex_ar_install_*.log`)
- System information (`uname -a`)
- Application logs
- Configuration details
- Steps to reproduce

---

**Note**: This installation script is designed for Ubuntu servers. For other operating systems, manual installation may be required.