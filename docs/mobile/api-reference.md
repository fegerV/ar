# 📖 Vertex AR Mobile API Quick Reference

Быстрый справочник всех эндпоинтов API для мобильной разработки.

---

## 📋 Содержание

1. [Общие параметры](#общие-параметры)
2. [Аутентификация](#аутентификация)
3. [Клиенты](#клиенты)
4. [Портреты](#портреты)
5. [Видео](#видео)
6. [Публичный доступ](#публичный-доступ)
7. [Пользователи](#пользователи)
8. [Системное](#системное)

---

## Общие параметры

### Base URL
```
Production:  https://api.vertex-ar.com
Development: http://localhost:8000
```

### Headers (во все запросы)
```http
Content-Type: application/json
Authorization: Bearer {access_token}
User-Agent: VertexAR-Mobile/1.3.0 {platform} {version}
```

### Response Format
```json
{
  "data": { /* payload */ },
  "status": 200,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Error Response
```json
{
  "detail": "Error description",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req-xxx-yyy-zzz"
}
```

---

## Аутентификация

### POST /auth/login
```http
POST /auth/login HTTP/1.1
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password123"
}
```

**Response 200 OK:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Errors:**
- `401` — Invalid credentials
- `423` — Account locked
- `429` — Rate limit exceeded

**cURL:**
```bash
curl -X POST https://api.vertex-ar.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user@example.com","password":"pass123"}'
```

---

### POST /auth/logout
```http
POST /auth/logout HTTP/1.1
Authorization: Bearer {access_token}
```

**Response 204 No Content**

**cURL:**
```bash
curl -X POST https://api.vertex-ar.com/auth/logout \
  -H "Authorization: Bearer {token}"
```

---

## Клиенты

### POST /clients/
Создать клиента.

```http
POST /clients/ HTTP/1.1
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "phone": "+7 (999) 123-45-67",
  "name": "Иван Петров",
  "company_id": "vertex-ar-default"
}
```

**Response 201 Created:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "phone": "+7 (999) 123-45-67",
  "name": "Иван Петров",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**cURL:**
```bash
curl -X POST https://api.vertex-ar.com/clients/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "phone":"+7 (999) 123-45-67",
    "name":"Иван Петров",
    "company_id":"vertex-ar-default"
  }'
```

---

### GET /clients/
Получить список клиентов.

```http
GET /clients/?page=1&page_size=50&search=Иван HTTP/1.1
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `page` (int, default: 1)
- `page_size` (int, default: 50, max: 500)
- `search` (string, optional) — поиск по имени/телефону
- `company_id` (string, optional) — фильтр по компании

**Response 200 OK:**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "phone": "+7 (999) 123-45-67",
      "name": "Иван Петров",
      "created_at": "2024-01-15T10:30:00Z",
      "portraits_count": 5,
      "latest_portrait_preview": "data:image/jpeg;base64,..."
    }
  ],
  "total": 127,
  "page": 1,
  "page_size": 50,
  "total_pages": 3
}
```

**cURL:**
```bash
curl "https://api.vertex-ar.com/clients/?page=1&page_size=50&search=Иван" \
  -H "Authorization: Bearer {token}"
```

---

### GET /clients/{client_id}
Получить клиента.

```http
GET /clients/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Authorization: Bearer {access_token}
```

**Response 200 OK:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "phone": "+7 (999) 123-45-67",
  "name": "Иван Петров",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### PUT /clients/{client_id}
Обновить клиента.

```http
PUT /clients/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "phone": "+7 (999) 987-65-43",
  "name": "Иван Сидоров"
}
```

**Response 200 OK:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "phone": "+7 (999) 987-65-43",
  "name": "Иван Сидоров",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### DELETE /clients/{client_id}
Удалить клиента и все портреты.

```http
DELETE /clients/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Authorization: Bearer {access_token}
```

**Response 204 No Content**

---

## Портреты

### POST /portraits/
Загрузить портрет (фотографию).

```http
POST /portraits/ HTTP/1.1
Authorization: Bearer {access_token}
Content-Type: multipart/form-data; boundary=----WebKit

----WebKit
Content-Disposition: form-data; name="client_id"

550e8400-e29b-41d4-a716-446655440000
----WebKit
Content-Disposition: form-data; name="image"; filename="portrait.jpg"
Content-Type: image/jpeg

[binary data]
----WebKit--
```

**Form Data:**
- `client_id` (string, required) — UUID клиента
- `image` (file, required) — JPEG/PNG/WebP, max 50MB

**Response 201 Created:**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "permanent_link": "portrait_660e8400-e29b-41d4-a716-446655440001",
  "qr_code_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAA...",
  "image_path": "/storage/portraits/550e8400.../660e8400.jpg",
  "view_count": 0,
  "created_at": "2024-01-15T10:35:00Z"
}
```

**cURL:**
```bash
curl -X POST https://api.vertex-ar.com/portraits/ \
  -H "Authorization: Bearer {token}" \
  -F "client_id=550e8400-e29b-41d4-a716-446655440000" \
  -F "image=@portrait.jpg"
```

---

### GET /portraits/
Получить портреты клиента.

```http
GET /portraits/?client_id=550e8400-e29b-41d4-a716-446655440000&page=1 HTTP/1.1
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `client_id` (string, required)
- `page` (int, default: 1)
- `page_size` (int, default: 50)

**Response 200 OK:**
```json
{
  "items": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "client_id": "550e8400-e29b-41d4-a716-446655440000",
      "permanent_link": "portrait_660e8400-e29b-41d4-a716-446655440001",
      "qr_code_base64": "data:image/png;base64,...",
      "image_path": "/storage/portraits/.../660e8400.jpg",
      "view_count": 42,
      "created_at": "2024-01-15T10:35:00Z"
    }
  ],
  "total": 5
}
```

---

### GET /portraits/{portrait_id}
Получить портрет по ID.

```http
GET /portraits/660e8400-e29b-41d4-a716-446655440001 HTTP/1.1
Authorization: Bearer {access_token}
```

**Response 200 OK:** (аналогично элементу списка)

---

### GET /portraits/{portrait_id}/view
Просмотреть портрет в AR (публичный доступ).

```http
GET /portraits/660e8400-e29b-41d4-a716-446655440001/view HTTP/1.1
```

**Response 200 OK:** HTML страница с AR.js

---

### DELETE /portraits/{portrait_id}
Удалить портрет.

```http
DELETE /portraits/660e8400-e29b-41d4-a716-446655440001 HTTP/1.1
Authorization: Bearer {access_token}
```

**Response 204 No Content**

---

## Видео

### POST /videos/
Загрузить видео для портрета.

```http
POST /videos/ HTTP/1.1
Authorization: Bearer {access_token}
Content-Type: multipart/form-data; boundary=----WebKit

