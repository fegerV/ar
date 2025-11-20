# 📱 Mobile Backend Integration Guide

**Версия:** 1.3.0 | **Дата:** 2024  
**Для:** мобильных приложений iOS/Android/Flutter/React Native

Полный справочник методов, функций, переменных, данных и API для подключения мобильного приложения к Vertex AR бэкенду.

---

## 📋 Оглавление

1. [Общая информация](#общая-информация)
2. [Базовая конфигурация](#базовая-конфигурация)
3. [Аутентификация](#аутентификация)
4. [API Endpoints](#api-endpoints)
5. [Модели данных](#модели-данных)
6. [Обработка ошибок](#обработка-ошибок)
7. [Примеры кода](#примеры-кода)
8. [Лучшие практики](#лучшие-практики)

---

## Общая информация

### Технологический стек

- **Протокол:** HTTP/HTTPS REST API
- **Формат данных:** JSON
- **Аутентификация:** Bearer JWT токены
- **Версия API:** 1.3.0
- **Базовая версия Python:** 3.10+
- **Фреймворк:** FastAPI

### Эндпоинты

| Эндпоинт | Назначение |
|----------|-----------|
| Base URL | `https://api.vertex-ar.com` (production) или `http://localhost:8000` (dev) |
| Swagger UI | `/docs` |
| ReDoc | `/redoc` |
| OpenAPI Schema | `/openapi.json` |
| Health Check | `/health` |

### Требования безопасности

- Все запросы должны использовать HTTPS (в продакшене)
- Token должен храниться безопасно (Keychain для iOS, KeyStore для Android)
- Обязательны таймауты сетевых запросов (рекомендуется 30 сек)
- Реализуйте механизм повторных попыток с экспоненциальной задержкой

---

## Базовая конфигурация

### Переменные окружения (для тестирования бэкенда)

```bash
# Основные параметры
BASE_URL=https://api.vertex-ar.com
ENVIRONMENT=production

# Аутентификация
SESSION_TIMEOUT_MINUTES=30
AUTH_MAX_ATTEMPTS=5
AUTH_LOCKOUT_MINUTES=15

# Rate limiting
RATE_LIMIT_ENABLED=true
GLOBAL_RATE_LIMIT=100/minute
AUTH_RATE_LIMIT=5/minute
UPLOAD_RATE_LIMIT=10/minute

# CORS (для frontend и мобильных приложений)
CORS_ORIGINS=https://mobile-app.example.com,https://web-app.example.com

# Хранилище файлов
STORAGE_TYPE=minio          # или local
MINIO_ENDPOINT=s3.example.com
MINIO_BUCKET=vertex-ar

# Лимиты файлов
MAX_FILE_SIZE=50            # MB
ALLOWED_IMAGE_TYPES=image/jpeg,image/png,image/webp
ALLOWED_VIDEO_TYPES=video/mp4,video/webm
```

### Инициализация клиента (Pseudocode)

```typescript
// Общая конфигурация для мобильного клиента
interface MobileClientConfig {
  baseUrl: string;              // "https://api.vertex-ar.com"
  timeout: number;              // 30000 ms
  retryAttempts: number;        // 3
  retryDelay: number;           // 1000 ms (exponential backoff)
  enableLogging: boolean;       // true for dev, false for prod
  apiVersion: string;           // "1.3.0"
}

// Инициализация
const config: MobileClientConfig = {
  baseUrl: "https://api.vertex-ar.com",
  timeout: 30000,
  retryAttempts: 3,
  retryDelay: 1000,
  enableLogging: false,
  apiVersion: "1.3.0"
};

class VertexARClient {
  private token: string | null = null;
  private config: MobileClientConfig;
  
  constructor(config: MobileClientConfig) {
    this.config = config;
    this.loadStoredToken();
  }
  
  // Загрузить токен из безопасного хранилища
  private async loadStoredToken(): Promise<void> {
    // iOS: Keychain, Android: KeyStore, etc.
  }
  
  // Сохранить токен в безопасное хранилище
  private async saveToken(token: string): Promise<void> {
    // iOS: Keychain, Android: KeyStore, etc.
  }
}
```

---

## Аутентификация

### POST /auth/login

Вход пользователя в систему.

**Request:**
```json
{
  "username": "user@example.com",
  "password": "securePassword123!"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800  // seconds (30 minutes by default)
}
```

**Error Responses:**
- `401 Unauthorized` — Invalid credentials
- `423 Locked` — Account locked after multiple failed attempts
- `429 Too Many Requests` — Rate limit exceeded

**Implementation (Swift):**
```swift
func login(username: String, password: String) async throws -> TokenResponse {
  let endpoint = "\(config.baseUrl)/auth/login"
  
  let payload = [
    "username": username,
    "password": password
  ]
  
  var request = URLRequest(url: URL(string: endpoint)!)
  request.httpMethod = "POST"
  request.setValue("application/json", forHTTPHeaderField: "Content-Type")
  request.timeoutInterval = Double(config.timeout) / 1000
  
  request.httpBody = try JSONEncoder().encode(payload)
  
  let (data, response) = try await URLSession.shared.data(for: request)
  
  guard let httpResponse = response as? HTTPURLResponse,
        (200...299).contains(httpResponse.statusCode) else {
    throw APIError.invalidResponse
  }
  
  let token = try JSONDecoder().decode(TokenResponse.self, from: data)
  
  // Сохранить токен в Keychain
  try await saveToken(token.access_token)
  
  return token
}
```

**Implementation (Kotlin):**
```kotlin
suspend fun login(username: String, password: String): TokenResponse {
  val payload = mapOf(
    "username" to username,
    "password" to password
  )
  
  return try {
    val response = httpClient.post("${config.baseUrl}/auth/login") {
      contentType(ContentType.Application.Json)
      setBody(Json.encodeToString(payload))
      timeout {
        requestTimeoutMillis = config.timeout.toLong()
      }
    }
    
    if (response.status.isSuccess()) {
      val token = response.body<TokenResponse>()
      saveTokenToKeyStore(token.access_token)
      token
    } else {
      throw APIException("Login failed: ${response.status}")
    }
  } catch (e: Exception) {
    throw APIException("Login error", e)
  }
}
```

### POST /auth/logout

Выход пользователя и отзыв токена.

**Request:**
```http
POST /auth/logout
Authorization: Bearer {access_token}
```

**Response (204 No Content):**
```
(empty body)
```

**Implementation:**
```typescript
async logout(): Promise<void> {
  const response = await fetch(
    `${this.config.baseUrl}/auth/logout`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      timeout: this.config.timeout
    }
  );
  
  if (response.ok) {
    this.token = null;
    await this.clearStoredToken();
  }
}
```

### Token Management

**Хранение токена:**
- **iOS:** Использовать Keychain (LocalAuthentication framework)
- **Android:** Использовать KeyStore
- **Flutter:** `flutter_secure_storage`
- **React Native:** `react-native-keychain`

**Обновление токена:**
```typescript
// Проверить срок действия токена перед каждым запросом
isTokenExpired(): boolean {
  if (!this.token) return true;
  
  const decoded = jwt_decode(this.token);
  const expiresAt = decoded.exp * 1000; // convert to ms
  const now = Date.now();
  
  // Обновить за 5 минут до истечения
  return (expiresAt - now) < 5 * 60 * 1000;
}

// Перед каждым запросом:
if (this.isTokenExpired()) {
  // Требуется повторная аутентификация
  // или использовать refresh token (если реализован)
}
```

**Отправка токена в запросах:**
```
Authorization: Bearer {access_token}
```

или через Cookie:
```
Cookie: authToken={access_token}
```

---

## API Endpoints

### 1. Управление клиентами

#### POST /clients/

Создание нового клиента.

**Request:**
```json
{
  "phone": "+7 (999) 123-45-67",
  "name": "Иван Петров",
  "company_id": "vertex-ar-default"
}
```

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "phone": "+7 (999) 123-45-67",
  "name": "Иван Петров",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Error Responses:**
- `400 Bad Request` — Invalid data format
- `409 Conflict` — Client with this phone already exists
- `401 Unauthorized` — Not authenticated

#### GET /clients/

Получить список клиентов.

**Query Parameters:**
| Параметр | Тип | Описание |
|----------|-----|---------|
| `page` | int | Номер страницы (по умолчанию 1) |
| `page_size` | int | Размер страницы (по умолчанию 50, макс 500) |
| `search` | string | Поиск по имени или телефону |

**Response (200 OK):**
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

#### GET /clients/{client_id}

Получить информацию о клиенте.

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "phone": "+7 (999) 123-45-67",
  "name": "Иван Петров",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### PUT /clients/{client_id}

Обновить информацию клиента.

**Request:**
```json
{
  "phone": "+7 (999) 987-65-43",
  "name": "Иван Сидоров"
}
```

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "phone": "+7 (999) 987-65-43",
  "name": "Иван Сидоров",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### DELETE /clients/{client_id}

Удалить клиента и все связанные портреты.

**Response (204 No Content):**
```
(empty body)
```

### 2. Управление портретами

#### POST /portraits/

Создание нового портрета (загрузка фотографии).

**Request (multipart/form-data):**
```
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

----WebKitFormBoundary
Content-Disposition: form-data; name="client_id"

550e8400-e29b-41d4-a716-446655440000
----WebKitFormBoundary
Content-Disposition: form-data; name="image"; filename="portrait.jpg"
Content-Type: image/jpeg

[binary image data]
----WebKitFormBoundary--
```

**Response (201 Created):**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "permanent_link": "portrait_660e8400-e29b-41d4-a716-446655440001",
  "qr_code_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAYAA...",
  "image_path": "/storage/portraits/550e8400-e29b-41d4-a716-446655440000/660e8400-e29b-41d4-a716-446655440001.jpg",
  "view_count": 0,
  "created_at": "2024-01-15T10:35:00Z"
}
```

**Implementation (Swift):**
```swift
func uploadPortrait(clientId: String, imageData: Data) async throws -> PortraitResponse {
  let endpoint = "\(config.baseUrl)/portraits/"
  
  var request = URLRequest(url: URL(string: endpoint)!)
  request.httpMethod = "POST"
  request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
  
  let boundary = "----WebKitFormBoundary\(UUID().uuidString)"
  request.setValue(
    "multipart/form-data; boundary=\(boundary)",
    forHTTPHeaderField: "Content-Type"
  )
  
  var body = Data()
  
  // Add client_id
  body.append("--\(boundary)\r\n".data(using: .utf8)!)
  body.append("Content-Disposition: form-data; name=\"client_id\"\r\n\r\n".data(using: .utf8)!)
  body.append("\(clientId)\r\n".data(using: .utf8)!)
  
  // Add image
  body.append("--\(boundary)\r\n".data(using: .utf8)!)
  body.append(
    "Content-Disposition: form-data; name=\"image\"; filename=\"portrait.jpg\"\r\n".data(using: .utf8)!
  )
  body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
  body.append(imageData)
  body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
  
  request.httpBody = body
  request.timeoutInterval = Double(config.timeout) / 1000
  
  let (data, response) = try await URLSession.shared.data(for: request)
  
  guard let httpResponse = response as? HTTPURLResponse,
        (200...299).contains(httpResponse.statusCode) else {
    throw APIError.uploadFailed
  }
  
  return try JSONDecoder().decode(PortraitResponse.self, from: data)
}
```

#### GET /portraits/

Получить список портретов клиента.

**Query Parameters:**
| Параметр | Тип | Описание |
|----------|-----|---------|
| `client_id` | string | ID клиента (обязателен) |
| `page` | int | Номер страницы |
| `page_size` | int | Размер страницы |

**Response (200 OK):**
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

#### GET /portraits/{portrait_id}

Получить портрет по ID.

**Response (200 OK):** (аналогично элементу из списка)

#### GET /portraits/{portrait_id}/view

Просмотр портрета AR (увеличивает счетчик просмотров).

**Response (200 OK):** HTML страница с AR контентом

**Query Parameters:**
| Параметр | Тип | Описание |
|----------|-----|---------|
| `portrait_id` | string | ID портрета (обязателен) |

#### DELETE /portraits/{portrait_id}

Удалить портрет.

**Response (204 No Content)**

### 3. Управление видео

#### POST /videos/

Загрузить видео для портрета.

**Request (multipart/form-data):**
```
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

----WebKitFormBoundary
Content-Disposition: form-data; name="portrait_id"

660e8400-e29b-41d4-a716-446655440001
----WebKitFormBoundary
Content-Disposition: form-data; name="video"; filename="video.mp4"
Content-Type: video/mp4

[binary video data]
----WebKitFormBoundary--
```

**Response (201 Created):**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "portrait_id": "660e8400-e29b-41d4-a716-446655440001",
  "video_path": "/storage/portraits/.../videos/770e8400-e29b-41d4-a716-446655440002.mp4",
  "is_active": true,
  "created_at": "2024-01-15T10:40:00Z",
  "file_size_mb": 45
}
```

#### GET /videos/?portrait_id={portrait_id}

Получить список видео для портрета.

**Response (200 OK):**
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

#### PATCH /videos/{video_id}/set-active

Установить видео активным.

**Response (200 OK):**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "portrait_id": "660e8400-e29b-41d4-a716-446655440001",
  "is_active": true,
  "created_at": "2024-01-15T10:40:00Z"
}
```

#### DELETE /videos/{video_id}

Удалить видео.

**Response (204 No Content)**

### 4. Публичный просмотр

#### GET /portraits/{portrait_id}/view

Просмотр портрета в AR.

**Response (200 OK):** HTML страница с интегрированным AR.js

```html
<!DOCTYPE html>
<html>
  <head>
    <script src="https://aframe.io/releases/1.4.0/aframe.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/ar.js@3.4.5/aframe/aframe-ar.js"></script>
  </head>
  <body style="margin: 0; overflow: hidden;">
    <a-scene embedded arjs="sourceType: webcam; debugUIEnabled: false;">
      <a-camera position="0 1.6 0" look-controls wasd-controls></a-camera>
      <a-entity
        id="nft-marker"
        type="nft"
        url="/nft-markers/{portrait_id}/portrait"
        scale="1 1 1"
      >
        <a-video src="{video_url}" width="1024" height="1024"></a-video>
      </a-entity>
    </a-scene>
  </body>
</html>
```

### 5. Аналитика и статистика

#### GET /users/profile

Получить профиль текущего пользователя.

**Request:**
```http
GET /users/profile
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "username": "user@example.com",
  "email": "user@example.com",
  "full_name": "Иван Петров",
  "created_at": "2024-01-01T10:00:00Z",
  "last_login": "2024-01-15T09:30:00Z"
}
```

#### GET /users/statistics

Получить статистику пользователя.

**Response (200 OK):**
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

#### GET /portraits/{portrait_id}/analytics

Получить аналитику по портрету.

**Response (200 OK):**
```json
{
  "portrait_id": "660e8400-e29b-41d4-a716-446655440001",
  "view_count": 542,
  "click_count": 123,
  "engagement_rate": 22.7,
  "created_at": "2024-01-15T10:35:00Z",
  "views_by_day": [
    { "date": "2024-01-15", "views": 25 },
    { "date": "2024-01-14", "views": 18 }
  ]
}
```

### 6. Health Check

#### GET /health

Проверить доступность сервера.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.3.0"
}
```

---

## Модели данных

### User Model

```typescript
interface User {
  username: string;           // Уникальное имя пользователя
  email: string;              // Email адрес
  full_name: string;          // Полное имя
  is_active: boolean;         // Активен ли пользователь
  is_admin: boolean;          // Имеет ли права администратора
  created_at: string;         // ISO 8601 timestamp
  last_login: string | null;  // ISO 8601 timestamp
}
```

### Client Model

```typescript
interface Client {
  id: string;                 // UUID
  phone: string;              // Номер телефона
  name: string;               // Имя клиента
  company_id: string;         // ID компании
  created_at: string;         // ISO 8601 timestamp
  updated_at: string;         // ISO 8601 timestamp
}
```

### Portrait Model

```typescript
interface Portrait {
  id: string;                 // UUID
  client_id: string;          // UUID клиента
  permanent_link: string;     // Постоянная ссылка (portrait_{id})
  qr_code_base64: string;     // QR-код в base64
  image_path: string;         // Путь к изображению на сервере
  nft_marker_path: string;    // Путь к NFT маркеру
  view_count: number;         // Количество просмотров
  click_count: number;        // Количество кликов
  created_at: string;         // ISO 8601 timestamp
  updated_at: string;         // ISO 8601 timestamp
}
```

### Video Model

```typescript
interface Video {
  id: string;                 // UUID
  portrait_id: string;        // UUID портрета
  video_path: string;         // Путь к видео на сервере
  is_active: boolean;         // Активно ли видео (выводится в AR)
  file_size_mb: number;       // Размер файла в МБ
  duration_seconds: number;   // Длительность видео
  created_at: string;         // ISO 8601 timestamp
}
```

### TokenResponse Model

```typescript
interface TokenResponse {
  access_token: string;       // JWT токен
  token_type: string;         // "bearer"
  expires_in: number;         // Время истечения в секундах
}
```

### ErrorResponse Model

```typescript
interface ErrorResponse {
  detail: string;             // Описание ошибки
  error_code?: string;        // Код ошибки (опционально)
  timestamp: string;          // ISO 8601 timestamp
  request_id?: string;        // Уникальный ID запроса
}
```

---

## Обработка ошибок

### HTTP Status Codes

| Code | Смысл | Действие |
|------|-------|---------|
| 200 | OK | Запрос выполнен успешно |
| 201 | Created | Ресурс создан успешно |
| 204 | No Content | Запрос выполнен, ответ пуст |
| 400 | Bad Request | Ошибка в данных запроса (валидация) |
| 401 | Unauthorized | Требуется аутентификация |
| 403 | Forbidden | Доступ запрещен |
| 404 | Not Found | Ресурс не найден |
| 409 | Conflict | Конфликт (например, дубликат) |
| 423 | Locked | Аккаунт заблокирован |
| 429 | Too Many Requests | Превышен лимит запросов |
| 500 | Internal Server Error | Ошибка на сервере |

### Error Response Examples

**400 Bad Request (Validation Error):**
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "password"],
      "msg": "String should have at least 8 characters",
      "input": "short"
    }
  ]
}
```

**401 Unauthorized:**
```json
{
  "detail": "Not authenticated"
}
```

**429 Too Many Requests:**
```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds"
}
```

### Error Handling Implementation

**Swift:**
```swift
enum APIError: LocalizedError {
  case invalidURL
  case invalidResponse
  case decodingError
  case networkError(URLError)
  case serverError(Int, String)
  case rateLimited(String)
  case unauthorized
  case validationError(String)
  
