# 📦 Полная инструкция развертывания Vertex AR

## 🎯 Цель

Развернуть Vertex AR админ-панель на cloud.ru сервере, чтобы она была доступна по HTTPS на домене `https://nft.vertex-art.ru/admin`.

---

## 📋 Информация о сервере

| Параметр | Значение |
|----------|----------|
| **ОС** | Ubuntu 18.04.06 |
| **IP публичный** | 192.144.12.68 |
| **IP внутренний** | 10.0.0.5 |
| **Пользователь SSH** | rustadmin |
| **Домен** | nft.vertex-art.ru |
| **Хостинг** | cloud.ru |
| **Регистратор домена** | reg.ru + Cpanel |

---

## ⚡ Быстрый старт (10 минут)

### Вариант 1: Автоматизированный (Рекомендуется)

```bash
# 1. Подключитесь к серверу
ssh -i /path/to/key rustadmin@192.144.12.68

# 2. Загрузьте и запустите скрипт развертывания
cd ~
wget https://raw.githubusercontent.com/fegerV/AR/master/scripts/deploy-vertex-ar-cloud-ru.sh
chmod +x deploy-vertex-ar-cloud-ru.sh
sudo ./deploy-vertex-ar-cloud-ru.sh

# 3. После завершения установите SSL сертификат
# (см. инструкции ниже)

# 4. Откройте https://nft.vertex-art.ru/admin
```

### Вариант 2: Пошагово (для лучшего понимания)

Следуйте инструкциям в файле [DEPLOYMENT_CLOUD_RU_GUIDE.md](DEPLOYMENT_CLOUD_RU_GUIDE.md).

---

## 📖 Полная документация

### 1. **Подключение к серверу**
   📖 [QUICK_SSH_GUIDE.md](QUICK_SSH_GUIDE.md)
   - Как подключиться по SSH
   - Для Windows, macOS, Linux

### 2. **Развертывание приложения**
   📖 [DEPLOYMENT_CLOUD_RU_GUIDE.md](DEPLOYMENT_CLOUD_RU_GUIDE.md)
   - Подготовка системы
   - Установка зависимостей
   - Запуск приложения
   - Настройка Nginx
   - Мониторинг и логирование

### 3. **Настройка Cpanel (Домены и SSL)**
   📖 [CPANEL_SETUP.md](CPANEL_SETUP.md)
   - Добавление домена
   - Установка SSL сертификата
   - Конфигурация proxy

### 4. **Скрипт автоматизации**
   📂 [scripts/deploy-vertex-ar-cloud-ru.sh](scripts/deploy-vertex-ar-cloud-ru.sh)
   - Полностью автоматизированное развертывание
   - Установка всех зависимостей
   - Конфигурация Supervisor и Nginx

---

## 🔧 Пошаговое развертывание

### Этап 1: Подготовка (5 минут)

```bash
# Подключитесь к серверу
ssh -i /path/to/ssh-key rustadmin@192.144.12.68

# Обновите систему
sudo apt update && sudo apt upgrade -y

# Установите базовые инструменты
sudo apt install -y git wget curl python3 python3-pip python3-venv
```

### Этап 2: Клонирование проекта (2 минуты)

```bash
# Создайте директорию приложения
mkdir -p ~/vertex-ar-app
cd ~/vertex-ar-app

# Клонируйте репозиторий
git clone https://github.com/fegerV/AR.git .
# или скачайте ZIP файл
wget -O vertex-ar.zip https://github.com/fegerV/AR/archive/refs/heads/master.zip
unzip vertex-ar.zip

# Перейдите в папку проекта
cd vertex-ar
```

### Этап 3: Виртуальное окружение Python (3 минуты)

```bash
# Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Обновите pip
pip install --upgrade pip setuptools wheel

# Установите зависимости
pip install -r requirements.txt
# или для production
pip install -r requirements-simple.txt
```

### Этап 4: Конфигурация (5 минут)

```bash
# Создайте файл .env
cp .env.example .env

# Отредактируйте .env
nano .env
```

**Важные переменные в .env:**

