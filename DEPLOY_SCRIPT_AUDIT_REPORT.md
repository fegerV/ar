# Аудит скрипта деплоя Vertex AR
## Comprehensive Deployment Script Audit Report

**Дата аудита:** 2025-01-XX  
**Версия скрипта:** 1.0  
**Аудируемый файл:** `deploy-vertex-ar-cloud-ru.sh`  
**Статус:** ❌ **НЕ ГОТОВ К ПРОДАКШН** (требуются критические исправления)

---

## Executive Summary

Скрипт деплоя Vertex AR имеет **10 критических проблем безопасности и готовности**, которые делают его **непригодным для использования в продакшн-среде** без исправлений. Основные риски:

1. 🔴 **Критическая уязвимость безопасности**: дефолтный пароль в plaintext
2. 🔴 **Отсутствие механизма backup/rollback**: риск потери данных при неудачном деплое
3. 🔴 **Устаревшие зависимости**: Ubuntu 18.04 и Node.js 16 достигли EOL
4. 🔴 **Отсутствие валидации**: нет проверки готовности к деплою
5. 🔴 **Неполная обработка ошибок**: нет cleanup при сбое

**Рекомендация:** Внести исправления в соответствии с разделом "Критические исправления" перед использованием в продакшне.

---

## 1. Синтаксис и валидность ✅

### Результаты проверки:
- ✅ **Bash синтаксис корректен** (`bash -n` проверка пройдена)
- ✅ **Shebang присутствует**: `#!/bin/bash`
- ✅ **set -e включен**: скрипт прервется при ошибке
- ✅ **Функции определены корректно**

### Используемые команды:
| Команда | Статус | Комментарий |
|---------|--------|-------------|
| `apt` | ✅ | Присутствует в Ubuntu |
| `git` | ⚠️ | Устанавливается скриптом |
| `python3` | ⚠️ | Устанавливается скриптом |
| `pip` | ⚠️ | Устанавливается скриптом |
| `supervisorctl` | ⚠️ | Устанавливается скриптом |
| `nginx` | ⚠️ | Устанавливается скриптом |
| `systemctl` | ✅ | Присутствует в systemd |
| `crontab` | ✅ | Стандартная утилита |

### Проблемы:
- ❌ **Нет проверки наличия команд перед использованием** (для уже установленных)
- ❌ **Нет проверки версии Python** (может быть 3.6, 3.8, 3.10 и т.д.)
- ⚠️ **Hardcoded пути**: `/home/rustadmin`, `/etc/nginx`, `/var/log`

---

## 2. Безопасность 🔴 КРИТИЧНО

### Критические проблемы безопасности:

#### 2.1 Hardcoded Credentials ❌ КРИТИЧНО
**Расположение:** Строки 203-208  
**Проблема:**
```bash
DEFAULT_ADMIN_PASSWORD=CHANGE_ME_IMMEDIATELY
```
Дефолтный пароль записывается в `.env` файл в plaintext. Если администратор забудет его изменить, система будет скомпрометирована.

**Риск:** КРИТИЧЕСКИЙ  
**Вероятность эксплуатации:** ВЫСОКАЯ  
**Рекомендация:**
```bash
# Генерировать случайный пароль и выводить администратору один раз
DEFAULT_ADMIN_PASSWORD=$(python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(24)))")
echo "========================================" >&2
echo "ВАЖНО! СОХРАНИТЕ ЭТИ ДАННЫЕ:" >&2
echo "Логин администратора: superar" >&2
echo "Пароль администратора: $DEFAULT_ADMIN_PASSWORD" >&2
echo "========================================" >&2
```

#### 2.2 Отсутствие валидации секретов ❌ КРИТИЧНО
**Проблема:** Скрипт не проверяет, что критичные секреты были изменены перед запуском приложения.

**Рекомендация:** Добавить функцию валидации:
```bash
validate_production_secrets() {
    print_header "Проверка безопасности"
    
    source "$ENV_FILE"
    
    # Проверка SECRET_KEY
    if [[ "$SECRET_KEY" == *"CHANGE_ME"* ]]; then
        print_error "SECRET_KEY не был изменен!"
        exit 1
    fi
    
    # Проверка дефолтного пароля
    if [[ "$DEFAULT_ADMIN_PASSWORD" == "CHANGE_ME_IMMEDIATELY" ]]; then
        print_error "DEFAULT_ADMIN_PASSWORD не был изменен!"
        exit 1
    fi
    
    print_success "Проверка безопасности пройдена"
}
```