  var errorDescription: String? {
    switch self {
    case .invalidURL:
      return "Invalid URL"
    case .invalidResponse:
      return "Invalid server response"
    case .decodingError:
      return "Failed to decode response"
    case .networkError(let error):
      return "Network error: \(error.localizedDescription)"
    case .serverError(let code, let message):
      return "Server error (\(code)): \(message)"
    case .rateLimited(let message):
      return "Rate limited: \(message)"
    case .unauthorized:
      return "Unauthorized - please login again"
    case .validationError(let message):
      return "Validation error: \(message)"
    }
  }
}

func handleAPIError(_ error: Error) -> APIError {
  if let urlError = error as? URLError {
    return .networkError(urlError)
  }
  
  if let apiError = error as? APIError {
    return apiError
  }
  
  return .invalidResponse
}
```

**Kotlin:**
```kotlin
sealed class APIError : Exception() {
  data class NetworkError(val exception: IOException) : APIError()
  data class ServerError(val code: Int, val message: String) : APIError()
  data class ValidationError(val details: String) : APIError()
  object Unauthorized : APIError()
  object Forbidden : APIError()
  data class RateLimited(val retryAfter: Int) : APIError()
  object NotFound : APIError()
  
  override val message: String
    get() = when (this) {
      is NetworkError -> "Network error: ${exception.message}"
      is ServerError -> "Server error ($code): $message"
      is ValidationError -> "Validation error: $details"
      Unauthorized -> "Unauthorized - please login again"
      Forbidden -> "Forbidden - insufficient permissions"
      is RateLimited -> "Rate limited - retry in $retryAfter seconds"
      NotFound -> "Resource not found"
    }
}