----WebKit
Content-Disposition: form-data; name="portrait_id"

660e8400-e29b-41d4-a716-446655440001
----WebKit
Content-Disposition: form-data; name="video"; filename="video.mp4"
Content-Type: video/mp4

[binary data]
----WebKit--
```

**Form Data:**
- `portrait_id` (string, required) — UUID портрета
- `video` (file, required) — MP4/WebM/MOV, max 50MB

**Response 201 Created:**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "portrait_id": "660e8400-e29b-41d4-a716-446655440001",
  "video_path": "/storage/portraits/.../videos/770e8400.mp4",
  "is_active": true,
  "created_at": "2024-01-15T10:40:00Z",
  "file_size_mb": 45
}
```

**cURL:**
```bash
curl -X POST https://api.vertex-ar.com/videos/ \
  -H "Authorization: Bearer {token}" \
  -F "portrait_id=660e8400-e29b-41d4-a716-446655440001" \
  -F "video=@video.mp4"
```

---

### GET /videos/
Получить видео портрета.

```http
GET /videos/?portrait_id=660e8400-e29b-41d4-a716-446655440001 HTTP/1.1
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `portrait_id` (string, required)
- `page` (int, default: 1)
- `page_size` (int, default: 50)

**Response 200 OK:**
```json
{
  "items": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440002",
      "portrait_id": "660e8400-e29b-41d4-a716-446655440001",
      "video_path": "/storage/portraits/.../770e8400.mp4",
      "is_active": true,
      "created_at": "2024-01-15T10:40:00Z",
      "file_size_mb": 45
    }
  ],
  "total": 3
}
```

---

### PATCH /videos/{video_id}/set-active
Установить видео активным (выводится в AR).

```http
PATCH /videos/770e8400-e29b-41d4-a716-446655440002/set-active HTTP/1.1
Authorization: Bearer {access_token}
```

**Response 200 OK:**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "portrait_id": "660e8400-e29b-41d4-a716-446655440001",
  "is_active": true,
  "created_at": "2024-01-15T10:40:00Z"
}
```

---

### DELETE /videos/{video_id}
Удалить видео.

```http
DELETE /videos/770e8400-e29b-41d4-a716-446655440002 HTTP/1.1
Authorization: Bearer {access_token}
```

**Response 204 No Content**

---

## Публичный доступ

### GET /portraits/{portrait_id}/view
Просмотр портрета AR (любой пользователь).

```http
GET /portraits/660e8400-e29b-41d4-a716-446655440001/view HTTP/1.1
```

**Response 200 OK:** HTML с AR.js сцена

**Возможные параметры:**
- Без аутентификации
- Увеличивает счетчик просмотров
- Возвращает HTML страницу с embedded AR контентом

---

### POST /portraits/{portrait_id}/click
Отследить клик (любой пользователь).

```http
POST /portraits/660e8400-e29b-41d4-a716-446655440001/click HTTP/1.1
```

**Response 200 OK:**
```json
{
  "status": "success",
  "portrait_id": "660e8400-e29b-41d4-a716-446655440001"
}
```

---

## Пользователи

