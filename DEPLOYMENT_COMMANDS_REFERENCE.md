# 🔧 Справочник команд для развертывания

Быстрый справочник команд, используемых при развертывании Vertex AR на cloud.ru.

---

## 🔌 SSH подключение

```bash
# Основное подключение
ssh -i ~/.ssh/id_rsa rustadmin@192.144.12.68

# С портом (если другой)
ssh -i ~/.ssh/id_rsa -p 22 rustadmin@192.144.12.68

# С логированием
ssh -v -i ~/.ssh/id_rsa rustadmin@192.144.12.68

# Создать alias для быстрого подключения
alias ssh-vertex="ssh -i ~/.ssh/id_rsa rustadmin@192.144.12.68"
# Затем просто: ssh-vertex
```

---

## 🖥️ Системные команды

### Обновление системы

```bash
# Обновить список пакетов
sudo apt update

# Обновить все установленные пакеты
sudo apt upgrade -y

# Удалить неиспользуемые пакеты
sudo apt autoremove -y

# Полное обновление (включая ядро)
sudo apt dist-upgrade -y
```

### Управление пакетами

```bash
# Установить пакет
sudo apt install -y package-name

# Установить несколько пакетов
sudo apt install -y python3 python3-pip python3-venv

# Удалить пакет
sudo apt remove -y package-name

# Найти пакет
apt search python3-pip

# Информация о пакете
apt show python3-pip
```

---

## 📦 Python и виртуальное окружение

### Создание виртуального окружения

```bash
# Перейти в директорию приложения
cd ~/vertex-ar-app/vertex-ar

# Создать виртуальное окружение
python3 -m venv venv

# Активировать виртуальное окружение
source venv/bin/activate

# Деактивировать виртуальное окружение
deactivate
```

### Управление зависимостями

```bash
# Установить зависимости
pip install -r requirements.txt

# Установить простой набор (для production)
pip install -r requirements-simple.txt

# Обновить pip, setuptools, wheel
pip install --upgrade pip setuptools wheel

# Показать установленные пакеты
pip list

# Показать информацию о пакете
pip show uvicorn

# Сохранить зависимости в файл
pip freeze > requirements.txt

# Удалить пакет
pip uninstall package-name -y
```

### Запуск приложения вручную

```bash
# Активировать виртуальное окружение
source ~/vertex-ar-app/venv/bin/activate

# Перейти в директорию приложения
cd ~/vertex-ar-app/vertex-ar

# Запустить приложение
uvicorn main:app --host 127.0.0.1 --port 8000

# Запустить с перезагрузкой при изменении кода
uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Запустить с несколькими workers
uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4

# Остановить приложение
# Нажмите Ctrl+C
```

---

## 🔧 Supervisor (управление процессами)

### Основные команды

```bash
# Перезагрузить конфигурацию
sudo supervisorctl reread

# Обновить конфигурацию
sudo supervisorctl update

# Просмотреть статус всех приложений
sudo supervisorctl status

# Просмотреть статус конкретного приложения
sudo supervisorctl status vertex-ar

# Запустить приложение
sudo supervisorctl start vertex-ar

# Остановить приложение
sudo supervisorctl stop vertex-ar

# Перезагрузить приложение
sudo supervisorctl restart vertex-ar

# Перезагрузить все приложения
sudo supervisorctl restart all
```

### Работа с конфигурацией

```bash
# Отредактировать конфиг
sudo nano /etc/supervisor/conf.d/vertex-ar.conf

# Просмотреть содержимое конфига
cat /etc/supervisor/conf.d/vertex-ar.conf

# Проверить синтаксис конфига
sudo supervisord -c /etc/supervisor/supervisord.conf

# Перезагрузить сам Supervisor
sudo systemctl restart supervisor
```

### Просмотр логов Supervisor

```bash
# Основной лог Supervisor
tail -f /var/log/supervisor/supervisord.log

# Лог конкретного приложения
tail -f /var/log/supervisor/vertex-ar_stdout.log
tail -f /var/log/supervisor/vertex-ar_stderr.log

# Или логи, указанные в конфиге
tail -f /var/log/vertex-ar/access.log
tail -f /var/log/vertex-ar/error.log
```

---

## 🌐 Nginx (веб-сервер и reverse proxy)

### Базовые команды

