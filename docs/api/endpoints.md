# Vertex AR - API Documentation

## Оглавление

1. [Введение](#введение)
2. [Базовая информация](#базовая-информация)
3. [Аутентификация](#аутентификация)
4. [Endpoints](#endpoints)
   - [Health Check](#health-check)
   - [Authentication](#authentication)
   - [AR Content](#ar-content)
   - [NFT Markers](#nft-markers)
   - [Admin Panel](#admin-panel)
   - [Statistics](#statistics)
5. [Модели данных](#модели-данных)
6. [Коды ответов](#коды-ответов)
7. [Примеры использования](#примеры-использования)
8. [Rate Limiting](#rate-limiting)
9. [Обработка ошибок](#обработка-ошибок)
10. [Best Practices](#best-practices)

---

## Введение

Vertex AR API - это RESTful API для создания и управления дополненной реальностью (AR) контентом. API позволяет загружать изображения портретов, создавать AR-маркеры, генерировать QR-коды и управлять AR-контентом.

### Основные возможности

- 🔐 Аутентификация пользователей с Bearer токенами
- 📤 Загрузка изображений и видео для создания AR-контента
- 🎯 Автоматическая генерация NFT-маркеров для AR
- 📊 Статистика и аналитика просмотров
- 👥 Административная панель для управления
- 🔍 Поддержка различных форматов файлов
- 🎨 Анимированные AR портреты с Anime.js
- 📱 Поддержка мобильных и десктоп устройств

---

## Базовая информация

### Base URL

```
Production: https://your-domain.com
Development: http://localhost:8000
```

### Версия API

Текущая версия: `1.0.0`

### Content Types

API принимает и возвращает данные в следующих форматах:
- `application/json` - для большинства запросов
- `multipart/form-data` - для загрузки файлов
- `text/html` - для HTML страниц (AR viewer, admin panel)
- `image/png` - для изображений (QR-коды, превью)
- `video/mp4` - для видео контента

### Заголовки

```
Content-Type: application/json
Authorization: Bearer <your_token>
```

---

## Аутентификация

Vertex AR использует Bearer Token аутентификацию. Для доступа к защищенным endpoints необходимо:

1. Зарегистрироваться через `/auth/register`
2. Получить токен через `/auth/login`
3. Использовать токен в заголовке Authorization для всех защищенных запросов

### Формат токена

```
Authorization: Bearer <token>
```

### Время жизни токена

Токены действительны до момента выхода пользователя из системы (`/auth/logout`) или до перезапуска сервера (хранятся в памяти).

### Права доступа

- **Публичный доступ** - не требует аутентификации
- **Аутентифицированный доступ** - требует валидный токен
- **Администраторский доступ** - требует токен администратора (первый зарегистрированный пользователь)

---

## Endpoints

### Health Check

#### GET `/health`

Проверка состояния сервиса. Используется для мониторинга и load balancers.

**Требования:** Публичный доступ, аутентификация не требуется

**Параметры запроса:** Нет

**Пример запроса:**
```bash
curl -X GET http://localhost:8000/health
```

**Успешный ответ (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

#### GET `/version`

Получение версии API.

**Требования:** Публичный доступ

**Пример запроса:**
```bash
curl -X GET http://localhost:8000/version
```

**Успешный ответ (200 OK):**
```json
{
  "version": "1.0.0"
}
```

---

#### GET `/`

Корневой endpoint, возвращает приветствие.

**Требования:** Публичный доступ

**Пример запроса:**
```bash
curl -X GET http://localhost:8000/
```

**Успешный ответ (200 OK):**
```json
{
  "Hello": "Vertex AR (Simplified)"
}
```

---

### Authentication

#### POST `/auth/register`

Регистрация нового пользователя. Первый зарегистрированный пользователь автоматически получает права администратора.

**Требования:** Публичный доступ

**Тело запроса:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Валидация:**
- `username` - от 1 до 150 символов
- `password` - от 1 до 256 символов

**Пример запроса:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "secure_password123"
  }'
```

**Успешный ответ (201 Created):**
```json
{
  "username": "admin"
}
```

**Ошибки:**
- `409 Conflict` - Пользователь уже существует

---

#### POST `/auth/login`

Аутентификация пользователя и получение токена доступа.

**Требования:** Публичный доступ

**Тело запроса:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Пример запроса:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "secure_password123"
  }'
```

**Успешный ответ (200 OK):**
```json
{
  "access_token": "abc123def456...",
  "token_type": "bearer"
}
```

**Ошибки:**
- `401 Unauthorized` - Неверные учетные данные

---

#### POST `/auth/logout`

Выход из системы и аннулирование токена.

**Требования:** Аутентификация required

**Заголовки:**
```
Authorization: Bearer <token>
```

**Пример запроса:**
```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer <your_token>"
```

**Успешный ответ:** `204 No Content`

**Ошибки:**
- `401 Unauthorized` - Невалидный или отсутствующий токен

---

### AR Content

#### POST `/ar/upload`

Загрузка изображения и видео для создания AR-контента. Автоматически генерирует NFT-маркеры, превью и QR-код.

**Требования:** Администраторские права

**Content-Type:** `multipart/form-data`

**Параметры:**
- `image` (file, required) - Изображение портрета (JPEG, PNG)
- `video` (file, required) - Видео для анимации (MP4)

**Пример запроса:**
```bash
curl -X POST http://localhost:8000/ar/upload \
  -H "Authorization: Bearer <your_token>" \
  -F "image=@portrait.jpg" \
  -F "video=@animation.mp4"
```

**Успешный ответ (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "ar_url": "http://localhost:8000/ar/550e8400-e29b-41d4-a716-446655440000",
  "qr_code_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "image_path": "/path/to/storage/image.jpg",
  "video_path": "/path/to/storage/video.mp4",
  "created_at": "2024-01-15T10:30:00"
}
```

**Ошибки:**
- `400 Bad Request` - Невалидный формат файла
- `401 Unauthorized` - Токен отсутствует или невалиден
- `403 Forbidden` - Недостаточно прав (требуется admin)
- `413 Payload Too Large` - Файл слишком большой

**Поддерживаемые форматы:**
- Изображения: JPEG, PNG
- Видео: MP4, WebM

**Ограничения:**
- Максимальный размер изображения: 10 MB
- Максимальный размер видео: 50 MB

**Процесс обработки:**
1. Валидация типов файлов
2. Сохранение оригинальных файлов
3. Генерация превью (image и video)
4. Создание NFT-маркеров (fset, fset3, iset)
5. Генерация QR-кода
6. Сохранение в базу данных

---

#### GET `/ar/list`

Получение списка всего AR-контента.

**Требования:** Аутентификация required

**Поведение:**
- Администраторы видят весь контент
- Обычные пользователи видят только свой контент

**Пример запроса:**
```bash
curl -X GET http://localhost:8000/ar/list \
  -H "Authorization: Bearer <your_token>"
```

**Успешный ответ (200 OK):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "admin",
    "image_path": "/path/to/image.jpg",
    "video_path": "/path/to/video.mp4",
    "image_preview_path": "/path/to/image_preview.jpg",
    "video_preview_path": "/path/to/video_preview.jpg",
    "marker_fset": "/path/to/marker.fset",
    "marker_fset3": "/path/to/marker.fset3",
    "marker_iset": "/path/to/marker.iset",
    "ar_url": "http://localhost:8000/ar/550e8400-e29b-41d4-a716-446655440000",
    "qr_code": "base64_string...",
    "view_count": 42,
    "click_count": 15,
    "created_at": "2024-01-15T10:30:00"
  }
]
```

**Ошибки:**
- `401 Unauthorized` - Токен отсутствует или невалиден

---

#### GET `/ar/{content_id}`

Просмотр AR-контента. Возвращает HTML страницу с AR viewer (A-Frame + AR.js).

**Требования:** Публичный доступ

**Параметры пути:**
- `content_id` (string) - UUID AR-контента

**Query параметры:**
- `animation` (boolean, optional) - Включить анимированный портрет с Anime.js (default: false)

**Пример запроса:**
```bash
# Обычный AR просмотр с видео
curl -X GET http://localhost:8000/ar/550e8400-e29b-41d4-a716-446655440000

# Анимированный портрет
curl -X GET "http://localhost:8000/ar/550e8400-e29b-41d4-a716-446655440000?animation=true"
```

**Успешный ответ:** HTML страница с AR viewer

**Особенности:**
- Автоматически увеличивает счетчик просмотров
- `animation=false`: Показывает видео при обнаружении маркера
- `animation=true`: Показывает интерактивный анимированный портрет с кнопками управления

**Ошибки:**
- `404 Not Found` - Контент не найден

---

#### GET `/ar/image/{content_id}`

Получение оригинального изображения AR-контента.

**Требования:** Публичный доступ

**Параметры пути:**
- `content_id` (string) - UUID AR-контента

**Пример запроса:**
```bash
curl -X GET http://localhost:8000/ar/image/550e8400-e29b-41d4-a716-446655440000 \
  -o portrait.jpg
```

**Успешный ответ:** JPEG/PNG изображение (FileResponse)

**Ошибки:**
- `404 Not Found` - Контент или файл не найден

---

#### GET `/ar/video/{content_id}`

Получение видео файла AR-контента.

**Требования:** Публичный доступ

**Параметры пути:**
- `content_id` (string) - UUID AR-контента

**Пример запроса:**
```bash
curl -X GET http://localhost:8000/ar/video/550e8400-e29b-41d4-a716-446655440000 \
  -o animation.mp4
```

**Успешный ответ:** MP4 видео файл (FileResponse)

**Content-Type:** `video/mp4`

**Ошибки:**
- `404 Not Found` - Контент или файл не найден

---

#### GET `/ar/markers/{content_id}.{marker_type}`

Получение файлов NFT-маркера для AR.js.

**Требования:** Публичный доступ

**Параметры пути:**
- `content_id` (string) - UUID AR-контента
- `marker_type` (string) - Тип маркера: `fset`, `fset3`, или `iset`

**Пример запроса:**
```bash
# Получить .fset файл
curl -X GET http://localhost:8000/ar/markers/550e8400-e29b-41d4-a716-446655440000.fset

# Получить .fset3 файл
curl -X GET http://localhost:8000/ar/markers/550e8400-e29b-41d4-a716-446655440000.fset3

# Получить .iset файл
curl -X GET http://localhost:8000/ar/markers/550e8400-e29b-41d4-a716-446655440000.iset
```

**Успешный ответ:** Файл маркера (FileResponse)

**Ошибки:**
- `400 Bad Request` - Неверный тип маркера
- `404 Not Found` - Контент или файл маркера не найден

**Описание типов маркеров:**
- `.fset` - Feature set (основной набор признаков)
- `.fset3` - Feature set level 3 (дополнительные уровни деталей)
- `.iset` - Image set (метаданные изображения)

---

#### GET `/ar/qr/{content_id}`

Получение QR-кода для AR-контента в формате JSON с base64.

**Требования:** Публичный доступ

**Параметры пути:**
- `content_id` (string) - UUID AR-контента

**Пример запроса:**
```bash
curl -X GET http://localhost:8000/ar/qr/550e8400-e29b-41d4-a716-446655440000
```

**Успешный ответ (200 OK):**
```json
{
  "content_id": "550e8400-e29b-41d4-a716-446655440000",
  "ar_url": "http://localhost:8000/ar/550e8400-e29b-41d4-a716-446655440000",
  "qr_code_base64": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

**Ошибки:**
- `404 Not Found` - Контент не найден

---

#### POST `/ar/{content_id}/click`

Отслеживание клика по ссылке AR-контента (для аналитики).

**Требования:** Публичный доступ

**Параметры пути:**
- `content_id` (string) - UUID AR-контента

**Пример запроса:**
```bash
curl -X POST http://localhost:8000/ar/550e8400-e29b-41d4-a716-446655440000/click
```

**Успешный ответ (200 OK):**
```json
{
  "status": "success",
  "content_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Ошибки:**
- `404 Not Found` - Контент не найден

---

#### DELETE `/ar/{content_id}`

Удаление AR-контента и всех связанных файлов.

**Требования:** Администраторские права

**Параметры пути:**
- `content_id` (string) - UUID AR-контента

**Пример запроса:**
```bash
curl -X DELETE http://localhost:8000/ar/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <your_token>"
```

**Успешный ответ (200 OK):**
```json
{
  "status": "success",
  "message": "AR content 550e8400-e29b-41d4-a716-446655440000 deleted successfully"
}
```

**Процесс удаления:**
1. Поиск контента в базе данных
2. Удаление всей директории с файлами (изображение, видео, превью, маркеры)
3. Удаление записи из базы данных

**Ошибки:**
- `401 Unauthorized` - Токен отсутствует или невалиден
- `403 Forbidden` - Недостаточно прав
- `404 Not Found` - Контент не найден
- `500 Internal Server Error` - Ошибка при удалении файлов

---

### NFT Markers

#### POST `/nft-marker/analyze`

Анализ изображения на пригодность для создания NFT-маркера.

**Требования:** Аутентификация required

**Content-Type:** `multipart/form-data`

**Параметры:**
- `image` (file, required) - Изображение для анализа

**Пример запроса:**
```bash
curl -X POST http://localhost:8000/nft-marker/analyze \
  -H "Authorization: Bearer <your_token>" \
  -F "image=@test_image.jpg"
```

**Успешный ответ (200 OK):**
```json
{
  "suitable": true,
  "confidence": 0.85,
  "width": 1920,
  "height": 1080,
  "dpi": 150,
  "feature_density": "high",
  "recommendations": [
    "Image has good contrast and feature density",
    "Optimal for AR marker generation"
  ],
  "warnings": []
}
```

**Поля ответа:**
- `suitable` (boolean) - Подходит ли изображение для маркера
- `confidence` (float) - Уровень уверенности (0-1)
- `width`, `height` (int) - Размеры изображения в пикселях
- `dpi` (int) - Разрешение изображения
- `feature_density` (string) - Плотность признаков: "low", "medium", "high"
- `recommendations` (array) - Рекомендации по улучшению
- `warnings` (array) - Предупреждения о потенциальных проблемах

**Ошибки:**
- `401 Unauthorized` - Токен отсутствует или невалиден
- `400 Bad Request` - Невалидный файл изображения

---

#### POST `/nft-marker/generate`

Генерация NFT-маркера из изображения.

**Требования:** Аутентификация required

**Content-Type:** `multipart/form-data`

**Параметры:**
- `image` (file, required) - Изображение для маркера
- `marker_name` (string, required) - Имя маркера
- `config` (string, optional) - JSON конфигурация маркера

**Config параметры:**
```json
{
  "min_dpi": 72,
  "max_dpi": 300,
  "levels": 3,
  "feature_density": "medium"
}
```

**Пример запроса:**
```bash
curl -X POST http://localhost:8000/nft-marker/generate \
  -H "Authorization: Bearer <your_token>" \
  -F "image=@marker_image.jpg" \
  -F "marker_name=my_marker" \
  -F 'config={"levels": 3, "feature_density": "high"}'
```

**Успешный ответ (200 OK):**
```json
{
  "name": "my_marker",
  "width": 1920,
  "height": 1080,
  "dpi": 150,
  "fset_path": "/storage/nft-markers/my_marker/my_marker.fset",
  "fset3_path": "/storage/nft-markers/my_marker/my_marker.fset3",
  "iset_path": "/storage/nft-markers/my_marker/my_marker.iset"
}
```

**Ошибки:**
- `401 Unauthorized` - Токен отсутствует или невалиден
- `400 Bad Request` - Невалидные параметры или изображение

---

#### GET `/nft-marker/list`

Получение списка всех сгенерированных NFT-маркеров.

**Требования:** Аутентификация required

**Пример запроса:**
```bash
curl -X GET http://localhost:8000/nft-marker/list \
  -H "Authorization: Bearer <your_token>"
```

**Успешный ответ (200 OK):**
```json
[
  {
    "name": "marker1",
    "width": 1920,
    "height": 1080,
    "dpi": 150,
    "created_at": "2024-01-15T10:30:00",
    "files": {
      "fset": "/storage/nft-markers/marker1/marker1.fset",
      "fset3": "/storage/nft-markers/marker1/marker1.fset3",
      "iset": "/storage/nft-markers/marker1/marker1.iset"
    }
  }
]
```

**Ошибки:**
- `401 Unauthorized` - Токен отсутствует или невалиден

---

### Admin Panel

#### GET `/admin`

Доступ к административной панели. Возвращает HTML страницу с управлением контентом и статистикой.

**Требования:** Публичный доступ (но полный функционал требует admin токена)

**Пример запроса:**
```bash
curl -X GET http://localhost:8000/admin
```

**Успешный ответ:** HTML страница админ-панели

**Функционал панели:**
- Просмотр всего AR-контента
- Загрузка нового контента
- Удаление контента
- Просмотр статистики
- Управление пользователями

---

### Statistics

#### GET `/admin/system-info`

Получение информации о системных ресурсах (диск и хранилище).

**Требования:** Администраторские права

**Пример запроса:**
```bash
curl -X GET http://localhost:8000/admin/system-info \
  -H "Authorization: Bearer <your_token>"
```

**Успешный ответ (200 OK):**
```json
{
  "disk_info": {
    "total": "500.0 GB",
    "used": "250.5 GB",
    "free": "249.5 GB",
    "used_percent": 50.1
  },
  "storage_info": {
    "total_size": "15.3 GB",
    "file_count": 245,
    "path": "storage/"
  }
}
```

**Ошибки:**
- `401 Unauthorized` - Токен отсутствует или невалиден
- `403 Forbidden` - Недостаточно прав

---

#### GET `/admin/storage-info`

Получение детальной информации о занятом и свободном дисковом пространстве.

**Требования:** Администраторские права

**Пример запроса:**
```bash
curl -X GET http://localhost:8000/admin/storage-info \
  -H "Authorization: Bearer <your_token>"
```

**Успешный ответ (200 OK):**
```json
{
  "disk_total": "500.0 GB",
  "disk_used": "250.5 GB",
  "disk_free": "249.5 GB",
  "disk_used_percent": 50.1,
  "storage_total_size": "15.3 GB",
  "storage_file_count": 245,
  "storage_path": "storage/"
}
```

**Ошибки:**
- `401 Unauthorized` - Токен отсутствует или невалиден
- `403 Forbidden` - Недостаточно прав

---

#### GET `/admin/content-stats`

Получение статистики просмотров и кликов для всего AR-контента.

**Требования:** Администраторские права

**Пример запроса:**
```bash
curl -X GET http://localhost:8000/admin/content-stats \
  -H "Authorization: Bearer <your_token>"
```

**Успешный ответ (200 OK):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "550e8400-e29b-41d4-a716-446655440000",
    "views": 142,
    "clicks": 35,
    "created_at": "2024-01-15T10:30:00",
    "ar_url": "http://localhost:8000/ar/550e8400-e29b-41d4-a716-446655440000"
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "title": "660e8400-e29b-41d4-a716-446655440001",
    "views": 98,
    "clicks": 22,
    "created_at": "2024-01-16T11:20:00",
    "ar_url": "http://localhost:8000/ar/660e8400-e29b-41d4-a716-446655440001"
  }
]
```

**Особенности:**
- Результаты отсортированы по количеству просмотров (по убыванию)
- Включает все метрики аналитики

**Ошибки:**
- `401 Unauthorized` - Токен отсутствует или невалиден
- `403 Forbidden` - Недостаточно прав

---

## Модели данных

### UserCreate

Модель для регистрации пользователя.

```json
{
  "username": "string",
  "password": "string"
}
```

**Поля:**
- `username` (string, required) - Имя пользователя (1-150 символов)
- `password` (string, required) - Пароль (1-256 символов)

---

### UserLogin

Модель для аутентификации пользователя.

```json
{
  "username": "string",
  "password": "string"
}
```

**Поля:**
- `username` (string, required) - Имя пользователя
- `password` (string, required) - Пароль

---

### TokenResponse

Модель ответа при успешной аутентификации.

```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

**Поля:**
- `access_token` (string) - Токен доступа для последующих запросов
- `token_type` (string) - Тип токена (всегда "bearer")

---

### ARContentResponse

Модель ответа при создании AR-контента.

```json
{
  "id": "string",
  "ar_url": "string",
  "qr_code_base64": "string | null",
  "image_path": "string",
  "video_path": "string",
  "created_at": "string"
}
```

**Поля:**
- `id` (string) - UUID контента
- `ar_url` (string) - URL для просмотра AR
- `qr_code_base64` (string, nullable) - QR-код в формате base64
- `image_path` (string) - Путь к изображению
- `video_path` (string) - Путь к видео
- `created_at` (string) - Timestamp создания (ISO 8601 format)

---

### ARContent (Database Model)

Полная модель AR-контента из базы данных.

```json
{
  "id": "string",
  "username": "string",
  "image_path": "string",
  "video_path": "string",
  "image_preview_path": "string | null",
  "video_preview_path": "string | null",
  "marker_fset": "string",
  "marker_fset3": "string",
  "marker_iset": "string",
  "ar_url": "string",
  "qr_code": "string | null",
  "view_count": "integer",
  "click_count": "integer",
  "created_at": "string"
}
```

**Поля:**
- `id` (string) - UUID контента
- `username` (string) - Имя пользователя-создателя
- `image_path` (string) - Путь к оригинальному изображению
- `video_path` (string) - Путь к видео
- `image_preview_path` (string, nullable) - Путь к превью изображения
- `video_preview_path` (string, nullable) - Путь к превью видео
- `marker_fset` (string) - Путь к .fset файлу
- `marker_fset3` (string) - Путь к .fset3 файлу
- `marker_iset` (string) - Путь к .iset файлу
- `ar_url` (string) - URL для просмотра AR
- `qr_code` (string, nullable) - QR-код в base64
- `view_count` (integer) - Количество просмотров
- `click_count` (integer) - Количество кликов
- `created_at` (string) - Timestamp создания

---

### StorageInfoResponse

Модель информации о хранилище.

```json
{
  "disk_total": "string",
  "disk_used": "string",
  "disk_free": "string",
  "disk_used_percent": "float",
  "storage_total_size": "string",
  "storage_file_count": "integer",
  "storage_path": "string"
}
```

---

### SystemInfoResponse

Модель системной информации.

```json
{
  "disk_info": {
    "total": "string",
    "used": "string",
    "free": "string",
    "used_percent": "float"
  },
  "storage_info": {
    "total_size": "string",
    "file_count": "integer",
    "path": "string"
  }
}
```

---

### NFTMarkerConfig

Конфигурация для генерации NFT-маркера.

```json
{
  "min_dpi": 72,
  "max_dpi": 300,
  "levels": 3,
  "feature_density": "medium"
}
```

**Поля:**
- `min_dpi` (integer) - Минимальное разрешение (default: 72)
- `max_dpi` (integer) - Максимальное разрешение (default: 300)
- `levels` (integer) - Количество уровней детализации (default: 3)
- `feature_density` (string) - Плотность признаков: "low", "medium", "high" (default: "medium")

---

## Коды ответов

### Успешные ответы

| Код | Описание |
|-----|----------|
| 200 OK | Успешный запрос |
| 201 Created | Ресурс успешно создан |
| 204 No Content | Успешное выполнение без тела ответа |

### Клиентские ошибки

| Код | Описание | Причины |
|-----|----------|---------|
| 400 Bad Request | Неверный запрос | Невалидные данные, неправильный формат, отсутствие обязательных параметров |
| 401 Unauthorized | Не авторизован | Отсутствующий, невалидный или истекший токен |
| 403 Forbidden | Доступ запрещен | Недостаточно прав (требуется admin) |
| 404 Not Found | Ресурс не найден | Несуществующий content_id, файл не найден |
| 409 Conflict | Конфликт | Пользователь уже существует, дублирование данных |
| 413 Payload Too Large | Слишком большой файл | Превышен лимит размера файла |

### Серверные ошибки

| Код | Описание |
|-----|----------|
| 500 Internal Server Error | Внутренняя ошибка сервера |
| 503 Service Unavailable | Сервис недоступен |

---

## Примеры использования

### Полный workflow

#### 1. Регистрация и аутентификация

```bash
# Регистрация
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"secure_pass"}'

# Логин и сохранение токена
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"secure_pass"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"
```

#### 2. Загрузка AR контента

```bash
# Загрузить изображение и видео
curl -X POST http://localhost:8000/ar/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "image=@portrait.jpg" \
  -F "video=@animation.mp4" \
  | jq '.'

# Сохранить content_id из ответа
CONTENT_ID="550e8400-e29b-41d4-a716-446655440000"
```

#### 3. Просмотр контента

```bash
# Получить список контента
curl -X GET http://localhost:8000/ar/list \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.'

# Получить QR-код
curl -X GET http://localhost:8000/ar/qr/$CONTENT_ID \
  | jq -r '.qr_code_base64' | base64 -d > qrcode.png

# Открыть AR viewer в браузере
xdg-open "http://localhost:8000/ar/$CONTENT_ID"

# Открыть анимированный портрет
xdg-open "http://localhost:8000/ar/$CONTENT_ID?animation=true"
```

#### 4. Аналитика

```bash
# Получить статистику контента
curl -X GET http://localhost:8000/admin/content-stats \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.'

# Получить информацию о системе
curl -X GET http://localhost:8000/admin/system-info \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.'
```

#### 5. Удаление контента

```bash
# Удалить AR контент
curl -X DELETE http://localhost:8000/ar/$CONTENT_ID \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.'
```

---

### Python (requests)

```python
import requests
import json
import base64
from pathlib import Path

BASE_URL = "http://localhost:8000"

class VertexARClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.token = None
    
    def register(self, username: str, password: str) -> dict:
        """Регистрация нового пользователя"""
        response = requests.post(
            f"{self.base_url}/auth/register",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        return response.json()
    
    def login(self, username: str, password: str) -> str:
        """Аутентификация и получение токена"""
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        return self.token
    
    def logout(self) -> None:
        """Выход из системы"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{self.base_url}/auth/logout",
            headers=headers
        )
        response.raise_for_status()
        self.token = None
    
    def upload_ar_content(self, image_path: str, video_path: str) -> dict:
        """Загрузка AR контента"""
        headers = {"Authorization": f"Bearer {self.token}"}
        files = {
            "image": open(image_path, "rb"),
            "video": open(video_path, "rb")
        }
        response = requests.post(
            f"{self.base_url}/ar/upload",
            headers=headers,
            files=files
        )
        response.raise_for_status()
        return response.json()
    
    def list_ar_content(self) -> list:
        """Получить список AR контента"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.base_url}/ar/list",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_qr_code(self, content_id: str, save_path: str = None) -> dict:
        """Получить QR-код"""
        response = requests.get(f"{self.base_url}/ar/qr/{content_id}")
        response.raise_for_status()
        data = response.json()
        
        if save_path:
            # Сохранить QR-код в файл
            qr_bytes = base64.b64decode(data["qr_code_base64"])
            Path(save_path).write_bytes(qr_bytes)
        
        return data
    
    def delete_ar_content(self, content_id: str) -> dict:
        """Удалить AR контент"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.delete(
            f"{self.base_url}/ar/{content_id}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_content_stats(self) -> list:
        """Получить статистику контента"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.base_url}/admin/content-stats",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    def analyze_nft_marker(self, image_path: str) -> dict:
        """Анализ изображения для NFT маркера"""
        headers = {"Authorization": f"Bearer {self.token}"}
        files = {"image": open(image_path, "rb")}
        response = requests.post(
            f"{self.base_url}/nft-marker/analyze",
            headers=headers,
            files=files
        )
        response.raise_for_status()
        return response.json()
    
    def generate_nft_marker(self, image_path: str, marker_name: str, 
                           config: dict = None) -> dict:
        """Генерация NFT маркера"""
        headers = {"Authorization": f"Bearer {self.token}"}
        files = {"image": open(image_path, "rb")}
        data = {
            "marker_name": marker_name,
            "config": json.dumps(config or {})
        }
        response = requests.post(
            f"{self.base_url}/nft-marker/generate",
            headers=headers,
            files=files,
            data=data
        )
        response.raise_for_status()
        return response.json()

# Пример использования
if __name__ == "__main__":
    client = VertexARClient()
    
    # Регистрация и логин
    try:
        client.register("admin", "secure_password123")
    except requests.exceptions.HTTPError:
        pass  # Пользователь уже существует
    
    client.login("admin", "secure_password123")
    
    # Загрузка AR контента
    result = client.upload_ar_content("portrait.jpg", "animation.mp4")
    print(f"Создан AR контент: {result['ar_url']}")
    content_id = result["id"]
    
    # Получение QR-кода
    client.get_qr_code(content_id, save_path="qrcode.png")
    print("QR-код сохранен в qrcode.png")
    
    # Просмотр списка
    content_list = client.list_ar_content()
    print(f"Всего контента: {len(content_list)}")
    
    # Статистика
    stats = client.get_content_stats()
    for item in stats:
        print(f"ID: {item['id']}, Views: {item['views']}, Clicks: {item['clicks']}")
    
    # Выход
    client.logout()
```

---

### JavaScript (fetch)

```javascript
class VertexARClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
    this.token = null;
  }

  async register(username, password) {
    const response = await fetch(`${this.baseUrl}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async login(username, password) {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    this.token = data.access_token;
    return this.token;
  }

  async logout() {
    const response = await fetch(`${this.baseUrl}/auth/logout`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    this.token = null;
  }

  async uploadARContent(imageFile, videoFile) {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('video', videoFile);
    
    const response = await fetch(`${this.baseUrl}/ar/upload`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${this.token}` },
      body: formData
    });
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async listARContent() {
    const response = await fetch(`${this.baseUrl}/ar/list`, {
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async getQRCode(contentId) {
    const response = await fetch(`${this.baseUrl}/ar/qr/${contentId}`);
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async deleteARContent(contentId) {
    const response = await fetch(`${this.baseUrl}/ar/${contentId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async getContentStats() {
    const response = await fetch(`${this.baseUrl}/admin/content-stats`, {
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async analyzeNFTMarker(imageFile) {
    const formData = new FormData();
    formData.append('image', imageFile);
    
    const response = await fetch(`${this.baseUrl}/nft-marker/analyze`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${this.token}` },
      body: formData
    });
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async generateNFTMarker(imageFile, markerName, config = {}) {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('marker_name', markerName);
    formData.append('config', JSON.stringify(config));
    
    const response = await fetch(`${this.baseUrl}/nft-marker/generate`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${this.token}` },
      body: formData
    });
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }
}

// Пример использования
(async () => {
  const client = new VertexARClient();
  
  // Регистрация и логин
  try {
    await client.register('admin', 'secure_password123');
  } catch (e) {
    console.log('User already exists');
  }
  
  await client.login('admin', 'secure_password123');
  console.log('Logged in successfully');
  
  // Загрузка AR контента
  const imageInput = document.getElementById('imageInput');
  const videoInput = document.getElementById('videoInput');
  
  const result = await client.uploadARContent(
    imageInput.files[0],
    videoInput.files[0]
  );
  console.log('AR Content created:', result.ar_url);
  
  // Получение списка
  const contentList = await client.listARContent();
  console.log(`Total content: ${contentList.length}`);
  
  // Статистика
  const stats = await client.getContentStats();
  stats.forEach(item => {
    console.log(`ID: ${item.id}, Views: ${item.views}, Clicks: ${item.clicks}`);
  });
  
  // Выход
  await client.logout();
})();
```

---

### cURL Examples

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"

# Регистрация
echo "=== Регистрация ==="
curl -X POST $BASE_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"secure_pass"}'

echo -e "\n"

# Логин и сохранение токена
echo "=== Логин ==="
TOKEN=$(curl -s -X POST $BASE_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"secure_pass"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"
echo -e "\n"

# Загрузка AR контента
echo "=== Загрузка AR контента ==="
UPLOAD_RESULT=$(curl -s -X POST $BASE_URL/ar/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "image=@portrait.jpg" \
  -F "video=@animation.mp4")

echo $UPLOAD_RESULT | jq '.'
CONTENT_ID=$(echo $UPLOAD_RESULT | jq -r '.id')
echo "Content ID: $CONTENT_ID"
echo -e "\n"

# Получение списка контента
echo "=== Список контента ==="
curl -s -X GET $BASE_URL/ar/list \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.'

echo -e "\n"

# Получение QR-кода
echo "=== Получение QR-кода ==="
curl -s -X GET $BASE_URL/ar/qr/$CONTENT_ID \
  | jq -r '.qr_code_base64' \
  | base64 -d > qrcode.png

echo "QR-код сохранен в qrcode.png"
echo -e "\n"

# Анализ изображения для NFT маркера
echo "=== Анализ NFT маркера ==="
curl -s -X POST $BASE_URL/nft-marker/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -F "image=@test_image.jpg" \
  | jq '.'

echo -e "\n"

# Генерация NFT маркера
echo "=== Генерация NFT маркера ==="
curl -s -X POST $BASE_URL/nft-marker/generate \
  -H "Authorization: Bearer $TOKEN" \
  -F "image=@marker_image.jpg" \
  -F "marker_name=my_marker" \
  -F 'config={"levels": 3, "feature_density": "high"}' \
  | jq '.'

echo -e "\n"

# Список NFT маркеров
echo "=== Список NFT маркеров ==="
curl -s -X GET $BASE_URL/nft-marker/list \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.'

echo -e "\n"

# Статистика контента
echo "=== Статистика контента ==="
curl -s -X GET $BASE_URL/admin/content-stats \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.'

echo -e "\n"

# Системная информация
echo "=== Системная информация ==="
curl -s -X GET $BASE_URL/admin/system-info \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.'

echo -e "\n"

# Информация о хранилище
echo "=== Информация о хранилище ==="
curl -s -X GET $BASE_URL/admin/storage-info \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.'

echo -e "\n"

# Трекинг клика
echo "=== Трекинг клика ==="
curl -s -X POST $BASE_URL/ar/$CONTENT_ID/click \
  | jq '.'

echo -e "\n"

# Удаление контента
echo "=== Удаление контента ==="
curl -s -X DELETE $BASE_URL/ar/$CONTENT_ID \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.'

echo -e "\n"

# Выход
echo "=== Выход ==="
curl -X POST $BASE_URL/auth/logout \
  -H "Authorization: Bearer $TOKEN"

echo -e "\n=== Готово ==="
```

---

## Rate Limiting

В текущей версии rate limiting не реализован. В продакшн окружении рекомендуется реализовать следующие ограничения:

### Рекомендуемые лимиты

| Endpoint Type | Requests per Minute | Requests per Hour |
|--------------|---------------------|-------------------|
| Аутентификация | 5 | 20 |
| Загрузка файлов | - | 10 |
| API запросы (authenticated) | 100 | 1000 |
| Публичные endpoints | 1000 | 10000 |
| Админ endpoints | 50 | 500 |

### Реализация

Рекомендуется использовать:
- **FastAPI-Limiter** для встроенной защиты
- **Redis** для хранения счетчиков
- **Nginx** для rate limiting на уровне reverse proxy

Пример конфигурации Nginx:

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=10r/h;

location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
}

location /ar/upload {
    limit_req zone=upload_limit burst=2;
}
```

---

## Обработка ошибок

Все ошибки возвращаются в стандартном формате FastAPI:

```json
{
  "detail": "Описание ошибки"
}
```

### Примеры ошибок

#### 400 Bad Request

```json
{
  "detail": "Invalid image file"
}
```

```json
{
  "detail": "Marker name is required"
}
```

```json
{
  "detail": "Invalid marker type"
}
```

#### 401 Unauthorized

```json
{
  "detail": "Invalid token"
}
```

```json
{
  "detail": "Invalid credentials"
}
```

#### 403 Forbidden

```json
{
  "detail": "Admin access required"
}
```

#### 404 Not Found

```json
{
  "detail": "AR content not found"
}
```

```json
{
  "detail": "Image file not found"
}
```

```json
{
  "detail": "Marker file not found"
}
```

#### 409 Conflict

```json
{
  "detail": "User already exists"
}
```

#### 500 Internal Server Error

```json
{
  "detail": "Ошибка при удалении файлов: [detailed error message]"
}
```

```json
{
  "detail": "Не удалось удалить контент из базы данных"
}
```

### Обработка ошибок в клиентском коде

#### Python

```python
import requests

try:
    response = requests.post(
        "http://localhost:8000/ar/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files
    )
    response.raise_for_status()
    data = response.json()
except requests.exceptions.HTTPError as e:
    error_detail = e.response.json().get("detail", "Unknown error")
    print(f"Error: {error_detail}")
except requests.exceptions.RequestException as e:
    print(f"Connection error: {e}")
```

#### JavaScript

```javascript
try {
  const response = await fetch(`${baseUrl}/ar/upload`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Unknown error');
  }
  
  const data = await response.json();
  return data;
} catch (error) {
  console.error('Error:', error.message);
  // Show user-friendly error message
  alert(`Failed to upload: ${error.message}`);
}
```

---

## Best Practices

### Безопасность

1. **Всегда используйте HTTPS** в продакшн окружении
   ```nginx
   server {
       listen 443 ssl http2;
       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;
   }
   ```

2. **Храните токены безопасно**
   - Не храните в localStorage (уязвимо для XSS)
   - Используйте httpOnly cookies
   - Используйте sessionStorage для временного хранения

3. **Не логируйте токены** и чувствительные данные
   ```python
   # Плохо
   logger.info(f"Token: {token}")
   
   # Хорошо
   logger.info("User authenticated successfully")
   ```

4. **Используйте сильные пароли**
   - Минимум 8 символов
   - Заглавные и строчные буквы
   - Цифры и спецсимволы
   - Не используйте словарные слова

5. **Валидация файлов**
   ```python
   # Проверяйте не только content-type, но и реальное содержимое
   from PIL import Image
   
   try:
       img = Image.open(file)
       img.verify()
   except Exception:
       raise ValueError("Invalid image file")
   ```

6. **Защита от CSRF**
   - Используйте CSRF токены для форм
   - Проверяйте Origin/Referer заголовки

7. **CORS настройки**
   ```python
   # В продакшн используйте конкретные домены
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://your-domain.com"],
       allow_credentials=True,
       allow_methods=["GET", "POST", "DELETE"],
       allow_headers=["Authorization", "Content-Type"],
   )
   ```

### Производительность

1. **Кэшируйте статические ресурсы**
   ```nginx
   location ~* \.(jpg|jpeg|png|gif|mp4)$ {
       expires 1y;
       add_header Cache-Control "public, immutable";
   }
   ```

2. **Используйте CDN** для доставки медиа файлов
   - CloudFlare
   - AWS CloudFront
   - Azure CDN

3. **Оптимизируйте размеры файлов** перед загрузкой
   ```python
   # Сжатие изображений
   from PIL import Image
   
   img = Image.open("large.jpg")
   img.thumbnail((1920, 1080))
   img.save("optimized.jpg", quality=85, optimize=True)
   ```

4. **Используйте pagination** для списков контента
   ```python
   @app.get("/ar/list")
   async def list_ar_content(
       skip: int = 0,
       limit: int = 20,
       username: str = Depends(get_current_user)
   ):
       return database.list_ar_content(username, skip=skip, limit=limit)
   ```

5. **Асинхронная обработка** для тяжелых операций
   ```python
   import asyncio
   
   async def process_upload(file):
       # Длительная обработка в фоне
       await asyncio.to_thread(heavy_processing, file)
   ```

6. **Используйте WebP** для изображений
   - Меньший размер при том же качестве
   - Поддержка прозрачности
   - 25-35% экономии трафика

### Надежность

1. **Всегда проверяйте статус ответа**
   ```python
   response = requests.post(url, data=data)
   if response.status_code == 200:
       return response.json()
   elif response.status_code == 401:
       # Обновить токен и повторить
       refresh_token()
   else:
       raise Exception(f"Unexpected status: {response.status_code}")
   ```

2. **Retry механизм** для сетевых запросов
   ```python
   from requests.adapters import HTTPAdapter
   from requests.packages.urllib3.util.retry import Retry
   
   session = requests.Session()
   retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
   adapter = HTTPAdapter(max_retries=retry)
   session.mount('http://', adapter)
   session.mount('https://', adapter)
   ```

3. **Таймауты** для всех запросов
   ```python
   response = requests.get(url, timeout=(3.05, 27))  # connect, read
   ```

4. **Graceful degradation**
   - Fallback для недоступных сервисов
   - Кэширование при недоступности API

5. **Мониторинг и логирование**
   ```python
   import logging
   
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
       handlers=[
           logging.FileHandler('app.log'),
           logging.StreamHandler()
       ]
   )
   ```

### Юзабилити

1. **Показывайте понятные сообщения пользователю**
   ```javascript
   catch (error) {
     const userMessage = {
       400: 'Invalid file format. Please upload JPEG or PNG.',
       401: 'Session expired. Please login again.',
       403: 'You don\'t have permission to perform this action.',
       404: 'Content not found.',
       413: 'File too large. Maximum size is 50MB.',
       500: 'Server error. Please try again later.'
     }[error.status] || 'An unexpected error occurred.';
     
     showNotification(userMessage, 'error');
   }
   ```

2. **Progress indicators** для загрузки файлов
   ```javascript
   const xhr = new XMLHttpRequest();
   xhr.upload.addEventListener('progress', (e) => {
     if (e.lengthComputable) {
       const percentComplete = (e.loaded / e.total) * 100;
       updateProgressBar(percentComplete);
     }
   });
   ```

3. **Валидация на клиенте**
   ```javascript
   function validateFiles(imageFile, videoFile) {
     const maxImageSize = 10 * 1024 * 1024; // 10MB
     const maxVideoSize = 50 * 1024 * 1024; // 50MB
     
     if (imageFile.size > maxImageSize) {
       throw new Error('Image too large (max 10MB)');
     }
     
     if (videoFile.size > maxVideoSize) {
       throw new Error('Video too large (max 50MB)');
     }
     
     if (!imageFile.type.startsWith('image/')) {
       throw new Error('Invalid image file');
     }
     
     if (!videoFile.type.startsWith('video/')) {
       throw new Error('Invalid video file');
     }
   }
   ```

---

## Дополнительная информация

### Автоматическая документация

FastAPI автоматически генерирует интерактивную документацию:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

### Тестирование API

#### Unit тесты

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "1.0.0"}

def test_register_and_login():
    # Регистрация
    response = client.post(
        "/auth/register",
        json={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 201
    
    # Логин
    response = client.post(
        "/auth/login",
        json={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
```

#### Интеграционные тесты

```bash
#!/bin/bash
# integration_test.sh

# Запустить сервер
python -m uvicorn main:app --port 8000 &
SERVER_PID=$!

# Подождать запуска
sleep 3

# Тесты
bash test_scripts/test_api.sh

# Остановить сервер
kill $SERVER_PID
```

### Развертывание

#### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./storage:/app/storage
      - ./app_data.db:/app/app_data.db
    environment:
      - BASE_URL=https://your-domain.com
```

### Поддержка

- **GitHub Issues**: [https://github.com/your-repo/vertex-ar/issues](https://github.com/your-repo/vertex-ar/issues)
- **Email**: support@vertex-ar.com
- **Документация**: [https://docs.vertex-ar.com](https://docs.vertex-ar.com)
- **Telegram**: @vertex_ar_support

### Changelog

См. [CHANGELOG.md](./CHANGELOG.md) для истории изменений API.

### Лицензия

MIT License - см. [LICENSE](./LICENSE)

---

## Приложения

### Полный список endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | Public | Приветствие |
| GET | `/health` | Public | Проверка здоровья |
| GET | `/version` | Public | Версия API |
| POST | `/auth/register` | Public | Регистрация |
| POST | `/auth/login` | Public | Аутентификация |
| POST | `/auth/logout` | Auth | Выход |
| POST | `/ar/upload` | Admin | Загрузка AR контента |
| GET | `/ar/list` | Auth | Список AR контента |
| GET | `/ar/{content_id}` | Public | Просмотр AR |
| GET | `/ar/image/{content_id}` | Public | Получить изображение |
| GET | `/ar/video/{content_id}` | Public | Получить видео |
| GET | `/ar/markers/{content_id}.{type}` | Public | Получить маркер |
| GET | `/ar/qr/{content_id}` | Public | Получить QR-код |
| POST | `/ar/{content_id}/click` | Public | Трекинг клика |
| DELETE | `/ar/{content_id}` | Admin | Удалить контент |
| POST | `/nft-marker/analyze` | Auth | Анализ маркера |
| POST | `/nft-marker/generate` | Auth | Генерация маркера |
| GET | `/nft-marker/list` | Auth | Список маркеров |
| GET | `/admin` | Public | Админ панель |
| GET | `/admin/system-info` | Admin | Системная информация |
| GET | `/admin/storage-info` | Admin | Информация о хранилище |
| GET | `/admin/content-stats` | Admin | Статистика контента |

### Глоссарий

- **AR (Augmented Reality)** - Дополненная реальность
- **NFT Marker** - Natural Feature Tracking маркер, используется для обнаружения изображений в AR
- **Bearer Token** - Токен доступа, передаваемый в заголовке Authorization
- **QR Code** - Quick Response код для быстрого доступа к AR
- **A-Frame** - Веб-фреймворк для создания VR/AR опыта
- **AR.js** - Библиотека для AR в браузере
- **Anime.js** - Библиотека анимаций JavaScript
- **CORS** - Cross-Origin Resource Sharing
- **UUID** - Universally Unique Identifier
- **DPI** - Dots Per Inch (разрешение изображения)
- **Feature Density** - Плотность характерных признаков на изображении

---

**Версия документации:** 1.1.0  
**Последнее обновление:** 2024-11-07  
**Статус:** Полная документация ✅

