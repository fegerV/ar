# Интеграция удаленных хранилищ для бэкапов

Vertex AR поддерживает автоматическую синхронизацию бэкапов с облачными хранилищами:
- **Яндекс Диск**
- **Google Drive**

## Содержание

1. [Настройка Яндекс Диска](#настройка-яндекс-диска)
2. [Настройка Google Drive](#настройка-google-drive)
3. [API для работы с удаленными хранилищами](#api)
4. [Автоматическая синхронизация](#автоматическая-синхронизация)

---

## Настройка Яндекс Диска

### 1. Получение OAuth токена

Для работы с Яндекс Диском нужен OAuth токен:

1. Перейдите на [OAuth-страницу Яндекса](https://oauth.yandex.ru/)
2. Зарегистрируйте приложение
3. Получите права доступа к Яндекс Диску
4. Сохраните OAuth токен

### 2. Конфигурация

Создайте файл `config/remote_storage.json` на основе примера:

```json
{
  "yandex_disk": {
    "enabled": true,
    "oauth_token": "ВАШ_YANDEX_OAUTH_TOKEN"
  }
}
```

### 3. Проверка подключения

```bash
curl -X GET "http://localhost:8000/remote-storage/test-connection/yandex_disk" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## Настройка Google Drive

### 1. Создание проекта в Google Cloud

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект
3. Включите Google Drive API
4. Создайте учетные данные (OAuth 2.0 или Service Account)

### 2. Получение токена доступа

#### Вариант A: OAuth 2.0 (для личных аккаунтов)

```python
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/drive.file']
flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)
print(f"Access token: {creds.token}")
```

#### Вариант B: Service Account (для организаций)

Скачайте JSON-файл ключа сервисного аккаунта и используйте его для генерации access token.

### 3. Конфигурация

```json
{
  "google_drive": {
    "enabled": true,
    "credentials": {
      "access_token": "ВАШ_GOOGLE_DRIVE_ACCESS_TOKEN",
      "folder_id": "ID_ПАПКИ_ДЛЯ_БЭКАПОВ"
    }
  }
}
```

**Примечание**: `folder_id` — опционально. Если указан, все бэкапы будут сохраняться в эту папку.

### 4. Проверка подключения

```bash
curl -X GET "http://localhost:8000/remote-storage/test-connection/google_drive" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## API для работы с удаленными хранилищами

### Обновление конфигурации

```bash
curl -X POST "http://localhost:8000/remote-storage/config" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "yandex_disk": {
      "enabled": true,
      "oauth_token": "YOUR_TOKEN"
    }
  }'
```

### Получение информации о хранилище

```bash
curl -X GET "http://localhost:8000/remote-storage/storage-info/yandex_disk" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

Ответ:
```json
{
  "success": true,
  "provider": "yandex_disk",
  "total_gb": 10.0,
  "used_gb": 2.5,
  "available_gb": 7.5,
  "trash_gb": 0.1
}
```

### Синхронизация бэкапа в облако

```bash
curl -X POST "http://localhost:8000/remote-storage/sync" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "backup_path": "/path/to/backup/db_backup_20231124_120000.db",
    "provider": "yandex_disk",
    "remote_dir": "vertex-ar-backups"
  }'
```

### Синхронизация всех бэкапов

```bash
curl -X POST "http://localhost:8000/remote-storage/sync-all/yandex_disk" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Список файлов в облаке

```bash
curl -X GET "http://localhost:8000/remote-storage/list/yandex_disk" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

Ответ:
```json
{
  "success": true,
  "provider": "yandex_disk",
  "files": [
    {
      "name": "db_backup_20231124_120000.db",
      "size": 1048576,
      "created": "2023-11-24T12:00:00Z",
      "modified": "2023-11-24T12:00:00Z",
      "provider": "yandex_disk"
    }
  ],
  "count": 1
}
```

### Скачивание бэкапа из облака

```bash
curl -X POST "http://localhost:8000/remote-storage/download" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "remote_filename": "db_backup_20231124_120000.db",
    "provider": "yandex_disk",
    "remote_dir": "vertex-ar-backups"
  }'
```

После скачивания используйте стандартный endpoint для восстановления:

```bash
curl -X POST "http://localhost:8000/backups/restore" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "backup_path": "/path/to/downloaded/db_backup_20231124_120000.db",
    "verify_checksum": true
  }'
```

### Удаление бэкапа из облака

```bash
curl -X DELETE "http://localhost:8000/remote-storage/delete/yandex_disk?remote_path=vertex-ar-backups/db_backup_20231124_120000.db" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## Автоматическая синхронизация

### Настройка автоматической синхронизации с планировщиком

Можно добавить автоматическую синхронизацию в существующий планировщик бэкапов.

Отредактируйте `backup_scheduler.py`:

```python
def schedule_remote_sync(self):
    """Schedule automatic sync to remote storage."""
    if not self.enable_remote_sync:
        return
    
    from remote_storage import get_remote_storage_manager
    
    def sync_latest_backup():
        try:
            manager = create_backup_manager()
            storage_manager = get_remote_storage_manager()
            
            # Get latest backup
            backups = manager.list_backups("all")
            if not backups:
                return
            
            latest = backups[0]
            backup_path = Path(latest.get("backup_path"))
            
            # Sync to all configured providers
            for provider in storage_manager.list_providers():
                storage = storage_manager.get_storage(provider)
                if storage:
                    manager.sync_to_remote(backup_path, storage)
                    logger.info(f"Synced to {provider}")
        except Exception as e:
            logger.error("Remote sync failed", error=str(e))
    
    self.scheduler.add_job(
        sync_latest_backup,
        'cron',
        hour=2,
        minute=0,
        id='remote_sync'
    )
```

### Синхронизация через cron

Альтернативно, настройте cron-задачу:

```bash
# Синхронизация в 2:00 каждый день
0 2 * * * cd /path/to/vertex-ar && python3 -c "from backup_manager import create_backup_manager; from remote_storage import get_remote_storage_manager; manager = create_backup_manager(); storage_manager = get_remote_storage_manager(); [manager.sync_to_remote(manager.list_backups('all')[0]['backup_path'], storage_manager.get_storage(p)) for p in storage_manager.list_providers()]"
```

---

## Рекомендации по безопасности

1. **Храните токены в безопасном месте**: Используйте переменные окружения или encrypted secrets
2. **Ограничьте права доступа**: Дайте приложению минимальные необходимые права
3. **Регулярно обновляйте токены**: Особенно для OAuth токенов
4. **Шифруйте конфиг**: Файл `config/remote_storage.json` содержит чувствительные данные
5. **Используйте HTTPS**: Всегда используйте защищенное соединение

## Мониторинг

### Проверка статуса синхронизации

```bash
# Проверить доступность хранилища
curl -X GET "http://localhost:8000/remote-storage/test-connection/yandex_disk" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# Получить информацию о занятом месте
curl -X GET "http://localhost:8000/remote-storage/storage-info/yandex_disk" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Логирование

Все операции с удаленными хранилищами логируются в стандартный лог приложения:

```python
logger.info("Backup synced to remote storage", provider="yandex_disk")
logger.error("Failed to sync backup", error=str(e))
```

---

## Устранение неполадок

### Ошибка: "OAuth token expired"

**Решение**: Обновите OAuth токен в конфигурации.

### Ошибка: "Insufficient storage"

**Решение**: Освободите место в облачном хранилище или удалите старые бэкапы.

### Ошибка: "Connection timeout"

**Решение**: Проверьте интернет-соединение и firewall настройки.

### Ошибка: "File not found in remote storage"

**Решение**: Проверьте `remote_dir` и имя файла. Используйте `/remote-storage/list/{provider}` для просмотра файлов.

---

## Примеры использования

### Полный цикл бэкапа с синхронизацией

```bash
# 1. Создать бэкап
BACKUP_RESPONSE=$(curl -s -X POST "http://localhost:8000/backups/create" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type": "full"}')

# 2. Извлечь путь к бэкапу
BACKUP_PATH=$(echo $BACKUP_RESPONSE | jq -r '.backup.backup_path')

# 3. Синхронизировать с Яндекс Диском
curl -X POST "http://localhost:8000/remote-storage/sync" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"backup_path\": \"$BACKUP_PATH\", \"provider\": \"yandex_disk\"}"

# 4. Синхронизировать с Google Drive
curl -X POST "http://localhost:8000/remote-storage/sync" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"backup_path\": \"$BACKUP_PATH\", \"provider\": \"google_drive\"}"
```

### Восстановление из облака

```bash
# 1. Список файлов в облаке
curl -X GET "http://localhost:8000/remote-storage/list/yandex_disk" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 2. Скачать нужный бэкап
curl -X POST "http://localhost:8000/remote-storage/download" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "remote_filename": "db_backup_20231124_120000.db",
    "provider": "yandex_disk"
  }'

# 3. Восстановить из скачанного бэкапа
curl -X POST "http://localhost:8000/backups/restore" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "backup_path": "backups/database/db_backup_20231124_120000.db"
  }'
```

---

## Заключение

Интеграция с облачными хранилищами обеспечивает:
- ✅ Дополнительную защиту от потери данных
- ✅ Возможность восстановления при полном отказе сервера
- ✅ Долгосрочное хранение бэкапов
- ✅ Легкий доступ к бэкапам из любой точки

Рекомендуется настроить автоматическую синхронизацию хотя бы с одним облачным провайдером.