#### 2.3 Публичные репозитории ⚠️
**Расположение:** Строка 113 (scripts version)  
**Проблема:**
```bash
git clone https://github.com/fegerV/AR.git $APP_DIR
```
Прямое клонирование из публичного GitHub без верификации. Потенциальный вектор атаки через компрометацию репозитория.

**Рекомендация:**
- Использовать верификацию git commit signature
- Или скачивать конкретный release/tag
- Или использовать приватный репозиторий с SSH ключами

#### 2.4 Права доступа к файлам ✅ Частично хорошо
**Что хорошо:**
- ✅ `.env` файл имеет права 600 (только владелец может читать/писать)
- ✅ Логи принадлежат `rustadmin:rustadmin`

**Что нужно улучшить:**
- ❌ Директория `/etc/ssl/private` может не иметь правильных прав (должна быть 700)
- ❌ SSL приватный ключ должен иметь права 400 (только чтение для владельца)

#### 2.5 SSL/TLS сертификаты ⚠️
**Проблема:** Nginx конфигурация создается со ссылками на несуществующие сертификаты (строки 329-330):
```nginx
ssl_certificate /etc/ssl/certs/nft.vertex-art.ru.crt;
ssl_certificate_key /etc/ssl/private/nft.vertex-art.ru.key;
```

Nginx попытается запуститься и упадет с ошибкой, если сертификаты не существуют.

**Рекомендация:**
- Сначала создать self-signed сертификаты для первого запуска
- Или вообще не включать HTTPS конфигурацию до установки реальных сертификатов
- Или использовать certbot с Let's Encrypt автоматически

#### 2.6 Environment Variables Exposure ⚠️
**Проблема:** Переменные окружения передаются в supervisor, но не проверяется, что конфиденциальные данные не логируются.

**Рекомендация:**
- Убедиться что DEBUG=False в продакшне
- Настроить structlog для фильтрации конфиденциальных данных

---

## 3. Зависимости и требования 🔴 КРИТИЧНО

### 3.1 Устаревшая ОС ❌ КРИТИЧНО
**Проблема:** Скрипт написан для Ubuntu 18.04  
**Статус:** Ubuntu 18.04 LTS достиг End of Life в **апреле 2023**  
**Риски:**
- Отсутствие обновлений безопасности
- Уязвимости на уровне ОС
- Несовместимость с новыми пакетами

**Рекомендация:** Обновить на Ubuntu 22.04 LTS (поддержка до 2027) или Ubuntu 24.04 LTS (поддержка до 2029)

### 3.2 Устаревший Node.js ❌ КРИТИЧНО
**Расположение:** Строка 94  
**Проблема:**
```bash
curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
```
Node.js 16.x достиг End of Life в **сентябре 2023**

**Рекомендация:** Обновить на Node.js 20.x (LTS до апреля 2026) или Node.js 22.x (current)

### 3.3 Неуказанная версия Python ⚠️
**Проблема:** Используется просто `python3`, без уточнения версии.
- Ubuntu 18.04: Python 3.6 (EOL)
- Ubuntu 20.04: Python 3.8
- Ubuntu 22.04: Python 3.10
- Ubuntu 24.04: Python 3.12

Vertex AR требует **Python 3.10** согласно документации.

**Рекомендация:**
```bash
# Проверить версию Python
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
REQUIRED_VERSION="3.10"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    print_error "Требуется Python 3.10 или выше, установлено: $PYTHON_VERSION"
    print_warning "Устанавливаем Python 3.10..."
    add-apt-repository ppa:deadsnakes/ppa -y
    apt install -y python3.10 python3.10-venv python3.10-dev
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
fi
```

### 3.4 Отсутствие проверки системных требований ❌
**Проблема:** Нет проверки:
- Доступного места на диске
- Доступной оперативной памяти
- Занятости портов (8000, 80, 443)

