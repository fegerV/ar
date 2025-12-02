# Исправление проблемы перезапуска Nginx

## Проблема

Контейнер Nginx постоянно перезапускался при запуске через Docker Compose.

## Причины

1. **Отсутствие SSL-сертификатов**: Конфигурация требовала обязательные файлы `/etc/nginx/ssl/cert.pem` и `/etc/nginx/ssl/key.pem`, которых не было
2. **Ссылки на MinIO**: Конфигурация содержала proxy_pass на несуществующий сервис `minio:9000`
3. **Принудительный HTTPS**: Редирект с HTTP на HTTPS без сертификатов приводил к падению nginx

## Внесенные изменения

### 1. nginx.conf

✅ **Изменения:**
- Убран обязательный HTTPS-сервер (закомментирован)
- Удалены ссылки на MinIO
- Добавлен рабочий HTTP-сервер на порту 80
- Добавлена поддержка больших файлов (500MB)
- Увеличены таймауты для загрузки видео/изображений
- Добавлен healthcheck endpoint `/health`
- Добавлены правильные MIME-типы и логирование

✅ **Что работает:**
- HTTP на порту 80
- Проксирование к FastAPI приложению
- Обработка статических файлов через `/storage/`
- WebSocket поддержка (если потребуется)

✅ **Опционально (для будущего):**
- HTTPS блок закомментирован с инструкциями по активации
- Готов к использованию после получения SSL-сертификатов

### 2. docker-compose.yml

✅ **Изменения:**
- Убрана обязательная монтировка `./ssl` директории
- Добавлена монтировка логов nginx в volume
- Добавлен healthcheck для мониторинга состояния
- Конфиг монтируется в read-only режиме (`:ro`)

✅ **Healthcheck:**
```yaml
healthcheck:
  test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 3. Документация

✅ **Создан файл:** `docs/deployment/nginx-ssl-setup.md`
- Инструкции по настройке SSL
- 3 варианта получения сертификатов
- Troubleshooting
- Best practices для безопасности

## Как использовать

### Запуск без HTTPS (текущая конфигурация)

```bash
# Запустить контейнеры
docker compose up -d

# Проверить статус
docker compose ps

# Проверить логи
docker compose logs nginx

# Проверить healthcheck
docker compose ps nginx
# Должно показать (healthy) в столбце Status
```

Приложение доступно на: **http://localhost**

### Активация HTTPS (опционально)

Если нужен HTTPS - следуйте инструкциям в `docs/deployment/nginx-ssl-setup.md`:

1. Получите SSL-сертификаты (самоподписанные или Let's Encrypt)
2. Раскомментируйте HTTPS блок в `nginx.conf`
3. Раскомментируйте монтировку SSL в `docker-compose.yml`
4. Перезапустите: `docker compose restart nginx`

## Тестирование

### Проверка конфигурации Nginx

```bash
# Проверить синтаксис
docker compose exec nginx nginx -t

# Должен вывести:
# nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### Проверка работы приложения

```bash
# Проверить healthcheck
curl http://localhost/health

# Проверить главную страницу
curl -I http://localhost/

# Проверить что nginx проксирует к app
docker compose logs app --tail=20
```

### Проверка логов

```bash
# Логи nginx
docker compose logs nginx --tail=50 --follow

# Логи приложения
docker compose logs app --tail=50 --follow

# Все логи
docker compose logs --tail=50 --follow
```

## Troubleshooting

### Контейнер все еще перезапускается

```bash
# Проверить логи детально
docker compose logs nginx --tail=100

# Проверить синтаксис конфигурации
docker compose exec nginx nginx -t

# Проверить что порт 80 свободен
sudo lsof -i :80
```

### Healthcheck failed

```bash
# Проверить что приложение отвечает
docker compose exec nginx wget -O- http://app:8000/health

# Проверить внутри nginx
docker compose exec nginx sh
wget -O- http://localhost/health
```

### Порт занят

```bash
# Найти процесс
sudo lsof -i :80

# Изменить порт в docker-compose.yml
ports:
  - "8080:80"  # Использовать 8080 вместо 80
```

## Обратная совместимость

### Для production с существующими сертификатами

Если у вас уже есть сертификаты в `./ssl/`:

1. Раскомментируйте HTTPS блок в `nginx.conf` (строки 63-108)
2. Раскомментируйте монтировку в `docker-compose.yml` (строка 36)
3. Опционально: добавьте редирект HTTP→HTTPS в HTTP блок

```nginx
# В секции server { listen 80; ... }
# Вместо всех location блоков:
return 301 https://$server_name$request_uri;
```

## Преимущества новой конфигурации

✅ **Работает "из коробки"** - не требует предварительной настройки SSL  
✅ **Готов к production** - HTTPS блок легко активируется  
✅ **Healthcheck** - автоматический мониторинг состояния  
✅ **Увеличенные лимиты** - поддержка больших файлов (500MB)  
✅ **Правильные таймауты** - для медленных соединений  
✅ **Логирование** - удобная отладка через volume  
✅ **Безопасность** - read-only монтировка конфигурации  

## Следующие шаги

1. ✅ Проверить что nginx запускается и работает
2. ✅ Протестировать доступ к приложению через nginx
3. ⏳ При необходимости настроить HTTPS (см. документацию)
4. ⏳ Настроить автоматическое обновление SSL-сертификатов

## Дополнительные ресурсы

- `docs/deployment/nginx-ssl-setup.md` - полная инструкция по SSL
- `nginx.conf` - основная конфигурация с комментариями
- `docker-compose.yml` - конфигурация контейнеров

---

**Автор:** AI Assistant  
**Дата:** 2025-01-XX  
**Ветка:** bugfix/docker-nginx-restart-loop
