#!/bin/bash

# Скрипт для настройки SSL-сертификатов Let's Encrypt для nft.vertex-art.ru
# Использует webroot plugin для работы с Docker-контейнерами

DOMAIN="nft.vertex-art.ru"
EMAIL="admin@vertex-art.ru"  # Укажите реальный email для уведомлений от Let's Encrypt

echo "Настройка SSL-сертификатов для $DOMAIN"

# Создаем директорию для webroot
sudo mkdir -p /var/www/certbot

# Запускаем контейнер только с Nginx для получения сертификата
docker-compose up -d nginx

# Ждем, пока Nginx запустится
sleep 10

# Получаем SSL-сертификат с помощью webroot plugin
sudo certbot certonly --webroot --webroot-path=/var/www/certbot -d $DOMAIN --email $EMAIL --agree-tos --non-interactive

# Проверяем, успешно ли получен сертификат
if [ $? -eq 0 ]; then
    echo "SSL-сертификат успешно получен для $DOMAIN"
    echo "Сертификаты находятся в /etc/letsencrypt/live/$DOMAIN/"

    # Копируем сертификаты в директорию ssl для использования в Docker
    sudo mkdir -p ./ssl
    sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ./ssl/cert.pem
    sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ./ssl/key.pem

    # Устанавливаем правильные права доступа
    sudo chmod -R 755 ./ssl/

    echo "Сертификаты скопированы в директорию ssl/"

    # Обновляем конфигурацию nginx для использования SSL
    echo "Обновление конфигурации nginx..."

    cat > nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream app_server {
        server app:8000;
    }

    # Директория для проверки домена certbot'ом
    server {
        listen 80;
        server_name nft.vertex-art.ru;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        # Редирект остальных запросов на HTTPS
        location / {
            return 301 https://$host$request_uri;
        }
    }

    server {
        listen 443 ssl;
        server_name nft.vertex-art.ru;

        # SSL сертификаты
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # Основные настройки SSL
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5:!EXPORT:!DES:!RC4:!PSK:!aECDH:!EDH-DSS-DES-CBC3-SHA:!EDH-RSA-DES-CBC3-SHA:!KRB5-DES-CBC3-SHA;
        ssl_prefer_server_ciphers off;

        # Настройки для админ-панели и API
        location / {
            proxy_pass http://app_server;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Прямая раздача NFT-файлов из MinIO
        location /nft-markers/ {
            proxy_pass http://minio:9000/vertex-art-bucket/nft-markers/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Прямая раздача изображений из MinIO
        location /images/ {
            proxy_pass http://minio:9000/vertex-art-bucket/images/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Прямая раздача видео из MinIO
        location /videos/ {
            proxy_pass http://minio:9000/vertex-art-bucket/videos/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

    echo "Конфигурация nginx обновлена"

    # Добавляем задачу в cron для автоматического обновления сертификатов
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --post-hook 'docker-compose restart nginx'") | crontab -

    echo "Добавлена задача в cron для автоматического обновления сертификатов"

    # Перезапускаем Nginx для применения изменений
    docker-compose restart nginx
else
    echo "Ошибка при получении SSL-сертификата"
    exit 1
fi