**Рекомендация:** Добавить функцию pre-flight checks:
```bash
check_system_requirements() {
    print_header "Проверка системных требований"
    
    # Проверка свободного места (минимум 5GB)
    AVAILABLE_SPACE=$(df -BG / | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ "$AVAILABLE_SPACE" -lt 5 ]; then
        print_error "Недостаточно места на диске: ${AVAILABLE_SPACE}GB (требуется минимум 5GB)"
        exit 1
    fi
    
    # Проверка памяти (минимум 2GB)
    AVAILABLE_MEMORY=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$AVAILABLE_MEMORY" -lt 2 ]; then
        print_error "Недостаточно оперативной памяти: ${AVAILABLE_MEMORY}GB (требуется минимум 2GB)"
        exit 1
    fi
    
    # Проверка портов
    for PORT in 8000 80 443; do
        if netstat -tuln | grep -q ":$PORT "; then
            print_warning "Порт $PORT уже занят"
            read -p "Продолжить? (y/n): " CONTINUE
            if [ "$CONTINUE" != "y" ]; then
                exit 1
            fi
        fi
    done
    
    print_success "Системные требования проверены"
}
```

### 3.5 Отсутствие списка всех зависимостей 📋
**Проблема:** В README нет полного списка системных и Python зависимостей с версиями.

**Рекомендация:** Создать файл `DEPENDENCIES.md` с полным списком.

---

## 4. Процесс деплоя 🔴 КРИТИЧНО

### 4.1 Отсутствие механизма backup ❌ КРИТИЧНО
**Проблема:** При повторном деплое (обновлении) данные могут быть потеряны:
- База данных SQLite (`app_data.db`)
- Загруженные файлы (portraits, videos)
- Конфигурация `.env`

**Риск:** КРИТИЧЕСКИЙ - потеря данных пользователей

**Рекомендация:**
```bash
backup_before_deploy() {
    print_header "Создание backup перед деплоем"
    
    BACKUP_DIR="/home/rustadmin/backups/pre-deploy-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup базы данных
    if [ -f "$APP_DIR/vertex-ar/app_data.db" ]; then
        cp "$APP_DIR/vertex-ar/app_data.db" "$BACKUP_DIR/"
        print_success "База данных сохранена"
    fi
    
    # Backup storage
    if [ -d "$APP_DIR/vertex-ar/storage" ]; then
        cp -r "$APP_DIR/vertex-ar/storage" "$BACKUP_DIR/"
        print_success "Файлы storage сохранены"
    fi
    
    # Backup .env
    if [ -f "$APP_DIR/vertex-ar/.env" ]; then
        cp "$APP_DIR/vertex-ar/.env" "$BACKUP_DIR/"
        print_success "Конфигурация .env сохранена"
    fi
    
    echo "$BACKUP_DIR" > /tmp/vertex-ar-last-backup.txt
    print_success "Backup создан: $BACKUP_DIR"
}
```

### 4.2 Отсутствие механизма rollback ❌ КРИТИЧНО
**Проблема:** Если деплой не удался, нет способа откатиться к предыдущей версии.

**Рекомендация:**
```bash
rollback_deployment() {
    print_header "Откат к предыдущей версии"
    
    if [ ! -f /tmp/vertex-ar-last-backup.txt ]; then
        print_error "Backup не найден, откат невозможен"
        exit 1
    fi
    
    BACKUP_DIR=$(cat /tmp/vertex-ar-last-backup.txt)
    
    # Остановить приложение
    supervisorctl stop vertex-ar
    
    # Восстановить базу данных
    if [ -f "$BACKUP_DIR/app_data.db" ]; then
        cp "$BACKUP_DIR/app_data.db" "$APP_DIR/vertex-ar/"
        print_success "База данных восстановлена"
    fi
    
    # Восстановить storage
    if [ -d "$BACKUP_DIR/storage" ]; then
        rm -rf "$APP_DIR/vertex-ar/storage"
        cp -r "$BACKUP_DIR/storage" "$APP_DIR/vertex-ar/"
        print_success "Файлы storage восстановлены"
    fi
    
    # Восстановить .env
    if [ -f "$BACKUP_DIR/.env" ]; then
        cp "$BACKUP_DIR/.env" "$APP_DIR/vertex-ar/"
        print_success "Конфигурация .env восстановлена"
    fi
    
    # Запустить приложение
    supervisorctl start vertex-ar
    print_success "Откат завершен"
}
```

