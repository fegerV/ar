# Vertex AR Installation

This directory contains comprehensive installation scripts and documentation for deploying Vertex AR on Ubuntu servers.

## 🚀 Quick Start

### Option 1: Quick Installation (Recommended)
```bash
# With domain and SSL
sudo ./quick_install.sh yourdomain.com admin@yourdomain.com

# Without domain (development)
sudo ./quick_install.sh
```

### Option 2: Advanced Installation
```bash
# Production with all features
sudo ./install_ubuntu.sh --domain yourdomain.com --email admin@yourdomain.com

# Development mode
sudo ./install_ubuntu.sh --mode development --no-docker --no-ssl

# From local source
sudo ./install_ubuntu.sh --local ./vertex-ar --mode development
```

## 📁 Files Overview

| File | Description |
|------|-------------|
| `install_ubuntu.sh` | **Main installation script** - Full-featured installer with all options |
| `quick_install.sh` | **Quick installer** - Simplified installation for common scenarios |
| `UBUNTU_INSTALL_GUIDE.md` | **Comprehensive guide** - Detailed installation instructions |
| `INSTALLATION_EXAMPLES.md` | **Examples** - Real-world installation scenarios |
| `INSTALL_README.md` | **This file** - Quick overview and getting started |

## 🎯 Installation Options

### Production Installation
- ✅ SSL certificates with Let's Encrypt
- ✅ PostgreSQL database (optional)
- ✅ MinIO object storage
- ✅ Nginx reverse proxy
- ✅ Security headers and optimizations
- ✅ Rate limiting
- ✅ Health monitoring

### Development Installation
- ✅ Debug mode enabled
- ✅ Local storage (SQLite)
- ✅ Verbose logging
- ✅ Node.js for frontend development
- ✅ Hot reload support

### Custom Installation
- ✅ Choose database (SQLite/PostgreSQL)
- ✅ Choose storage (Local/MinIO)
- ✅ Docker or native installation
- ✅ Custom ports and configuration
- ✅ Local source installation

## 📋 System Requirements

- **OS**: Ubuntu 20.04 LTS or higher
- **RAM**: 2GB minimum (4GB+ recommended)
- **Storage**: 5GB free space (10GB+ recommended)
- **Network**: Internet connection

## 🛠️ Installation Methods

### 1. Quick Install (Recommended for Beginners)
```bash
# Basic installation
sudo ./quick_install.sh

# With domain and SSL
sudo ./quick_install.sh example.com admin@example.com
```

### 2. Advanced Install (Full Control)
```bash
# See all options
./install_ubuntu.sh --help

# Production example
sudo ./install_ubuntu.sh \
    --domain example.com \
    --email admin@example.com \
    --postgres \
    --app-port 8080
```

### 3. Development Install (From Source)
```bash
# Install from local directory
sudo ./install_ubuntu.sh \
    --local ./vertex-ar \
    --mode development \
    --no-docker \
    --no-ssl
```

## 🔧 Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `--domain` | Domain name for SSL | None |
| `--email` | Email for certificates | None |
| `--mode` | production/development | production |
| `--no-docker` | Install without Docker | false |
| `--no-ssl` | Skip SSL setup | false |
| `--postgres` | Use PostgreSQL | false |
| `--no-minio` | Skip MinIO | false |
| `--local` | Install from local directory | Git repo |
| `--app-port` | Custom application port | 8000 |

## 🌐 Access After Installation

Once installation completes, you can access:

- **Main Application**: `http://your-server-ip:8000` or `https://yourdomain.com`
- **Admin Panel**: `http://your-server-ip:8000/admin`
- **MinIO Console**: `http://your-server-ip:9001` (if enabled)

## 🔐 Default Credentials

- **Admin Username**: `admin`
- **Admin Password**: Generated during installation (check logs)
- **MinIO Username**: `minioadmin`
- **MinIO Password**: Generated during installation

## 📚 Documentation

1. **[Ubuntu Install Guide](UBUNTU_INSTALL_GUIDE.md)** - Comprehensive installation guide
2. **[Installation Examples](INSTALLATION_EXAMPLES.md)** - Real-world scenarios
3. **[Main Project README](README.md)** - Project overview and features

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

## 🔍 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   sudo netstat -tuln | grep :8000
   sudo kill -9 <PID>
   ```

2. **Service Won't Start**
   ```bash
   sudo systemctl status vertex-ar
   sudo journalctl -u vertex-ar -n 50
   ```

3. **SSL Certificate Issues**
   ```bash
   sudo certbot certificates
   sudo nginx -t
   ```

### Getting Help

1. Check installation logs: `/tmp/vertex_ar_install_*.log`
2. Review the [Ubuntu Install Guide](UBUNTU_INSTALL_GUIDE.md)
3. Check [Installation Examples](INSTALLATION_EXAMPLES.md)
4. Review service logs and status

## 🔄 Updates and Maintenance

### System Updates
```bash
sudo apt update && sudo apt upgrade -y
```

### Application Updates
```bash
# Native
cd /opt/vertex-ar
sudo -u vertexar git pull
sudo systemctl restart vertex-ar

# Docker
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
```

## 🛡️ Security

### Firewall Setup
```bash
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### Security Best Practices

1. Change default passwords after installation
2. Use SSL in production (enabled by default with domain)
3. Regularly update system and application
4. Monitor logs for suspicious activity
5. Implement backup strategy

## 📞 Support

For support and issues:

1. **Check logs** first - installation and application logs
2. **Review documentation** - comprehensive guides available
3. **Search existing issues** - common problems already solved
4. **Provide details** when reporting issues:
   - Installation log
   - System information
   - Configuration details
   - Steps to reproduce

## 🎉 Next Steps

After successful installation:

1. **Access your application** and create admin account
2. **Configure domain settings** (DNS, SSL verification)
3. **Review security settings** and change default passwords
4. **Test all features** to ensure everything works
5. **Set up monitoring** and backup procedures
6. **Explore admin features** and customize settings

---

**Happy installing! 🚀**

For detailed information, please refer to the comprehensive guides in this directory.