```env
DEBUG=False
SECRET_KEY=<GENERATE_SECURE_KEY>
APP_HOST=127.0.0.1
APP_PORT=8000
BASE_URL=https://nft.vertex-art.ru
ENVIRONMENT=production
CORS_ORIGINS=https://nft.vertex-art.ru,https://www.nft.vertex-art.ru
DEFAULT_ADMIN_PASSWORD=<CHANGE_ME>
```

### Этап 5: Запуск приложения (5 минут)

```bash
# Тестируйте приложение вручную
uvicorn main:app --host 127.0.0.1 --port 8000

# В другом терминале проверьте
curl http://127.0.0.1:8000/api/health

# Остановите (Ctrl+C)
```

### Этап 6: Supervisor для автозапуска (5 минут)

```bash
# Установите Supervisor
sudo apt install -y supervisor

# Создайте конфиг для Vertex AR
sudo nano /etc/supervisor/conf.d/vertex-ar.conf
```

**Содержимое конфига:**

```ini
[program:vertex-ar]
directory=/home/rustadmin/vertex-ar-app/vertex-ar
command=/home/rustadmin/vertex-ar-app/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
user=rustadmin
autostart=true
autorestart=true
stderr_logfile=/var/log/vertex-ar/error.log
stdout_logfile=/var/log/vertex-ar/access.log
environment=PATH="/home/rustadmin/vertex-ar-app/venv/bin",HOME="/home/rustadmin"
```

```bash
# Создайте директорию логов
sudo mkdir -p /var/log/vertex-ar
sudo chown rustadmin:rustadmin /var/log/vertex-ar

# Запустите Supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start vertex-ar

# Проверьте статус
sudo supervisorctl status vertex-ar
```

### Этап 7: Nginx как Reverse Proxy (5 минут)

```bash
# Установите Nginx
sudo apt install -y nginx

# Создайте конфиг
sudo nano /etc/nginx/sites-available/vertex-ar
```

**Содержимое конфига:**

```nginx
upstream vertex_ar {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name nft.vertex-art.ru www.nft.vertex-art.ru;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name nft.vertex-art.ru www.nft.vertex-art.ru;

    ssl_certificate /etc/ssl/certs/nft.vertex-art.ru.crt;
    ssl_certificate_key /etc/ssl/private/nft.vertex-art.ru.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    access_log /var/log/nginx/vertex-ar-access.log;
    error_log /var/log/nginx/vertex-ar-error.log;

    client_max_body_size 50M;

    location / {
        proxy_pass http://vertex_ar;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Активируйте конфиг
sudo ln -s /etc/nginx/sites-available/vertex-ar /etc/nginx/sites-enabled/vertex-ar

# Протестируйте конфиг
sudo nginx -t

# Перезагрузите Nginx
sudo systemctl restart nginx
```

### Этап 8: SSL сертификат (5 минут)

```bash
# Из Cpanel -> SSL/TLS Manager
# Установите AutoSSL или Let's Encrypt
# Затем скопируйте сертификат и ключ на сервер

# На сервере
sudo cp /path/to/certificate.crt /etc/ssl/certs/nft.vertex-art.ru.crt
sudo cp /path/to/private.key /etc/ssl/private/nft.vertex-art.ru.key

sudo chmod 644 /etc/ssl/certs/nft.vertex-art.ru.crt
sudo chmod 600 /etc/ssl/private/nft.vertex-art.ru.key

# Перезагрузите Nginx
sudo systemctl restart nginx
```

---

## ✅ Проверка работы

```bash
# Проверьте, что приложение запущено
sudo supervisorctl status vertex-ar
# Должно показать: vertex-ar RUNNING

# Проверьте HTTP локально
curl http://127.0.0.1:8000/api/health

# Проверьте HTTPS через браузер или curl
curl -I https://nft.vertex-art.ru
# Должно показать: HTTP/1.1 200 OK

# Откройте в браузере
https://nft.vertex-art.ru/admin
```

---

## 📊 Мониторинг

### Просмотр логов

