# Vertex AR - Подробное руководство по установке

## 📋 Оглавление

1. [Введение](#введение)
2. [Системные требования](#системные-требования)
3. [Установка зависимостей](#установка-зависимостей)
4. [Установка проекта](#установка-проекта)
5. [Конфигурация](#конфигурация)
6. [Запуск приложения](#запуск-приложения)
7. [Docker развертывание](#docker-развертывание)
8. [Продакшен развертывание](#продакшен-развертывание)
9. [Настройка HTTPS](#настройка-https)
10. [Резервное копирование](#резервное-копирование)
11. [Мониторинг и обслуживание](#мониторинг-и-обслуживание)
12. [Решение проблем](#решение-проблем)

---

## 🎯 Введение

Это подробное руководство по установке **Vertex AR** - системы для создания дополненной реальности из портретов.

### Что будет установлено

- ✅ FastAPI веб-приложение
- ✅ SQLite база данных
- ✅ Файловое хранилище
- ✅ NFT маркер генератор
- ✅ AR viewer (A-Frame + AR.js)
- ✅ Административная панель

### Варианты установки

**1. Локальная разработка**
- Для разработки и тестирования
- Запуск на localhost
- Легкая отладка

**2. Docker контейнер**
- Изолированная среда
- Легкое развертывание
- Консистентность окружения

**3. Продакшен сервер**
- Ubuntu/Debian VPS
- Nginx reverse proxy
- SSL сертификаты
- Systemd сервис

---

## 💻 Системные требования

### Минимальные требования

#### Аппаратные требования

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| **CPU** | 2 ядра | 4+ ядра |
| **RAM** | 2 GB | 4-8 GB |
| **Диск** | 10 GB | 50 GB SSD |
| **Сеть** | 10 Mbps | 100+ Mbps |

#### Операционная система

**Linux (Рекомендуется):**
- Ubuntu 20.04 LTS или новее
- Debian 11 или новее
- CentOS 8 / Rocky Linux 8
- Fedora 35+

**macOS:**
- macOS 11 Big Sur или новее
- Homebrew для установки зависимостей

**Windows:**
- Windows 10 или новее
- WSL2 (рекомендуется для разработки)
- Или нативная установка

#### Программное обеспечение

| Софт | Версия | Обязательно |
|------|--------|-------------|
| **Python** | 3.11+ | ✅ Да |
| **pip** | 23.0+ | ✅ Да |
| **Git** | 2.x | ✅ Да |
| **OpenCV** | 4.x | ✅ Да |
| **libmagic** | 5.x | ✅ Да |
| **Docker** | 20.10+ | ⚪ Опционально |
| **Nginx** | 1.18+ | ⚪ Для продакшена |

### Проверка системы

#### Проверка версии Python

```bash
python3 --version
# Требуется: Python 3.11.0 или выше
```

Если версия ниже 3.11:

**Ubuntu/Debian:**
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

**macOS:**
```bash
brew install python@3.11
```

**Windows:**
Скачайте установщик с https://www.python.org/downloads/

#### Проверка pip

```bash
python3.11 -m pip --version
# Требуется: pip 23.0 или выше
```

Обновление pip:
```bash
python3.11 -m pip install --upgrade pip
```

#### Проверка Git

```bash
git --version
# Требуется: git version 2.x
```

Установка Git:

**Ubuntu/Debian:**
```bash
sudo apt install git
```

**macOS:**
```bash
brew install git
```

**Windows:**
Скачайте с https://git-scm.com/download/win

#### Проверка свободного места

```bash
df -h
# Убедитесь, что есть минимум 10 GB свободного места
```

#### Проверка памяти

```bash
free -h
# Убедитесь, что есть минимум 2 GB RAM
```

---

## 📦 Установка зависимостей

### Ubuntu/Debian

#### Шаг 1: Обновление системы

```bash
sudo apt update
sudo apt upgrade -y
```

#### Шаг 2: Установка Python и зависимостей

```bash
# Python и dev пакеты
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip

# Build tools
sudo apt install -y \
    build-essential \
    gcc \
    g++ \
    make \
    cmake

# Библиотеки для обработки изображений
sudo apt install -y \
    libopencv-dev \
    python3-opencv \
    libpng-dev \
    libjpeg-dev \
    libtiff-dev

# Дополнительные библиотеки
sudo apt install -y \
    libmagic1 \
    libmagic-dev \
    libffi-dev \
    libssl-dev

# Git и curl
sudo apt install -y \
    git \
    curl \
    wget
```

#### Шаг 3: Проверка установки

```bash
# Проверка Python
python3.11 --version

# Проверка OpenCV
python3.11 -c "import cv2; print(cv2.__version__)"

# Проверка magic
python3.11 -m pip install python-magic
python3.11 -c "import magic; print('magic OK')"
```

### macOS

#### Шаг 1: Установка Homebrew

```bash
# Если Homebrew не установлен
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### Шаг 2: Установка зависимостей

```bash
# Python
brew install python@3.11

# OpenCV
brew install opencv

# libmagic
brew install libmagic

# Git
brew install git

# Дополнительные инструменты
brew install wget curl
```

#### Шаг 3: Настройка PATH

Добавьте в `~/.zshrc` или `~/.bash_profile`:

```bash
export PATH="/usr/local/opt/python@3.11/bin:$PATH"
export LDFLAGS="-L/usr/local/opt/python@3.11/lib"
export CPPFLAGS="-I/usr/local/opt/python@3.11/include"
```

Применить изменения:
```bash
source ~/.zshrc  # или ~/.bash_profile
```

### Windows

#### Вариант 1: WSL2 (Рекомендуется)

**Установка WSL2:**
```powershell
# В PowerShell с правами администратора
wsl --install -d Ubuntu-22.04
```

После установки следуйте инструкциям для Ubuntu.

#### Вариант 2: Нативная установка

**1. Установка Python:**
- Скачайте Python 3.11+ с https://www.python.org/downloads/
- При установке отметьте "Add Python to PATH"

**2. Установка Visual C++ Build Tools:**
- Скачайте с https://visualstudio.microsoft.com/downloads/
- Установите "Desktop development with C++"

**3. Установка Git:**
- Скачайте с https://git-scm.com/download/win
- Используйте настройки по умолчанию

**4. Установка OpenCV:**
```powershell
pip install opencv-python opencv-contrib-python
```

**5. Установка python-magic (Windows):**
```powershell
pip install python-magic-bin
```

---

## 🚀 Установка проекта

### Шаг 1: Клонирование репозитория

```bash
# Клонирование проекта
git clone https://github.com/your-org/vertex-ar.git
cd vertex-ar

# Проверка структуры
ls -la
# Должны увидеть: vertex-ar/, README.md, и др.
```

### Шаг 2: Переход в основную директорию

```bash
cd vertex-ar
ls -la
# Должны увидеть: main.py, requirements.txt, templates/, и др.
```

### Шаг 3: Создание виртуального окружения

```bash
# Создание venv
python3.11 -m venv .venv

# Проверка создания
ls -la .venv
# Должны увидеть: bin/, lib/, include/, pyvenv.cfg
```

### Шаг 4: Активация виртуального окружения

**Linux/macOS:**
```bash
source .venv/bin/activate
```

После активации в начале строки появится `(.venv)`:
```bash
(.venv) user@host:~/vertex-ar/vertex-ar$
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

Если возникает ошибка ExecutionPolicy:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Шаг 5: Обновление pip

```bash
python -m pip install --upgrade pip setuptools wheel
```

### Шаг 6: Установка зависимостей Python

#### Основные зависимости

```bash
# Установка из requirements.txt
pip install -r requirements.txt
```

Если возникают ошибки, установите по одному:

```bash
# Web framework
pip install fastapi==0.104.1
pip install uvicorn[standard]==0.24.0

# Database
pip install sqlalchemy==2.0.23

# Authentication
pip install python-jose[cryptography]==3.3.0
pip install passlib[bcrypt]==1.7.4
pip install python-multipart==0.0.6

# Image processing
pip install Pillow==10.1.0
pip install opencv-python==4.8.1.78
pip install numpy==1.26.2

# File handling
pip install python-magic==0.4.27
pip install qrcode[pil]==7.4.2

# Storage
pip install minio==7.2.0

# Utilities
pip install python-dotenv==1.0.0
pip install requests==2.31.0
```

#### Зависимости для разработки (опционально)

```bash
# Установка dev зависимостей
pip install -r requirements-dev.txt

# Или вручную
pip install pytest pytest-asyncio pytest-cov httpx
pip install flake8 pylint mypy
pip install black isort
pip install ipython ipdb
```

### Шаг 7: Проверка установки

```bash
# Проверка установленных пакетов
pip list

# Проверка версий ключевых пакетов
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')"
python -c "import cv2; print(f'OpenCV: {cv2.__version__}')"
python -c "import PIL; print(f'Pillow: {PIL.__version__}')"
```

Ожидаемый вывод:
```
FastAPI: 0.104.1
OpenCV: 4.8.1
Pillow: 10.1.0
```

### Шаг 8: Создание необходимых директорий

```bash
# Создание директорий для хранилища
mkdir -p storage/ar_content
mkdir -p storage/nft-markers
mkdir -p storage/qr-codes
mkdir -p storage/temp
mkdir -p storage/previews

# Создание директории для логов
mkdir -p logs

# Создание директории для статики
mkdir -p static

# Установка прав (Linux/macOS)
chmod 755 storage logs static
```

Проверка структуры:
```bash
tree -L 2 storage
# Должно быть:
# storage/
# ├── ar_content/
# ├── nft-markers/
# ├── qr-codes/
# ├── temp/
# └── previews/
```

### Шаг 9: Копирование конфигурации

```bash
# Копирование примера .env
cp .env.example .env

# Проверка
ls -la .env
# Должен существовать файл .env
```

---

## ⚙️ Конфигурация

### Редактирование .env файла

```bash
# Откройте в вашем любимом редакторе
nano .env
# или
vim .env
# или
code .env  # VS Code
```

### Основные настройки

```env
# ═══════════════════════════════════════
# ПРИЛОЖЕНИЕ
# ═══════════════════════════════════════

# Режим отладки (True для разработки, False для продакшена)
DEBUG=True

# Секретный ключ для шифрования (ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ!)
# Генерация: openssl rand -hex 32
SECRET_KEY=your-very-secret-key-change-this-in-production

# Хост и порт
APP_HOST=0.0.0.0
APP_PORT=8000

# Базовый URL (для генерации ссылок)
BASE_URL=http://localhost:8000

# ═══════════════════════════════════════
# БАЗА ДАННЫХ
# ═══════════════════════════════════════

# Путь к SQLite БД
DATABASE_URL=sqlite:///./app_data.db

# Или для PostgreSQL (опционально):
# DATABASE_URL=postgresql://user:password@localhost/vertex_ar

# ═══════════════════════════════════════
# ХРАНИЛИЩЕ ФАЙЛОВ
# ═══════════════════════════════════════

# Тип хранилища: 'local' или 'minio'
STORAGE_TYPE=local

# Путь для локального хранилища
STORAGE_PATH=./storage

# MinIO настройки (если STORAGE_TYPE=minio)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=vertex-ar
MINIO_SECURE=False

# ═══════════════════════════════════════
# БЕЗОПАСНОСТЬ
# ═══════════════════════════════════════

# CORS разрешенные origins (через запятую)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Максимальный размер загружаемого файла (в байтах)
# 52428800 = 50 MB
MAX_UPLOAD_SIZE=52428800

# Максимальный размер изображения (в байтах)
# 10485760 = 10 MB
MAX_IMAGE_SIZE=10485760

# Максимальный размер видео (в байтах)
# 52428800 = 50 MB
MAX_VIDEO_SIZE=52428800

# ═══════════════════════════════════════
# NFT МАРКЕРЫ
# ═══════════════════════════════════════

# DPI для генерации маркеров (72-300)
NFT_MARKER_DPI=150

# Количество уровней пирамиды (1-3)
NFT_MARKER_LEVELS=3

# Плотность признаков: 'low', 'medium', 'high'
NFT_MARKER_FEATURE_DENSITY=medium

# ═══════════════════════════════════════
# ЛОГИРОВАНИЕ
# ═══════════════════════════════════════

# Уровень логирования: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Путь к файлу логов
LOG_FILE=./logs/app.log

# Максимальный размер файла лога (в байтах)
LOG_MAX_SIZE=10485760  # 10 MB

# Количество backup файлов
LOG_BACKUP_COUNT=5

# ═══════════════════════════════════════
# ПРОИЗВОДИТЕЛЬНОСТЬ
# ═══════════════════════════════════════

# Количество worker процессов
WORKERS=4

# Таймаут запроса (в секундах)
REQUEST_TIMEOUT=300

# Размер пула подключений к БД
DB_POOL_SIZE=10

# ═══════════════════════════════════════
# ДОПОЛНИТЕЛЬНО
# ═══════════════════════════════════════

# Включить/выключить документацию API
ENABLE_DOCS=True

# Включить/выключить admin панель
ENABLE_ADMIN=True

# Timezone
TIMEZONE=Europe/Moscow
```

### Генерация секретного ключа

**Linux/macOS:**
```bash
# Используя OpenSSL
openssl rand -hex 32

# Или Python
python -c "import secrets; print(secrets.token_hex(32))"
```

**Windows (PowerShell):**
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Скопируйте сгенерированный ключ в `.env`:
```env
SECRET_KEY=abc123def456...ваш_сгенерированный_ключ...789xyz
```

### Настройка для разработки

```env
DEBUG=True
APP_HOST=127.0.0.1
APP_PORT=8000
BASE_URL=http://localhost:8000
STORAGE_TYPE=local
LOG_LEVEL=DEBUG
ENABLE_DOCS=True
ENABLE_ADMIN=True
```

### Настройка для продакшена

```env
DEBUG=False
APP_HOST=0.0.0.0
APP_PORT=8000
BASE_URL=https://yourdomain.com
STORAGE_TYPE=local  # или minio для масштабирования
LOG_LEVEL=WARNING
ENABLE_DOCS=False  # отключите в продакшене
ENABLE_ADMIN=True
SECRET_KEY=ваш_надежный_секретный_ключ
```

### Валидация конфигурации

Создайте скрипт `validate_config.py`:

```python
#!/usr/bin/env python3
"""Валидация конфигурации"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def validate_config():
    errors = []
    warnings = []

    # Проверка SECRET_KEY
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key or secret_key == 'your-very-secret-key-change-this-in-production':
        errors.append("SECRET_KEY не установлен или используется дефолтное значение!")
    elif len(secret_key) < 32:
        warnings.append("SECRET_KEY слишком короткий (рекомендуется 64+ символов)")

    # Проверка путей
    storage_path = Path(os.getenv('STORAGE_PATH', './storage'))
    if not storage_path.exists():
        errors.append(f"STORAGE_PATH не существует: {storage_path}")

    # Проверка DEBUG в продакшене
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    base_url = os.getenv('BASE_URL', '')
    if debug and 'localhost' not in base_url:
        warnings.append("DEBUG=True в продакшен окружении!")

    # Проверка BASE_URL
    if not base_url:
        errors.append("BASE_URL не установлен!")

    # Вывод результатов
    if errors:
        print("❌ ОШИБКИ:")
        for error in errors:
            print(f"  - {error}")

    if warnings:
        print("⚠️  ПРЕДУПРЕЖДЕНИЯ:")
        for warning in warnings:
            print(f"  - {warning}")

    if not errors and not warnings:
        print("✅ Конфигурация корректна!")

    return len(errors) == 0

if __name__ == '__main__':
    import sys
    sys.exit(0 if validate_config() else 1)
```

Запуск валидации:
```bash
python validate_config.py
```

---

## 🏃 Запуск приложения

### Инициализация базы данных

База данных создается автоматически при первом запуске, но можно инициализировать вручную:

```python
# init_db.py
from pathlib import Path
from main import Database

db = Database(Path('app_data.db'))
print("✅ База данных инициализирована!")
```

Запуск:
```bash
python init_db.py
```

### Режим разработки

#### Вариант 1: Через Uvicorn (Рекомендуется)

```bash
# С auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# С логированием
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level info

# С конкретным количеством workers (для продакшена)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Вариант 2: Через Python

```bash
python main.py
```

#### Вариант 3: С отладчиком

```bash
# В VS Code создайте .vscode/launch.json:
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "main:app",
                "--reload",
                "--host", "0.0.0.0",
                "--port", "8000"
            ],
            "jinja": true,
            "justMyCode": false
        }
    ]
}
```

### Проверка запуска

#### 1. Health Check

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

#### 2. OpenAPI документация

Откройте в браузере:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

#### 3. Админ-панель

Откройте: http://localhost:8000/admin

#### 4. Логи

Проверьте файл логов:
```bash
tail -f logs/app.log
```

### Создание первого администратора

```bash
# Через curl
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "SecurePassword123!"
  }'
```

Или через Python:

```python
# create_admin.py
import requests

response = requests.post(
    'http://localhost:8000/auth/register',
    json={
        'username': 'admin',
        'password': 'SecurePassword123!'
    }
)
print(response.json())
```

Запуск:
```bash
python create_admin.py
```

**Важно:** Первый зарегистрированный пользователь автоматически становится администратором!

### Остановка приложения

**Graceful shutdown:**
```bash
# Нажмите Ctrl+C в терминале где запущен Uvicorn
^C
Shutting down
Waiting for application shutdown.
Application shutdown complete.
```

---

## 🐳 Docker развертывание

### Установка Docker

#### Ubuntu/Debian

```bash
# Удаление старых версий
sudo apt remove docker docker-engine docker.io containerd runc

# Установка зависимостей
sudo apt update
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Добавление Docker GPG ключа
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Добавление репозитория
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установка Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Перелогиньтесь для применения изменений
```

#### macOS

```bash
# Установка Docker Desktop
brew install --cask docker

# Или скачайте с docker.com
```

#### Windows

Скачайте Docker Desktop с https://www.docker.com/products/docker-desktop/

### Проверка Docker

```bash
# Версия Docker
docker --version

# Версия Docker Compose
docker compose version

# Тестовый запуск
docker run hello-world
```

### Сборка образа

```bash
# Вернитесь в корень проекта
cd /path/to/vertex-ar

# Сборка образа
docker build -f Dockerfile.app -t vertex-ar:latest vertex-ar/

# Проверка образа
docker images | grep vertex-ar
```

### Запуск контейнера

#### Базовый запуск

```bash
docker run -d \
  --name vertex-ar \
  -p 8000:8000 \
  -v $(pwd)/vertex-ar/storage:/app/storage \
  -v $(pwd)/vertex-ar/app_data.db:/app/app_data.db \
  -e SECRET_KEY=your-secret-key \
  -e DEBUG=False \
  vertex-ar:latest
```

#### С переменными окружения из файла

```bash
docker run -d \
  --name vertex-ar \
  -p 8000:8000 \
  -v $(pwd)/vertex-ar/storage:/app/storage \
  -v $(pwd)/vertex-ar/app_data.db:/app/app_data.db \
  --env-file vertex-ar/.env \
  vertex-ar:latest
```

### Docker Compose (Рекомендуется)

#### Создание docker-compose.yml

```yaml
version: '3.8'

services:
  vertex-ar:
    build:
      context: ./vertex-ar
      dockerfile: ../Dockerfile.app
    container_name: vertex-ar
    ports:
      - "8000:8000"
    volumes:
      - ./vertex-ar/storage:/app/storage
      - ./vertex-ar/app_data.db:/app/app_data.db
      - ./vertex-ar/logs:/app/logs
    env_file:
      - ./vertex-ar/.env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # MinIO (опционально, для S3-совместимого хранилища)
  minio:
    image: minio/minio:latest
    container_name: vertex-ar-minio
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - ./minio-data:/data
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    restart: unless-stopped

networks:
  default:
    name: vertex-ar-network
```

#### Запуск через Docker Compose

```bash
# Запуск всех сервисов
docker compose up -d

# Просмотр логов
docker compose logs -f

# Просмотр статуса
docker compose ps

# Остановка
docker compose down

# Остановка с удалением volumes
docker compose down -v
```

### Управление контейнерами

```bash
# Просмотр запущенных контейнеров
docker ps

# Просмотр всех контейнеров
docker ps -a

# Просмотр логов
docker logs vertex-ar
docker logs -f vertex-ar  # с follow

# Вход в контейнер
docker exec -it vertex-ar bash

# Остановка контейнера
docker stop vertex-ar

# Запуск контейнера
docker start vertex-ar

# Перезапуск контейнера
docker restart vertex-ar

# Удаление контейнера
docker rm vertex-ar

# Удаление образа
docker rmi vertex-ar:latest
```

---

## 🌐 Продакшен развертывание

### Подготовка сервера

#### Выбор хостинга

**Рекомендуемые провайдеры:**
- **DigitalOcean** - простота использования
- **Linode** - хорошая производительность
- **Hetzner** - доступные цены
- **AWS EC2** - масштабируемость
- **Google Cloud** - надежность

**Минимальная конфигурация VPS:**
- 2 vCPU
- 4 GB RAM
- 50 GB SSD
- Ubuntu 22.04 LTS

#### Первоначальная настройка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка firewall
sudo apt install ufw
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Создание пользователя
sudo adduser vertex
sudo usermod -aG sudo vertex

# Переключение на нового пользователя
su - vertex
```

#### Установка необходимого ПО

```bash
# Python и зависимости
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    build-essential \
    libopencv-dev \
    libmagic1 \
    git \
    nginx \
    supervisor

# Проверка
python3.11 --version
nginx -v
```

### Клонирование и настройка проекта

```bash
# Клонирование
cd /home/vertex
git clone https://github.com/your-org/vertex-ar.git
cd vertex-ar/vertex-ar

# Создание venv
python3.11 -m venv .venv
source .venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt

# Установка Gunicorn для продакшена
pip install gunicorn

# Создание директорий
mkdir -p storage/{ar_content,nft-markers,qr-codes,temp,previews}
mkdir -p logs

# Настройка .env
cp .env.example .env
nano .env  # отредактируйте настройки
```

### Настройка Gunicorn

#### Создание конфигурации

```bash
# /home/vertex/vertex-ar/vertex-ar/gunicorn_config.py
import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 300
keepalive = 5

# Logging
accesslog = "/home/vertex/vertex-ar/vertex-ar/logs/access.log"
errorlog = "/home/vertex/vertex-ar/vertex-ar/logs/error.log"
loglevel = "info"

# Process naming
proc_name = "vertex-ar"

# Server mechanics
daemon = False
pidfile = "/home/vertex/vertex-ar/vertex-ar/gunicorn.pid"
user = "vertex"
group = "vertex"
umask = 0o007
```

#### Тестовый запуск Gunicorn

```bash
gunicorn main:app -c gunicorn_config.py
```

Проверка:
```bash
curl http://127.0.0.1:8000/health
```

### Настройка Supervisor

#### Создание конфигурации

```bash
sudo nano /etc/supervisor/conf.d/vertex-ar.conf
```

Содержимое:
```ini
[program:vertex-ar]
directory=/home/vertex/vertex-ar/vertex-ar
command=/home/vertex/vertex-ar/vertex-ar/.venv/bin/gunicorn main:app -c gunicorn_config.py
user=vertex
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/vertex/vertex-ar/vertex-ar/logs/supervisor.log
environment=PATH="/home/vertex/vertex-ar/vertex-ar/.venv/bin"
```

#### Запуск через Supervisor

```bash
# Перезагрузка конфигурации
sudo supervisorctl reread
sudo supervisorctl update

# Запуск приложения
sudo supervisorctl start vertex-ar

# Проверка статуса
sudo supervisorctl status vertex-ar

# Управление
sudo supervisorctl stop vertex-ar
sudo supervisorctl restart vertex-ar
```

### Настройка Nginx

#### Создание конфигурации

```bash
sudo nano /etc/nginx/sites-available/vertex-ar
```

Содержимое:
```nginx
# Upstream для FastAPI
upstream vertex_ar {
    server 127.0.0.1:8000 fail_timeout=0;
}

# HTTP редирект на HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;

    # Редирект на HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTPS сервер
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL сертификаты (будут добавлены Certbot)
    # ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Logs
    access_log /var/log/nginx/vertex-ar-access.log;
    error_log /var/log/nginx/vertex-ar-error.log;

    # Max upload size
    client_max_body_size 100M;

    # Proxy settings
    location / {
        proxy_pass http://vertex_ar;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Websocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Static files
    location /storage/ {
        alias /home/vertex/vertex-ar/vertex-ar/storage/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /static/ {
        alias /home/vertex/vertex-ar/vertex-ar/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Health check
    location /health {
        proxy_pass http://vertex_ar;
        access_log off;
    }
}
```

#### Активация конфигурации

```bash
# Создание символической ссылки
sudo ln -s /etc/nginx/sites-available/vertex-ar /etc/nginx/sites-enabled/

# Удаление дефолтного сайта
sudo rm /etc/nginx/sites-enabled/default

# Проверка конфигурации
sudo nginx -t

# Перезапуск Nginx
sudo systemctl restart nginx

# Включение автозапуска
sudo systemctl enable nginx
```

---

## 🔐 Настройка HTTPS

### Установка Certbot

```bash
# Ubuntu/Debian
sudo apt install certbot python3-certbot-nginx
```

### Получение SSL сертификата

```bash
# Получение сертификата для домена
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Следуйте инструкциям:
# 1. Введите email
# 2. Согласитесь с условиями
# 3. Выберите редирект HTTP->HTTPS (рекомендуется)
```

### Автоматическое обновление сертификатов

```bash
# Certbot автоматически создает cron задачу
# Проверка:
sudo systemctl status certbot.timer

# Тестовое обновление
sudo certbot renew --dry-run
```

### Проверка SSL

Откройте в браузере:
```
https://yourdomain.com
```

Проверьте сертификат:
- Зеленый замок в адресной строке
- Валидный сертификат от Let's Encrypt

Онлайн проверка:
```
https://www.ssllabs.com/ssltest/analyze.html?d=yourdomain.com
```

---

## 💾 Резервное копирование

### Скрипт backup

Создайте `/home/vertex/backup_vertex_ar.sh`:

```bash
#!/bin/bash

# Конфигурация
BACKUP_DIR="/home/vertex/backups"
PROJECT_DIR="/home/vertex/vertex-ar/vertex-ar"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="vertex-ar-backup-$DATE"

# Создание директории для бэкапов
mkdir -p $BACKUP_DIR

# Создание temporary директории для бэкапа
TEMP_DIR="$BACKUP_DIR/$BACKUP_NAME"
mkdir -p $TEMP_DIR

# Backup базы данных
echo "Backing up database..."
cp $PROJECT_DIR/app_data.db $TEMP_DIR/

# Backup storage
echo "Backing up storage..."
cp -r $PROJECT_DIR/storage $TEMP_DIR/

# Backup .env
echo "Backing up .env..."
cp $PROJECT_DIR/.env $TEMP_DIR/

# Создание архива
echo "Creating archive..."
cd $BACKUP_DIR
tar -czf $BACKUP_NAME.tar.gz $BACKUP_NAME/

# Удаление temporary директории
rm -rf $TEMP_DIR

# Удаление старых бэкапов (старше 30 дней)
find $BACKUP_DIR -name "vertex-ar-backup-*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
```

Установка прав:
```bash
chmod +x /home/vertex/backup_vertex_ar.sh
```

### Автоматические бэкапы

```bash
# Добавление в crontab
crontab -e
```

Добавьте строку (ежедневно в 2:00 AM):
```cron
0 2 * * * /home/vertex/backup_vertex_ar.sh >> /home/vertex/backup.log 2>&1
```

### Восстановление из бэкапа

```bash
# Остановка приложения
sudo supervisorctl stop vertex-ar

# Распаковка бэкапа
cd /home/vertex/backups
tar -xzf vertex-ar-backup-20240115_020000.tar.gz

# Восстановление БД
cp vertex-ar-backup-20240115_020000/app_data.db \
   /home/vertex/vertex-ar/vertex-ar/

# Восстановление storage
rm -rf /home/vertex/vertex-ar/vertex-ar/storage
cp -r vertex-ar-backup-20240115_020000/storage \
   /home/vertex/vertex-ar/vertex-ar/

# Восстановление .env (если нужно)
cp vertex-ar-backup-20240115_020000/.env \
   /home/vertex/vertex-ar/vertex-ar/

# Запуск приложения
sudo supervisorctl start vertex-ar
```

---

## 📊 Мониторинг и обслуживание

### Мониторинг логов

```bash
# Application logs
tail -f /home/vertex/vertex-ar/vertex-ar/logs/app.log

# Nginx access logs
sudo tail -f /var/log/nginx/vertex-ar-access.log

# Nginx error logs
sudo tail -f /var/log/nginx/vertex-ar-error.log

# Supervisor logs
sudo tail -f /home/vertex/vertex-ar/vertex-ar/logs/supervisor.log

# System logs
sudo journalctl -u nginx -f
```

### Мониторинг ресурсов

```bash
# CPU и RAM
htop

# Disk usage
df -h
du -sh /home/vertex/vertex-ar/*

# Процессы
ps aux | grep gunicorn
ps aux | grep nginx

# Network
netstat -tlnp | grep :8000
netstat -tlnp | grep :80
```

### Очистка логов

```bash
# Ротация логов
sudo logrotate -f /etc/logrotate.d/nginx

# Ручная очистка
sudo truncate -s 0 /var/log/nginx/vertex-ar-access.log
truncate -s 0 /home/vertex/vertex-ar/vertex-ar/logs/app.log
```

### Обновление приложения

```bash
# Остановка
sudo supervisorctl stop vertex-ar

# Обновление кода
cd /home/vertex/vertex-ar
git pull origin main

# Активация venv
cd vertex-ar
source .venv/bin/activate

# Обновление зависимостей
pip install -r requirements.txt

# Применение миграций (если есть)
# python migrate.py

# Запуск
sudo supervisorctl start vertex-ar
```

---

## 🔧 Решение проблем

### Приложение не запускается

**Проверка 1: Порт занят**
```bash
sudo lsof -i :8000
# Убейте процесс: sudo kill -9 <PID>
```

**Проверка 2: Права доступа**
```bash
ls -la /home/vertex/vertex-ar/vertex-ar/
# Исправление: sudo chown -R vertex:vertex /home/vertex/vertex-ar/
```

**Проверка 3: Зависимости**
```bash
pip list
# Переустановка: pip install -r requirements.txt --force-reinstall
```

### Ошибки при загрузке файлов

**Проблема: "413 Request Entity Too Large"**

Решение - увеличьте лимит в Nginx:
```nginx
client_max_body_size 100M;
```

Перезапустите Nginx:
```bash
sudo systemctl restart nginx
```

### База данных заблокирована

**Ошибка: "database is locked"**

Решение:
```bash
# Остановите приложение
sudo supervisorctl stop vertex-ar

# Проверьте lock файл
ls -la /home/vertex/vertex-ar/vertex-ar/app_data.db*

# Удалите lock файлы
rm /home/vertex/vertex-ar/vertex-ar/app_data.db-*

# Запустите приложение
sudo supervisorctl start vertex-ar
```

### SSL сертификат не обновляется

```bash
# Проверка статуса
sudo certbot certificates

# Ручное обновление
sudo certbot renew --force-renewal

# Проверка cron/systemd timer
sudo systemctl status certbot.timer
```

---

**Версия документа**: 1.0.0
**Последнее обновление**: 2024
**Проект**: Vertex AR

📧 Поддержка: support@vertex-ar.com