### 4.3 Отсутствие health checks ❌
**Проблема:** Скрипт проверяет только что supervisor запустил процесс, но не проверяет:
- Отвечает ли HTTP сервер
- Доступен ли `/health` endpoint
- Подключается ли приложение к базе данных

**Рекомендация:**
```bash
verify_application_health() {
    print_header "Проверка работоспособности приложения"
    
    # Ждем пока приложение запустится
    sleep 5
    
    # Проверяем health endpoint
    MAX_RETRIES=10
    RETRY_COUNT=0
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -s http://127.0.0.1:8000/health | grep -q "ok"; then
            print_success "Приложение отвечает на health checks"
            return 0
        fi
        
        RETRY_COUNT=$((RETRY_COUNT + 1))
        print_warning "Попытка $RETRY_COUNT/$MAX_RETRIES..."
        sleep 2
    done
    
    print_error "Приложение не отвечает на health checks"
    print_error "Проверьте логи: tail -f $LOG_DIR/error.log"
    
    # Предложить rollback
    read -p "Выполнить откат? (y/n): " DO_ROLLBACK
    if [ "$DO_ROLLBACK" = "y" ]; then
        rollback_deployment
    fi
    
    exit 1
}
```

### 4.4 Отсутствие database migrations ⚠️
**Проблема:** При обновлении приложения могут потребоваться миграции базы данных. Скрипт не запускает миграции.

**Рекомендация:**
```bash
run_database_migrations() {
    print_header "Запуск миграций базы данных"
    
    cd "$APP_DIR/vertex-ar"
    source "$VENV_DIR/bin/activate"
    
    # Если используется Alembic
    if [ -d "alembic" ]; then
        alembic upgrade head
        print_success "Миграции применены"
    else
        print_warning "Миграции не найдены (alembic directory отсутствует)"
    fi
    
    deactivate
}
```

### 4.5 Неправильная последовательность шагов ⚠️
**Проблема:** Nginx настраивается и перезапускается до того, как SSL сертификаты установлены. Это вызовет ошибку.

**Текущая последовательность (строки 515-532):**
```bash
setup_supervisor      # Запускает приложение
setup_nginx          # Настраивает nginx с SSL - УПАДЕТ!
setup_ssl_certificates # Предлагает установить SSL
```

**Правильная последовательность:**
```bash
setup_supervisor
setup_ssl_certificates  # Сначала SSL или self-signed
setup_nginx            # Потом nginx
verify_application_health
```

### 4.6 Нет zero-downtime deployment ⚠️
**Проблема:** При обновлении приложение будет недоступно.

**Рекомендация для будущего:**
- Использовать Blue-Green deployment
- Или использовать несколько worker'ов и обновлять их по очереди

---

## 5. Обработка ошибок и восстановление 🔴

### 5.1 Отсутствие trap handler ❌ КРИТИЧНО
**Проблема:** Если скрипт прервется (Ctrl+C, ошибка), cleanup не выполнится.

**Рекомендация:**
```bash
# Добавить в начало скрипта после set -e
cleanup() {
    EXIT_CODE=$?
    if [ $EXIT_CODE -ne 0 ]; then
        print_error "Деплой завершился с ошибкой (код: $EXIT_CODE)"
        print_warning "Лог ошибок: $LOG_DIR/error.log"
        
        # Предложить rollback
        if [ -f /tmp/vertex-ar-last-backup.txt ]; then
            read -p "Выполнить автоматический откат? (y/n): " DO_ROLLBACK
            if [ "$DO_ROLLBACK" = "y" ]; then
                rollback_deployment
            fi
        fi
    fi
}

trap cleanup EXIT INT TERM
```

### 5.2 Недостаточное логирование ⚠️
**Проблема:** Скрипт выводит информацию в stdout, но не сохраняет лог деплоя.

