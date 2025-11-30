# Настройка продакшена Vertex AR

**Версия:** 1.3.0  
**Дата обновления:** 7 ноября 2024

Документ описывает развёртывание приложения `vertex-ar` на отдельном сервере Linux. Инструкции ориентированы на Ubuntu 22.04, но могут быть адаптированы под другие дистрибутивы.

---

## 1. Подготовка сервера

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git nginx supervisor curl unzip
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

Создайте системного пользователя:
```bash
sudo adduser --system --group --home /opt/vertex-ar vertexar
sudo mkdir -p /opt/vertex-ar
sudo chown vertexar:vertexar /opt/vertex-ar
```

---

## 2. Получение кода

```bash
sudo -u vertexar -H bash -c '
  cd /opt/vertex-ar && \
  git clone https://github.com/your-org/vertex-ar.git src && \
  cd src && \
  git checkout main
'
```

Структура:
```
/opt/vertex-ar
└── src/          # Репозиторий
```

---

## 3. Виртуальное окружение и зависимости

```bash
sudo -u vertexar -H bash -c '
  cd /opt/vertex-ar/src/vertex-ar && \
  python3 -m venv ../venv && \
  source ../venv/bin/activate && \
  pip install --upgrade pip && \
  pip install -r requirements.txt && \
  pip install -r requirements-dev.txt
'
```

Если используется генерация маркеров через OpenCV или дополнительные библиотеки — установите их заранее (см. `../docs/guides/installation.md`).

---

## 4. Конфигурация окружения

```bash
sudo -u vertexar -H bash -c '
  cd /opt/vertex-ar/src/vertex-ar && \
  cp .env.production.example .env
'
```

Обязательные параметры `.env`:
- `BASE_URL=https://ar.example.com`
- `STORAGE_TYPE=minio` или `local`
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`
- `SESSION_TIMEOUT_MINUTES=30`, `AUTH_MAX_ATTEMPTS=5`, `AUTH_LOCKOUT_MINUTES=15`
- `CORS_ORIGINS=https://ar.example.com`
- `SENTRY_DSN` (опционально)

Создайте каталоги хранения:
```bash
sudo -u vertexar -H bash -c '
  mkdir -p /opt/vertex-ar/data/storage/ar_content \
           /opt/vertex-ar/data/storage/nft-markers \
           /opt/vertex-ar/data/storage/qr-codes \
           /opt/vertex-ar/data/logs
'
```

Добавьте в `.env`:
```
STORAGE_ROOT=/opt/vertex-ar/data/storage
LOGS_ROOT=/opt/vertex-ar/data/logs
```

---

## 5. Uvicorn Runtime Configuration

### Worker Tuning

Vertex AR supports comprehensive uvicorn runtime tuning. The deployment automatically calculates optimal worker count based on CPU cores:

**Default Formula:** `workers = (2 × CPU_cores) + 1`

See [Uvicorn Tuning Guide](uvicorn-tuning.md) for detailed configuration options.

### Systemd Service

Создайте файл `/etc/systemd/system/vertex-ar.service`:
```ini
[Unit]
Description=Vertex AR API
After=network.target

[Service]
User=vertexar
Group=vertexar
WorkingDirectory=/opt/vertex-ar/src/vertex-ar
Environment="PATH=/opt/vertex-ar/venv/bin"
EnvironmentFile=/opt/vertex-ar/src/vertex-ar/.env
ExecStart=/opt/vertex-ar/venv/bin/uvicorn app.main:app \
  --host 127.0.0.1 --port 9000 \
  --workers ${UVICORN_WORKERS} \
  --timeout-keep-alive ${UVICORN_TIMEOUT_KEEP_ALIVE:-5} \
  --backlog ${UVICORN_BACKLOG:-2048} \
  --proxy-headers \
  --timeout-graceful-shutdown ${UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN:-30}
Restart=always
RestartSec=5
TimeoutStopSec=${UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN:-30}

[Install]
WantedBy=multi-user.target
```