suspend fun <T> makeRequest(
  call: suspend () -> T,
  retryAttempts: Int = 3,
  retryDelay: Long = 1000
): T {
  repeat(retryAttempts) { attempt ->
    try {
      return call()
    } catch (e: APIError) {
      if (e is APIError.RateLimited && attempt < retryAttempts - 1) {
        delay(e.retryAfter * 1000L)
      } else if (attempt == retryAttempts - 1) {
        throw e
      } else {
        delay(retryDelay * (attempt + 1))
      }
    }
  }
  throw APIError.NetworkError(IOException("Max retries exceeded"))
}
```

---

## Примеры кода

### iOS (Swift)

#### Полный пример приложения

```swift
import Foundation

// MARK: - Configuration
struct APIConfig {
  let baseUrl: String = "https://api.vertex-ar.com"
  let timeout: TimeInterval = 30
}

// MARK: - Models
struct TokenResponse: Codable {
  let access_token: String
  let token_type: String
}

struct ClientResponse: Codable {
  let id: String
  let phone: String
  let name: String
  let created_at: String
}

struct PortraitResponse: Codable {
  let id: String
  let client_id: String
  let permanent_link: String
  let qr_code_base64: String?
  let image_path: String
  let view_count: Int
  let created_at: String
}

// MARK: - API Client
class VertexARClient {
  private let config = APIConfig()
  private var token: String?
  