**Рекомендация:**
```bash
# В начале main()
DEPLOY_LOG="/var/log/vertex-ar/deploy-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$(dirname "$DEPLOY_LOG")"

# Дублировать вывод в файл
exec > >(tee -a "$DEPLOY_LOG")
exec 2>&1

print_success "Лог деплоя: $DEPLOY_LOG"
```

### 5.3 Неинформативные сообщения об ошибках ⚠️
**Проблема:** При ошибке установки зависимостей (pip install) ошибка может быть неясной.

**Рекомендация:**
```bash
install_python_dependencies() {
    print_header "Установка Python зависимостей"
    
    cd "$APP_DIR/vertex-ar"
    
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip with error handling
    if ! pip install --upgrade pip setuptools wheel; then
        print_error "Не удалось обновить pip/setuptools/wheel"
        print_error "Проверьте подключение к интернету и доступность PyPI"
        exit 1
    fi
    
    # Install requirements with detailed error
    if [ -f "requirements-simple.txt" ]; then
        if ! pip install -r requirements-simple.txt; then
            print_error "Не удалось установить зависимости из requirements-simple.txt"
            print_error "Последние 20 строк лога pip:"
            pip install -r requirements-simple.txt 2>&1 | tail -20
            exit 1
        fi
        print_success "Зависимости установлены (requirements-simple.txt)"
    elif [ -f "requirements.txt" ]; then
        if ! pip install -r requirements.txt; then
            print_error "Не удалось установить зависимости из requirements.txt"
            exit 1
        fi
        print_success "Зависимости установлены (requirements.txt)"
    else
        print_error "Файл requirements не найден в $APP_DIR/vertex-ar"
        exit 1
    fi
    
    deactivate
}
```

---

## 6. Конфигурация и окружение

### 6.1 Неполный .env файл ❌
**Проблема:** Генерируемый .env файл (строки 167-244) содержит только базовые переменные. Отсутствуют:

**Отсутствующие переменные из .env.example:**
- `INTERNAL_HEALTH_URL`
- `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM`
- `ADMIN_EMAILS`
- `ALERTING_ENABLED`
- `CPU_THRESHOLD`, `MEMORY_THRESHOLD`, `DISK_THRESHOLD`
- `HEALTH_CHECK_INTERVAL`
- `WEEKLY_REPORT_DAY`, `WEEKLY_REPORT_TIME`
- `REDIS_URL`, `REDIS_PASSWORD`
- `VIDEO_SCHEDULER_ENABLED`, `VIDEO_SCHEDULER_CHECK_INTERVAL`, etc.
- `LIFECYCLE_SCHEDULER_ENABLED`, `LIFECYCLE_CHECK_INTERVAL_SECONDS`, `LIFECYCLE_NOTIFICATIONS_ENABLED`

**Рекомендация:** Использовать полный .env.example как основу или явно документировать что не включено.

### 6.2 Hardcoded значения ⚠️
**Проблема:** Множество значений hardcoded в скрипте:

```bash
APP_USER="rustadmin"          # Строка 19
APP_GROUP="rustadmin"         # Строка 20
DOMAIN="nft.vertex-art.ru"    # Строка 25
APP_PORT=8000                 # Строка 24
```

**Рекомендация:** Сделать параметрами скрипта или спросить у пользователя:
```bash
# Параметры деплоя (можно переопределить)
APP_USER="${APP_USER:-rustadmin}"
APP_GROUP="${APP_GROUP:-$APP_USER}"
DOMAIN="${DOMAIN:-nft.vertex-art.ru}"
APP_PORT="${APP_PORT:-8000}"

# Или интерактивный режим
if [ -z "$DOMAIN" ]; then
    read -p "Введите домен (например, nft.vertex-art.ru): " DOMAIN
fi
```

### 6.3 Supervisor конфигурация ⚠️
**Проблема в строке 274:**
```bash
command=$VENV_DIR/bin/uvicorn main:app --host 127.0.0.1 --port $APP_PORT
```

**Проблемы:**
1. Не указано количество workers (должно быть `--workers N`)
2. Не настроено graceful shutdown timeout
3. Нет переменных окружения из .env

