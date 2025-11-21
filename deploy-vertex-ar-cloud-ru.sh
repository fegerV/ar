#!/bin/bash

#############################################
# Vertex AR Deployment Script for cloud.ru
# Ubuntu 18.04 + Cpanel
# Version: 1.0
#############################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_USER="rustadmin"
APP_GROUP="rustadmin"
APP_HOME="/home/rustadmin"
APP_DIR="$APP_HOME/vertex-ar-app"
VENV_DIR="$APP_DIR/venv"
APP_PORT=8000
DOMAIN="nft.vertex-art.ru"
LOG_DIR="/var/log/vertex-ar"

# Functions
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

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "Этот скрипт должен быть запущен с правами root"
        exit 1
    fi
}

update_system() {
    print_header "Обновление системы"

    apt update
    apt upgrade -y
    print_success "Система обновлена"
}

install_dependencies() {
    print_header "Установка зависимостей"

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
        libgl1-mesa-glx

    print_success "Зависимости установлены"
}

install_nodejs() {
    print_header "Установка Node.js"

    if ! command -v node &> /dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
        apt install -y nodejs
        print_success "Node.js установлен"
    else
        print_success "Node.js уже установлен ($(node -v))"
    fi
}

clone_repository() {
    print_header "Клонирование репозитория"

    if [ ! -d "$APP_DIR" ]; then
        mkdir -p "$APP_DIR"
        print_success "Директория создана: $APP_DIR"
    fi

    if [ ! -d "$APP_DIR/.git" ]; then
        print_warning "Репозиторий не найден. Пожалуйста, скачайте вручную:"
        echo "git clone https://github.com/fegerV/AR.git $APP_DIR"
        echo "или"
        echo "wget -O $APP_DIR/vertex-ar.zip https://your-repo/archive/main.zip"
        echo "unzip $APP_DIR/vertex-ar.zip -d $APP_DIR"
        print_error "Пожалуйста, загрузите проект и снова запустите скрипт"
        exit 1
    else
        print_success "Репозиторий уже существует"
    fi

    # Change ownership
    chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"
}

create_virtualenv() {
    print_header "Создание виртуального окружения Python"

    if [ ! -d "$VENV_DIR" ]; then
        sudo -u "$APP_USER" python3 -m venv "$VENV_DIR"
        print_success "Виртуальное окружение создано"
    else
        print_success "Виртуальное окружение уже существует"
    fi
}