  // MARK: - Authentication
  
  func login(username: String, password: String) async throws -> TokenResponse {
    let endpoint = "\(config.baseUrl)/auth/login"
    
    let payload = [
      "username": username,
      "password": password
    ]
    
    var request = URLRequest(url: URL(string: endpoint)!)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.timeoutInterval = config.timeout
    request.httpBody = try JSONEncoder().encode(payload)
    
    let (data, response) = try await URLSession.shared.data(for: request)
    
    guard let httpResponse = response as? HTTPURLResponse,
          (200...299).contains(httpResponse.statusCode) else {
      throw APIError.invalidResponse
    }
    
    let tokenResponse = try JSONDecoder().decode(TokenResponse.self, from: data)
    self.token = tokenResponse.access_token
    
    // Save to Keychain
    try saveTokenToKeychain(tokenResponse.access_token)
    
    return tokenResponse
  }
  
  // MARK: - Clients
  
  func createClient(phone: String, name: String) async throws -> ClientResponse {
    let endpoint = "\(config.baseUrl)/clients/"
    
    let payload = [
      "phone": phone,
      "name": name,
      "company_id": "vertex-ar-default"
    ]
    
    var request = URLRequest(url: URL(string: endpoint)!)
    request.httpMethod = "POST"
    addAuthHeader(to: &request)
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.timeoutInterval = config.timeout
    request.httpBody = try JSONEncoder().encode(payload)
    
    let (data, response) = try await URLSession.shared.data(for: request)
    
    guard let httpResponse = response as? HTTPURLResponse,
          (200...299).contains(httpResponse.statusCode) else {
      throw APIError.invalidResponse
    }
    
    return try JSONDecoder().decode(ClientResponse.self, from: data)
  }
  