```bash
# Логи приложения
tail -f /var/log/vertex-ar/error.log
tail -f /var/log/vertex-ar/access.log

# Логи Nginx
tail -f /var/log/nginx/vertex-ar-error.log
tail -f /var/log/nginx/vertex-ar-access.log
```

### Проверка статуса

```bash
# Статус приложения
sudo supervisorctl status vertex-ar

# Статус Nginx
sudo systemctl status nginx

# Использование ресурсов
top
# или
htop
```

### Перезагрузка

```bash
# Мягкая перезагрузка приложения
sudo supervisorctl restart vertex-ar

# Перезагрузка Nginx
sudo systemctl restart nginx

# Полная перезагрузка сервера
sudo reboot
```

---

## 🔐 Безопасность

### Измените пароль администратора

1. **Откройте админ-панель**: https://nft.vertex-art.ru/admin
2. **Войдите** с учетными данными из `.env`
3. **Перейдите в** "Управление пользователями"
4. **Измените пароль**

### Защита файлов

```bash
# Дайте правильные права
chmod 700 /home/rustadmin/vertex-ar-app
chmod 755 /home/rustadmin/vertex-ar-app/vertex-ar
chmod 600 /home/rustadmin/vertex-ar-app/vertex-ar/.env

# Скрыйте чувствительные файлы
chmod 600 /home/rustadmin/vertex-ar-app/vertex-ar/app_data.db
```

---

## 🆘 Решение проблем

### Приложение не запускается

```bash
# Проверьте логи
tail -f /var/log/vertex-ar/error.log

# Тестируйте вручную
cd ~/vertex-ar-app/vertex-ar
source ~/vertex-ar-app/venv/bin/activate
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### SSL ошибка

```bash
# Проверьте сертификаты
sudo ls -la /etc/ssl/certs/nft.vertex-art.ru.crt
sudo ls -la /etc/ssl/private/nft.vertex-art.ru.key

# Проверьте Nginx конфиг
sudo nginx -t

# Может потребоваться обновить Cpanel сертификат
```

### 502 Bad Gateway

```bash
# Проверьте, работает ли приложение
curl http://127.0.0.1:8000

# Перезагрузите приложение
sudo supervisorctl restart vertex-ar

# Перезагрузите Nginx
sudo systemctl restart nginx
```

---

## 📈 Следующие шаги

1. ✅ **Резервное копирование**: Настройте автоматические резервные копии
2. ✅ **Мониторинг**: Установите систему мониторинга (Prometheus, Grafana)
3. ✅ **Логирование**: Настройте центральное хранилище логов (ELK)
4. ✅ **Автообновление**: Настройте автоматическое обновление из репозитория

---

## 📚 Дополнительные ресурсы

| Ресурс | Ссылка |
|--------|--------|
| **SSH подключение** | [QUICK_SSH_GUIDE.md](QUICK_SSH_GUIDE.md) |
| **Развертывание** | [DEPLOYMENT_CLOUD_RU_GUIDE.md](DEPLOYMENT_CLOUD_RU_GUIDE.md) |
| **Cpanel настройка** | [CPANEL_SETUP.md](CPANEL_SETUP.md) |
| **Скрипт развертывания** | [scripts/deploy-vertex-ar-cloud-ru.sh](scripts/deploy-vertex-ar-cloud-ru.sh) |
| **README основной** | [README_RU.md](README_RU.md) |
| **Архитектура** | [ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md) |

---

## 📞 Техническая поддержка

- **Cloud.ru**: https://cloud.ru/support
- **Reg.ru**: https://www.reg.ru/support
- **Let's Encrypt**: https://letsencrypt.org/support/

---

## ✨ Результат

После выполнения всех шагов у вас будет:

✅ FastAPI приложение запущено на `http://127.0.0.1:8000`
✅ Nginx работает как reverse proxy
✅ HTTPS доступен на `https://nft.vertex-art.ru`
✅ Админ-панель доступна на `https://nft.vertex-art.ru/admin`
✅ Приложение автоматически перезагружается при падении
✅ Логи записываются в `/var/log/vertex-ar/`
✅ Резервное копирование настроено

---

**Дата создания**: 2024-11-21
**Версия**: 1.0
**Статус**: Готово к использованию