**Рекомендация:**
```bash
[program:vertex-ar]
directory=$APP_DIR/vertex-ar
command=$VENV_DIR/bin/uvicorn main:app --host 127.0.0.1 --port $APP_PORT --workers 4 --timeout-keep-alive 30
user=$APP_USER
autostart=true
autorestart=true
stderr_logfile=$LOG_DIR/error.log
stdout_logfile=$LOG_DIR/access.log
environment=PATH="$VENV_DIR/bin",HOME="$APP_HOME"
numprocs=1
priority=999
stopwaitsecs=30
killasgroup=true
```

---

## 7. Дополнительные проблемы

### 7.1 Различия между версиями ⚠️
**Проблема:** Есть два файла:
- `/home/engine/project/deploy-vertex-ar-cloud-ru.sh` (537 строк)
- `/home/engine/project/scripts/deploy-vertex-ar-cloud-ru.sh` (534 строк)

**Критическое различие в функции `clone_repository()`:**

**Root version (строки 111-117):**
```bash
if [ ! -d "$APP_DIR/.git" ]; then
    print_warning "Репозиторий не найден. Пожалуйста, скачайте вручную:"
    echo "git clone https://github.com/fegerV/AR.git $APP_DIR"
    # ... инструкции ...
    exit 1
```

**Scripts version (строки 111-114):**
```bash
if [ ! -d "$APP_DIR/.git" ]; then
    print_warning "Репозиторий не найден. Клонируем из правильного источника:"
    git clone https://github.com/fegerV/AR.git $APP_DIR
    print_success "Репозиторий успешно клонирован"
```

**Рекомендация:** Синхронизировать версии и выбрать одну как каноническую.

### 7.2 Отсутствие проверки пользователя rustadmin ⚠️
**Проблема:** Скрипт предполагает что пользователь `rustadmin` существует, но не проверяет это.

**Рекомендация:**
```bash
check_app_user() {
    print_header "Проверка пользователя приложения"
    
    if ! id "$APP_USER" &>/dev/null; then
        print_warning "Пользователь $APP_USER не существует"
        print_warning "Создаем пользователя..."
        
        useradd -m -s /bin/bash "$APP_USER"
        print_success "Пользователь $APP_USER создан"
    else
        print_success "Пользователь $APP_USER существует"
    fi
}
```

### 7.3 Backup скрипт имеет проблемы ⚠️
**Расположение:** Строки 420-445

**Проблемы:**
1. Hardcoded пути
2. Нет обработки ошибок
3. Нет проверки что backup_cli.py существует
4. Python код в heredoc может сломаться

**Рекомендация:**
```bash
cat > "$BACKUP_SCRIPT" << 'EOF'
#!/bin/bash
set -e

# Variables
APP_DIR="/home/rustadmin/vertex-ar-app/vertex-ar"
VENV_DIR="/home/rustadmin/vertex-ar-app/venv"
LOG_FILE="/var/log/vertex-ar/backup.log"

# Logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Change directory
cd "$APP_DIR" || {
    log "ERROR: Failed to change directory to $APP_DIR"
    exit 1
}

# Activate venv
source "$VENV_DIR/bin/activate" || {
    log "ERROR: Failed to activate virtual environment"
    exit 1
}

# Check if backup_cli.py exists
if [ ! -f "backup_cli.py" ]; then
    log "ERROR: backup_cli.py not found"
    exit 1
fi

# Create backup
log "INFO: Starting backup..."
if python3 backup_cli.py create; then
    log "INFO: Backup created successfully"
else
    log "ERROR: Backup creation failed"
    exit 1
fi

# Cleanup old backups (keep last 7)
log "INFO: Cleaning up old backups..."
python3 << 'PYEOF'
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    backup_dir = Path('./backups')
    if backup_dir.exists():
        backups = sorted(backup_dir.glob('*.zip'), key=os.path.getctime, reverse=True)
        deleted_count = 0
        for backup in backups[7:]:
            backup.unlink()
            logger.info(f'Deleted old backup: {backup.name}')
            deleted_count += 1
        logger.info(f'Cleaned up {deleted_count} old backups')
    else:
        logger.warning('Backup directory does not exist')
except Exception as e:
    logger.error(f'Error during backup cleanup: {e}')
    exit(1)
PYEOF

log "INFO: Backup process completed"
deactivate
EOF
```

