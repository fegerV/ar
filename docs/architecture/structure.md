# Структура проекта Vertex AR

**Версия:** 1.4.0
**Дата обновления:** 21 ноября 2024
**После реорганизации:** project-structure-reorganization

Этот документ описывает актуальную структуру проекта Vertex AR после масштабной очистки и консолидации.

---

## 📂 Общая структура

```
vertex-ar/
├── 📄 README.md                         # Главный входной файл проекта
├── 📄 CHANGELOG.md                      # История всех изменений
├── 📄 CONTRIBUTING.md                   # Руководство для контрибьюторов
├── 📄 ROADMAP.md                        # Дорожная карта развития
├── 📄 SECURITY.md                       # Политика безопасности
├── 📄 LICENSE                           # Лицензия MIT
├── 📄 CLEANUP_SUMMARY.md                # Отчёт о недавней очистке проекта
│
├── 📁 docs/                             # 📚 Основная документация
│   ├── README.md                        # Оглавление всей документации
│   ├── api/                             # API документация (3 файла)
│   ├── development/                     # Руководства для разработчиков (3 файла)
│   ├── features/                        # Описание функциональности (2 файла)
│   ├── guides/                          # Руководства пользователей/админов (4 файла)
│   └── releases/                        # История релизов (1 файл)
│
├── 📁 vertex-ar/                        # 🎯 Основное приложение
│   ├── app/                             # Основной код приложения
│   │   ├── __init__.py
│   │   ├── main.py                      # Точка входа FastAPI
│   │   ├── config.py                    # Конфигурация приложения
│   │   ├── models.py                    # SQLAlchemy модели
│   │   ├── database.py                  # Работа с БД
│   │   ├── auth.py                      # Аутентификация
│   │   ├── validators.py                # Валидация данных
│   │   ├── middleware.py                # HTTP middleware
│   │   ├── rate_limiter.py              # Rate limiting
│   │   ├── storage.py                   # Абстракция хранилища
│   │   ├── storage_local.py             # Локальное хранилище
│   │   ├── storage_minio.py             # MinIO/S3 хранилище
│   │   └── api/                         # API роуты
│   │       ├── __init__.py
│   │       ├── admin.py                 # Админ-панель и управление
│   │       ├── ar.py                    # AR-viewer эндпоинты
│   │       ├── auth.py                  # Аутентификация API
│   │       ├── clients.py               # Управление клиентами
│   │       ├── portraits.py             # Управление портретами
│   │       ├── videos.py                # Управление видео
│   │       └── nft_markers.py           # Генерация NFT-маркеров
│   │
│   ├── templates/                       # 🎨 HTML шаблоны (4 файла)
│   │   ├── admin_dashboard.html         # Главная админ-панель
│   │   ├── admin_order_detail.html      # Детали заказа
│   │   ├── ar_page.html                 # AR-viewer
│   │   └── login.html                   # Страница входа
│   │
│   ├── tests/                           # 🧪 Тесты
│   │   ├── __init__.py
│   │   ├── conftest.py                  # Pytest конфигурация
│   │   ├── test_auth.py                 # Тесты аутентификации
│   │   ├── test_clients.py              # Тесты клиентов
│   │   ├── test_portraits.py            # Тесты портретов
│   │   ├── test_videos.py               # Тесты видео
│   │   ├── test_nft_markers.py          # Тесты NFT-маркеров
│   │   ├── test_storage.py              # Тесты хранилища
│   │   └── test_validators.py           # Тесты валидации
│   │
│   ├── nft_marker_generator.py          # Генератор NFT-маркеров
│   ├── preview_generator.py             # Генератор превью
│   ├── notification_handler.py          # Обработка уведомлений
│   ├── notifications.py                 # Система уведомлений
│   ├── file_validator.py                # Валидация файлов
│   ├── logging_setup.py                 # Настройка логирования
│   ├── utils.py                         # Утилиты
│   ├── storage.py                       # Основное хранилище
│   ├── storage_adapter.py               # Адаптер хранилищ
│   ├── storage_local.py                 # Локальное хранилище
│   ├── nft_maker.py                     # NFT Maker утилиты
│   ├── generate-nft.js                  # Node.js генератор NFT
│   │
│   ├── requirements.txt                 # Python зависимости (продакшен)
│   ├── requirements-dev.txt             # Python зависимости (разработка)
│   ├── requirements-simple.txt          # Минимальные зависимости
│   ├── pyproject.toml                   # Python проект конфигурация
│   │
│   ├── .env.example                     # Пример конфигурации
│   ├── .env.production.example          # Пример продакшен конфигурации
│   ├── .pre-commit-config.yaml          # Pre-commit hooks
│   │
│   ├── Dockerfile.nft-maker             # Docker для NFT maker
│   ├── Makefile                         # Make команды
│   ├── start.sh                         # Скрипт запуска
│   ├── build-nft-maker.sh               # Сборка NFT maker
│   ├── deploy.sh                        # Скрипт деплоя
│   │
│   ├── CHANGELOG.md                     # История изменений модуля
│   ├── README.md                        # README модуля
│   ├── NFT_GENERATOR_README.md          # Документация NFT генератора
│   ├── PORTRAITS_FEATURE.md             # Документация функции портретов
│   └── production_setup.md              # Настройка продакшена
│
├── 📁 test_files/                       # 🧪 Интеграционные и производительные тесты
│   ├── test_api_endpoints.py            # Тесты API эндпоинтов
│   ├── test_admin_panel.py              # Тесты админ-панели
│   ├── test_ar_functionality.py         # Тесты AR функциональности
│   ├── test_performance.py              # Тесты производительности
│   ├── test_comprehensive_performance.py # Комплексные тесты производительности
│   ├── test_security.py                 # Тесты безопасности
│   ├── run_tests.sh                     # Скрипт запуска тестов
│   ├── run_performance_tests.sh         # Скрипт производительных тестов
│   └── ...
│
├── 📁 scripts/                          # 🔧 Скрипты автоматизации
│   ├── backup.sh                        # Скрипт бэкапа
│   ├── check_deployment_readiness.sh    # Проверка готовности к деплою
│   ├── check_production_readiness.sh    # Проверка готовности к продакшену
│   ├── deploy-simplified.sh             # Упрощенный скрипт деплоя
│   ├── install_ubuntu.sh                # Установка Ubuntu
│   ├── quick_install.sh                 # Быстрая установка
│   ├── quick_test.sh                    # Быстрый запуск тестов
│   ├── run_performance_tests.sh         # Производительные тесты
│   ├── setup_local_ssl.sh               # Настройка локального SSL
│   └── setup_ssl.sh                     # Настройка SSL
│
├── 📁 storage/                          # 💾 Локальное хранилище
│   ├── portraits/                       # Загруженные портреты
│   ├── videos/                          # Загруженные видео
│   ├── nft_markers/                     # Сгенерированные NFT-маркеры
│   ├── nft_cache/                       # Кэш анализа изображений
│   └── qr_codes/                        # Сгенерированные QR-коды
│
├── 📁 app_data/                         # 🗄️ Данные приложения
│   └── vertex.db                        # SQLite база данных
│
├── 📁 .github/                          # ⚙️ GitHub конфигурация
│   └── workflows/                       # GitHub Actions
│       ├── ci.yml                       # CI pipeline
│       └── tests.yml                    # Автотесты
│
├── 📁 .vscode/                          # VS Code настройки
├── 📁 .venv/                            # Python виртуальное окружение
│
├── 📄 .env.example                      # Пример переменных окружения
├── 📄 .gitignore                        # Git ignore правила
├── 📄 Dockerfile.app                    # Docker для приложения
├── 📄 docker-compose.yml                # Docker Compose конфигурация
├── 📄 Makefile                          # Make команды
│
├── 📄 ARCHITECTURE_OVERVIEW.md          # Обзор архитектуры проекта
├── 📄 IMPLEMENTATION_STATUS.md          # Статус реализации функций
├── 📄 SSL_INSTALLATION_GUIDE.md         # Руководство по установке SSL
│
├── 📄 QUICK_START_RU.md                 # 🚀 Быстрый старт (5 минут)
├── 📄 LOCAL_TESTING_GUIDE.md            # 📘 Полное руководство по тестированию
├── 📄 TESTING_SCENARIOS.md              # 🎯 Готовые тестовые сценарии
├── 📄 TESTING_README.md                 # 📖 Основное руководство по тестам
├── 📄 TESTING_REPORT.md                 # 📊 Отчёт о покрытии тестами
├── 📄 IDE_TESTING_SETUP.md              # 🛠️ Настройка IDE для тестирования
│
├── 📄 test_ui_improvements.py           # Тесты UI улучшений
├── 📄 test_enhanced_admin.py            # Тесты админ-панели
├── 📄 locustfile.py                     # Конфигурация нагрузочных тестов
└── 📄 pytest.ini                        # Pytest конфигурация
```