  func getClients(page: Int = 1, pageSize: Int = 50) async throws -> [ClientResponse] {
    let endpoint = "\(config.baseUrl)/clients/?page=\(page)&page_size=\(pageSize)"
    
    var request = URLRequest(url: URL(string: endpoint)!)
    request.httpMethod = "GET"
    addAuthHeader(to: &request)
    request.timeoutInterval = config.timeout
    
    let (data, response) = try await URLSession.shared.data(for: request)
    
    guard let httpResponse = response as? HTTPURLResponse,
          (200...299).contains(httpResponse.statusCode) else {
      throw APIError.invalidResponse
    }
    
    let wrapper = try JSONDecoder().decode(
      [String: AnyCodable].self,
      from: data
    )
    
    guard let items = wrapper["items"] as? [[String: Any]] else {
      return []
    }
    
    return try items.map { item in
      let data = try JSONSerialization.data(withJSONObject: item)
      return try JSONDecoder().decode(ClientResponse.self, from: data)
    }
  }
  
  // MARK: - Portraits
  
  func uploadPortrait(
    clientId: String,
    imageData: Data
  ) async throws -> PortraitResponse {
    let endpoint = "\(config.baseUrl)/portraits/"
    
    var request = URLRequest(url: URL(string: endpoint)!)
    request.httpMethod = "POST"
    addAuthHeader(to: &request)
    request.timeoutInterval = config.timeout * 2 // Longer timeout for uploads
    
    let boundary = "----WebKitFormBoundary\(UUID().uuidString)"
    request.setValue(
      "multipart/form-data; boundary=\(boundary)",
      forHTTPHeaderField: "Content-Type"
    )
    
    var body = Data()
    
    // Add client_id field
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append("Content-Disposition: form-data; name=\"client_id\"\r\n\r\n".data(using: .utf8)!)
    body.append("\(clientId)\r\n".data(using: .utf8)!)
    
    // Add image field
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append(
      "Content-Disposition: form-data; name=\"image\"; filename=\"portrait.jpg\"\r\n".data(using: .utf8)!
    )
    body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
    body.append(imageData)
    body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
    
    request.httpBody = body
    
    let (data, response) = try await URLSession.shared.data(for: request)
    
    guard let httpResponse = response as? HTTPURLResponse,
          (200...299).contains(httpResponse.statusCode) else {
      throw APIError.invalidResponse
    }
    
    return try JSONDecoder().decode(PortraitResponse.self, from: data)
  }
  
  // MARK: - Helper Methods
  
  private func addAuthHeader(to request: inout URLRequest) {
    if let token = token {
      request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    }
  }
  
  private func saveTokenToKeychain(_ token: String) throws {
    // Implementation for Keychain storage
    let query: [String: Any] = [
      kSecClass as String: kSecClassGenericPassword,
      kSecAttrAccount as String: "vertex_ar_token",
      kSecValueData as String: token.data(using: .utf8)!
    ]
    
    SecItemDelete(query as CFDictionary)
    SecItemAdd(query as CFDictionary, nil)
  }
}

// MARK: - Usage Example
@main
struct VertexARApp {
  static func main() async {
    let client = VertexARClient()
    
    do {
      // Login
      let token = try await client.login(
        username: "user@example.com",
        password: "password123"
      )
      print("Login successful: \(token.access_token)")
      
      // Create client
      let newClient = try await client.createClient(
        phone: "+1234567890",
        name: "John Doe"
      )
      print("Client created: \(newClient.id)")
      
      // Get clients
      let clients = try await client.getClients()
      print("Found \(clients.count) clients")
      
    } catch {
      print("Error: \(error)")
    }
  }
}
```

### Android (Kotlin)

#### Полный пример приложения

```kotlin
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*
import com.google.gson.annotations.SerializedName
import java.util.concurrent.TimeUnit

// MARK: - Configuration
object APIConfig {
  const val BASE_URL = "https://api.vertex-ar.com"
  const val TIMEOUT_SECONDS = 30L
}

// MARK: - Models
data class TokenResponse(
  @SerializedName("access_token")
  val accessToken: String,
  @SerializedName("token_type")
  val tokenType: String
)

data class ClientResponse(
  val id: String,
  val phone: String,
  val name: String,
  val created_at: String
)

data class ClientsListResponse(
  val items: List<ClientResponse>,
  val total: Int,
  val page: Int,
  val page_size: Int,
  val total_pages: Int
)

data class PortraitResponse(
  val id: String,
  val client_id: String,
  val permanent_link: String,
  val qr_code_base64: String?,
  val image_path: String,
  val view_count: Int,
  val created_at: String
)