### 7.4 Cron job может быть добавлен некорректно ⚠️
**Расположение:** Строки 457-459

**Проблема:**
```bash
if ! crontab -u "$APP_USER" -l 2>/dev/null | grep -q "backup.cron.sh"; then
    (crontab -u "$APP_USER" -l 2>/dev/null; echo "$CRON_JOB") | crontab -u "$APP_USER" -
```

Это может создать дубликаты при повторных запусках если путь изменится.

**Рекомендация:**
```bash
# Удалить старые записи vertex-ar backup
crontab -u "$APP_USER" -l 2>/dev/null | grep -v "vertex-ar" | grep -v "backup.cron.sh" | crontab -u "$APP_USER" - 2>/dev/null || true

# Добавить новую запись
(crontab -u "$APP_USER" -l 2>/dev/null; echo "$CRON_JOB") | crontab -u "$APP_USER" -
```

### 7.5 Nginx: Отсутствие rate limiting ⚠️
**Проблема:** Nginx конфигурация не включает rate limiting, хотя приложение имеет встроенный rate limiting.

**Рекомендация:** Добавить в nginx.conf:
```nginx
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=general:10m rate=100r/m;
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=upload:10m rate=10r/m;

server {
    # ...
    
    location /api/auth/ {
        limit_req zone=auth burst=10 nodelay;
        proxy_pass http://vertex_ar;
        # ...
    }
    
    location /api/upload/ {
        limit_req zone=upload burst=5 nodelay;
        proxy_pass http://vertex_ar;
        # ...
    }
    
    location / {
        limit_req zone=general burst=20 nodelay;
        proxy_pass http://vertex_ar;
        # ...
    }
}
```

### 7.6 Отсутствие мониторинга процесса деплоя ⚠️
**Проблема:** Нет уведомлений о результатах деплоя (успех/неудача).

**Рекомендация:**
```bash
send_deploy_notification() {
    STATUS=$1
    MESSAGE=$2
    
    # Отправка в Telegram (если настроен)
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
            -d chat_id="$TELEGRAM_CHAT_ID" \
            -d text="🚀 Vertex AR Deployment
Status: $STATUS
Message: $MESSAGE
Host: $(hostname)
Time: $(date)" >/dev/null
    fi
    
    # Отправка email (если настроен)
    # ...
}

# В конце main()
if [ $? -eq 0 ]; then
    send_deploy_notification "✅ SUCCESS" "Deployment completed successfully"
else
    send_deploy_notification "❌ FAILURE" "Deployment failed"
fi
```

---

## 8. Чек-лист готовности к деплою

### 🔴 Критические проблемы (MUST FIX)
- [ ] ❌ Исправить дефолтный пароль в plaintext
- [ ] ❌ Добавить механизм backup перед деплоем
- [ ] ❌ Добавить механизм rollback
- [ ] ❌ Добавить trap handler для cleanup
- [ ] ❌ Обновить Ubuntu 18.04 → 22.04/24.04
- [ ] ❌ Обновить Node.js 16 → 20/22
- [ ] ❌ Добавить проверку версии Python 3.10+
- [ ] ❌ Добавить health check после деплоя
- [ ] ❌ Исправить порядок setup (SSL перед nginx)
- [ ] ❌ Добавить валидацию секретов перед запуском

### ⚠️ Важные улучшения (SHOULD FIX)
- [ ] ⚠️ Добавить pre-flight checks (диск, память, порты)
- [ ] ⚠️ Добавить полный .env из .env.example
- [ ] ⚠️ Синхронизировать две версии скрипта
- [ ] ⚠️ Добавить проверку пользователя rustadmin
- [ ] ⚠️ Улучшить backup скрипт с обработкой ошибок
- [ ] ⚠️ Добавить логирование деплоя в файл
- [ ] ⚠️ Добавить database migrations
- [ ] ⚠️ Настроить количество workers в supervisor
- [ ] ⚠️ Добавить rate limiting в nginx
- [ ] ⚠️ Добавить уведомления о результатах деплоя