```bash
# Установить Nginx
sudo apt install -y nginx

# Запустить Nginx
sudo systemctl start nginx

# Остановить Nginx
sudo systemctl stop nginx

# Перезагрузить Nginx
sudo systemctl restart nginx

# Перезагрузить конфигурацию (мягко)
sudo systemctl reload nginx

# Проверить статус
sudo systemctl status nginx

# Автозагрузка при запуске
sudo systemctl enable nginx
```

### Работа с конфигурацией

```bash
# Отредактировать конфиг
sudo nano /etc/nginx/sites-available/vertex-ar

# Протестировать конфиг (ВАЖНО перед перезагрузкой)
sudo nginx -t

# Просмотреть конфиг
cat /etc/nginx/sites-available/vertex-ar

# Активировать конфиг (создать символическую ссылку)
sudo ln -s /etc/nginx/sites-available/vertex-ar /etc/nginx/sites-enabled/vertex-ar

# Деактивировать конфиг
sudo rm /etc/nginx/sites-enabled/vertex-ar

# Просмотреть включенные конфиги
ls -la /etc/nginx/sites-enabled/

# Проверить синтаксис основного конфига
sudo nginx -T
```

### Просмотр логов Nginx

```bash
# Логи доступа (успешные запросы)
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/vertex-ar-access.log

# Логи ошибок
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/vertex-ar-error.log

# Последние 50 строк
tail -50 /var/log/nginx/access.log

# Поиск ошибок 5xx
grep " 5[0-9][0-9] " /var/log/nginx/access.log

# Количество запросов
wc -l /var/log/nginx/access.log
```

---

## 🔐 SSL сертификаты

### Управление сертификатами

```bash
# Проверить существование сертификатов
ls -la /etc/ssl/certs/nft.vertex-art.ru.crt
ls -la /etc/ssl/private/nft.vertex-art.ru.key

# Копировать сертификат на сервер
sudo cp /tmp/certificate.crt /etc/ssl/certs/nft.vertex-art.ru.crt

# Копировать ключ на сервер
sudo cp /tmp/private.key /etc/ssl/private/nft.vertex-art.ru.key

# Установить правильные права для сертификата
sudo chmod 644 /etc/ssl/certs/nft.vertex-art.ru.crt

# Установить правильные права для ключа
sudo chmod 600 /etc/ssl/private/nft.vertex-art.ru.key

# Установить владельца
sudo chown root:root /etc/ssl/certs/nft.vertex-art.ru.crt
sudo chown root:root /etc/ssl/private/nft.vertex-art.ru.key
```

### Проверка сертификата

```bash
# Просмотреть информацию о сертификате
openssl x509 -in /etc/ssl/certs/nft.vertex-art.ru.crt -text -noout

# Проверить срок действия
openssl x509 -enddate -noout -in /etc/ssl/certs/nft.vertex-art.ru.crt

# Проверить дату запуска действия
openssl x509 -startdate -noout -in /etc/ssl/certs/nft.vertex-art.ru.crt

# Проверить отпечаток (fingerprint)
openssl x509 -in /etc/ssl/certs/nft.vertex-art.ru.crt -noout -fingerprint

# Проверить соответствие сертификата и ключа
openssl x509 -noout -modulus -in /etc/ssl/certs/nft.vertex-art.ru.crt | openssl md5
openssl rsa -noout -modulus -in /etc/ssl/private/nft.vertex-art.ru.key | openssl md5
# Хеши должны совпадать
```

### Проверка SSL через интернет

```bash
# Проверить SSL сертификат через curl
curl -I https://nft.vertex-art.ru

# Проверить SSL цепь
curl -vI https://nft.vertex-art.ru 2>&1 | grep "subject:"

# Онлайн проверка (с другой машины)
openssl s_client -connect nft.vertex-art.ru:443 -showcerts

# Проверить HTTPS редирект
curl -I http://nft.vertex-art.ru
# Должен быть 301 редирект на https
```

---

## 📁 Управление файлами и директориями

### Основные команды