// MARK: - API Service Interface
interface VertexARService {
  @POST("/auth/login")
  suspend fun login(@Body request: LoginRequest): TokenResponse
  
  @POST("/clients/")
  suspend fun createClient(@Body request: CreateClientRequest): ClientResponse
  
  @GET("/clients/")
  suspend fun getClients(
    @Query("page") page: Int = 1,
    @Query("page_size") pageSize: Int = 50
  ): ClientsListResponse
  
  @POST("/portraits/")
  suspend fun uploadPortrait(
    @Part("client_id") clientId: okhttp3.RequestBody,
    @Part image: MultipartBody.Part
  ): PortraitResponse
}

data class LoginRequest(
  val username: String,
  val password: String
)

data class CreateClientRequest(
  val phone: String,
  val name: String,
  val company_id: String = "vertex-ar-default"
)

// MARK: - API Client
class VertexARClient {
  private var token: String? = null
  private lateinit var service: VertexARService
  
  init {
    setupRetrofit()
  }
  
  private fun setupRetrofit() {
    val httpClient = OkHttpClient.Builder()
      .connectTimeout(APIConfig.TIMEOUT_SECONDS, TimeUnit.SECONDS)
      .readTimeout(APIConfig.TIMEOUT_SECONDS, TimeUnit.SECONDS)
      .writeTimeout(APIConfig.TIMEOUT_SECONDS, TimeUnit.SECONDS)
      .addInterceptor { chain ->
        val originalRequest = chain.request()
        val requestBuilder = originalRequest.newBuilder()
        
        token?.let {
          requestBuilder.addHeader("Authorization", "Bearer $it")
        }
        
        val newRequest = requestBuilder.build()
        chain.proceed(newRequest)
      }
      .build()
    
    val retrofit = Retrofit.Builder()
      .baseUrl(APIConfig.BASE_URL)
      .addConverterFactory(GsonConverterFactory.create())
      .client(httpClient)
      .build()
    
    service = retrofit.create(VertexARService::class.java)
  }
  
  suspend fun login(username: String, password: String): TokenResponse {
    return withContext(Dispatchers.IO) {
      val request = LoginRequest(username, password)
      val response = service.login(request)
      token = response.accessToken
      
      // Save token to KeyStore
      saveTokenToKeyStore(response.accessToken)
      
      response
    }
  }
  
  suspend fun createClient(phone: String, name: String): ClientResponse {
    return withContext(Dispatchers.IO) {
      val request = CreateClientRequest(phone, name)
      service.createClient(request)
    }
  }
  
  suspend fun getClients(page: Int = 1, pageSize: Int = 50): ClientsListResponse {
    return withContext(Dispatchers.IO) {
      service.getClients(page, pageSize)
    }
  }
  
  suspend fun uploadPortrait(
    clientId: String,
    imageData: ByteArray,
    fileName: String = "portrait.jpg"
  ): PortraitResponse {
    return withContext(Dispatchers.IO) {
      val clientIdBody = clientId.toRequestBody("text/plain".toMediaType())
      val imageBody = okhttp3.RequestBody.create(
        "image/jpeg".toMediaType(),
        imageData
      )
      val imagePart = MultipartBody.Part.createFormData(
        "image",
        fileName,
        imageBody
      )
      
      service.uploadPortrait(clientIdBody, imagePart)
    }
  }
  
  private fun saveTokenToKeyStore(token: String) {
    // Implementation for KeyStore storage
    val keyStore = android.security.keystore.KeyStore.getInstance("AndroidKeyStore")
    keyStore.load(null)
    // ... save token
  }
}

// MARK: - Usage Example
class MainActivity : AppCompatActivity() {
  private lateinit var apiClient: VertexARClient
  
  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    
    apiClient = VertexARClient()
    
