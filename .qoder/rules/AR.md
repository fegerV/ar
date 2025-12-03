---
trigger: manual
---
# Vertex AR - Правила для Qoder
Ход процесса всегда пиши на русском языке
## Обзор проекта
Vertex AR - веб-приложение для создания и управления AR-контентом на базе AR.js NFT. FastAPI backend, SQLite/PostgreSQL, Docker-ready, готовность к продакшену 98%.

## Технологический стек
- **Backend**: Python 3.10+, FastAPI, SQLAlchemy, Pydantic v2
- **Frontend**: Jinja2, A-Frame, AR.js, Anime.js, Bootstrap
- **Storage**: SQLite (dev), PostgreSQL (prod), MinIO/S3/Yandex Disk
- **Infrastructure**: Docker Compose, Nginx, Uvicorn, Supervisor
- **Testing**: pytest, pytest-cov (80% покрытие)

## Структура проекта
vertex-ar/
├── app/ # Основной код приложения
├── templates/ # HTML шаблоны Jinja2
├── tests/ # Unit тесты
test_files/ # Интеграционные тесты
docs/ # Документация
scripts/ # Автоматизация
storage/ # Локальное хранилище

text

## Стандарты кода

### Python
- **Стиль**: PEP 8, Black (120 символов)
- **Typing**: обязательные type hints для всех функций
- **Async**: используйте async/await для I/O операций
- **Логирование**: structlog с JSON-форматом
- **Исключения**: явная обработка с контекстными сообщениями

### Архитектурные паттерны
- **Слои**: routes → services → repositories → models
- **Dependency Injection**: FastAPI Depends для всех зависимостей
- **Schemas**: Pydantic BaseModel для валидации (v2 синтаксис)
- **Database**: SQLAlchemy ORM, session per request
- **Storage**: абстрактный интерфейс `StorageInterface` для всех провайдеров

### Безопасность
- JWT токены для аутентификации (Bearer схема)
- Rate limiting на критичные эндпоинты
- Валидация всех входных данных через Pydantic
- CORS настраивается через `.env`
- Блокировка аккаунтов после многократных неудачных попыток входа

## Ключевые компоненты

### API Endpoints
- `/auth/*` - регистрация, вход, токены
- `/api/companies/*` - управление компаниями и категориями
- `/api/clients/*` - CRUD клиентов
- `/api/portraits/*` - загрузка портретов
- `/api/videos/*` - управление видео
- `/api/nft-markers/*` - генерация NFT маркеров
- `/qr/*`, `/ar/*` - публичный AR viewer

### Storage Providers
- `local_disk` - локальное хранилище (по умолчанию)
- `yandex_disk` - Яндекс.Диск через WebDAV
- `minio` / `s3` - MinIO или Amazon S3

### Особенности архитектуры
- Централизованная валидация через `app/validation.py`
- Request ID трассировка во всех логах
- Автоматический расчёт Uvicorn воркеров по CPU
- Динамическое разрешение DNS в Nginx (исправлен restart loop)

## Процессы разработки

### Новый код
1. Создавайте фичу-бранч от `main`
2. Пишите тесты перед реализацией (TDD предпочтительно)
3. Обновляйте `docs/` если меняется API или архитектура
4. Запускайте `./scripts/quick_test.sh` перед коммитом
5. Проверяйте покрытие: `pytest --cov=vertex-ar`

### Коммиты
**Формат**: `type(scope): краткое описание`
- `feat` - новая функциональность
- `fix` - исправление бага
- `refactor` - рефакторинг без изменения функциональности
- `docs` - изменения в документации
- `test` - добавление/изменение тестов
- `chore` - инфраструктурные изменения

**Примеры**:
feat(storage): add Google Drive provider support
fix(nginx): resolve restart loop with dynamic DNS resolution
refactor(auth): extract token validation to separate service
docs(api): update endpoints documentation for v1.5

text

### Pull Requests
- Название PR должно следовать формату коммитов
- Описание должно включать:
  - Что изменилось и почему
  - Ссылки на связанные issues
  - Инструкции по тестированию
  - Breaking changes (если есть)

