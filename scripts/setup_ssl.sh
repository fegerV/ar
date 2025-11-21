#!/bin/bash

# Скрипт для настройки SSL-сертификатов Let's Encrypt для nft.vertex-art.ru
# Использует webroot plugin для работы с Docker-контейнерами
# Поддерживает как продакшен, так и локальную разработку

# Default configuration
DOMAIN="nft.vertex-art.ru"
EMAIL="admin@vertex-art.ru"
MODE="production"  # production|local
USE_MKCERT=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --email)
            EMAIL="$2"
            shift 2
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        --mkcert)
            USE_MKCERT=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --domain DOMAIN      Set domain name (default: nft.vertex-art.ru)"
            echo "  --email EMAIL        Set email for Let's Encrypt"
            echo "  --mode MODE          Set mode: production|local (default: production)"
            echo "  --mkcert             Use mkcert for local development"
            echo "  --help               Show this help"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Production with default domain"
            echo "  $0 --domain mydomain.com --email admin@mydomain.com"
            echo "  $0 --mode local --mkcert              # Local development with mkcert"
            echo "  $0 --mode local                       # Local development with self-signed"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "Настройка SSL-сертификатов для $DOMAIN (режим: $MODE)"

# Function for local development setup
setup_local_ssl() {
    echo "Настройка локального SSL для разработки..."
    
    # Создаем директорию для SSL
    sudo mkdir -p ./ssl
    
    if [[ "$USE_MKCERT" == true ]]; then
        # Используем mkcert для локально-доверенных сертификатов
        if ! command -v mkcert &> /dev/null; then
            echo "Установка mkcert..."
            # Установка mkcert для Linux
            if command -v apt &> /dev/null; then
                sudo apt update
                sudo apt install -y wget libnss3-tools
            fi
            
            # Скачиваем mkcert
            MKCERT_VERSION="1.4.4"
            wget "https://github.com/FiloSottile/mkcert/releases/download/v${MKCERT_VERSION}/mkcert-v${MKCERT_VERSION}-linux-amd64" -O mkcert
            chmod +x mkcert
            sudo mv mkcert /usr/local/bin/
        fi
        
        # Устанавливаем локальный CA
        mkcert -install
        
        # Генерируем сертификат
        mkcert -cert-file ./ssl/cert.pem -key-file ./ssl/key.pem localhost 127.0.0.1 ::1
        
        echo "Локально-доверенные сертификаты mkcert созданы"
    else
        # Используем самоподписанные сертификаты
        echo "Создание самоподписанных сертификатов..."
        
        # Создаем конфигурацию для сертификата
        cat > ./ssl/localhost.conf << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
CN = localhost

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = *.localhost
IP.1 = 127.0.0.1
IP.2 = ::1
EOF
        
        # Генерируем сертификат
        openssl genrsa -out ./ssl/key.pem 2048
        openssl req -new -x509 -key ./ssl/key.pem -out ./ssl/cert.pem -days 365 \
            -config ./ssl/localhost.conf -extensions v3_req
        
        echo "Самоподписанные сертификаты созданы"
        echo "ВНИМАНИЕ: Браузеры будут показывать предупреждения безопасности"
    fi
    
    # Устанавливаем права доступа
    sudo chmod -R 755 ./ssl/
    sudo chmod 600 ./ssl/key.pem
    sudo chmod 644 ./ssl/cert.pem
    
    echo "Локальные SSL сертификаты настроены в директории ./ssl/"
}

# Function for production setup
setup_production_ssl() {
    echo "Настройка продакшен SSL с Let's Encrypt для $DOMAIN"
    
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
}

# Function to create local nginx config
create_local_nginx_config() {
    echo "Создание локальной конфигурации nginx..."
    
    cat > nginx.local.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream app_server {
        server app:8000;
    }

    # Local development server with SSL
    server {
        listen 80;
        server_name localhost 127.0.0.1;
        
        # Редирект на HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl;
        server_name localhost 127.0.0.1;

        # SSL сертификаты для локальной разработки
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # Настройки SSL для разработки
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers off;
        
        # Отключаем проверку для локальной разработки
        ssl_verify_client off;

        # Основные настройки
        location / {
            proxy_pass http://app_server;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Увеличиваем таймауты для разработки
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
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

    # Дополнительный сервер для доступа к MinIO напрямую
    server {
        listen 9000;
        server_name localhost;

        location / {
            proxy_pass http://minio:9000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

    echo "Локальная конфигурация nginx создана: nginx.local.conf"
}

# Function to show usage instructions
show_usage_instructions() {
    echo ""
    echo "==================================="
    echo "SSL Setup Complete!"
    echo "==================================="
    echo ""
    
    if [[ "$MODE" == "local" ]]; then
        echo "Локальная разработка:"
        echo "  - Сертификаты созданы в ./ssl/"
        echo "  - Используйте docker-compose -f docker-compose.local.yml up"
        echo "  - Доступ: https://localhost"
        
        if [[ "$USE_MKCERT" == true ]]; then
            echo "  - Сертификаты доверяются браузером (mkcert)"
        else
            echo "  - ВНИМАНИЕ: Браузеры будут показывать предупреждения безопасности"
        fi
    else
        echo "Продакшен установка:"
        echo "  - SSL сертификаты установлены для $DOMAIN"
        echo "  - Автоматическое обновление настроено через cron"
        echo "  - Доступ: https://$DOMAIN"
    fi
    
    echo ""
    echo "Следующие шаги:"
    echo "1. Запустите docker-compose up -d"
    echo "2. Проверьте работу приложения"
    echo "3. Настройте DNS (для продакшена)"
}

# Main execution logic
if [[ "$MODE" == "local" ]]; then
    setup_local_ssl
    create_local_nginx_config
else
    setup_production_ssl
fi

show_usage_instructions