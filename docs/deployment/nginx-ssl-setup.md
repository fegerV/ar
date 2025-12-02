# Настройка SSL для Nginx

## Проблема

Контейнер Nginx перезапускался из-за отсутствия SSL-сертификатов, которые были указаны в конфигурации как обязательные.

## Решение

Конфигурация Nginx была обновлена для работы в HTTP-режиме по умолчанию. HTTPS-блок закомментирован и может быть активирован после получения сертификатов.

## Текущая конфигурация

- **HTTP**: Работает на порту 80 (активно)
- **HTTPS**: Закомментировано, требует SSL-сертификаты (порт 443)
- **Зависимости**: Убрана обязательная монтировка директории `./ssl`

## Активация HTTPS

### Вариант 1: Самоподписанные сертификаты (для разработки)

```bash
# Создать директорию для сертификатов
mkdir -p ssl

# Сгенерировать самоподписанный сертификат
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/key.pem \
  -out ssl/cert.pem \
  -subj "/C=RU/ST=Moscow/L=Moscow/O=VertexAR/CN=nft.vertex-art.ru"

# Установить правильные права
chmod 600 ssl/key.pem
chmod 644 ssl/cert.pem
```

### Вариант 2: Let's Encrypt (для продакшн)

```bash
# Установить certbot
sudo apt-get update
sudo apt-get install certbot

# Получить сертификат (Nginx должен быть остановлен или использовать webroot)
sudo certbot certonly --standalone \
  -d nft.vertex-art.ru \
  --email your-email@example.com \
  --agree-tos

# Скопировать сертификаты в проект
mkdir -p ssl
sudo cp /etc/letsencrypt/live/nft.vertex-art.ru/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/nft.vertex-art.ru/privkey.pem ssl/key.pem
sudo chown $USER:$USER ssl/*.pem
```

### Вариант 3: Автоматическое получение с Certbot в Docker

```bash
# Добавить certbot сервис в docker-compose.yml
# (см. docker-compose.certbot.yml)

# Получить сертификат
docker-compose run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  -d nft.vertex-art.ru \
  --email your-email@example.com \
  --agree-tos
```

## После получения сертификатов

1. **Раскомментировать HTTPS блок в nginx.conf**:
   - Найти секцию `# HTTPS сервер (опциональный...)`
   - Раскомментировать весь блок `server { listen 443 ssl http2; ... }`

2. **Раскомментировать монтировку SSL в docker-compose.yml**:
   ```yaml
   volumes:
     - ./nginx.conf:/etc/nginx/nginx.conf:ro
     - ./ssl:/etc/nginx/ssl:ro  # <- раскомментировать эту строку
   ```

3. **Опционально: добавить редирект с HTTP на HTTPS**:
   ```nginx
   server {
       listen 80;
       server_name nft.vertex-art.ru;
       # Добавить редирект
       return 301 https://$server_name$request_uri;
   }
   ```

4. **Перезапустить контейнеры**:
   ```bash
   docker compose restart nginx
   # или
   docker compose down && docker compose up -d
   ```

## Проверка конфигурации

```bash
# Проверить синтаксис nginx
docker compose exec nginx nginx -t

# Проверить логи
docker compose logs nginx --tail=50

# Проверить healthcheck
docker compose ps nginx
```

## Мониторинг SSL

```bash
# Проверить срок действия сертификата
openssl x509 -in ssl/cert.pem -noout -dates

# Проверить подключение
curl -I https://nft.vertex-art.ru

# Детальная информация
openssl s_client -connect nft.vertex-art.ru:443 -servername nft.vertex-art.ru
```

## Автоматическое обновление Let's Encrypt

Добавить в crontab:

```bash
# Обновление каждые 12 часов
0 */12 * * * certbot renew --quiet && docker compose restart nginx
```

## Troubleshooting

### Nginx падает при старте
- Проверьте наличие файлов `ssl/cert.pem` и `ssl/key.pem`
- Проверьте права доступа к файлам
- Проверьте синтаксис: `docker compose exec nginx nginx -t`

### Ошибка "certificate verify failed"
- Убедитесь, что используете правильный сертификат
- Для самоподписанных: браузер покажет предупреждение (это нормально для dev)
- Для Let's Encrypt: проверьте, что домен настроен правильно

### Порт 443 уже используется
```bash
# Найти процесс
sudo lsof -i :443

# Остановить конфликтующий сервис
sudo systemctl stop <service-name>
```

## Дополнительная безопасность

### HSTS (HTTP Strict Transport Security)
Добавить в HTTPS блок:
```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### OCSP Stapling
```nginx
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/nginx/ssl/chain.pem;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;
```

### Рейтинг SSL (Mozilla SSL Configuration Generator)
https://ssl-config.mozilla.org/

Используйте "Modern" или "Intermediate" профиль в зависимости от требований совместимости.

## Ссылки

- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Nginx SSL Configuration](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [SSL Labs Server Test](https://www.ssllabs.com/ssltest/)