### GET /users/profile
Получить профиль текущего пользователя.

```http
GET /users/profile HTTP/1.1
Authorization: Bearer {access_token}
```

**Response 200 OK:**
```json
{
  "username": "user@example.com",
  "email": "user@example.com",
  "full_name": "Иван Петров",
  "created_at": "2024-01-01T10:00:00Z",
  "last_login": "2024-01-15T09:30:00Z"
}
```

---

### GET /users/statistics
Получить статистику пользователя.

```http
GET /users/statistics HTTP/1.1
Authorization: Bearer {access_token}
```

**Response 200 OK:**
```json
{
  "total_clients": 127,
  "total_portraits": 542,
  "total_videos": 1243,
  "total_views": 15643,
  "total_clicks": 2341,
  "storage_usage_mb": 5234,
  "storage_limit_mb": 10240,
  "last_updated_at": "2024-01-15T10:00:00Z"
}
```

---

### PUT /users/profile
Обновить профиль.

```http
PUT /users/profile HTTP/1.1
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "email": "newemail@example.com",
  "full_name": "Иван Петров"
}
```

**Response 200 OK:** (обновленный профиль)

---

### POST /users/change-password
Изменить пароль.

```http
POST /users/change-password HTTP/1.1
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "current_password": "oldPassword123!",
  "new_password": "newPassword456!"
}
```

**Response 204 No Content**

---

## Системное

### GET /health
Проверить доступность сервера.

```http
GET /health HTTP/1.1
```

**Response 200 OK:**
```json
{
  "status": "healthy",
  "version": "1.3.0"
}
```

---

### GET /docs
Интерактивная документация (Swagger UI).

```
https://api.vertex-ar.com/docs
```

---

### GET /redoc
Альтернативная документация (ReDoc).

```
https://api.vertex-ar.com/redoc
```

---

### GET /openapi.json
OpenAPI спецификация.

```
https://api.vertex-ar.com/openapi.json
```

---

## Состояния и коды ошибок

### HTTP Status Codes

| Code | Значение |
|------|----------|
| 200 | OK |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 423 | Locked |
| 429 | Too Many Requests |
| 500 | Internal Server Error |

### Custom Error Codes

| Code | Описание |
|------|---------|
| `INVALID_CREDENTIALS` | Неверные логин/пароль |
| `ACCOUNT_LOCKED` | Аккаунт заблокирован |
| `RATE_LIMIT_EXCEEDED` | Превышен лимит запросов |
| `VALIDATION_ERROR` | Ошибка валидации данных |
| `RESOURCE_NOT_FOUND` | Ресурс не найден |
| `UNAUTHORIZED` | Требуется аутентификация |
| `FORBIDDEN` | Доступ запрещен |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/auth/login` | 5 запросов/минуту |
| `/portraits/` (upload) | 10 запросов/минуту |
| `/videos/` (upload) | 10 запросов/минуту |
| Other endpoints | 100 запросов/минуту |

---

## Примеры запросов

### JavaScript (fetch)

```javascript
// Login
const response = await fetch('https://api.vertex-ar.com/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'user@example.com',
    password: 'password123'
  })
});

const { access_token } = await response.json();

// Создать клиента
const clientResponse = await fetch('https://api.vertex-ar.com/clients/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    phone: '+7 (999) 123-45-67',
    name: 'Иван Петров',
    company_id: 'vertex-ar-default'
  })
});

const newClient = await clientResponse.json();
console.log('Client created:', newClient.id);
```

### Python (requests)

```python
import requests

BASE_URL = 'https://api.vertex-ar.com'

# Login
response = requests.post(f'{BASE_URL}/auth/login', json={
    'username': 'user@example.com',
    'password': 'password123'
})
token = response.json()['access_token']

# Get clients
headers = {'Authorization': f'Bearer {token}'}
response = requests.get(f'{BASE_URL}/clients/', headers=headers)
clients = response.json()['items']

print(f'Found {len(clients)} clients')
```

### Postman

1. Создайте Postman Collection
2. Добавьте переменные окружения:
   - `base_url` = `https://api.vertex-ar.com`
   - `token` = (заполнится после логина)
3. Используйте pre-request script для автоматического обновления токена

```javascript
// Pre-request Script в Postman
if (!pm.globals.get("token")) {
    pm.sendRequest({
        url: pm.globals.get("base_url") + '/auth/login',
        method: 'POST',
        header: { 'Content-Type': 'application/json' },
        body: {
            mode: 'raw',
            raw: JSON.stringify({
                username: pm.globals.get("username"),
                password: pm.globals.get("password")
            })
        }
    }, (err, res) => {
        pm.globals.set("token", res.json().access_token);
    });
}
```

---

## Версионирование

API версия: **1.3.0**

Поддерживаемые версии:
- `1.3.0` — Current (production ready)
- `1.2.0` — Legacy (deprecated Dec 31, 2024)
- `1.1.0` — EOL

---

**Последнее обновление:** 2024
**Статус:** ✅ Production Ready