**Note:** Configure uvicorn settings in `.env` file (see [Configuration Reference](#uvicorn-environment-variables)).

Активируйте службу:
```bash
sudo systemctl daemon-reload
sudo systemctl enable vertex-ar.service
sudo systemctl start vertex-ar.service
sudo systemctl status vertex-ar.service
```

### Uvicorn Environment Variables

Add to your `.env` file:

```bash
# Worker Configuration (auto-calculated if not set)
UVICORN_WORKERS=9  # (2 × 4 cores) + 1

# Connection Management
UVICORN_TIMEOUT_KEEP_ALIVE=5
UVICORN_LIMIT_CONCURRENCY=0  # 0 = unlimited
UVICORN_BACKLOG=2048
UVICORN_PROXY_HEADERS=true
UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=30

# Health Check Tuning
WEB_HEALTH_CHECK_TIMEOUT=5
WEB_HEALTH_CHECK_USE_HEAD=false
WEB_HEALTH_CHECK_COOLDOWN=30
```

See **[Uvicorn Tuning Guide](uvicorn-tuning.md)** for comprehensive tuning scenarios and best practices.

---

## 6. Nginx

Создайте `/etc/nginx/sites-available/vertex-ar.conf`:
```nginx
server {
    listen 80;
    server_name ar.example.com;

    access_log /opt/vertex-ar/data/logs/nginx_access.log;
    error_log  /opt/vertex-ar/data/logs/nginx_error.log;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass         http://127.0.0.1:9000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/vertex-ar/src/vertex-ar/static/;
        add_header Cache-Control "public, max-age=3600";
    }
}
```

Активируйте сайт:
```bash
sudo ln -s /etc/nginx/sites-available/vertex-ar.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

> Для HTTPS используйте Certbot: `sudo certbot --nginx -d ar.example.com`.

---

## 7. Плановое обслуживание

| Задача | Команда |
| --- | --- |
| Резервное копирование хранилища | `tar czf backup-$(date +%F).tar.gz /opt/vertex-ar/data/storage` |
| Обновление зависимостей | `pip install -r requirements.txt --upgrade` |
| Проверка готовности | `/opt/vertex-ar/src/check_production_readiness.sh` |
| Нагрузочные тесты | `/opt/vertex-ar/src/run_performance_tests.sh` |
| Очистка маркеров | `curl -X POST https://ar.example.com/api/nft-markers/cleanup -H "Authorization: Bearer <token>"` |

Рекомендуется раз в неделю анализировать логи `/opt/vertex-ar/data/logs/*.log`.

---

## 8. Мониторинг и алерты

- Интегрируйте Sentry (DSN в `.env`).  
- Отправляйте логи в ELK/Datadog (JSON-формат совместим).  
- Используйте Prometheus-экспортер или систему метрик `metrics` (roadmap v1.4).  
- Настройте системные метрики (CPU/RAM/Disk) через Netdata или Grafana Agent.

---

## 9. Обновления приложения

```bash
sudo systemctl stop vertex-ar.service
sudo -u vertexar -H bash -c '
  cd /opt/vertex-ar/src && git fetch && git checkout main && git pull
  source ../venv/bin/activate
  pip install -r vertex-ar/requirements.txt
  pip install -r vertex-ar/requirements-dev.txt
'
sudo systemctl start vertex-ar.service
```

После обновления запустите автотесты вручную или в CI:
```bash
cd /opt/vertex-ar/src
source ../venv/bin/activate
pytest --maxfail=1
```

---

## 10. Контрольный список перед запуском

- [ ] Настроен `.env`, секреты сохранены в менеджере секретов
- [ ] Работает HTTPS (сертификаты обновляются автоматически)
- [ ] Созданы резервные копии хранилища и `.env`
- [ ] Прошли `pytest` и `check_production_readiness.sh`
- [ ] Логи и директории имеют права пользователя `vertexar`
- [ ] Добавлено наблюдение за доступностью `/health`

---

При возникновении вопросов обратитесь к `../docs/guides/installation.md`, `../SECURITY.md` или команде DevOps: devops@vertex-ar.example.com.
