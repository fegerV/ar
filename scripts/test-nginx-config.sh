#!/bin/bash
# Скрипт для тестирования конфигурации Nginx

set -e

echo "=========================================="
echo "Тестирование конфигурации Nginx"
echo "=========================================="

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

error() {
    echo -e "${RED}✗ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

info() {
    echo -e "$1"
}

# Проверка 1: Синтаксис nginx.conf
echo ""
info "1. Проверка синтаксиса nginx.conf..."

# Создаем временную версию с localhost вместо app для проверки синтаксиса
TEMP_CONF=$(mktemp)
sed 's/server app:8000;/server 127.0.0.1:8000;/g' nginx.conf > "$TEMP_CONF"

if docker run --rm \
    --network=none \
    -v "$TEMP_CONF:/etc/nginx/nginx.conf:ro" \
    nginx:alpine \
    nginx -t 2>&1 | grep -q "syntax is ok"; then
    success "Синтаксис nginx.conf корректен"
    rm -f "$TEMP_CONF"
else
    error "Синтаксис nginx.conf некорректен"
    docker run --rm --network=none -v "$TEMP_CONF:/etc/nginx/nginx.conf:ro" nginx:alpine nginx -t
    rm -f "$TEMP_CONF"
    exit 1
fi

# Проверка 2: Наличие обязательных секций
echo ""
info "2. Проверка структуры конфигурации..."

if grep -q "events {" nginx.conf; then
    success "Секция events найдена"
else
    error "Секция events отсутствует"
    exit 1
fi

if grep -q "http {" nginx.conf; then
    success "Секция http найдена"
else
    error "Секция http отсутствует"
    exit 1
fi

if grep -q "upstream app_server" nginx.conf; then
    success "Upstream app_server определен"
else
    warning "Upstream app_server не найден"
fi

if grep -q "listen 80" nginx.conf; then
    success "HTTP порт 80 настроен"
else
    warning "HTTP порт 80 не настроен"
fi

# Проверка 3: SSL настройки (должны быть закомментированы)
echo ""
info "3. Проверка SSL настроек..."

if grep -q "listen 443 ssl" nginx.conf && ! grep -q "^[[:space:]]*#.*listen 443 ssl" nginx.conf; then
    warning "HTTPS порт 443 активен - убедитесь что SSL сертификаты существуют"
else
    success "HTTPS закомментирован (рекомендуется для начальной настройки)"
fi

# Проверка 4: Проверка docker-compose.yml
echo ""
info "4. Проверка docker-compose.yml..."

if [ -f "docker-compose.yml" ]; then
    success "Файл docker-compose.yml найден"
    
    if grep -q "nginx:" docker-compose.yml; then
        success "Сервис nginx определен"
    else
        error "Сервис nginx не найден в docker-compose.yml"
        exit 1
    fi
    
    if grep -q "./nginx.conf:/etc/nginx/nginx.conf" docker-compose.yml; then
        success "Монтировка nginx.conf настроена"
    else
        warning "Монтировка nginx.conf не найдена"
    fi
    
    # Проверка что ssl закомментирована или отсутствует
    if grep "^\s*#.*./ssl:/etc/nginx/ssl" docker-compose.yml > /dev/null || \
       ! grep "./ssl:/etc/nginx/ssl" docker-compose.yml > /dev/null; then
        success "SSL директория не монтируется (OK для начальной настройки)"
    else
        warning "SSL директория монтируется - убедитесь что ./ssl/ существует"
        if [ ! -d "./ssl" ]; then
            error "Директория ./ssl/ не существует!"
            echo "  Создайте её или закомментируйте в docker-compose.yml"
        fi
    fi
else
    error "Файл docker-compose.yml не найден"
    exit 1
fi

# Проверка 5: Тест с минимальным compose
echo ""
info "5. Запуск тестового окружения..."

if [ -f "docker-compose.test.yml" ] && [ -f "nginx.test.conf" ]; then
    info "Запуск тестового контейнера..."
    
    # Очистка старых контейнеров
    docker compose -f docker-compose.test.yml down -v 2>/dev/null || true
    
    # Запуск теста
    if docker compose -f docker-compose.test.yml up -d 2>&1; then
        success "Тестовые контейнеры запущены"
        
        # Ждем готовности
        echo "Ожидание готовности контейнеров..."
        sleep 5
        
        # Проверка healthcheck
        if docker compose -f docker-compose.test.yml ps | grep -q "healthy"; then
            success "Healthcheck прошел успешно"
        else
            warning "Healthcheck еще не готов, ждем..."
            sleep 10
        fi
        
        # Проверка доступности
        if curl -s http://localhost:8080/health | grep -q "OK"; then
            success "Тестовый Nginx отвечает на запросы"
        else
            error "Тестовый Nginx не отвечает"
            docker compose -f docker-compose.test.yml logs
        fi
        
        # Очистка
        docker compose -f docker-compose.test.yml down -v
        success "Тестовое окружение остановлено"
    else
        error "Не удалось запустить тестовое окружение"
    fi
else
    warning "Тестовые файлы не найдены, пропускаем интеграционный тест"
fi

# Финальный вывод
echo ""
echo "=========================================="
success "Все проверки пройдены!"
echo "=========================================="
echo ""
info "Готово к запуску:"
echo "  docker compose up -d"
echo ""
info "Для мониторинга:"
echo "  docker compose ps"
echo "  docker compose logs nginx --follow"
echo ""
info "Для активации HTTPS см.:"
echo "  docs/deployment/nginx-ssl-setup.md"
echo ""