```bash
# Перейти в директорию
cd ~/vertex-ar-app

# Показать текущую директорию
pwd

# Создать директорию
mkdir /home/rustadmin/vertex-ar-app

# Создать вложенные директории
mkdir -p /var/log/vertex-ar

# Удалить пустую директорию
rmdir /path/to/empty/dir

# Удалить директорию с содержимым
rm -rf /path/to/dir

# Копировать файл
cp /source/file /destination/file

# Копировать директорию
cp -r /source/dir /destination/dir

# Переместить файл
mv /source/file /destination/file

# Переименовать файл
mv /path/to/old_name /path/to/new_name

# Просмотреть содержимое файла
cat /path/to/file

# Просмотреть большой файл постранично
less /path/to/file

# Первые 10 строк файла
head -10 /path/to/file

# Последние 10 строк файла
tail -10 /path/to/file

# Следить за изменениями файла в реальном времени
tail -f /path/to/file
```

### Права доступа

```bash
# Изменить права доступа
chmod 755 /path/to/file
chmod 600 /path/to/file
chmod 700 /path/to/dir

# Изменить владельца файла
chown rustadmin:rustadmin /path/to/file

# Изменить владельца директории и содержимого
chown -R rustadmin:rustadmin /path/to/dir

# Просмотреть права доступа
ls -la /path/to/file
```

### Поиск файлов

```bash
# Найти файлы по названию
find /home -name "*.py"

# Найти файлы по типу
find /home -type f -name "*.txt"

# Найти директории
find /home -type d -name "backups"

# Найти и удалить файлы
find /home -name "*.tmp" -delete

# Поиск в содержимом файлов
grep -r "error" /var/log/vertex-ar/
grep -l "import" /home/rustadmin/vertex-ar-app/vertex-ar/*.py
```

---

## 📊 Мониторинг и диагностика

### Информация о системе

```bash
# Информация об ОС
uname -a

# Версия Ubuntu
lsb_release -a

# Архитектура процессора
uname -m

# Информация о процессоре
nproc
cat /proc/cpuinfo

# Информация об оперативной памяти
free -h

# Дисковое пространство
df -h

# Размер директории
du -sh /home/rustadmin/vertex-ar-app/

# Загруженность системы
uptime

# Процесс список
ps aux

# Поиск процесса
ps aux | grep uvicorn

# Мониторинг в реальном времени
top
# или
htop

# Сетевые подключения
netstat -tlpn
netstat -tlpn | grep 8000
netstat -tlpn | grep :443

# Список открытых портов
sudo lsof -i -P -n

# Проверить конкретный порт
sudo lsof -i :8000
sudo lsof -i :80
sudo lsof -i :443
```

### Диагностика приложения

```bash
# Проверить, слушает ли приложение порт
curl http://127.0.0.1:8000/api/health

# Проверить через Nginx
curl -I https://nft.vertex-art.ru

# Проверить конкретный эндпоинт
curl https://nft.vertex-art.ru/api/health

# Подробный вывод curl
curl -v https://nft.vertex-art.ru

# Проверить DNS
nslookup nft.vertex-art.ru
dig nft.vertex-art.ru

# Проверить соединение
ping 192.144.12.68

# Проверить доступность на портах
telnet 127.0.0.1 8000
telnet 127.0.0.1 443
```

---

## 💾 Резервное копирование

### Резервные копии базы данных

```bash
# Создать резервную копию SQLite
cp /home/rustadmin/vertex-ar-app/vertex-ar/app_data.db /home/rustadmin/backups/app_data_$(date +%Y%m%d_%H%M%S).db

# Использовать встроенный скрипт
cd ~/vertex-ar-app/vertex-ar
python3 backup_cli.py create

# Просмотреть созданные резервные копии
ls -lh backups/

# Восстановить из резервной копии
python3 backup_cli.py restore backup_2024-11-21_12-00-00.zip
```

### Резервные копии файлов

```bash
# Создать архив всего приложения
tar -czf /home/rustadmin/backups/vertex-ar-app_$(date +%Y%m%d_%H%M%S).tar.gz /home/rustadmin/vertex-ar-app/

# Создать архив только исходного кода
tar -czf /home/rustadmin/backups/vertex-ar-src_$(date +%Y%m%d_%H%M%S).tar.gz /home/rustadmin/vertex-ar-app/vertex-ar/ --exclude=.git --exclude=.venv --exclude=__pycache__

# Распаковать архив
tar -xzf /home/rustadmin/backups/vertex-ar-app_20241121_120000.tar.gz -C /
```

---

## 🔄 Git и управление версиями

### Базовые команды Git