---

## 📚 Навигация по документации

### Для новичков
1. Начните с **README.md** в корне проекта
2. Прочитайте **QUICK_START_RU.md** для быстрого старта за 5 минут
3. Изучите **docs/README.md** для навигации по всей документации

### Для разработчиков
1. **docs/development/setup.md** - настройка среды разработки
2. **docs/development/architecture.md** - архитектура системы
3. **docs/development/testing.md** - стратегия тестирования
4. **TESTING_README.md** - полное руководство по тестам
5. **IDE_TESTING_SETUP.md** - настройка вашей IDE

### Для администраторов
1. **docs/guides/installation.md** - установка и развёртывание
2. **docs/guides/admin-guide.md** - администрирование системы
3. **SSL_INSTALLATION_GUIDE.md** - настройка HTTPS
4. **SECURITY.md** - политика безопасности

### Для пользователей API
1. **docs/api/README.md** - обзор API
2. **docs/api/endpoints.md** - справочник эндпоинтов
3. **docs/api/examples.md** - примеры использования

---

## 🎯 Ключевые компоненты

### Backend (FastAPI)
- **Точка входа:** `vertex-ar/app/main.py`
- **API роуты:** `vertex-ar/app/api/`
- **Модели данных:** `vertex-ar/app/models.py`
- **База данных:** `vertex-ar/app/database.py`

