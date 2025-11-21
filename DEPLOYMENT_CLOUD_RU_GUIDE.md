# 🚀 Развертывание Vertex AR на cloud.ru (Ubuntu 18.04 + Cpanel)

## 📋 Информация о сервере

- **Хост-провайдер**: cloud.ru
- **ОС**: Ubuntu 18.04.06
- **IP публичный**: 192.144.12.68
- **IP внутренний**: 10.0.0.5
- **Доменное имя**: nft.vertex-art.ru (reg.ru + Cpanel)
- **SSH-ключ**: Настроен для пользователя `rustadmin`
- **Имя хоста**: rustdesk

---

## ⚡ Быстрый старт (5 минут)

### 1️⃣ Подключитесь к серверу

```bash
ssh -i /path/to/key rustadmin@192.144.12.68
```

### 2️⃣ Скачайте и запустите скрипт развертывания

```bash
cd /home/rustadmin
wget https://raw.githubusercontent.com/your-repo/deploy-vertex-ar.sh
chmod +x deploy-vertex-ar.sh
./deploy-vertex-ar.sh
```

### 3️⃣ Отправьте SSL-сертификат из Cpanel

```bash
# Из Cpanel: AutoSSL или Let's Encrypt
# Сертификат должен быть установлен на домен nft.vertex-art.ru
```

### 4️⃣ Настройте Cpanel Proxy

```bash
# В Cpanel -> Addon Domains:
# Домен: nft.vertex-art.ru
# Документная корневая папка: /public_html
# Перенаправить на: http://127.0.0.1:8000
```

### 5️⃣ Откройте браузер

```
https://nft.vertex-art.ru/admin
```

---

## 📦 Полное руководство по установке

### Шаг 1: Подготовка системы

```bash
# Обновите систему
sudo apt update && sudo apt upgrade -y

# Установите необходимые пакеты
sudo apt install -y \
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
    python3-dev

# Установите Node.js (для NFT маркер генератора)
curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
sudo apt install -y nodejs
```

### Шаг 2: Клонируйте репозиторий

```bash
# Создайте директорию приложения
mkdir -p /home/rustadmin/vertex-ar-app
cd /home/rustadmin/vertex-ar-app

# Клонируйте проект
git clone https://github.com/your-repo/vertex-ar.git .
# или
wget -O vertex-ar.zip https://your-repo/archive/main.zip
unzip vertex-ar.zip
```

### Шаг 3: Создайте виртуальное окружение Python

```bash
cd /home/rustadmin/vertex-ar-app
python3 -m venv venv
source venv/bin/activate

# Обновите pip
pip install --upgrade pip setuptools wheel
```

### Шаг 4: Установите зависимости

```bash
# Перейдите в папку vertex-ar
cd vertex-ar

# Установите зависимости
pip install -r requirements.txt

# Или используйте простой набор для production
pip install -r requirements-simple.txt
```

### Шаг 5: Создайте файл .env для production

```bash
cat > .env << 'EOF'
# ============================================
# Application Settings
# ============================================
DEBUG=False
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
APP_HOST=127.0.0.1
APP_PORT=8000
BASE_URL=https://nft.vertex-art.ru
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
CORS_ORIGINS=https://nft.vertex-art.ru,https://www.nft.vertex-art.ru
SESSION_TIMEOUT_MINUTES=30
AUTH_MAX_ATTEMPTS=5
AUTH_LOCKOUT_MINUTES=15
TOKEN_EXPIRATION_HOURS=24
BCRYPT_ROUNDS=12

# ============================================
# Admin Credentials
# ============================================
DEFAULT_ADMIN_USERNAME=superar
DEFAULT_ADMIN_PASSWORD=CHANGE_ME_TO_SECURE_PASSWORD
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
```

### Шаг 6: Инициализируйте базу данных

```bash
# Если есть скрипт инициализации
python3 create_test_data.py

# Или просто создайте пустую базу через приложение
```

### Шаг 7: Тестируем приложение

```bash
# Запустите приложение вручную для тестирования
uvicorn main:app --host 127.0.0.1 --port 8000

# В другом терминале проверьте:
curl http://127.0.0.1:8000/api/health
```

### Шаг 8: Настройте Supervisor для автозапуска

```bash
sudo nano /etc/supervisor/conf.d/vertex-ar.conf
```

Вставьте содержимое:

