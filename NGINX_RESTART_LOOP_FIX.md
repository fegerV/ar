# Nginx Restart Loop - Диагностика и Решение

## Проблема

Docker контейнер с nginx **постоянно перезапускается** (restart loop) при использовании в docker-compose с FastAPI backend.

### Симптомы

- Контейнер nginx в статусе `Restarting` или постоянно перезапускается
- В логах ошибка: `nginx: [emerg] host not found in upstream "app:8000"`
- Nginx не может стартовать, даже если backend готов

### Корневая причина

**Проблема:** В старой конфигурации использовался блок `upstream`:

```nginx
upstream app_server {
    server app:8000;
}
```

Nginx пытается **разрешить DNS имя** backend сервера (`app`) **в момент запуска**. Если:
- Backend еще не запущен
- Backend не готов принимать соединения  
- DNS не может разрешить имя (даже временно)

То nginx **падает с ошибкой** и рестартует. Это создает бесконечный restart loop.

## Решение

### Изменения в nginx.conf

**1. Убрали жесткий upstream блок**

Старый код (проблемный):
```nginx
upstream app_server {
    server app:8000;  # DNS разрешается при старте nginx!
}

location / {
    proxy_pass http://app_server;
}
```

Новый код (исправленный):
```nginx
# DNS resolver для динамического разрешения имен
# 127.0.0.11 - встроенный DNS Docker, 8.8.8.8 - fallback
resolver 127.0.0.11 8.8.8.8 valid=10s ipv6=off;

server {
    location / {
        # Используем переменную для ОТЛОЖЕННОГО разрешения DNS
        # Это критически важно: nginx НЕ будет пытаться разрешить DNS при старте!
        set $upstream_app app;
        set $upstream_port 8000;
        proxy_pass http://$upstream_app:$upstream_port;
        
        # ... остальные proxy_set_header
    }
    
    location /storage/ {
        set $upstream_app app;
        set $upstream_port 8000;
        proxy_pass http://$upstream_app:$upstream_port/storage/;
        # ... headers
    }
    
    location /health {
        set $upstream_app app;
        set $upstream_port 8000;
        proxy_pass http://$upstream_app:$upstream_port/health;
        access_log off;
    }
}
```

**2. Добавили resolver директиву**

```nginx
# DNS resolver для динамического разрешения имен
# 127.0.0.11 - встроенный DNS Docker
# 8.8.8.8 - публичный DNS Google (fallback)
# valid=10s - кэшировать DNS запись на 10 секунд
# ipv6=off - отключить IPv6 для совместимости
resolver 127.0.0.11 8.8.8.8 valid=10s ipv6=off;
```

**Почему это работает:**

1. **Переменные в proxy_pass** - Когда используется переменная (`$upstream_app`), nginx НЕ разрешает DNS при старте
2. **DNS lookup при каждом запросе** - Имя backend'а разрешается динамически при каждом HTTP запросе
3. **Nginx стартует независимо** - Даже если backend недоступен, nginx успешно запускается
4. **Кэширование DNS** - `valid=10s` кэширует DNS на 10 секунд для производительности
5. **Fallback resolver** - Если Docker DNS (127.0.0.11) недоступен, используется 8.8.8.8

### Изменения в docker-compose.yml

**1. Обновили healthcheck**

Старый (использовал wget, которого нет в nginx:alpine):
```yaml
healthcheck:
  test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/health"]
```

Новый (использует curl):
```yaml
healthcheck:
  test: ["CMD", "sh", "-c", "curl -f http://localhost/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s  # Даем nginx 40 секунд на старт
```

**2. Добавили readonly монтирование конфигов**

```yaml
volumes:
  - ./nginx.conf:/etc/nginx/nginx.conf:ro  # :ro = read-only
```

**3. Добавили том для логов**

```yaml
volumes:
  - nginx_logs:/var/log/nginx  # Для отладки

volumes:
  nginx_logs:  # Объявление named volume
```

## Проверка работоспособности

### Тест 1: Nginx запускается без backend