    lifecycleScope.launch {
      try {
        // Login
        val token = apiClient.login(
          username = "user@example.com",
          password = "password123"
        )
        println("Login successful: ${token.accessToken}")
        
        // Create client
        val newClient = apiClient.createClient(
          phone = "+1234567890",
          name = "John Doe"
        )
        println("Client created: ${newClient.id}")
        
        // Get clients
        val clientsList = apiClient.getClients()
        println("Found ${clientsList.items.size} clients")
        
      } catch (e: Exception) {
        println("Error: ${e.message}")
        e.printStackTrace()
      }
    }
  }
}
```

### Flutter (Dart)

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

// MARK: - Configuration
class APIConfig {
  static const String baseUrl = 'https://api.vertex-ar.com';
  static const Duration timeout = Duration(seconds: 30);
}

// MARK: - Models
class TokenResponse {
  final String accessToken;
  final String tokenType;
  
  TokenResponse({
    required this.accessToken,
    required this.tokenType,
  });
  
  factory TokenResponse.fromJson(Map<String, dynamic> json) {
    return TokenResponse(
      accessToken: json['access_token'],
      tokenType: json['token_type'] ?? 'bearer',
    );
  }
}

class ClientResponse {
  final String id;
  final String phone;
  final String name;
  final String createdAt;
  
  ClientResponse({
    required this.id,
    required this.phone,
    required this.name,
    required this.createdAt,
  });
  
  factory ClientResponse.fromJson(Map<String, dynamic> json) {
    return ClientResponse(
      id: json['id'],
      phone: json['phone'],
      name: json['name'],
      createdAt: json['created_at'],
    );
  }
}

class PortraitResponse {
  final String id;
  final String clientId;
  final String permanentLink;
  final String? qrCodeBase64;
  final String imagePath;
  final int viewCount;
  final String createdAt;
  
  PortraitResponse({
    required this.id,
    required this.clientId,
    required this.permanentLink,
    this.qrCodeBase64,
    required this.imagePath,
    required this.viewCount,
    required this.createdAt,
  });
  
  factory PortraitResponse.fromJson(Map<String, dynamic> json) {
    return PortraitResponse(
      id: json['id'],
      clientId: json['client_id'],
      permanentLink: json['permanent_link'],
      qrCodeBase64: json['qr_code_base64'],
      imagePath: json['image_path'],
      viewCount: json['view_count'],
      createdAt: json['created_at'],
    );
  }
}

// MARK: - API Client
class VertexARClient {
  final _secureStorage = FlutterSecureStorage();
  String? _token;
  
  Future<void> _loadToken() async {
    _token = await _secureStorage.read(key: 'vertex_ar_token');
  }
  
  Future<void> _saveToken(String token) async {
    _token = token;
    await _secureStorage.write(key: 'vertex_ar_token', value: token);
  }
  
  Future<TokenResponse> login(String username, String password) async {
    final url = Uri.parse('${APIConfig.baseUrl}/auth/login');
    
    final response = await http.post(
      url,
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'username': username,
        'password': password,
      }),
      timeout: APIConfig.timeout,
    ).catchError((e) {
      throw Exception('Network error: $e');
    });
    
    if (response.statusCode == 200) {
      final tokenResponse = TokenResponse.fromJson(
        jsonDecode(response.body),
      );
      await _saveToken(tokenResponse.accessToken);
      return tokenResponse;
    } else {
      throw Exception('Login failed: ${response.statusCode}');
    }
  }
  
  Future<ClientResponse> createClient(String phone, String name) async {
    await _loadToken();
    
    final url = Uri.parse('${APIConfig.baseUrl}/clients/');
    
    final response = await http.post(
      url,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_token',
      },
      body: jsonEncode({
        'phone': phone,
        'name': name,
        'company_id': 'vertex-ar-default',
      }),
      timeout: APIConfig.timeout,
    ).catchError((e) {
      throw Exception('Network error: $e');
    });
    
    if (response.statusCode == 201) {
      return ClientResponse.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to create client: ${response.statusCode}');
    }
  }
  
  Future<List<ClientResponse>> getClients({
    int page = 1,
    int pageSize = 50,
  }) async {
    await _loadToken();
    
    final url = Uri.parse(
      '${APIConfig.baseUrl}/clients/?page=$page&page_size=$pageSize'
    );
    
    final response = await http.get(
      url,
      headers: {
        'Authorization': 'Bearer $_token',
      },
      timeout: APIConfig.timeout,
    ).catchError((e) {
      throw Exception('Network error: $e');
    });
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      final items = (data['items'] as List)
          .map((item) => ClientResponse.fromJson(item))
          .toList();
      return items;
    } else {
      throw Exception('Failed to fetch clients: ${response.statusCode}');
    }
  }
  
  Future<PortraitResponse> uploadPortrait(
    String clientId,
    List<int> imageBytes,
    String fileName,
  ) async {
    await _loadToken();
    
    final url = Uri.parse('${APIConfig.baseUrl}/portraits/');
    
    final request = http.MultipartRequest('POST', url)
      ..headers['Authorization'] = 'Bearer $_token'
      ..fields['client_id'] = clientId
      ..files.add(
        http.MultipartFile.fromBytes(
          'image',
          imageBytes,
          filename: fileName,
        ),
      );
    
    final response = await request
        .send()
        .timeout(APIConfig.timeout);
    
    if (response.statusCode == 201) {
      final body = await response.stream.bytesToString();
      return PortraitResponse.fromJson(jsonDecode(body));
    } else {
      throw Exception('Portrait upload failed: ${response.statusCode}');
    }
  }
}

// MARK: - Usage Example
void main() {
  runApp(const MyApp());
}

class MyApp extends StatefulWidget {
  const MyApp({Key? key}) : super(key: key);
  
  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  final apiClient = VertexARClient();
  
  @override
  void initState() {
    super.initState();
    _testAPI();
  }
  
  Future<void> _testAPI() async {
    try {
      // Login
      final token = await apiClient.login(
        'user@example.com',
        'password123',
      );
      print('Login successful: ${token.accessToken}');
      
      // Create client
      final newClient = await apiClient.createClient(
        '+1234567890',
        'John Doe',
      );
      print('Client created: ${newClient.id}');
      
      // Get clients
      final clients = await apiClient.getClients();
      print('Found ${clients.length} clients');
    } catch (e) {
      print('Error: $e');
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Vertex AR',
      theme: ThemeData(primarySwatch: Colors.blue),
      home: const Scaffold(
        body: Center(child: Text('Check console output')),
      ),
    );
  }
}
```

---

## Лучшие практики

### 1. Безопасность

```typescript
// ✅ ПРАВИЛЬНО: Безопасное хранение токена
async function loginAndSaveSecurely(username: string, password: string) {
  const token = await login(username, password);
  
  // iOS Keychain / Android KeyStore
  await secureStorage.setItem('auth_token', token);
}

// ✅ ПРАВИЛЬНО: Проверка истечения токена
function isTokenValid(): boolean {
  const token = getStoredToken();
  if (!token) return false;
  
  const decoded = jwt_decode(token);
  return decoded.exp * 1000 > Date.now() + 5 * 60 * 1000;
}

// ❌ НЕПРАВИЛЬНО: Хранение токена в plaintext
localStorage.setItem('token', token);

// ❌ НЕПРАВИЛЬНО: Отправка токена в URL
fetch(`https://api.example.com/data?token=${token}`);
```

### 2. Обработка сетевых ошибок

```typescript
// ✅ ПРАВИЛЬНО: Повторные попытки с exponential backoff
async function apiCallWithRetry(
  fn: () => Promise<any>,
  maxRetries = 3
): Promise<any> {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === maxRetries - 1) throw error;
      
      const delay = Math.pow(2, attempt) * 1000;
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}

