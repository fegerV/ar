# Развертывание Vertex AR (упрощённая инструкция)

Документ описывает базовый сценарий установки и запуска приложения `vertex-ar` как отдельного сервиса.

---

## Развертывание

Ниже приведён пошаговый план: установка зависимостей, настройка окружения, запуск приложения, конфигурация и рекомендации по эксплуатации.

---

## Установка зависимостей

```bash
cd vertex-ar
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Для работы генератора маркеров требуется пакет `python-magic`. Установите его при необходимости:
```bash
pip install python-magic
```

---

## Настройка окружения

1. Скопируйте файл конфигурации:
   ```bash
   cp .env.example .env
   ```
2. Укажите значения переменных:
   - `SECRET_KEY` — случайная строка для подписи токенов
   - `STORAGE_TYPE=local` или `minio`
   - `BASE_URL=https://your-domain.com`
   - `CORS_ORIGINS=https://your-domain.com`
   - `SESSION_TIMEOUT_MINUTES`, `AUTH_MAX_ATTEMPTS`
   - Параметры MinIO (`MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`)

Создайте директории хранения, если запускаете без Docker:
```bash
mkdir -p storage/ar_content storage/nft-markers storage/qr-codes
mkdir -p static templates
```

---

## Запуск приложения

### Запуск модулем Python
```bash
python -m main
```

### Запуск через Uvicorn
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Приложение будет доступно по адресу `http://localhost:8000`. Swagger доступен по `/docs`, админ-панель — `/admin`.

---

## Docker

```bash
cd ..
docker-compose up --build -d
```

Переменные окружения прокидываются через `.env`. Для продакшена рекомендуется настроить внешний обратный прокси (Nginx) и HTTPS.

---

## Конфигурация

### Основные переменные `.env`
- `STORAGE_TYPE` — режим хранения (`local`, `minio`)
- `MINIO_*` — параметры подключения к MinIO/S3
- `BASE_URL` — базовый URL сервиса
- `CORS_ORIGINS` — список разрешённых доменов
- `SESSION_TIMEOUT_MINUTES` — время жизни токена
- `AUTH_MAX_ATTEMPTS` и `AUTH_LOCKOUT_MINUTES`
- `SENTRY_DSN`, `SENTRY_TRACES_SAMPLE_RATE` (опционально)

### Логи
- Структурированные JSON-логи выводятся в stdout
- Для Docker рекомендуется подключать их к внешнему агрегатору (ELK/Datadog)

---

## Рекомендации для продакшена

- Настройте HTTPS (скрипт `../setup_ssl.sh` или собственная автоматизация)
- Регулярно запускайте `../check_production_readiness.sh`
- Настройте резервное копирование директории `storage/`
- Включите мониторинг запросов и генерации маркеров (`run_performance_tests.sh`)
- Используйте внешнее S3-хранилище и базу данных PostgreSQL (планируется в v1.4)

---

Дополнительные материалы: `../docs/guides/installation.md`, `../SECURITY.md`, `../README.md`.