## Тестирование

### Запуск тестов
Быстрая демонстрация
./scripts/quick_test.sh demo

Все тесты
pytest

С покрытием
pytest --cov=vertex-ar --cov-report=term-missing

Производительность
./test_files/run_performance_tests.sh

text

### Требования к тестам
- Минимум 80% code coverage для нового кода
- Unit тесты в `vertex-ar/tests/`
- Интеграционные тесты в `test_files/`
- Используйте фикстуры для тестовых данных
- Моки для внешних сервисов (S3, email, etc.)

### Тестовые данные
- Админ по умолчанию: `superar` / `ffE48f0ns@HQ`
- Компания по умолчанию: "Vertex AR" (создаётся автоматически)
- Тестовые файлы в `test_files/test_data/`

## Развёртывание

### Docker Development
docker-compose up --build

App: http://localhost:8000
Docs: http://localhost:8000/docs
Admin: http://localhost:8000/admin
text

### Production Checklist
1. Настроить переменные в `.env` (SECRET_KEY, DATABASE_URL, CORS)
2. Включить HTTPS через `setup_ssl_local.conf` или Let's Encrypt
3. Настроить backup провайдеры для компаний
4. Проверить логирование и мониторинг
5. Запустить `scripts/check_production_readiness.sh`

### Мониторинг
- Логи: JSON-формат, request tracing
- Метрики: встроенные в API responses
- Health check: `/health` endpoint
- Готовность к интеграции с Prometheus/Grafana

## Документация

### Обязательно обновлять
- `README.md` - при изменении функциональности
- `docs/api/endpoints.md` - новые/изменённые API endpoints
- `docs/releases/changelog.md` - все изменения
- `docs/development/architecture.md` - архитектурные изменения

### Стиль документации
- Markdown с корректным форматированием
- Примеры кода с синтаксической подсветкой
- Скриншоты для UI изменений
- Ссылки на связанные документы

## Частые задачи

### Добавление нового storage provider
1. Реализуйте `StorageInterface` в `app/storage/`
2. Добавьте конфигурацию в `.env.example`
3. Обновите `docs/features/storage-implementation.md`
4. Напишите тесты в `test_files/test_storage_*.py`

### Новый API endpoint
1. Создайте схемы в `app/schemas/`
2. Реализуйте роутер в `app/api/v1/`
3. Добавьте сервисную логику в `app/services/`
4. Обновите `docs/api/endpoints.md`
5. Добавьте тесты в `test_files/test_api_*.py`

### Миграция базы данных
1. Используйте Alembic для миграций
2. Создайте резервную копию перед применением
3. Тестируйте на копии production данных
4. Документируйте в `docs/releases/changelog.md`

## Приоритеты и ограничения

### Текущие приоритеты (Q1 2025)
1. PostgreSQL миграция и асинхронное хранилище
2. Расширенная аналитика и dashboard
3. Mobile API оптимизация
4. Интеграция с новыми AR платформами

### Технический долг
- ⚠️ Nginx restart loop исправлен (Jan 2025)
- ⚠️ Видео расписание - проверить ротацию архива
- ⚠️ MinIO remote storage - финальное тестирование
- ℹ️ PostgreSQL миграция - в планах v1.4

### Не делать
- ❌ Не коммитьте credentials в `.env` (используйте `.env.example`)
- ❌ Не пушьте в `main` напрямую (только через PR)
- ❌ Не снижайте test coverage ниже 80%
- ❌ Не игнорируйте линтер warnings (Black, flake8)

## Полезные ссылки
- Документация: `docs/README.md`
- API Reference: `http://localhost:8000/docs`
- GitHub: https://github.com/fegerV/AR
- Roadmap: `docs/releases/roadmap.md`
- Troubleshooting: `docs/guides/troubleshooting.md`

## Контакты
- Issues/Bugs: GitHub Issues
- Вопросы по разработке: README Contributors section