```bash
# Инициализировать репозиторий
git init

# Клонировать репозиторий
git clone https://github.com/your-repo/vertex-ar.git

# Проверить статус
git status

# Добавить файлы в staging
git add .

# Создать коммит
git commit -m "Описание изменений"

# Отправить на сервер
git push origin main

# Обновить из сервера
git pull origin main

# Просмотреть историю
git log

# Просмотреть различия
git diff
git diff HEAD~1

# Откатить изменения
git revert HEAD
git reset --hard HEAD~1
```

---

## ⚙️ Cron задачи (расписание)

### Управление Cron

```bash
# Просмотреть текущие Cron задачи
crontab -l

# Отредактировать Cron задачи
crontab -e

# Просмотреть Cron задачи другого пользователя
sudo crontab -u rustadmin -l

# Отредактировать Cron задачи другого пользователя
sudo crontab -u rustadmin -e

# Логи Cron
grep CRON /var/log/syslog
# или
tail -f /var/log/syslog | grep CRON
```

### Примеры Cron выражений

```bash
# Ежедневно в 2:00 AM
0 2 * * * /path/to/script.sh

# Каждый час
0 * * * * /path/to/script.sh

# Каждые 30 минут
*/30 * * * * /path/to/script.sh

# По будням (пн-пт) в 9:00
0 9 * * 1-5 /path/to/script.sh

# Каждое воскресенье в полночь
0 0 * * 0 /path/to/script.sh

# Первый день месяца в 00:00
0 0 1 * * /path/to/script.sh
```

---

## 🔒 Безопасность

### Управление пользователями

```bash
# Создать нового пользователя
sudo useradd -m -s /bin/bash newuser

# Установить пароль
sudo passwd newuser

# Удалить пользователя
sudo userdel -r newuser

# Добавить пользователя в sudo группу
sudo usermod -aG sudo newuser

# Просмотреть все пользователей
cat /etc/passwd

# Просмотреть группы пользователя
id rustadmin
```

### Firewall (UFW)

```bash
# Включить firewall
sudo ufw enable

# Отключить firewall
sudo ufw disable

# Просмотреть правила
sudo ufw status

# Открыть порт
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443

# Закрыть порт
sudo ufw deny 8000

# Удалить правило
sudo ufw delete allow 8000

# Открыть порт для конкретного IP
sudo ufw allow from 192.168.1.100 to any port 22
```

---

## 📚 Справка по команде

```bash
# Справка по команде
man ls
man ssh
man curl

# Краткая справка
ls --help
ssh --help

# Информация о команде
which python3
whereis python3

# История команд
history

# Последняя выполненная команда с 'python'
history | grep python
```

---

## 🆘 Решение проблем

### Проверка ошибок

```bash
# Просмотреть последние ошибки системы
dmesg | tail -20

# Просмотреть системные логи
tail -f /var/log/syslog

# Просмотреть логи приложения
tail -f /var/log/vertex-ar/error.log

# Поиск ошибок в логах
grep -i "error" /var/log/vertex-ar/error.log
```

### Перезагрузка

```bash
# Мягкая перезагрузка (с сохранением)
sudo reboot

# Жесткая перезагрузка (может привести к потере данных)
sudo shutdown -r now

# Выключение
sudo shutdown -h now

# Перезагрузка через N минут
sudo shutdown -r +10 "Перезагрузка через 10 минут"

# Отмена перезагрузки
sudo shutdown -c
```

---

## 📝 Быстрые шаблоны

### Стартовый скрипт

```bash
#!/bin/bash
cd ~/vertex-ar-app/vertex-ar
source ~/vertex-ar-app/venv/bin/activate
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Скрипт резервного копирования

```bash
#!/bin/bash
cd ~/vertex-ar-app/vertex-ar
source ~/vertex-ar-app/venv/bin/activate
python3 backup_cli.py create
```

### Скрипт проверки здоровья

```bash
#!/bin/bash
echo "Статус приложения:"
sudo supervisorctl status vertex-ar
echo ""
echo "Статус Nginx:"
sudo systemctl status nginx
echo ""
echo "Здоровье приложения:"
curl -s http://127.0.0.1:8000/api/health | python3 -m json.tool
```

---

**Версия**: 1.0
**Последнее обновление**: 2024-11-21
**Статус**: Активно используется
