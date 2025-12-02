# Deployment Quick Start - После Nginx Bugfix

Этот документ описывает быстрый деплой Vertex AR с исправленной конфигурацией nginx.

## Предварительные требования

- Docker и Docker Compose установлены
- Доступ к серверу (SSH)
- Порты 80 и 443 открыты в файерволе
- (Опционально) SSL сертификаты для HTTPS

## Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/fegerV/ar.git vertex-ar
cd vertex-ar
git checkout bugfix/docker-nginx-restart-loop
```

### 2. Настройка окружения

```bash
# Копируем шаблон .env
cp .env.example .env

# Редактируем .env (минимальные настройки)
nano .env
```

Обязательно установите:
```bash
# Безопасность
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<strong-password>
SECRET_KEY=<random-64-char-string>

# Приложение
BASE_URL=http://your-domain.com
CORS_ORIGINS=http://your-domain.com,https://your-domain.com

# База данных (по умолчанию SQLite, можно оставить)
DATABASE_URL=sqlite:///./app_data.db
```

### 3. Проверка конфигурации nginx

```bash
# Проверка синтаксиса
docker run --rm \
  -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro \
  nginx:alpine nginx -t

# Вывод должен быть:
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 4. Запуск приложения

```bash
# Сборка и запуск контейнеров
docker compose up -d --build

# Проверка статуса
docker compose ps

# Вывод должен показать:
# NAME                              STATUS
# vertex_ar_app_simplified          Up (healthy)
# vertex_ar_nginx_simplified        Up (healthy)
```

### 5. Проверка работоспособности

```bash
# Проверка healthcheck
curl http://localhost/health
# Ответ: {"status":"healthy","timestamp":"..."}

# Проверка логов nginx (НЕ должно быть [emerg] ошибок)
docker compose logs nginx | grep -E "error|emerg"

# Проверка логов приложения
docker compose logs app | tail -20
```

### 6. Доступ к админ-панели

Откройте в браузере: `http://your-domain.com/admin`

Логин:
- **Username:** значение из `ADMIN_USERNAME` (по умолчанию: admin)
- **Password:** значение из `ADMIN_PASSWORD`

## Проверка что bugfix работает

### Тест 1: Nginx стартует без backend

```bash
# Остановим только backend
docker compose stop app

# Проверим что nginx всё еще работает
docker compose ps nginx
# Статус должен быть: Up (healthy)

# Проверим healthcheck
curl http://localhost/health
# Может вернуть 502 (это нормально, backend недоступен)

# Запустим backend обратно
docker compose start app
```

### Тест 2: Перезапуск nginx без restart loop

```bash
# Перезапустим nginx
docker compose restart nginx

# Проверим логи (НЕ должно быть [emerg])
docker compose logs nginx | tail -20

# Проверим статус
docker compose ps
# Оба контейнера должны быть: Up (healthy)
```

## Мониторинг в продакшене

### Проверка статуса контейнеров

```bash
# Статус всех сервисов
docker compose ps

# Логи nginx (последние 50 строк)
docker compose logs nginx --tail=50 --follow

# Логи приложения
docker compose logs app --tail=50 --follow

# Использование ресурсов
docker stats --no-stream
```

### Типичные логи nginx (нормальные)

```
/docker-entrypoint.sh: Configuration complete; ready for start up
```
✅ Nginx стартовал успешно

```
recv() failed (111: Connection refused) while resolving
```
⚠️ Docker DNS временно недоступен, используется fallback (8.8.8.8) - это нормально

```
test-app could not be resolved (110: Operation timed out)
```
⚠️ Backend недоступен - nginx продолжит работать, клиенты получат 502

### Критичные ошибки

```
nginx: [emerg] host not found in upstream
```
❌ Используется старая конфигурация! Нужно обновить nginx.conf

```
nginx: [emerg] no resolver defined
```
❌ Отсутствует директива `resolver` - проверьте nginx.conf

## HTTPS Setup (опционально)

### С Let's Encrypt

```bash
# 1. Установите certbot
sudo apt-get update
sudo apt-get install certbot

# 2. Получите сертификаты
sudo certbot certonly --standalone \
  -d your-domain.com \
  --email your-email@example.com \
  --agree-tos

# 3. Копируйте сертификаты в проект
mkdir -p ssl
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem
sudo chown $USER:$USER ssl/*.pem

# 4. Раскомментируйте HTTPS блок в nginx.conf
nano nginx.conf
# Найдите "# HTTPS сервер" и раскомментируйте блок server

# 5. Раскомментируйте SSL volume в docker-compose.yml
nano docker-compose.yml
# Найдите "# - ./ssl:/etc/nginx/ssl:ro" и раскомментируйте

# 6. Перезапустите nginx
docker compose restart nginx
```

## Обновление приложения

```bash
# 1. Pull последних изменений
git pull origin bugfix/docker-nginx-restart-loop

# 2. Пересобрать и перезапустить
docker compose up -d --build

# 3. Проверить статус
docker compose ps
```

## Откат к предыдущей версии

```bash
# 1. Остановить контейнеры
docker compose down

# 2. Откатить git
git checkout <previous-commit-hash>

# 3. Запустить старую версию
docker compose up -d --build
```

## Резервное копирование

### Бэкап данных

```bash
# Создать директорию для бэкапов
mkdir -p backups

# Бэкап SQLite базы
docker compose cp app:/app/data/app_data.db backups/app_data_$(date +%Y%m%d).db

# Бэкап storage (портреты, видео)
tar -czf backups/storage_$(date +%Y%m%d).tar.gz storage/

# Бэкап .env
cp .env backups/.env_$(date +%Y%m%d)
```

### Восстановление

```bash
# Остановить контейнеры
docker compose down

# Восстановить базу данных
cp backups/app_data_20250102.db app_data/app_data.db

# Восстановить storage
tar -xzf backups/storage_20250102.tar.gz

# Запустить контейнеры
docker compose up -d
```

## Troubleshooting

### Nginx не стартует

```bash
# Проверить синтаксис конфигурации
docker run --rm -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro nginx:alpine nginx -t

# Проверить логи
docker compose logs nginx
```

### Backend не отвечает

```bash
# Проверить логи приложения
docker compose logs app

# Перезапустить backend
docker compose restart app

# Проверить healthcheck
docker compose exec app curl http://localhost:8000/health
```

### Порты заняты

```bash
# Проверить какой процесс использует порт 80
sudo lsof -i :80

# Остановить конфликтующий сервис (например, apache)
sudo systemctl stop apache2

# Перезапустить Docker Compose
docker compose up -d
```

## Полезные команды

```bash
# Просмотр логов в реальном времени
docker compose logs -f

# Вход в контейнер nginx
docker compose exec nginx sh

# Вход в контейнер приложения
docker compose exec app bash

# Перезагрузка nginx (reload конфигурации)
docker compose exec nginx nginx -s reload

# Полная очистка и пересборка
docker compose down -v
docker compose up -d --build
```

## Контакты

Для вопросов и проблем создавайте issue в репозитории: https://github.com/fegerV/ar/issues

---

**Версия:** 1.5.1  
**Дата:** 2025-01-02  
**Bugfix:** Nginx Restart Loop исправлен ✅