// ✅ ПРАВИЛЬНО: Timeout для запросов
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 30000);

try {
  const response = await fetch(url, { signal: controller.signal });
} finally {
  clearTimeout(timeoutId);
}
```

### 3. Загрузка файлов

```typescript
// ✅ ПРАВИЛЬНО: Проверка размера перед загрузкой
async function uploadFile(file: File) {
  const MAX_SIZE = 50 * 1024 * 1024; // 50 MB
  
  if (file.size > MAX_SIZE) {
    throw new Error(`File too large: ${file.size} > ${MAX_SIZE}`);
  }
  
  // Проверка MIME type
  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
  if (!allowedTypes.includes(file.type)) {
    throw new Error(`Invalid file type: ${file.type}`);
  }
  
  // Загрузить с progress tracking
  const formData = new FormData();
  formData.append('image', file);
  
  const xhr = new XMLHttpRequest();
  xhr.upload.addEventListener('progress', (e) => {
    const percent = (e.loaded / e.total) * 100;
    console.log(`Upload progress: ${percent}%`);
  });
  
  return new Promise((resolve, reject) => {
    xhr.addEventListener('load', () => resolve(xhr.response));
    xhr.addEventListener('error', reject);
    xhr.open('POST', `${baseUrl}/portraits/`);
    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.send(formData);
  });
}

// ❌ НЕПРАВИЛЬНО: Загрузка без проверок
const formData = new FormData();
formData.append('image', userFile);
fetch(`${baseUrl}/portraits/`, { method: 'POST', body: formData });
```

### 4. Кэширование

```typescript
// ✅ ПРАВИЛЬНО: Умное кэширование данных
class CachedAPIClient {
  private cache = new Map<string, { data: any; timestamp: number }>();
  private readonly CACHE_TTL = 5 * 60 * 1000; // 5 minutes
  
  async getClients(useCache = true): Promise<Client[]> {
    const cacheKey = 'clients_list';
    
    if (useCache && this.cache.has(cacheKey)) {
      const { data, timestamp } = this.cache.get(cacheKey)!;
      if (Date.now() - timestamp < this.CACHE_TTL) {
        return data;
      }
    }
    
    const data = await this.fetchClients();
    this.cache.set(cacheKey, { data, timestamp: Date.now() });
    
    return data;
  }
  
  clearCache() {
    this.cache.clear();
  }
}
```

### 5. Логирование

```typescript
// ✅ ПРАВИЛЬНО: Структурированное логирование
interface LogEntry {
  timestamp: string;
  level: 'info' | 'warn' | 'error';
  message: string;
  context?: Record<string, any>;
}

class Logger {
  private logs: LogEntry[] = [];
  
  log(level: string, message: string, context?: any) {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level: level as any,
      message,
      context
    };
    
    this.logs.push(entry);
    
    if (level === 'error') {
      console.error(JSON.stringify(entry));
    }
  }
}

// Использование
logger.log('info', 'Portrait uploaded', {
  portraitId: '660e8400...',
  size: 1024000,
  duration: 2500
});

logger.log('error', 'Upload failed', {
  portraitId: '660e8400...',
  error: error.message,
  statusCode: 500
});
```

### 6. Обработка состояния приложения

```typescript
// ✅ ПРАВИЛЬНО: Рефреш токена при возобновлении приложения
class AppLifecycleManager {
  async onAppResumed() {
    // Проверить, валиден ли токен
    if (!this.isTokenValid()) {
      // Требуется повторная аутентификация
      await this.redirectToLogin();
    } else {
      // Синхронизировать данные
      await this.syncData();
    }
  }
  
  async onAppPaused() {
    // Сохранить состояние
    await this.saveAppState();
  }
}
```

### 7. Обработка offline режима

```typescript
// ✅ ПРАВИЛЬНО: Поддержка offline функциональности
class OfflineManager {
  private queue: PendingRequest[] = [];
  private isOnline = true;
  
  constructor() {
    this.setupNetworkListener();
  }
  
  private setupNetworkListener() {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.processPendingRequests();
    });
    
    window.addEventListener('offline', () => {
      this.isOnline = false;
    });
  }
  
  async makeRequest(req: Request) {
    if (!this.isOnline) {
      // Добавить в очередь
      this.queue.push(req);
      return { cached: true, message: 'Request queued' };
    }
    
    return fetch(req);
  }
  
  private async processPendingRequests() {
    while (this.queue.length > 0) {
      const req = this.queue.shift()!;
      try {
        await fetch(req);
      } catch (e) {
        this.queue.unshift(req); // вернуть в начало очереди
        break;
      }
    }
  }
}
```

---

## Дополнительные ресурсы

### Полезные ссылки

- 📚 [FastAPI Documentation](https://fastapi.tiangolo.com/)
- 🔐 [JWT Authentication](https://tools.ietf.org/html/rfc7519)
- 🌐 [REST API Best Practices](https://restfulapi.net/)
- 📱 [Mobile Development Best Practices](https://developer.apple.com/design/tips/)

### Получение помощи

- 📧 Email: support@vertex-ar.com
- 💬 API Swagger UI: `{baseUrl}/docs`
- 📖 ReDoc: `{baseUrl}/redoc`

### Версионирование

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.3.0 | 2024-01 | Стабильный релиз с поддержкой мобильных приложений |
| 1.2.0 | 2023-12 | Добавлена система бэкапов |
| 1.1.0 | 2023-11 | Поддержка мультикомпании |

---

**Документ готов к использованию мобильными разработчиками.**  
Последнее обновление: 2024