```bash
# Запускаем только nginx (без app)
docker run -d --name test_nginx -p 9090:80 \
  -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro \
  nginx:alpine

# Проверяем статус
docker ps | grep test_nginx
# Должен быть: Up X seconds

# Проверяем логи (НЕ должно быть [emerg])
docker logs test_nginx 2>&1 | grep -E "error|emerg"
# Выход должен быть пустым или только предупреждения

# Проверяем healthcheck endpoint
curl http://localhost:9090/health
# Ответ: OK

# Очистка
docker rm -f test_nginx
```

### Тест 2: Docker Compose с тестовым backend

```bash
# Запуск тестового окружения
docker compose -f docker-compose.test.yml up -d

# Проверка статуса (оба должны быть healthy)
docker compose -f docker-compose.test.yml ps

# Остановка backend (nginx должен продолжать работать!)
docker compose -f docker-compose.test.yml stop test-app

# Проверка что nginx всё еще работает
docker compose -f docker-compose.test.yml ps
# nginx-proxy должен быть: Up (healthy)

# Очистка
docker compose -f docker-compose.test.yml down
```

### Тест 3: Проверка синтаксиса конфигурации

```bash
# Проверка nginx.conf
docker run --rm \
  -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro \
  nginx:alpine nginx -t

# Вывод должен быть:
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful
```

## Результат

✅ **Проблема решена:**
- Nginx стартует **независимо от доступности backend**
- Никаких restart loops
- Healthcheck работает корректно
- DNS разрешается динамически при каждом запросе
- Добавлен fallback DNS resolver (8.8.8.8)

✅ **Производительность:**
- DNS кэшируется на 10 секунд (`valid=10s`)
- Минимальное влияние на latency
- Backend может перезапускаться без влияния на nginx

✅ **Надежность:**
- Nginx работает даже если backend временно недоступен
- Клиенты получают 502 Bad Gateway вместо полного отказа сервиса
- Автоматическое восстановление при появлении backend

## Мониторинг

### Проверка статуса контейнеров

```bash
# Статус всех сервисов
docker compose ps

# Логи nginx
docker compose logs nginx | tail -50

# Логи backend
docker compose logs app | tail -50
```

### Типичные ошибки в логах (нормальные)

```
recv() failed (111: Connection refused) while resolving
```
Это нормально, если Docker DNS временно недоступен. Используется fallback (8.8.8.8).

```
test-app could not be resolved (110: Operation timed out)
```
Это нормально, если backend еще не запущен. Клиент получит 502, nginx продолжит работать.

### Критичные ошибки (требуют внимания)

```
nginx: [emerg] host not found in upstream
```
❌ Это старая ошибка! Означает что используется устаревшая конфигурация с upstream блоком.

```
nginx: [emerg] no resolver defined to resolve
```
❌ Отсутствует директива `resolver` при использовании переменных в proxy_pass.

## Откат (если нужно)

Если по какой-то причине новая конфигурация не работает:

```bash
# Остановить сервисы
docker compose down

# Восстановить старую конфигурацию из git
git checkout HEAD -- nginx.conf docker-compose.yml

# Запустить с старой конфигурацией
docker compose up -d
```

**Важно:** Старая конфигурация имеет restart loop проблему!

## Дополнительная информация

### Файлы изменены

- `nginx.conf` - основная конфигурация nginx
- `nginx.test.conf` - тестовая конфигурация для изолированного тестирования
- `docker-compose.yml` - основной compose файл
- `docker-compose.test.yml` - тестовый compose файл для диагностики
- `NGINX_RESTART_LOOP_FIX.md` - эта документация

### Полезные ссылки

- [Nginx Dynamic DNS Resolution](http://nginx.org/en/docs/http/ngx_http_core_module.html#resolver)
- [Docker DNS](https://docs.docker.com/config/containers/container-networking/#dns-services)
- [Nginx Variables](http://nginx.org/en/docs/varindex.html)

## Контакты

Для вопросов и проблем создавайте issue в репозитории проекта.

---

**Версия документа:** 1.0  
**Дата:** 2025-01-02  
**Статус:** ✅ Исправлено и протестировано