install_python_dependencies() {
    print_header "Установка Python зависимостей"

    cd "$APP_DIR/vertex-ar"

    # Activate venv and upgrade pip
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip setuptools wheel

    # Install requirements
    if [ -f "requirements-simple.txt" ]; then
        pip install -r requirements-simple.txt
        print_success "Зависимости установлены (requirements-simple.txt)"
    elif [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "Зависимости установлены (requirements.txt)"
    else
        print_error "Файл requirements не найден"
        exit 1
    fi

    deactivate
}

create_env_file() {
    print_header "Создание файла .env"

    ENV_FILE="$APP_DIR/vertex-ar/.env"

    if [ ! -f "$ENV_FILE" ]; then
        # Generate secret key
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

        cat > "$ENV_FILE" << EOF
# ============================================
# Application Settings
# ============================================
DEBUG=False
SECRET_KEY=$SECRET_KEY
APP_HOST=127.0.0.1
APP_PORT=$APP_PORT
BASE_URL=https://$DOMAIN
ENVIRONMENT=production

# ============================================
# Database Settings
# ============================================
DATABASE_URL=sqlite:///./app_data.db

# ============================================
# Storage Settings
# ============================================
STORAGE_TYPE=local
STORAGE_PATH=./storage

# ============================================
# Security Settings
# ============================================
CORS_ORIGINS=https://$DOMAIN,https://www.$DOMAIN
SESSION_TIMEOUT_MINUTES=30
AUTH_MAX_ATTEMPTS=5
AUTH_LOCKOUT_MINUTES=15
TOKEN_EXPIRATION_HOURS=24
BCRYPT_ROUNDS=12

# ============================================
# Admin Credentials
# ============================================
DEFAULT_ADMIN_USERNAME=superar
DEFAULT_ADMIN_PASSWORD=CHANGE_ME_IMMEDIATELY
DEFAULT_ADMIN_EMAIL=admin@vertex-ar.local
DEFAULT_ADMIN_FULL_NAME=Super Administrator

# ============================================
# Rate Limiting
# ============================================
RATE_LIMIT_ENABLED=true
GLOBAL_RATE_LIMIT=100/minute
AUTH_RATE_LIMIT=5/minute
UPLOAD_RATE_LIMIT=10/minute

# ============================================
# Logging
# ============================================
LOG_LEVEL=INFO
JSON_LOGS=true

# ============================================
# File Upload Limits
# ============================================
MAX_IMAGE_SIZE_MB=10
MAX_VIDEO_SIZE_MB=50
ALLOWED_IMAGE_FORMATS=jpg,jpeg,png
ALLOWED_VIDEO_FORMATS=mp4,webm

# ============================================
# NFT Marker Generation
# ============================================
NFT_FEATURE_DENSITY=high
NFT_PYRAMID_LEVELS=3
NFT_TARGET_DPI=150

# ============================================
# Backup Settings
# ============================================
BACKUP_DESTINATION=local
BACKUP_RETENTION_DAYS=7
EOF

        chown "$APP_USER:$APP_GROUP" "$ENV_FILE"
        chmod 600 "$ENV_FILE"

        print_success ".env файл создан"
        print_warning "ВАЖНО: Измените DEFAULT_ADMIN_PASSWORD в $ENV_FILE"
    else
        print_success ".env файл уже существует"
    fi
}

create_log_directory() {
    print_header "Создание директории логов"

    mkdir -p "$LOG_DIR"
    chown "$APP_USER:$APP_GROUP" "$LOG_DIR"
    chmod 755 "$LOG_DIR"

    print_success "Директория логов создана: $LOG_DIR"
}

setup_supervisor() {
    print_header "Настройка Supervisor"

    SUPERVISOR_CONF="/etc/supervisor/conf.d/vertex-ar.conf"

    cat > "$SUPERVISOR_CONF" << EOF
[program:vertex-ar]
directory=$APP_DIR/vertex-ar
command=$VENV_DIR/bin/uvicorn main:app --host 127.0.0.1 --port $APP_PORT
user=$APP_USER
autostart=true
autorestart=true
stderr_logfile=$LOG_DIR/error.log
stdout_logfile=$LOG_DIR/access.log
environment=PATH="$VENV_DIR/bin",HOME="$APP_HOME"
numprocs=1
priority=999

[group:vertex-ar]
programs=vertex-ar
EOF

    # Reload and start supervisor
    supervisorctl reread
    supervisorctl update
    supervisorctl start vertex-ar

    # Wait for application to start
    sleep 2

    # Check status
    if supervisorctl status vertex-ar | grep -q "RUNNING"; then
        print_success "Supervisor настроен и приложение запущено"
    else
        print_error "Приложение не запустилось. Проверьте логи: tail -f $LOG_DIR/error.log"
        exit 1
    fi
}

setup_nginx() {
    print_header "Настройка Nginx"

    NGINX_CONF="/etc/nginx/sites-available/vertex-ar"
    NGINX_ENABLED="/etc/nginx/sites-enabled/vertex-ar"

    cat > "$NGINX_CONF" << 'EOF'
upstream vertex_ar {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name nft.vertex-art.ru www.nft.vertex-art.ru;

    # Перенаправить на HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name nft.vertex-art.ru www.nft.vertex-art.ru;

    # SSL сертификаты (будут обновлены после установки SSL)
    ssl_certificate /etc/ssl/certs/nft.vertex-art.ru.crt;
    ssl_certificate_key /etc/ssl/private/nft.vertex-art.ru.key;

    # SSL параметры
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Логи
    access_log /var/log/nginx/vertex-ar-access.log;
    error_log /var/log/nginx/vertex-ar-error.log;

    # Размер загруженного файла
    client_max_body_size 50M;

    # Proxy параметры
    location / {
        proxy_pass http://vertex_ar;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;

        # WebSocket поддержка
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Таймауты
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Статические файлы
    location /static/ {
        alias /home/rustadmin/vertex-ar-app/vertex-ar/static/;
        expires 30d;
    }
}
EOF

    # Enable site
    if [ ! -L "$NGINX_ENABLED" ]; then
        ln -s "$NGINX_CONF" "$NGINX_ENABLED"
    fi

    # Test configuration
    if nginx -t 2>&1 | grep -q "successful"; then
        print_success "Nginx конфигурация валидна"
    else
        print_warning "Nginx конфигурация содержит ошибки. Проверьте SSL сертификаты."
    fi

    # Restart nginx
    systemctl restart nginx
    print_success "Nginx перезагружен"
}

setup_ssl_certificates() {
    print_header "Настройка SSL сертификатов"

    print_warning "SSL сертификаты еще не установлены."
    print_warning "Выполните следующие действия:"
    echo ""
    echo "1. В Cpanel перейдите в: SSL/TLS Manager"
    echo "2. Нажмите 'Manage SSL sites'"
    echo "3. Выберите домен: nft.vertex-art.ru"
    echo "4. Если сертификат еще не установлен, используйте AutoSSL или Let's Encrypt"
    echo "5. Скопируйте PEM сертификат и ключ на сервер:"
    echo ""
    echo "   sudo nano /etc/ssl/certs/nft.vertex-art.ru.crt"
    echo "   sudo nano /etc/ssl/private/nft.vertex-art.ru.key"
    echo ""
    echo "6. После установки сертификатов перезагрузите Nginx:"
    echo "   sudo systemctl restart nginx"
    echo ""

    # Try to find existing certificates
    if [ -f "/etc/ssl/certs/nft.vertex-art.ru.crt" ] && [ -f "/etc/ssl/private/nft.vertex-art.ru.key" ]; then
        print_success "SSL сертификаты найдены"
        systemctl restart nginx
    fi
}

create_backup_script() {
    print_header "Создание скрипта резервного копирования"

    BACKUP_SCRIPT="$APP_DIR/vertex-ar/backup.cron.sh"

    cat > "$BACKUP_SCRIPT" << 'EOF'
#!/bin/bash
# Vertex AR Backup Script
# Run daily from cron

cd /home/rustadmin/vertex-ar-app/vertex-ar
source /home/rustadmin/vertex-ar-app/venv/bin/activate

# Create backup
python3 backup_cli.py create

# Keep only last 7 backups
python3 -c "
import os
import time
from pathlib import Path

backup_dir = Path('./backups')
if backup_dir.exists():
    backups = sorted(backup_dir.glob('*.zip'), key=os.path.getctime, reverse=True)
    for backup in backups[7:]:
        backup.unlink()
        print(f'Deleted old backup: {backup.name}')
"

deactivate
EOF

    chmod +x "$BACKUP_SCRIPT"
    chown "$APP_USER:$APP_GROUP" "$BACKUP_SCRIPT"

    # Add to cron
    CRON_JOB="0 2 * * * $BACKUP_SCRIPT >> /var/log/vertex-ar/backup.log 2>&1"

    # Check if cron job already exists
    if ! crontab -u "$APP_USER" -l 2>/dev/null | grep -q "backup.cron.sh"; then
        (crontab -u "$APP_USER" -l 2>/dev/null; echo "$CRON_JOB") | crontab -u "$APP_USER" -
        print_success "Резервное копирование настроено (ежедневно в 2:00 AM)"
    else
        print_success "Резервное копирование уже настроено"
    fi
}

setup_logrotate() {
    print_header "Настройка логирования"

    LOGROTATE_CONF="/etc/logrotate.d/vertex-ar"

    cat > "$LOGROTATE_CONF" << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 7
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

    print_success "Ротация логов настроена"
}

print_final_info() {
    print_header "Развертывание завершено!"

    echo ""
    echo -e "${GREEN}Приложение готово к запуску!${NC}"
    echo ""
    echo "📍 Адрес: https://$DOMAIN/admin"
    echo "📝 Логи приложения: tail -f $LOG_DIR/error.log"
    echo "🔧 Статус: sudo supervisorctl status vertex-ar"
    echo ""
    echo -e "${YELLOW}ВАЖНО: Следующие шаги${NC}"
    echo "1. Установите SSL сертификат из Cpanel"
    echo "2. Скопируйте PEM сертификат в /etc/ssl/certs/nft.vertex-art.ru.crt"
    echo "3. Скопируйте приватный ключ в /etc/ssl/private/nft.vertex-art.ru.key"
    echo "4. Перезагрузите Nginx: sudo systemctl restart nginx"
    echo "5. Измените пароль администратора в .env файле"
    echo ""
    echo "📚 Подробная документация: $APP_DIR/DEPLOYMENT_CLOUD_RU_GUIDE.md"
    echo ""
}

# Main execution
main() {
    print_header "Vertex AR Deployment для cloud.ru"
    echo "Домен: $DOMAIN"
    echo "Пользователь: $APP_USER"
    echo "Приложение: $APP_DIR"
    echo ""

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

# Run main
main
