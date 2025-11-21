#!/bin/bash

# Скрипт для настройки SSL-сертификатов для локальной разработки Vertex AR
# Поддерживает два режима: self-signed сертификаты и mkcert

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="localhost"
IP_ADDRESS="127.0.0.1"
SSL_DIR="./ssl"
CERT_FILE="$SSL_DIR/cert.pem"
KEY_FILE="$SSL_DIR/key.pem"

echo -e "${BLUE}===================================${NC}"
echo -e "${BLUE}Local SSL Setup for Vertex AR${NC}"
echo -e "${BLUE}===================================${NC}"
echo ""

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to create SSL directory
create_ssl_directory() {
    print_status "Creating SSL directory..."
    mkdir -p "$SSL_DIR"
    chmod 755 "$SSL_DIR"
    print_status "SSL directory created: $SSL_DIR"
}

# Function to generate self-signed certificate
generate_self_signed_cert() {
    print_status "Generating self-signed certificate..."
    
    # Create certificate configuration
    cat > "$SSL_DIR/localhost.conf" << EOF
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

    # Generate private key
    openssl genrsa -out "$KEY_FILE" 2048
    
    # Generate certificate
    openssl req -new -x509 -key "$KEY_FILE" -out "$CERT_FILE" -days 365 \
        -config "$SSL_DIR/localhost.conf" -extensions v3_req
    
    # Set permissions
    chmod 600 "$KEY_FILE"
    chmod 644 "$CERT_FILE"
    
    print_status "Self-signed certificate generated successfully"
    print_warning "This certificate will show security warnings in browsers"
}

# Function to setup mkcert
setup_mkcert() {
    print_status "Setting up mkcert for locally-trusted certificates..."
    
    # Check if mkcert is installed
    if ! command_exists mkcert; then
        print_warning "mkcert not found. Installing mkcert..."
        
        # Detect OS and install mkcert
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux
            if command_exists apt; then
                # Ubuntu/Debian
                sudo apt update
                sudo apt install -y wget libnss3-tools
            elif command_exists yum; then
                # CentOS/RHEL/Fedora
                sudo yum install -y wget nss-tools
            elif command_exists dnf; then
                # Fedora
                sudo dnf install -y wget nss-tools
            fi
            
            # Download and install mkcert
            MKCERT_VERSION="1.4.4"
            MKCERT_URL="https://github.com/FiloSottile/mkcert/releases/download/v${MKCERT_VERSION}/mkcert-v${MKCERT_VERSION}-linux-amd64"
            
            wget "$MKCERT_URL" -O mkcert
            chmod +x mkcert
            sudo mv mkcert /usr/local/bin/
            
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            if command_exists brew; then
                brew install mkcert nss
            else
                print_error "Homebrew not found. Please install Homebrew first."
                exit 1
            fi
        else
            print_error "Unsupported OS for mkcert installation"
            exit 1
        fi
    fi
    
    # Install local CA
    print_status "Installing local certificate authority..."
    mkcert -install
    
    # Generate certificate
    print_status "Generating certificate for localhost..."
    mkcert -cert-file "$CERT_FILE" -key-file "$KEY_FILE" localhost 127.0.0.1 ::1
    
    print_status "mkcert certificate generated successfully"
    print_status "Certificate will be trusted by browsers"
}

# Function to update nginx configuration for local development
update_nginx_config() {
    print_status "Creating local nginx configuration..."
    
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

    print_status "Local nginx configuration created: nginx.local.conf"
}

# Function to test certificates
test_certificates() {
    print_status "Testing generated certificates..."
    
    if [[ -f "$CERT_FILE" && -f "$KEY_FILE" ]]; then
        # Check certificate validity
        if openssl x509 -in "$CERT_FILE" -text -noout | grep -q "localhost"; then
            print_status "Certificate is valid for localhost"
        else
            print_error "Certificate is not valid for localhost"
            return 1
        fi
        
        # Check key matches certificate
        CERT_MODULUS=$(openssl x509 -noout -modulus -in "$CERT_FILE" | openssl md5)
        KEY_MODULUS=$(openssl rsa -noout -modulus -in "$KEY_FILE" | openssl md5)
        
        if [[ "$CERT_MODULUS" == "$KEY_MODULUS" ]]; then
            print_status "Certificate and key match"
        else
            print_error "Certificate and key do not match"
            return 1
        fi
        
        print_status "Certificate test passed"
        return 0
    else
        print_error "Certificate files not found"
        return 1
    fi
}

# Function to show usage instructions
show_usage_instructions() {
    echo ""
    echo -e "${GREEN}===================================${NC}"
    echo -e "${GREEN}SSL Setup Complete!${NC}"
    echo -e "${GREEN}===================================${NC}"
    echo ""
    echo "Generated files:"
    echo "  - Certificate: $CERT_FILE"
    echo "  - Private Key: $KEY_FILE"
    echo "  - Nginx Config: nginx.local.conf"
    echo ""
    echo "Usage instructions:"
    echo ""
    echo "1. For Docker development:"
    echo "   docker-compose -f docker-compose.yml -f docker-compose.local.yml up"
    echo ""
    echo "2. Access the application:"
    echo "   https://localhost"
    echo "   https://127.0.0.1"
    echo ""
    
    if [[ "$METHOD" == "mkcert" ]]; then
        echo "3. The certificate is trusted by your browser - no warnings!"
    else
        echo "3. You will see a security warning in your browser"
        echo "   Click 'Advanced' → 'Proceed to localhost (unsafe)'"
    fi
    
    echo ""
    echo "4. To use with local nginx:"
    echo "   cp nginx.local.conf /etc/nginx/sites-available/vertex-ar-local"
    echo "   sudo ln -s /etc/nginx/sites-available/vertex-ar-local /etc/nginx/sites-enabled/"
    echo "   sudo nginx -t && sudo systemctl reload nginx"
    echo ""
}

# Main menu
echo "Choose SSL certificate method:"
echo "1) Self-signed certificate (simple, browser warnings)"
echo "2) mkcert (locally trusted, no warnings)"
echo "3) Remove existing certificates"
echo ""

read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        METHOD="self-signed"
        print_status "Using self-signed certificates..."
        create_ssl_directory
        generate_self_signed_cert
        update_nginx_config
        test_certificates
        show_usage_instructions
        ;;
    2)
        METHOD="mkcert"
        print_status "Using mkcert for locally-trusted certificates..."
        create_ssl_directory
        setup_mkcert
        update_nginx_config
        test_certificates
        show_usage_instructions
        ;;
    3)
        print_status "Removing existing certificates..."
        if [[ -d "$SSL_DIR" ]]; then
            rm -rf "$SSL_DIR"
            print_status "SSL directory removed"
        else
            print_warning "SSL directory does not exist"
        fi
        if [[ -f "nginx.local.conf" ]]; then
            rm nginx.local.conf
            print_status "Local nginx config removed"
        fi
        ;;
    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac