# Система бэкапов Vertex AR

Полное руководство по системе резервного копирования и восстановления данных.

## Обзор

Система бэкапов Vertex AR предоставляет надежное решение для создания, управления и восстановления резервных копий:

- **База данных SQLite** - все данные о клиентах, портретах, видео и пользователях
- **Файлы хранилища** - изображения, видео, превью и NFT-маркеры
- **Автоматическая ротация** - удаление старых бэкапов
- **Проверка целостности** - SHA256 чексуммы для каждого бэкапа
- **Восстановление** - простое восстановление из любого бэкапа

## Компоненты системы

### 1. BackupManager (`backup_manager.py`)

Основной Python модуль для управления бэкапами:

```python
from backup_manager import create_backup_manager

# Создать менеджер бэкапов
manager = create_backup_manager()

# Создать полный бэкап
result = manager.create_full_backup()

# Создать бэкап только базы данных
result = manager.backup_database()

# Создать бэкап только файлов
result = manager.backup_storage()

# Список всех бэкапов
backups = manager.list_backups("all")

# Статистика
stats = manager.get_backup_stats()

# Ротация старых бэкапов
removed = manager.rotate_backups()

# Восстановление
manager.restore_database(Path("backups/database/db_backup_20240101_120000.db"))
manager.restore_storage(Path("backups/storage/storage_backup_20240101_120000.tar.gz"))
```

### 2. CLI интерфейс (`backup_cli.py`)

Консольная утилита для управления бэкапами:

```bash
# Создать полный бэкап
python backup_cli.py create --type full

# Создать бэкап базы данных
python backup_cli.py create --type database

# Создать бэкап файлов
python backup_cli.py create --type storage

# Список всех бэкапов
python backup_cli.py list

# Статистика
python backup_cli.py stats

# Восстановление
python backup_cli.py restore backups/database/db_backup_20240101_120000.db

# Ротация старых бэкапов
python backup_cli.py rotate --max-backups 7
```

### 3. Bash скрипт (`backup.sh`)

Shell скрипт для автоматизации и интеграции с cron:

```bash
# Создать полный бэкап
./backup.sh

# Создать бэкап базы данных
./backup.sh --type database

# Указать количество сохраняемых бэкапов
./backup.sh --max-backups 14

# Указать директорию для бэкапов
./backup.sh --backup-dir /mnt/backups
```

### 4. REST API (`app/api/backups.py`)

API endpoints для интеграции с админ-панелью:

```bash
# Создать бэкап
POST /backups/create
{
  "type": "full"
}

# Список бэкапов
GET /backups/list?backup_type=all

# Статистика
GET /backups/stats

# Восстановление
POST /backups/restore
{
  "backup_path": "backups/database/db_backup_20240101_120000.db",
  "verify_checksum": true
}

# Ротация
POST /backups/rotate?max_backups=7
```

## Типы бэкапов

### Full (Полный бэкап)

Создает резервную копию и базы данных, и файлов хранилища:

- Файл базы данных: `backups/database/db_backup_YYYYMMDD_HHMMSS.db`
- Архив файлов: `backups/storage/storage_backup_YYYYMMDD_HHMMSS.tar.gz`
- Метаданные: `backups/full/full_backup_YYYYMMDD_HHMMSS.json`

**Когда использовать:** 
- Перед важными обновлениями системы
- Регулярные ежедневные/еженедельные бэкапы
- Перед миграцией на новый сервер

### Database (База данных)

Создает резервную копию только SQLite базы данных:

- Размер: обычно < 10 MB
- Скорость: очень быстро (секунды)
- Содержит: пользователей, клиентов, портреты, видео, метаданные

**Когда использовать:**
- Частые бэкапы (каждые 6 часов)
- Перед операциями с данными
- Для быстрого восстановления метаданных

### Storage (Файлы)

Создает сжатый архив файлов хранилища:

- Размер: зависит от объема файлов (может быть > 1 GB)
- Скорость: зависит от размера и компрессии
- Содержит: изображения, видео, превью, NFT-маркеры

**Когда использовать:**
- Еженедельные бэкапы файлов
- Перед очисткой старых файлов
- Для архивирования завершенных проектов

## Структура бэкапов

```
backups/
├── database/
│   ├── db_backup_20240101_120000.db
│   ├── db_backup_20240101_120000.json (метаданные)
│   ├── db_backup_20240102_120000.db
│   └── db_backup_20240102_120000.json
├── storage/
│   ├── storage_backup_20240101_120000.tar.gz
│   ├── storage_backup_20240101_120000.json (метаданные)
│   ├── storage_backup_20240102_120000.tar.gz
│   └── storage_backup_20240102_120000.json
├── full/
│   ├── full_backup_20240101_120000.json
│   └── full_backup_20240102_120000.json
└── backup.log
```

### Формат метаданных

Каждый бэкап сопровождается JSON файлом с метаданными:

```json
{
  "timestamp": "20240101_120000",
  "type": "database",
  "original_path": "/app/data/app_data.db",
  "backup_path": "/app/backups/database/db_backup_20240101_120000.db",
  "file_size": 2048576,
  "checksum": "a1b2c3d4...",
  "created_at": "2024-01-01T12:00:00",
  "file_count": 150
}
```

## Автоматизация с Cron

### Рекомендуемое расписание

```bash
# Редактировать crontab
crontab -e

# Полный бэкап каждый день в 2:00
0 2 * * * /path/to/vertex-ar/backup.sh --type full >> /var/log/vertex-ar-backup.log 2>&1

# База данных каждые 6 часов
0 */6 * * * /path/to/vertex-ar/backup.sh --type database

# Еженедельный бэкап файлов (воскресенье в 3:00)
0 3 * * 0 /path/to/vertex-ar/backup.sh --type storage

# Ежедневная ротация старых бэкапов (в 4:00)
0 4 * * * cd /path/to/vertex-ar && python3 backup_cli.py rotate --max-backups 7
```

### С уведомлениями в Telegram

```bash
# Установить переменные окружения в crontab
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Полный бэкап с уведомлением
0 2 * * * /path/to/vertex-ar/backup.sh --type full
```

## Восстановление данных

### Восстановление базы данных

```bash
# Через CLI
python backup_cli.py restore backups/database/db_backup_20240101_120000.db

# Через bash скрипт (ручная команда)
# 1. Остановить приложение
docker-compose down

# 2. Создать резервную копию текущей БД
cp app_data/app_data.db app_data/app_data.db.backup

# 3. Восстановить из бэкапа
cp backups/database/db_backup_20240101_120000.db app_data/app_data.db

# 4. Запустить приложение
docker-compose up -d
```

### Восстановление файлов

```bash
# Через CLI
python backup_cli.py restore backups/storage/storage_backup_20240101_120000.tar.gz

# Ручное восстановление
# 1. Остановить приложение
docker-compose down

# 2. Создать резервную копию текущих файлов
mv storage storage_backup

# 3. Распаковать бэкап
tar -xzf backups/storage/storage_backup_20240101_120000.tar.gz

# 4. Запустить приложение
docker-compose up -d
```

### Полное восстановление

```bash
# 1. Остановить приложение
docker-compose down

# 2. Восстановить базу данных
python backup_cli.py restore backups/database/db_backup_20240101_120000.db

# 3. Восстановить файлы
python backup_cli.py restore backups/storage/storage_backup_20240101_120000.tar.gz

# 4. Запустить приложение
docker-compose up -d
```

## Проверка целостности

Каждый бэкап создается с SHA256 чексуммой для проверки целостности:

```bash
# Автоматическая проверка при восстановлении
python backup_cli.py restore backups/database/db_backup_20240101_120000.db

# Отключить проверку (не рекомендуется)
python backup_cli.py restore backups/database/db_backup_20240101_120000.db --no-verify
```

### Ручная проверка чексуммы

```bash
# Вычислить чексумму файла
sha256sum backups/database/db_backup_20240101_120000.db

# Сравнить с чексуммой из метаданных
cat backups/database/db_backup_20240101_120000.json | grep checksum
```

## Ротация бэкапов

Система автоматически удаляет старые бэкапы, сохраняя указанное количество последних:

```python
# По умолчанию сохраняется 7 последних бэкапов
manager = create_backup_manager(max_backups=7)
manager.rotate_backups()

# Изменить количество сохраняемых бэкапов
manager = create_backup_manager(max_backups=30)
```

### Рекомендации по ротации

- **Ежедневные бэкапы:** сохранять 7-14 последних (1-2 недели)
- **Еженедельные бэкапы:** сохранять 4-8 последних (1-2 месяца)
- **Ежемесячные архивы:** переносить в отдельное хранилище

## Хранение бэкапов

### Локальное хранение

```bash
# По умолчанию: ./backups/
./backup.sh

# Указать директорию
./backup.sh --backup-dir /mnt/backups
```

### Внешнее хранилище

Рекомендуется копировать бэкапы на внешнее хранилище:

```bash
# Копировать на NAS/удаленный сервер
rsync -avz backups/ user@backup-server:/backups/vertex-ar/

# Копировать в облако (AWS S3)
aws s3 sync backups/ s3://my-bucket/vertex-ar-backups/

# Копировать в облако (Google Cloud Storage)
gsutil -m rsync -r backups/ gs://my-bucket/vertex-ar-backups/
```

### Docker volume бэкапы

Если используется Docker, также можно бэкапить volumes:

```bash
# Бэкап Docker volume
docker run --rm \
  -v vertex_ar_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/docker_volume_backup.tar.gz -C /data .

# Восстановление Docker volume
docker run --rm \
  -v vertex_ar_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/docker_volume_backup.tar.gz -C /data
```

## Мониторинг бэкапов

### Проверка статуса

