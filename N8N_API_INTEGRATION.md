# N8N API Integration Guide

Данное руководство описывает API endpoints для интеграции с n8n для автоматизации процессов управления заказами в Vertex AR.

## Аутентификация

Все запросы к API требуют аутентификации через Bearer token.

### Получение токена

```http
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your_password"
}
```

Ответ:
```json
{
  "access_token": "your_token_here",
  "token_type": "bearer"
}
```

Используйте полученный токен в заголовке Authorization для всех последующих запросов:
```
Authorization: Bearer your_token_here
```

## API Endpoints для n8n

### 1. Создание нового заказа

Создает клиента, портрет и первое видео. Генерирует постоянную ссылку и QR код.

```http
POST /orders/create
Authorization: Bearer {token}
Content-Type: multipart/form-data

phone: +7 (999) 123-45-67
name: Иван Иванов
image: [binary file]
video: [binary file]
```

Ответ:
```json
{
  "client": {
    "id": "uuid",
    "phone": "+7 (999) 123-45-67",
    "name": "Иван Иванов",
    "created_at": "2024-01-01T12:00:00"
  },
  "portrait": {
    "id": "uuid",
    "client_id": "uuid",
    "permanent_link": "http://example.com/portrait/uuid",
    "qr_code_base64": "base64_string",
    "image_path": "path/to/image.jpg",
    "view_count": 0,
    "created_at": "2024-01-01T12:00:00"
  },
  "video": {
    "id": "uuid",
    "portrait_id": "uuid",
    "video_path": "path/to/video.mp4",
    "is_active": true,
    "created_at": "2024-01-01T12:00:00"
  }
}
```

### 2. Поиск клиента по телефону

```http
GET /clients/search?phone={phone_number}
Authorization: Bearer {token}
```

Ответ:
```json
[
  {
    "id": "uuid",
    "phone": "+7 (999) 123-45-67",
    "name": "Иван Иванов",
    "created_at": "2024-01-01T12:00:00"
  }
]
```

### 3. Получение информации о клиенте

```http
GET /clients/{client_id}
Authorization: Bearer {token}
```

### 4. Получение портретов клиента

```http
GET /portraits/list?client_id={client_id}
Authorization: Bearer {token}
```

Ответ:
```json
[
  {
    "id": "uuid",
    "client_id": "uuid",
    "permanent_link": "http://example.com/portrait/uuid",
    "qr_code_base64": "base64_string",
    "image_path": "path/to/image.jpg",
    "view_count": 42,
    "created_at": "2024-01-01T12:00:00"
  }
]
```

### 5. Добавление нового видео к портрету

```http
POST /videos/add
Authorization: Bearer {token}
Content-Type: multipart/form-data

portrait_id: uuid
video: [binary file]
```

Ответ:
```json
{
  "id": "uuid",
  "portrait_id": "uuid",
  "video_path": "path/to/video.mp4",
  "is_active": false,
  "created_at": "2024-01-01T12:00:00"
}
```

### 6. Активация видео

Делает видео активным (отображается по постоянной ссылке). Деактивирует остальные видео портрета.

```http
PUT /videos/{video_id}/activate
Authorization: Bearer {token}
```

Ответ:
```json
{
  "id": "uuid",
  "portrait_id": "uuid",
  "video_path": "path/to/video.mp4",
  "is_active": true,
  "created_at": "2024-01-01T12:00:00"
}
```

### 7. Получение списка видео для портрета

```http
GET /videos/list/{portrait_id}
Authorization: Bearer {token}
```

Ответ:
```json
[
  {
    "id": "uuid",
    "portrait_id": "uuid",
    "video_path": "path/to/video.mp4",
    "is_active": true,
    "created_at": "2024-01-01T12:00:00"
  },
  {
    "id": "uuid2",
    "portrait_id": "uuid",
    "video_path": "path/to/video2.mp4",
    "is_active": false,
    "created_at": "2024-01-01T13:00:00"
  }
]
```

## Примеры использования в n8n

### Workflow 1: Создание заказа из Google Forms/Typeform

```
1. Trigger: Google Forms/Typeform New Response
2. HTTP Request: Login to API
3. HTTP Request: Create Order
   - Method: POST
   - URL: {{$node["API_URL"].json["url"]}}/orders/create
   - Authentication: Bearer Token
   - Body:
     - phone: {{$node["Trigger"].json["phone"]}}
     - name: {{$node["Trigger"].json["name"]}}
     - image: {{$node["Trigger"].json["image"]}}
     - video: {{$node["Trigger"].json["video"]}}
4. Send Email/Telegram: Notify admin with QR code
```

### Workflow 2: Поиск клиента и добавление нового видео

