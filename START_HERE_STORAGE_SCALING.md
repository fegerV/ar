# 🚀 Storage Scaling - Start Here!

## Что это?

Vertex AR теперь поддерживает **масштабируемое хранилище**. Вы можете подключить удаленный MinIO сервер или облачное хранилище вместо локального диска.

## ⚡ Быстрый старт (2 минуты)

### Проверьте текущую конфигурацию

```bash
python check_storage.py
```

### Переключитесь на удаленное хранилище

Отредактируйте `.env`:

```env
STORAGE_TYPE=minio
MINIO_ENDPOINT=your-minio-server:9000
MINIO_ACCESS_KEY=your-key
MINIO_SECRET_KEY=your-secret
MINIO_BUCKET=vertex-ar
MINIO_SECURE=true
```

Перезапустите:

```bash
docker-compose restart
# или
systemctl restart vertex-ar
```

Проверьте:

```bash
python check_storage.py
```

**Готово!** 🎉

## 📖 Куда идти дальше?

### Для быстрого старта
👉 [**SCALING_QUICK_START_RU.md**](./SCALING_QUICK_START_RU.md) - Пошаговая инструкция на русском

### Для полного понимания
👉 [**SCALING_STORAGE_GUIDE.md**](./SCALING_STORAGE_GUIDE.md) - Подробное руководство

### Для Docker деплоя
👉 [**DOCKER_COMPOSE_EXAMPLES.md**](./DOCKER_COMPOSE_EXAMPLES.md) - Примеры конфигураций

### Что нового?
👉 [**WHATS_NEW_STORAGE_SCALING.md**](./WHATS_NEW_STORAGE_SCALING.md) - Обзор изменений

### Технические детали
👉 [**STORAGE_SCALING_IMPLEMENTATION.md**](./STORAGE_SCALING_IMPLEMENTATION.md) - Реализация

## 💡 Зачем это нужно?

### Проблема
- 💾 Локальный диск сервера ограничен
- 📈 AR контент растет
- 💰 Расширение диска дорого

### Решение
- ☁️ Удаленное хранилище неограниченно
- 📦 Платите только за использованное
- 🔄 Легко масштабируется

### Экономия
100GB хранилища:
- Локальный диск: **$12-25/мес**
- Облако: **$0.50-5/мес**
- Экономия: **до 95%** 💰

## 🎯 Варианты использования

### 1. Локальное (по умолчанию)
```env
STORAGE_TYPE=local
```
✅ Разработка, тестирование

### 2. Свой MinIO сервер
```env
STORAGE_TYPE=minio
MINIO_ENDPOINT=minio.company.com:9000
```
✅ Продакшен, полный контроль

### 3. DigitalOcean Spaces
```env
STORAGE_TYPE=minio
MINIO_ENDPOINT=nyc3.digitaloceanspaces.com
```
✅ Простота, CDN, $5/мес

### 4. Backblaze B2
```env
STORAGE_TYPE=minio
MINIO_ENDPOINT=s3.us-west-000.backblazeb2.com
```
✅ Дешево, $0.50/100GB

### 5. Yandex Object Storage
```env
STORAGE_TYPE=minio
MINIO_ENDPOINT=storage.yandexcloud.net
```
✅ РФ, локальный дата-центр

## ✅ Проверка работы

```bash
python check_storage.py
```

Ожидаемый результат:
```
============================================================
Vertex AR - Storage Connection Check
============================================================
📦 Storage Type: minio
✅ MinIO endpoint is reachable
✅ Test file upload successful
✅ Test file download successful
🎉 Storage check completed successfully!
============================================================
```

## 🆘 Не работает?

### "Connection refused"
```bash
# Проверьте MinIO
curl http://your-minio:9000/minio/health/live
```

### "Access denied"
Проверьте ключи в `.env`

### Откат
```env
STORAGE_TYPE=local
```
Перезапустите приложение

## 📚 Полная документация

| Документ | Описание | Размер |
|----------|----------|--------|
| [WHATS_NEW_STORAGE_SCALING.md](./WHATS_NEW_STORAGE_SCALING.md) | Что нового | 7KB |
| [STORAGE_SCALING_README.md](./STORAGE_SCALING_README.md) | Краткий гид | 6KB |
| [SCALING_QUICK_START_RU.md](./SCALING_QUICK_START_RU.md) | Быстрый старт (RU) | 9KB |
| [SCALING_STORAGE_GUIDE.md](./SCALING_STORAGE_GUIDE.md) | Полное руководство | 14KB |
| [DOCKER_COMPOSE_EXAMPLES.md](./DOCKER_COMPOSE_EXAMPLES.md) | Docker примеры | 7KB |

## 🔧 Инструменты

| Файл | Назначение |
|------|-----------|
| `check_storage.py` | Проверка подключения |
| `docker-compose.minio-remote.yml` | Docker для удаленного MinIO |
| `vertex-ar/.env.production.example` | Примеры конфигов |

## 💬 Нужна помощь?

1. 📖 Читайте документацию выше
2. 🧪 Запустите `python check_storage.py`
3. 💬 Создайте issue с выводом скрипта

## 🎓 Для разработчиков

### Новый модуль
`vertex-ar/storage_adapter.py` - Унифицированный интерфейс хранилища

### API
```python
from storage_adapter import get_storage, upload_file

# Получить текущее хранилище
storage = get_storage()

# Загрузить файл
url = storage.upload_file(content, "file.txt", "text/plain")

# Или через compatibility функцию
url = upload_file(content, "file.txt", "text/plain")
```

### Тесты
`vertex-ar/tests/test_storage_adapter.py`

## 🎉 Готово!

Теперь вы можете:
- ✅ Масштабировать хранилище неограниченно
- ✅ Экономить на дисковом пространстве
- ✅ Использовать облачные провайдеры
- ✅ Легко мигрировать данные

**Начните с:** [SCALING_QUICK_START_RU.md](./SCALING_QUICK_START_RU.md)

---

**Вопросы?** Создайте issue на GitHub!  
**Удачного масштабирования!** 🚀