### ✅ Рекомендуемые улучшения (NICE TO HAVE)
- [ ] ✅ Сделать параметры скрипта настраиваемыми
- [ ] ✅ Добавить интерактивный режим
- [ ] ✅ Добавить dry-run режим
- [ ] ✅ Добавить версионирование деплоев
- [ ] ✅ Добавить zero-downtime deployment
- [ ] ✅ Добавить проверку git commit signature
- [ ] ✅ Создать DEPENDENCIES.md
- [ ] ✅ Добавить smoke tests после деплоя

---

## 9. Итоговая рекомендация

### 🔴 СТАТУС: НЕ ГОТОВ К ПРОДАКШН

**Критические проблемы:** 10  
**Важные проблемы:** 10  
**Рекомендуемые улучшения:** 8

### Минимальный набор исправлений для продакшн:

1. **Безопасность (КРИТИЧНО):**
   - Генерировать случайный пароль при создании .env
   - Добавить валидацию секретов
   - Обеспечить правильные права на SSL ключи

2. **Надежность (КРИТИЧНО):**
   - Добавить backup перед деплоем
   - Добавить rollback механизм
   - Добавить trap handler
   - Добавить health check

3. **Зависимости (КРИТИЧНО):**
   - Обновить целевую ОС до Ubuntu 22.04+
   - Обновить Node.js до версии 20+
   - Проверить версию Python 3.10+

4. **Процесс (ВАЖНО):**
   - Исправить порядок шагов (SSL before nginx)
   - Добавить pre-flight checks
   - Добавить полный .env
   - Улучшить логирование

### Временная шкала:
- **Критические исправления:** 2-3 дня разработки + тестирование
- **Важные улучшения:** 1-2 дня
- **Рекомендуемые:** По мере необходимости

### Следующие шаги:
1. ✅ Создать ветку `fix/deploy-script-production-ready`
2. ✅ Внести критические исправления
3. ✅ Протестировать на staging окружении
4. ✅ Провести code review
5. ✅ Обновить документацию
6. ✅ Деплой на продакшн с backup планом

---

## 10. Приложение: Улучшенная версия скрипта (структура)

### Рекомендуемая структура улучшенного скрипта:

```bash
#!/bin/bash
# Vertex AR Production Deployment Script v2.0

set -euo pipefail

# ===== CONFIGURATION =====
# (параметризованная конфигурация)

# ===== FUNCTIONS =====
# Utility functions
print_header()
print_success()
print_error()
print_warning()
log_to_file()

# Pre-flight checks
check_root()
check_system_requirements()
check_dependencies()
check_app_user()
validate_configuration()

# Backup & Rollback
backup_before_deploy()
rollback_deployment()

# Main deployment steps
update_system()
install_dependencies()
install_python()
install_nodejs()
clone_or_update_repository()
create_virtualenv()
install_python_dependencies()
run_database_migrations()
create_or_update_env_file()
validate_production_secrets()
create_log_directory()
setup_ssl_certificates()
setup_nginx()
setup_supervisor()
verify_application_health()
create_backup_script()
setup_logrotate()
setup_monitoring()

# Notifications
send_deploy_notification()

# Cleanup
cleanup()

# ===== TRAP HANDLERS =====
trap cleanup EXIT INT TERM

# ===== MAIN =====
main() {
    # Pre-flight
    check_root
    check_system_requirements
    check_dependencies
    check_app_user
    
    # Backup
    backup_before_deploy
    
    # Deploy
    update_system
    install_dependencies
    install_python
    install_nodejs
    clone_or_update_repository
    create_virtualenv
    install_python_dependencies
    run_database_migrations
    create_or_update_env_file
    validate_production_secrets
    create_log_directory
    setup_ssl_certificates
    setup_nginx
    setup_supervisor
    
    # Verify
    verify_application_health
    
    # Post-deploy
    create_backup_script
    setup_logrotate
    setup_monitoring
    
    # Notify
    send_deploy_notification "SUCCESS" "Deployment completed"
    
    # Final info
    print_final_info
}

main "$@"
```

---

## Контакты и дополнительная информация

**Аудитор:** AI Engine  
**Дата:** 2025-01-XX  
**Версия отчета:** 1.0

Для вопросов по данному аудиту или помощи в исправлении проблем, пожалуйста, обратитесь к команде разработки.

---

**END OF AUDIT REPORT**