```ini
[program:vertex-ar]
directory=/home/rustadmin/vertex-ar-app/vertex-ar
command=/home/rustadmin/vertex-ar-app/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
user=rustadmin
autostart=true
autorestart=true
stderr_logfile=/var/log/vertex-ar/error.log
stdout_logfile=/var/log/vertex-ar/access.log
environment=PATH="/home/rustadmin/vertex-ar-app/venv/bin",HOME="/home/rustadmin"

[group:vertex-ar]
programs=vertex-ar
```

Создайте директорию логов:

```bash
sudo mkdir -p /var/log/vertex-ar
sudo chown rustadmin:rustadmin /var/log/vertex-ar
```

### Шаг 9: Запустите Supervisor

```bash
# Перезагрузите конфигурацию Supervisor
sudo supervisorctl reread
sudo supervisorctl update

# Запустите приложение
sudo supervisorctl start vertex-ar

# Проверьте статус
sudo supervisorctl status vertex-ar
```

### Шаг 10: Настройте Nginx как reverse proxy

```bash
sudo nano /etc/nginx/sites-available/vertex-ar
```

Вставьте содержимое:

```nginx
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

    # SSL сертификаты из Cpanel
    ssl_certificate /etc/ssl/certs/nft.vertex-art.ru.crt;
    ssl_certificate_key /etc/ssl/private/nft.vertex-art.ru.key;
    
    # SSL параметры
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

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
        
        # WebSocket поддержка (если нужна)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Таймауты
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Статические файлы (если есть)
    location /static/ {
        alias /home/rustadmin/vertex-ar-app/vertex-ar/static/;
        expires 30d;
    }
}
```

Активируйте конфиг:

```bash
sudo ln -s /etc/nginx/sites-available/vertex-ar /etc/nginx/sites-enabled/vertex-ar
sudo nginx -t
sudo systemctl restart nginx
```

### Шаг 11: Экспортируйте SSL сертификат из Cpanel

В **Cpanel -> AutoSSL** или **Let's Encrypt**:

1. Найдите сертификат для `nft.vertex-art.ru`
2. Экспортируйте сертификат в формате PEM
3. Загрузите на сервер:

```bash
# Скопируйте сертификат
sudo cp /path/to/certificate.crt /etc/ssl/certs/nft.vertex-art.ru.crt
sudo cp /path/to/private.key /etc/ssl/private/nft.vertex-art.ru.key

# Установите правильные права доступа
sudo chmod 644 /etc/ssl/certs/nft.vertex-art.ru.crt
sudo chmod 600 /etc/ssl/private/nft.vertex-art.ru.key
```

### Шаг 12: Проверьте работу

```bash
# Проверьте статус приложения
curl https://nft.vertex-art.ru/api/health

# Проверьте логи
tail -f /var/log/vertex-ar/access.log
tail -f /var/log/vertex-ar/error.log

# Проверьте Nginx
sudo tail -f /var/log/nginx/vertex-ar-error.log
```

---

## 🔐 Настройка Cpanel Proxy (Альтернатива Nginx)

Если Cpanel управляет доменом:

1. **Перейдите в Cpanel -> Addon Domains**
2. **Добавьте домен**: `nft.vertex-art.ru`
3. **Установите Document Root**: `/public_html/nft.vertex-art.ru`
4. **В файле `.htaccess`** (в Document Root):

```apache
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ http://127.0.0.1:8000/$1 [P,L]
```

5. **Включите SSL**:
   - Перейдите в **SSL/TLS Manager**
   - Используйте **AutoSSL** или установите сертификат от **Let's Encrypt**

---

## 📊 Мониторинг и логирование

### Просмотр логов приложения

```bash
# Логи Supervisor
sudo tail -f /var/log/vertex-ar/access.log

# Логи ошибок
sudo tail -f /var/log/vertex-ar/error.log

# Логи Nginx
sudo tail -f /var/log/nginx/vertex-ar-error.log
```

### Проверка статуса

```bash
# Статус приложения
sudo supervisorctl status vertex-ar

# Статус Nginx
sudo systemctl status nginx

# Проверка портов
sudo netstat -tlpn | grep 8000
sudo netstat -tlpn | grep :443
```

### Перезагрузка приложения

```bash
# Мягкая перезагрузка
sudo supervisorctl restart vertex-ar

# Жесткая перезагрузка
sudo supervisorctl stop vertex-ar
sleep 2
sudo supervisorctl start vertex-ar
```

---

## 🆘 Решение проблем

### Проблема: Приложение не запускается

```bash
# Проверьте логи Supervisor
sudo tail -f /var/log/vertex-ar/error.log

# Проверьте виртуальное окружение
source /home/rustadmin/vertex-ar-app/venv/bin/activate
python3 -c "import main"

# Проверьте порт
sudo lsof -i :8000
```

