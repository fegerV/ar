# Vertex AR - Architecture Documentation

## Оглавление

1. [Введение](#введение)
2. [Общая архитектура](#общая-архитектура)
3. [Компоненты системы](#компоненты-системы)
4. [Схема базы данных](#схема-базы-данных)
5. [Поток данных](#поток-данных)
6. [Модули и их взаимодействие](#модули-и-их-взаимодействие)
7. [Технологический стек](#технологический-стек)
8. [Безопасность](#безопасность)
9. [Масштабируемость](#масштабируемость)
10. [Развертывание](#развертывание)

---

## Введение

Vertex AR - это веб-приложение для создания дополненной реальности (AR) из статичных портретов. Архитектура построена на принципах простоты, модульности и эффективности.

### Ключевые принципы

- **Простота**: Минимум зависимостей, понятная структура
- **Модульность**: Четкое разделение ответственности
- **Производительность**: Оптимизированная обработка файлов
- **Безопасность**: Token-based аутентификация, валидация входных данных

---

## Общая архитектура

### High-Level Architecture

```
┌─────────────────┐
│   Web Browser   │ (User Interface)
│  (A-Frame + AR) │
└────────┬────────┘
         │
         │ HTTP/HTTPS
         ▼
┌─────────────────────────────────────┐
│         FastAPI Application         │
│  ┌─────────────────────────────┐   │
│  │   API Endpoints             │   │
│  │  • Auth                     │   │
│  │  • AR Upload/View           │   │
│  │  • Admin Panel              │   │
│  └──────────┬──────────────────┘   │
│             │                       │
│  ┌──────────┴──────────────────┐   │
│  │   Business Logic Modules    │   │
│  │  • NFT Marker Generator     │   │
│  │  • File Validator           │   │
│  │  • Preview Generator        │   │
│  │  • Notification Handler     │   │
│  └──────────┬──────────────────┘   │
│             │                       │
│  ┌──────────┴──────────────────┐   │
│  │   Data Access Layer         │   │
│  │  • Database (SQLite)        │   │
│  │  • Storage (Local/MinIO)    │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
         │                  │
         │                  │
         ▼                  ▼
┌────────────┐      ┌──────────────┐
│   SQLite   │      │ File Storage │
│  Database  │      │   (Local)    │
└────────────┘      └──────────────┘
```

---

## Компоненты системы

### 1. Frontend Components

#### AR Viewer (A-Frame + AR.js)
- **Назначение**: Отображение AR контента в браузере
- **Технологии**: A-Frame, AR.js, Anime.js
- **Функции**:
  - Распознавание NFT маркеров
  - Наложение видео на изображение
  - Анимации (моргание, улыбка, поворот головы)
  - Адаптивный дизайн для мобильных устройств

#### Admin Panel
- **Назначение**: Управление контентом и пользователями
- **Технологии**: HTML, Jinja2 Templates, JavaScript
- **Функции**:
  - Загрузка изображений и видео
  - Просмотр списка AR контента
  - Статистика и аналитика
  - Управление пользователями

### 2. Backend Components

#### Main Application (main.py)
- **Назначение**: Основное FastAPI приложение
- **Ответственность**:
  - Routing и обработка HTTP запросов
  - Middleware (CORS, authentication)
  - Статические файлы и шаблоны
  - Координация между модулями

**Основные классы:**

```python
class Database:
    """Управление SQLite базой данных"""
    - create_user()
    - get_user()
    - create_ar_content()
    - get_ar_content()
    - list_ar_content()

class TokenManager:
    """Управление токенами аутентификации"""
    - issue_token()
    - verify_token()
    - revoke_token()
```

#### Authentication Module (auth.py)
- **Назначение**: Аутентификация и авторизация
- **Функции**:
  - Хеширование паролей (bcrypt)
  - Генерация JWT токенов
  - Валидация токенов
  - Проверка прав доступа

#### NFT Marker Generator (nft_marker_generator.py)
- **Назначение**: Генерация AR маркеров из изображений
- **Процесс**:
  1. Загрузка изображения
  2. Извлечение feature points (SIFT/ORB)
  3. Генерация .fset, .fset3, .iset файлов
  4. Оптимизация для AR.js

**Конфигурация:**
```python
class NFTMarkerConfig:
    feature_density: str  # "low", "medium", "high"
    levels: int          # Number of pyramid levels (1-3)
    dpi: int            # Target DPI (72-300)
```

#### File Validator (file_validator.py)
- **Назначение**: Валидация загружаемых файлов
- **Проверки**:
  - Тип файла (MIME type)
  - Размер файла
  - Формат и структура
  - Безопасность (magic bytes)

#### Storage Module (storage.py, storage_local.py)
- **Назначение**: Абстракция для работы с файловым хранилищем
- **Поддержка**:
  - Локальное хранилище
  - MinIO (S3-compatible)
- **Операции**:
  - Сохранение файлов
  - Получение файлов
  - Удаление файлов
  - Генерация URL

#### Preview Generator (preview_generator.py)
- **Назначение**: Генерация превью для изображений и видео
- **Функции**:
  - Создание thumbnail изображений
  - Извлечение frame из видео
  - Оптимизация размеров

#### Notification Handler (notification_handler.py)
- **Назначение**: Система уведомлений
- **Типы уведомлений**:
  - Email уведомления
  - Webhook callbacks
  - Internal events

### 3. Data Layer

#### Database (SQLite)
- **Назначение**: Хранение структурированных данных
- **Особенности**:
  - Встроенная база данных (no server)
  - Thread-safe операции
  - Простое развертывание
  - Поддержка миграций

#### File Storage
- **Назначение**: Хранение медиа файлов
- **Структура**:
```
storage/
├── ar_content/
│   └── {username}/
│       └── {content_id}/
│           ├── {content_id}.jpg    # Original image
│           ├── {content_id}.mp4    # Original video
│           └── preview.jpg         # Thumbnail
├── nft-markers/
│   └── {content_id}/
│       ├── marker.fset             # Feature set
│       ├── marker.fset3            # Feature set 3 levels
│       └── marker.iset             # Image set
└── qr-codes/
    └── {content_id}.png            # QR code
```

---

## Схема базы данных

### Entity-Relationship Diagram

```
┌──────────────────┐
│      users       │
├──────────────────┤
│ username (PK)    │───┐
│ hashed_password  │   │
│ is_admin         │   │
└──────────────────┘   │
                       │ 1:N
                       │
                       ▼
             ┌──────────────────┐
             │   ar_content     │
             ├──────────────────┤
             │ id (PK)          │
             │ username (FK)    │
             │ image_path       │
             │ video_path       │
             │ marker_fset      │
             │ marker_fset3     │
             │ marker_iset      │
             │ ar_url           │
             │ qr_code          │
             │ created_at       │
             └──────────────────┘
```

### Таблица: users

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| username | TEXT | PRIMARY KEY, NOT NULL | Уникальное имя пользователя |
| hashed_password | TEXT | NOT NULL | Хешированный пароль (bcrypt) |
| is_admin | INTEGER | NOT NULL, DEFAULT 0 | Флаг администратора (0/1) |

**Индексы:**
- PRIMARY KEY on `username`

### Таблица: ar_content

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | TEXT | PRIMARY KEY, NOT NULL | UUID контента |
| username | TEXT | NOT NULL, FOREIGN KEY | Владелец контента |
| image_path | TEXT | NOT NULL | Путь к изображению |
| video_path | TEXT | NOT NULL | Путь к видео |
| marker_fset | TEXT | NOT NULL | Путь к .fset файлу |
| marker_fset3 | TEXT | NOT NULL | Путь к .fset3 файлу |
| marker_iset | TEXT | NOT NULL | Путь к .iset файлу |
| ar_url | TEXT | NOT NULL | URL для просмотра AR |
| qr_code | TEXT | NULLABLE | QR-код (base64) |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Дата создания |

**Индексы:**
- PRIMARY KEY on `id`
- FOREIGN KEY on `username` references `users(username)`
- INDEX on `created_at` для сортировки

---

## Поток данных

### 1. Загрузка AR контента

```
User → [Upload Form] → FastAPI → [File Validation]
                                         │
                                         ▼
                                  [Save to Storage]
                                         │
                                         ▼
                              [NFT Marker Generation]
                                         │
                                         ▼
                                  [QR Code Generation]
                                         │
                                         ▼
                                [Database Insert]
                                         │
                                         ▼
                                    [Response]
```

**Детальные шаги:**

1. **Прием файлов** (FastAPI)
   - Проверка аутентификации
   - Проверка прав (admin only)
   - Валидация Content-Type

2. **Валидация файлов** (file_validator.py)
   - Проверка MIME type
   - Проверка размера файла
   - Проверка формата

3. **Сохранение файлов** (storage.py)
   - Генерация UUID
   - Создание директорий
   - Сохранение image и video

4. **Генерация NFT маркеров** (nft_marker_generator.py)
   - Обработка изображения
   - Извлечение features
   - Создание .fset, .fset3, .iset

5. **Генерация QR-кода** (qrcode library)
   - Создание QR с AR URL
   - Конвертация в base64

6. **Сохранение в БД** (database.py)
   - Создание записи ar_content
   - Commit транзакции

7. **Возврат ответа**
   - ARContentResponse с metadata

### 2. Просмотр AR контента

```
User → [Scan QR/Click Link] → FastAPI → [Get AR Content]
                                             │
                                             ▼
                                      [Load Template]
                                             │
                                             ▼
                                    [Render HTML + AR.js]
                                             │
                                             ▼
                                        [Browser]
                                             │
                                             ▼
                                   [AR.js Load Markers]
                                             │
                                             ▼
                                    [Camera Detection]
                                             │
                                             ▼
                                     [Play Video]
```

### 3. Аутентификация

```
User → [Login Form] → FastAPI → [Verify Credentials]
                                       │
                                       ▼
                                [Hash Password]
                                       │
                                       ▼
                                [Compare Hashes]
                                       │
                                       ▼
                                [Generate Token]
                                       │
                                       ▼
                               [Store in TokenManager]
                                       │
                                       ▼
                                 [Return Token]
```

---

## Модули и их взаимодействие

### Dependency Graph

```
main.py
├── auth.py
│   └── passlib (bcrypt)
├── database.py
│   └── sqlite3
├── file_validator.py
│   ├── python-magic
│   └── pathlib
├── nft_marker_generator.py
│   ├── opencv-python
│   ├── numpy
│   └── pillow
├── storage.py / storage_local.py
│   └── minio (optional)
├── preview_generator.py
│   ├── pillow
│   └── opencv-python
├── notification_handler.py
│   └── requests
└── utils.py
```

### Module Communication

```
┌─────────────┐
│   main.py   │
└──────┬──────┘
       │
       ├──────────────┐
       │              │
       ▼              ▼
┌──────────┐   ┌──────────────┐
│ auth.py  │   │ database.py  │
└──────────┘   └──────────────┘
       │              ▲
       │              │
       ▼              │
┌─────────────────────┴────┐
│ nft_marker_generator.py  │
└──────────┬───────────────┘
           │
           ▼
┌─────────────────────┐
│   storage.py        │
└─────────────────────┘
```

---

## Технологический стек

### Backend

| Компонент | Технология | Версия | Назначение |
|-----------|-----------|--------|------------|
| Web Framework | FastAPI | 0.104+ | REST API, routing |
| Web Server | Uvicorn | 0.24+ | ASGI server |
| Database | SQLite | 3.x | Data persistence |
| ORM | SQLAlchemy | 2.x | Database abstraction |
| Authentication | python-jose | 3.x | JWT tokens |
| Password Hashing | passlib (bcrypt) | 1.7+ | Secure password storage |
| File Storage | MinIO | 7.x | S3-compatible storage |
| Image Processing | Pillow | 10.x | Image manipulation |
| Computer Vision | OpenCV | 4.x | Feature extraction |
| QR Codes | qrcode | 7.x | QR code generation |

### Frontend

| Компонент | Технология | Версия | Назначение |
|-----------|-----------|--------|------------|
| AR Framework | A-Frame | 1.4+ | WebXR/WebVR |
| AR Tracking | AR.js | 3.4+ | Marker tracking |
| Animation | Anime.js | 3.2+ | Smooth animations |
| Templates | Jinja2 | 3.x | Server-side rendering |

### Development Tools

| Tool | Назначение |
|------|------------|
| pytest | Unit testing |
| flake8 | Code linting |
| mypy | Type checking |
| black | Code formatting |
| Docker | Containerization |

---

## Безопасность

### Authentication & Authorization

#### Token-Based Authentication
- **Механизм**: Bearer tokens (in-memory)
- **Генерация**: Secure random tokens (secrets.token_urlsafe)
- **Хранение**: In-memory dictionary (не персистентные)
- **Lifetime**: До logout или restart

#### Password Security
- **Хеширование**: bcrypt (passlib)
- **Salt**: Автоматический (bcrypt)
- **Rounds**: 12 (default)

### Input Validation

```python
# File type validation
def validate_file_type(file: UploadFile):
    allowed_types = {
        "image": ["image/jpeg", "image/png"],
        "video": ["video/mp4", "video/webm"]
    }
    # Check MIME type
    # Check magic bytes
    # Check file extension
```

### File Upload Security

1. **MIME Type Validation**: Проверка Content-Type
2. **Magic Bytes**: Проверка реальной сигнатуры файла
3. **Size Limits**: 
   - Images: 10 MB
   - Videos: 50 MB
4. **Extension Whitelist**: Только разрешенные расширения
5. **Path Sanitization**: Предотвращение path traversal

### SQL Injection Prevention
- **Parameterized Queries**: Все SQL запросы используют параметры
- **SQLAlchemy ORM**: Автоматическое escaping

### XSS Prevention
- **Template Escaping**: Jinja2 автоматический escaping
- **Content-Type Headers**: Правильные MIME types

---

## Масштабируемость

### Current Architecture

**Ограничения:**
- SQLite (single-file database)
- In-memory tokens (не распределенные)
- Local file storage

**Подходит для:**
- Малые и средние нагрузки (< 1000 users)
- Одиночный сервер
- Proof of concept, MVP

### Scaling Strategies

#### Horizontal Scaling

**Необходимые изменения:**

1. **Database Migration**
   - SQLite → PostgreSQL
   - Поддержка concurrent connections
   - Connection pooling

2. **Token Storage**
   - In-memory → Redis
   - Distributed token management
   - Session sharing across instances

3. **File Storage**
   - Local → S3/MinIO cluster
   - CDN для статики
   - Distributed uploads

4. **Load Balancing**
   ```
   [Load Balancer (nginx)]
            │
            ├─── [FastAPI Instance 1]
            ├─── [FastAPI Instance 2]
            └─── [FastAPI Instance N]
            │
            ├─── [PostgreSQL]
            ├─── [Redis]
            └─── [S3/MinIO]
   ```

#### Vertical Scaling

- Увеличение CPU для NFT marker generation
- Больше RAM для caching
- Faster storage (SSD/NVMe)

#### Caching Strategy

```python
# Redis caching
cache_layers = {
    "ar_content": "1 hour",
    "nft_markers": "24 hours",
    "user_sessions": "30 minutes"
}
```

#### Background Jobs

```python
# Celery для async tasks
tasks = {
    "nft_marker_generation": "async",
    "video_transcoding": "async",
    "preview_generation": "async",
    "notification_sending": "async"
}
```

---

## Развертывание

### Development Environment

```bash
# Local setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python vertex-ar/main.py
```

### Production Deployment (Docker)

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./storage:/app/storage
    environment:
      - DATABASE_URL=sqlite:///app_data.db
      
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
```

### Deployment Checklist

- [ ] Обновить requirements.txt
- [ ] Настроить переменные окружения (.env)
- [ ] Настроить SSL/TLS сертификаты
- [ ] Настроить backup базы данных
- [ ] Настроить логирование
- [ ] Настроить мониторинг
- [ ] Провести нагрузочное тестирование
- [ ] Настроить CI/CD pipeline

---

## Мониторинг и Логирование

### Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
```

### Metrics

**Ключевые метрики:**
- Request rate (req/sec)
- Response time (ms)
- Error rate (%)
- File upload size/time
- NFT generation time
- Database query time

### Health Checks

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": VERSION,
        "database": check_database(),
        "storage": check_storage()
    }
```

---

## Будущие улучшения

### Short-term (1-3 months)
- [ ] Миграция на PostgreSQL
- [ ] Redis для token storage
- [ ] Background job processing (Celery)
- [ ] Advanced caching
- [ ] Rate limiting

### Mid-term (3-6 months)
- [ ] Microservices architecture
- [ ] GraphQL API
- [ ] WebSocket support (real-time updates)
- [ ] Advanced analytics
- [ ] Mobile app (React Native/Flutter)

### Long-term (6-12 months)
- [ ] AI-powered features
- [ ] Multi-tenant support
- [ ] White-label solution
- [ ] Enterprise features
- [ ] Global CDN

---

**Версия документации:** 1.1.0  
**Последнее обновление:** 2024-11-07