### Frontend (HTML/JS)
- **Шаблоны:** `vertex-ar/templates/`
- **Админ-панель:** `admin_dashboard.html`, `admin_order_detail.html`
- **AR-viewer:** `ar_page.html`

### Хранилище
- **Абстракция:** `vertex-ar/app/storage.py`
- **Локальное:** `vertex-ar/app/storage_local.py`
- **MinIO/S3:** `vertex-ar/app/storage_minio.py`

### NFT Маркеры
- **Генератор:** `vertex-ar/nft_marker_generator.py`
- **NFT Maker:** `vertex-ar/nft_maker.py`
- **JS генератор:** `vertex-ar/generate-nft.js`

### Тестирование
- **Unit тесты:** `vertex-ar/tests/` — быстрые, изолированные тесты
- **Интеграционные:** `test_files/test_*.py` — полные сценарии API, админ-панели, AR
- **Производительность:** `test_files/run_performance_tests.sh` — нагрузочные тесты
- **Готовность:** `scripts/check_production_readiness.sh` — проверка готовности к продакшену

---

## 🔧 Основные команды

### Разработка
```bash
# Запуск приложения
cd vertex-ar
uvicorn app.main:app --reload

# Запуск всех тестов
pytest

# Unit тесты
pytest vertex-ar/tests/

# Интеграционные тесты
pytest test_files/ -k "not performance"

# Быстрые тесты
./scripts/quick_test.sh quick

# Проверка типов
mypy vertex-ar/

# Линтер
flake8 vertex-ar/

# Форматирование
black vertex-ar/
```

### Docker
```bash
# Сборка и запуск
docker-compose up --build

# Только сборка
docker-compose build

# Остановка
docker-compose down
```

### Production
```bash
# Проверка готовности
./scripts/check_production_readiness.sh

# Производительные тесты
cd test_files && ./run_performance_tests.sh

# Деплой
cd vertex-ar && ./deploy.sh
```

---

## 📊 Статистика проекта

### Код
- Python файлов: **85** (без .venv)
- HTML шаблонов: **4** (активных)
- Тестов: **31** автоматизированный
- Строк кода: **~15,000** (без комментариев)

### Документация
- Markdown файлов: **28** (14 в корне + 14 в docs/)
- Руководств: **13**
- API эндпоинтов задокументировано: **50+**

### Покрытие
- Покрытие тестами: **78%**
- Реализованных функций: **107 из 122** (88%)
- Готовность к продакшену: **97%**

---

## 🗂️ Изменения после очистки

### Удалено (15 ноября 2024)
- ❌ 33 неиспользуемых файла
- ❌ 17 временных отчётов
- ❌ 8 дублирующихся руководств
- ❌ 4 устаревших Python файла
- ❌ 4 неиспользуемых HTML шаблона

### Результат
- ✅ Уменьшение .md файлов в корне на **63%** (38 → 14)
- ✅ Консолидация документации
- ✅ Упрощение навигации
- ✅ Улучшение читаемости

Подробный отчёт: **CLEANUP_SUMMARY.md**

---

## 🔗 Полезные ссылки

- **Главный README:** [README.md](README.md)
- **Документация:** [docs/README.md](docs/README.md)
- **История изменений:** [CHANGELOG.md](CHANGELOG.md)
- **Дорожная карта:** [ROADMAP.md](ROADMAP.md)
- **Архитектура:** [ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md)
- **Отчёт об очистке:** [CLEANUP_SUMMARY.md](CLEANUP_SUMMARY.md)

---

**Последнее обновление:** 15 ноября 2024
**Ветка:** cleanup-remove-unused-files-update-docs
**Версия:** 1.3.1