### Проблема: SSL ошибка

```bash
# Проверьте сертификаты
sudo ls -la /etc/ssl/certs/nft.vertex-art.ru.crt
sudo ls -la /etc/ssl/private/nft.vertex-art.ru.key

# Проверьте конфиг Nginx
sudo nginx -t

# Обновите сертификат из Cpanel
```

### Проблема: Ошибка 502 Bad Gateway

```bash
# Проверьте, работает ли приложение
curl http://127.0.0.1:8000

# Проверьте конфиг Nginx
sudo nginx -t

# Перезагрузите Nginx
sudo systemctl restart nginx
```

### Проблема: База данных недоступна

```bash
# Проверьте права доступа
ls -la /home/rustadmin/vertex-ar-app/vertex-ar/app_data.db

# Дайте права
chmod 644 /home/rustadmin/vertex-ar-app/vertex-ar/app_data.db
chmod 755 /home/rustadmin/vertex-ar-app/vertex-ar
```

---

## 🔄 Ежедневное обслуживание

### Резервное копирование

```bash
# Создание резервной копии
cd /home/rustadmin/vertex-ar-app/vertex-ar
python3 backup_cli.py create

# Расписание Cron (ежедневно в 2:00 AM)
0 2 * * * cd /home/rustadmin/vertex-ar-app/vertex-ar && python3 backup_cli.py create
```

### Ротация логов

```bash
# Создайте файл для logrotate
sudo nano /etc/logrotate.d/vertex-ar
```

Вставьте:

```
/var/log/vertex-ar/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 rustadmin rustadmin
    sharedscripts
    postrotate
        sudo supervisorctl restart vertex-ar > /dev/null 2>&1 || true
    endscript
}
```

### Мониторинг ресурсов

```bash
# Установите htop
sudo apt install -y htop

# Запустите мониторинг
htop

# Или используйте встроенные команды
ps aux | grep uvicorn
free -h
df -h
```

---

## 📈 Производительность

### Оптимизация Nginx

Отредактируйте `/etc/nginx/nginx.conf`:

```nginx
# Увеличьте worker процессы
worker_processes auto;

# Увеличьте подключения
events {
    worker_connections 2048;
}
```

### Оптимизация Uvicorn

В `/etc/supervisor/conf.d/vertex-ar.conf`:

```ini
command=/home/rustadmin/vertex-ar-app/venv/bin/uvicorn main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 4 \
    --loop uvloop \
    --log-level info
```

---

## 🔐 Безопасность

### Изменение пароля администратора

После первого запуска:

1. Откройте `https://nft.vertex-art.ru/admin`
2. Введите учетные данные из `.env` (DEFAULT_ADMIN_USERNAME/PASSWORD)
3. Перейдите в **Управление пользователями**
4. Измените пароль администратора

### Файл брандмауэра (.htaccess для Cpanel)

```apache
# Защита от DDoS
<IfModule mod_ratelimit.c>
    SetOutputFilter RATE_LIMIT
    SetEnv rate-limit 400
</IfModule>

# Защита от сканирования
<FilesMatch "\.php$|\.pl$|\.py$|\.jsp$|\.asp$|\.sh$|\.cgi$">
    Order Deny,Allow
    Deny from all
</FilesMatch>
```

---

## 📝 Чек-лист развертывания

- [ ] ОС обновлена
- [ ] Установлены все зависимости
- [ ] Репозиторий клонирован
- [ ] Виртуальное окружение создано
- [ ] Зависимости установлены
- [ ] .env файл создан с правильными переменными
- [ ] База данных инициализирована
- [ ] Приложение тестируется вручную
- [ ] Supervisor настроен и запущен
- [ ] Nginx настроен как reverse proxy
- [ ] SSL сертификат установлен
- [ ] Домен работает на HTTPS
- [ ] Админка доступна на https://nft.vertex-art.ru/admin
- [ ] Логи настроены и работают
- [ ] Резервное копирование настроено
- [ ] Мониторинг активирован

---

## 📞 Техническая поддержка

Если возникли проблемы:

1. **Проверьте логи**:
   ```bash
   tail -f /var/log/vertex-ar/error.log
   sudo tail -f /var/log/nginx/vertex-ar-error.log
   ```

2. **Проверьте конфигурацию**:
   ```bash
   curl http://127.0.0.1:8000/api/health
   sudo nginx -t
   ```

3. **Перезагрузите приложение**:
   ```bash
   sudo supervisorctl restart vertex-ar
   ```

---

**Дата создания**: 2024-11-21
**Версия**: 1.0
**Статус**: Готово к production развертыванию