```
1. Trigger: Webhook/Schedule
2. HTTP Request: Search Client
   - Method: GET
   - URL: {{$node["API_URL"].json["url"]}}/clients/search?phone={{$json["phone"]}}
3. HTTP Request: Get Portraits
   - Method: GET
   - URL: {{$node["API_URL"].json["url"]}}/portraits/list?client_id={{$json["client_id"]}}
4. HTTP Request: Add Video
   - Method: POST
   - URL: {{$node["API_URL"].json["url"]}}/videos/add
   - Body:
     - portrait_id: {{$json["portrait_id"]}}
     - video: {{$json["video"]}}
5. HTTP Request: Activate Video
   - Method: PUT
   - URL: {{$node["API_URL"].json["url"]}}/videos/{{$json["video_id"]}}/activate
```

### Workflow 3: Автоматическая смена видео по расписанию

```
1. Trigger: Cron (каждый день в 00:00)
2. HTTP Request: Get All Portraits
3. Loop: For each portrait
   4. HTTP Request: Get Videos
   5. Function: Select next video (round-robin)
   6. HTTP Request: Activate Selected Video
   7. Send Notification: Telegram/Email
```

### Workflow 4: Telegram Bot для управления заказами

```
1. Trigger: Telegram Bot
2. Switch: Command
   - /create_order → Create Order Flow
   - /search → Search Client Flow
   - /add_video → Add Video Flow
   - /activate_video → Activate Video Flow
3. Telegram: Send Response
```

## Telegram уведомления

Система автоматически отправляет уведомления в Telegram при:

1. **Создании нового заказа:**
   ```
   📸 Новый заказ создан!
   Клиент: Иван Иванов
   Телефон: +7 (999) 123-45-67
   Ссылка: http://example.com/portrait/uuid
   ```

2. **Смене активного видео:**
   ```
   🎬 Видео изменено!
   Клиент: Иван Иванов
   Портрет: http://example.com/portrait/uuid
   Новое активное видео: uuid
   ```

### Настройка Telegram бота

1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Получите токен бота
3. Получите свой chat_id через [@userinfobot](https://t.me/userinfobot)
4. Добавьте в `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```

## Webhooks для n8n

Вы можете создать webhook endpoints в n8n и вызывать их из Vertex AR API:

1. Создайте Webhook node в n8n
2. Скопируйте URL webhook
3. Используйте HTTP Request node в n8n для вызова Vertex AR API
4. Vertex AR может вызывать ваш webhook при определенных событиях

## Обработка ошибок

Все endpoints возвращают стандартные HTTP коды:

- `200` - Успешный запрос
- `201` - Ресурс создан
- `400` - Неверные данные запроса
- `401` - Не авторизован
- `403` - Доступ запрещен
- `404` - Ресурс не найден
- `500` - Внутренняя ошибка сервера

Формат ошибки:
```json
{
  "detail": "Описание ошибки"
}
```

## Rate Limiting

В production рекомендуется настроить rate limiting для API endpoints:

- Authenticated requests: 100 requests/minute
- Unauthenticated requests: 20 requests/minute

## Best Practices

1. **Безопасность:**
   - Всегда используйте HTTPS в production
   - Храните токены в безопасном месте (n8n Credentials)
   - Регулярно обновляйте токены

2. **Производительность:**
   - Кешируйте результаты поиска
   - Используйте webhook'и вместо polling'а
   - Батчите запросы где возможно

3. **Мониторинг:**
   - Логируйте все API вызовы
   - Настройте алерты для ошибок
   - Отслеживайте время отклика

4. **Резервное копирование:**
   - Регулярно делайте backup базы данных
   - Сохраняйте резервные копии файлов (изображения, видео)
   - Документируйте все workflows в n8n

## Примеры запросов с curl

### Создание заказа
```bash
# 1. Получение токена
TOKEN=$(curl -X POST "http://your-domain.com/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}' \
  | jq -r '.access_token')

# 2. Создание заказа
curl -X POST "http://your-domain.com/orders/create" \
  -H "Authorization: Bearer $TOKEN" \
  -F "phone=+7 (999) 123-45-67" \
  -F "name=Иван Иванов" \
  -F "image=@/path/to/image.jpg" \
  -F "video=@/path/to/video.mp4"
```

### Поиск клиента
```bash
curl -X GET "http://your-domain.com/clients/search?phone=%2B7" \
  -H "Authorization: Bearer $TOKEN"
```

### Добавление видео
```bash
curl -X POST "http://your-domain.com/videos/add" \
  -H "Authorization: Bearer $TOKEN" \
  -F "portrait_id=uuid" \
  -F "video=@/path/to/video.mp4"
```

### Активация видео
```bash
curl -X PUT "http://your-domain.com/videos/uuid/activate" \
  -H "Authorization: Bearer $TOKEN"
```

## Поддержка

Для получения помощи или отчета о проблемах:
- GitHub Issues: [ссылка на репозиторий]
- Email: support@vertex-ar.com
- Документация: http://your-domain.com/docs