```bash
# Статистика через CLI
python backup_cli.py stats

# Список последних бэкапов
python backup_cli.py list | head -20

# Проверить размер бэкапов
du -sh backups/*

# Проверить количество бэкапов
find backups -type f -name "*.db" | wc -l
find backups -type f -name "*.tar.gz" | wc -l
```

### Логи

Все операции логируются в `backups/backup.log`:

```bash
# Просмотр логов
tail -f backups/backup.log

# Поиск ошибок
grep ERROR backups/backup.log

# Поиск успешных бэкапов
grep "Backup completed successfully" backups/backup.log
```

### Алерты

Настройка алертов при проблемах с бэкапами:

```bash
#!/bin/bash
# check_backup_status.sh

# Проверить возраст последнего бэкапа
LATEST_BACKUP=$(find backups/database -name "*.db" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2)
BACKUP_AGE=$(($(date +%s) - $(stat -c %Y "$LATEST_BACKUP")))
MAX_AGE=$((24 * 60 * 60))  # 24 часа

if [ $BACKUP_AGE -gt $MAX_AGE ]; then
    echo "WARNING: Last backup is older than 24 hours!"
    # Отправить уведомление
fi
```

## API интеграция

### Использование в коде

```python
from fastapi import FastAPI
from app.api.backups import router

app = FastAPI()
app.include_router(router, tags=["backups"])
```

### Примеры запросов

```python
import requests

# Создать бэкап
response = requests.post(
    "http://localhost:8000/backups/create",
    json={"type": "full"},
    cookies={"authToken": "your_admin_token"}
)

# Получить статистику
response = requests.get(
    "http://localhost:8000/backups/stats",
    cookies={"authToken": "your_admin_token"}
)
stats = response.json()
print(f"Total backups: {stats['total_backups']}")
print(f"Total size: {stats['total_size_mb']} MB")
```

## Безопасность

### Права доступа

```bash
# Ограничить доступ к бэкапам
chmod 700 backups
chmod 600 backups/**/*

# Только root может читать бэкапы
chown root:root backups -R
```

### Шифрование

Для дополнительной безопасности можно шифровать бэкапы:

```bash
# Шифрование с помощью GPG
gpg --symmetric --cipher-algo AES256 backups/database/db_backup_20240101_120000.db

# Расшифровка
gpg --decrypt backups/database/db_backup_20240101_120000.db.gpg > restored.db

# Шифрование с помощью OpenSSL
openssl enc -aes-256-cbc -salt -in backup.tar.gz -out backup.tar.gz.enc

# Расшифровка
openssl enc -aes-256-cbc -d -in backup.tar.gz.enc -out backup.tar.gz
```

## Решение проблем

### Бэкап не создается

```bash
# Проверить права доступа
ls -la backups/

# Проверить свободное место
df -h

# Проверить логи
tail -100 backups/backup.log

# Проверить процессы
ps aux | grep backup
```

### Ошибка при восстановлении

```bash
# Проверить целостность бэкапа
sha256sum backups/database/db_backup_20240101_120000.db

# Проверить формат базы данных
file backups/database/db_backup_20240101_120000.db

# Попробовать открыть базу
sqlite3 backups/database/db_backup_20240101_120000.db "SELECT COUNT(*) FROM users;"

# Проверить архив
tar -tzf backups/storage/storage_backup_20240101_120000.tar.gz | head
```

### Медленные бэкапы

```bash
# Проверить размер базы данных
ls -lh app_data/app_data.db

# Проверить размер storage
du -sh storage/

# Оптимизировать базу данных
sqlite3 app_data/app_data.db "VACUUM;"

# Использовать быструю компрессию
# В backup_manager.py изменить compression="gz" на compression=""
```

## Лучшие практики

1. **Регулярность:** Автоматизируйте бэкапы с помощью cron
2. **3-2-1 правило:** 3 копии данных, 2 разных носителя, 1 офсайт копия
3. **Тестирование:** Регулярно проверяйте восстановление из бэкапов
4. **Мониторинг:** Следите за успешностью бэкапов и размером
5. **Документация:** Документируйте процедуры восстановления
6. **Шифрование:** Шифруйте бэкапы при хранении на внешних носителях
7. **Ротация:** Не храните слишком много старых бэкапов
8. **Версионность:** Используйте метаданные для отслеживания версий
9. **Уведомления:** Настройте алерты при проблемах с бэкапами
10. **Офсайт:** Храните копии бэкапов вне основного сервера

## Поддержка

При возникновении проблем:

1. Проверьте логи: `tail -100 backups/backup.log`
2. Проверьте статус: `python backup_cli.py stats`
3. Проверьте права доступа: `ls -la backups/`
4. Проверьте свободное место: `df -h`
5. Обратитесь к разделу "Решение проблем" выше

## Changelog

- **v1.0.0** - Первый релиз системы бэкапов
  - Создание full/database/storage бэкапов
  - CLI и bash интерфейсы
  - REST API endpoints
  - Автоматическая ротация
  - Проверка целостности с SHA256
  - Полная документация
