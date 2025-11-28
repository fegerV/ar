# 📊 Vertex AR Mobile - Полная таблица ссылок

Справочник всех переменных, функций, методов, параметров и типов данных.

---

## 📋 Содержание

1. [Переменные конфигурации](#переменные-конфигурации)
2. [Функции API](#функции-api)
3. [Параметры запросов](#параметры-запросов)
4. [Типы данных](#типы-данных)
5. [Коды ошибок](#коды-ошибок)
6. [Чек-лист интеграции](#чек-лист-интеграции)

---

## Переменные конфигурации

| Переменная | Тип | Значение (Dev) | Значение (Prod) | Описание |
|------------|-----|---|---|---|
| `BASE_URL` | string | `http://localhost:8000` | `https://api.vertex-ar.com` | Базовый URL API |
| `API_VERSION` | string | `1.3.0` | `1.3.0` | Версия API |
| `TIMEOUT` | number | 30000 | 30000 | Таймаут запроса (мс) |
| `RETRY_ATTEMPTS` | number | 3 | 3 | Количество повторных попыток |
| `RETRY_DELAY` | number | 1000 | 1000 | Задержка между попытками (мс) |
| `RATE_LIMIT_ENABLED` | boolean | false | true | Включить rate limiting |
| `CACHE_TTL` | number | 300000 | 300000 | TTL кэша (мс) |
| `MAX_FILE_SIZE` | number | 52428800 | 52428800 | Максимальный размер файла (50MB) |
| `ALLOWED_IMAGE_TYPES` | string[] | `["image/jpeg", "image/png"]` | `["image/jpeg", "image/png", "image/webp"]` | Допустимые типы изображений |
| `ALLOWED_VIDEO_TYPES` | string[] | `["video/mp4"]` | `["video/mp4", "video/webm"]` | Допустимые типы видео |
| `SESSION_TIMEOUT` | number | 1800000 | 1800000 | Таймаут сессии (мс, 30 мин) |
| `AUTH_MAX_ATTEMPTS` | number | 5 | 5 | Макс попыток входа |
| `AUTH_LOCKOUT_MINUTES` | number | 15 | 15 | Время блокировки (мин) |

---

## Функции API

### Аутентификация

| Функция | HTTP метод | Endpoint | Параметры | Возвращает | Код |
|---------|-----------|----------|-----------|-----------|-----|
| `login()` | POST | `/auth/login` | username, password | TokenResponse | 200 |
| `logout()` | POST | `/auth/logout` | - | void | 204 |
| `verifyToken()` | GET | `/auth/verify` | token (header) | { valid: boolean } | 200 |
| `refreshToken()` | POST | `/auth/refresh` | refresh_token | TokenResponse | 200 |

### Управление клиентами

| Функция | HTTP метод | Endpoint | Параметры | Возвращает | Код |
|---------|-----------|----------|-----------|-----------|-----|
| `createClient()` | POST | `/clients/` | ClientCreate | ClientResponse | 201 |
| `getClients()` | GET | `/clients/` | page, page_size, search | ClientsList | 200 |
| `getClient()` | GET | `/clients/{id}` | id | ClientResponse | 200 |
| `updateClient()` | PUT | `/clients/{id}` | id, ClientUpdate | ClientResponse | 200 |
| `deleteClient()` | DELETE | `/clients/{id}` | id | void | 204 |
| `searchClients()` | GET | `/clients/search` | q, limit | Client[] | 200 |
| `getClientStats()` | GET | `/clients/{id}/stats` | id | ClientStats | 200 |

### Управление портретами

| Функция | HTTP метод | Endpoint | Параметры | Возвращает | Код |
|---------|-----------|----------|-----------|-----------|-----|
| `createPortrait()` | POST | `/portraits/` | ClientId, image | PortraitResponse | 201 |
| `getPortraits()` | GET | `/portraits/` | client_id, page | PortraitsList | 200 |
| `getPortrait()` | GET | `/portraits/{id}` | id | PortraitResponse | 200 |
| `updatePortrait()` | PUT | `/portraits/{id}` | id, PortraitUpdate | PortraitResponse | 200 |
| `deletePortrait()` | DELETE | `/portraits/{id}` | id | void | 204 |
| `getPortraitView()` | GET | `/portraits/{id}/view` | id | HTML | 200 |
| `getPortraitAnalytics()` | GET | `/portraits/{id}/analytics` | id | Analytics | 200 |
| `trackPortraitClick()` | POST | `/portraits/{id}/click` | id | { status: string } | 200 |

### Управление видео

| Функция | HTTP метод | Endpoint | Параметры | Возвращает | Код |
|---------|-----------|----------|-----------|-----------|-----|
| `uploadVideo()` | POST | `/videos/` | portrait_id, video | VideoResponse | 201 |
| `getVideos()` | GET | `/videos/` | portrait_id, page | VideosList | 200 |
| `getVideo()` | GET | `/videos/{id}` | id | VideoResponse | 200 |
| `setVideoActive()` | PATCH | `/videos/{id}/set-active` | id | VideoResponse | 200 |
| `deleteVideo()` | DELETE | `/videos/{id}` | id | void | 204 |
| `getVideoPreview()` | GET | `/videos/{id}/preview` | id | image | 200 |

### Пользователи

| Функция | HTTP метод | Endpoint | Параметры | Возвращает | Код |
|---------|-----------|----------|-----------|-----------|-----|
| `getProfile()` | GET | `/users/profile` | - | UserProfile | 200 |
| `updateProfile()` | PUT | `/users/profile` | UserUpdate | UserProfile | 200 |
| `changePassword()` | POST | `/users/change-password` | PasswordChange | void | 204 |
| `getStatistics()` | GET | `/users/statistics` | - | UserStats | 200 |

### Системное

| Функция | HTTP метод | Endpoint | Параметры | Возвращает | Код |
|---------|-----------|----------|-----------|-----------|-----|
| `getHealth()` | GET | `/health` | - | HealthStatus | 200 |
| `getVersion()` | GET | `/health` | - | { version: string } | 200 |

---

## Параметры запросов

### Query параметры

#### Пагинация

| Параметр | Тип | Default | Max | Описание |
|----------|-----|---------|-----|---------|
| `page` | int | 1 | - | Номер страницы |
| `page_size` | int | 50 | 500 | Размер страницы |
| `offset` | int | 0 | - | Смещение от начала |
| `limit` | int | 50 | 500 | Лимит результатов |

#### Фильтрация

| Параметр | Тип | Описание |
|----------|-----|---------|
| `search` | string | Полнотекстовый поиск по имени/телефону |
| `company_id` | string | Фильтр по ID компании |
| `status` | string | Статус (active, inactive) |
| `created_from` | date | Дата начала (ISO 8601) |
| `created_to` | date | Дата окончания (ISO 8601) |
| `sort_by` | string | Поле сортировки (name, created_at, updated_at) |
| `sort_order` | string | Порядок сортировки (asc, desc) |

### Body параметры

#### ClientCreate

```json
{
  "phone": "string (required, 1-20 chars)",
  "name": "string (required, 1-150 chars)",
  "company_id": "string (required)"
}
```

#### ClientUpdate

```json
{
  "phone": "string (optional)",
  "name": "string (optional)"
}
```

#### PortraitCreate

```json
{
  "client_id": "string (required)",
  "image": "file (required, max 50MB)"
}
```

#### VideoCreate

```json
{
  "portrait_id": "string (required)",
  "video": "file (required, max 50MB)"
}
```

#### UserUpdate

```json
{
  "email": "string (optional)",
  "full_name": "string (optional)"
}
```

#### PasswordChange

```json
{
  "current_password": "string (required, min 8)",
  "new_password": "string (required, min 8, max 256)"
}
```

---

## Типы данных

### TokenResponse

```typescript
{
  access_token: string;      // JWT токен
  token_type: string;        // "bearer"
  expires_in?: number;       // Время истечения в сек
}
```

### ClientResponse

```typescript
{
  id: string;                // UUID
  phone: string;             // Телефон
  name: string;              // Имя
  created_at: string;        // ISO 8601
  updated_at?: string;       // ISO 8601
}
```

### ClientListItem

```typescript
{
  id: string;
  phone: string;
  name: string;
  created_at: string;
  portraits_count: number;   // Количество портретов
  latest_portrait_preview?: string;  // Base64 preview
}
```

### PortraitResponse

```typescript
{
  id: string;                // UUID
  client_id: string;         // UUID клиента
  permanent_link: string;    // Постоянная ссылка
  qr_code_base64?: string;   // QR-код в Base64
  image_path: string;        // Путь к изображению
  nft_marker_path?: string;  // Путь к NFT маркеру
  view_count: number;        // Количество просмотров
  click_count: number;       // Количество кликов
  created_at: string;        // ISO 8601
}
```

### VideoResponse

```typescript
{
  id: string;                // UUID
  portrait_id: string;       // UUID портрета
  video_path: string;        // Путь к видео
  is_active: boolean;        // Активно ли видео
  file_size_mb: number;      // Размер в МБ
  duration_seconds?: number; // Длительность
  created_at: string;        // ISO 8601
}
```

### UserProfile

```typescript
{
  username: string;          // Уникальное имя
  email: string;             // Email
  full_name: string;         // Полное имя
  is_active: boolean;        // Активен ли
  is_admin: boolean;         // Админ ли
  created_at: string;        // ISO 8601
  last_login?: string;       // ISO 8601
}
```

### UserStats

```typescript
{
  total_clients: number;     // Всего клиентов
  total_portraits: number;   // Всего портретов
  total_videos: number;      // Всего видео
  total_views: number;       // Всего просмотров
  total_clicks: number;      // Всего кликов
  storage_usage_mb: number;  // Использовано места
  storage_limit_mb: number;  // Лимит места
  last_updated_at: string;   // ISO 8601
}
```

### ErrorResponse

```typescript
{
  detail: string;            // Описание ошибки
  error_code?: string;       // Код ошибки
  timestamp: string;         // ISO 8601
  request_id?: string;       // ID запроса
  validation_errors?: {      // Ошибки валидации
    [field: string]: string[]
  }
}
```

---

## Коды ошибок

### HTTP Status

| Code | Название | Описание |
|------|----------|---------|
| 200 | OK | Успешный запрос |
| 201 | Created | Ресурс создан |
| 204 | No Content | Успешно, нет содержания |
| 400 | Bad Request | Ошибка в запросе |
| 401 | Unauthorized | Требуется аутентификация |
| 403 | Forbidden | Доступ запрещен |
| 404 | Not Found | Не найдено |
| 409 | Conflict | Конфликт данных |
| 423 | Locked | Аккаунт заблокирован |
| 429 | Too Many Requests | Превышен лимит |
| 500 | Server Error | Ошибка сервера |

### Custom Error Codes

| Код | Описание | HTTP Status |
|-----|---------|------------|
| `INVALID_CREDENTIALS` | Неверные логин/пароль | 401 |
| `ACCOUNT_LOCKED` | Аккаунт заблокирован | 423 |
| `TOKEN_EXPIRED` | Токен истек | 401 |
| `INVALID_TOKEN` | Недействительный токен | 401 |
| `RATE_LIMIT_EXCEEDED` | Превышен лимит запросов | 429 |
| `VALIDATION_ERROR` | Ошибка валидации | 400 |
| `RESOURCE_NOT_FOUND` | Ресурс не найден | 404 |
| `DUPLICATE_PHONE` | Телефон уже зарегистрирован | 409 |
| `INVALID_FILE_TYPE` | Недопустимый тип файла | 400 |
| `FILE_TOO_LARGE` | Файл слишком большой | 413 |
| `INSUFFICIENT_STORAGE` | Недостаточно места | 507 |
| `INTERNAL_ERROR` | Внутренняя ошибка | 500 |

---

## Чек-лист интеграции

### Этап 1: Подготовка

- [ ] Прочитать документацию [MOBILE_BACKEND_INTEGRATION.md](MOBILE_BACKEND_INTEGRATION.md)
- [ ] Прочитать API Reference [MOBILE_API_REFERENCE.md](MOBILE_API_REFERENCE.md)
- [ ] Изучить примеры для своей платформы в [MOBILE_SDK_EXAMPLES.md](MOBILE_SDK_EXAMPLES.md)
- [ ] Получить доступные credentials (username/password)
- [ ] Создать development окружение

### Этап 2: Настройка базовой аутентификации

- [ ] Реализовать функцию `login(username, password)`
- [ ] Реализовать безопасное хранилище токена (Keychain/KeyStore)
- [ ] Реализовать функцию `logout()`
- [ ] Добавить перехватчик для добавления Authorization header
- [ ] Протестировать вход/выход

### Этап 3: CRUD операции с клиентами

- [ ] Реализовать `createClient(phone, name)`
- [ ] Реализовать `getClients(page, pageSize)`
- [ ] Реализовать `getClient(id)`
- [ ] Реализовать `updateClient(id, updates)`
- [ ] Реализовать `deleteClient(id)`
- [ ] Протестировать все операции с клиентами

### Этап 4: Работа с портретами

- [ ] Реализовать `uploadPortrait(clientId, imageFile)`
- [ ] Реализовать `getPortraits(clientId, page)`
- [ ] Реализовать `getPortrait(id)`
- [ ] Реализовать `deletePortrait(id)`
- [ ] Добавить прогресс-бар для загрузки файлов
- [ ] Протестировать на больших файлах

### Этап 5: Работа с видео

- [ ] Реализовать `uploadVideo(portraitId, videoFile)`
- [ ] Реализовать `getVideos(portraitId, page)`
- [ ] Реализовать `setVideoActive(videoId)`
- [ ] Реализовать `deleteVideo(id)`
- [ ] Протестировать воспроизведение видео

### Этап 6: Обработка ошибок

- [ ] Реализовать обработку 401 Unauthorized (redirect на login)
- [ ] Реализовать обработку 429 Rate Limit (retry с backoff)
- [ ] Реализовать обработку 423 Account Locked (show message)
- [ ] Реализовать обработку 4xx ошибок валидации
- [ ] Реализовать обработку сетевых ошибок (timeout, connection)
- [ ] Добавить логирование ошибок

### Этап 7: Оптимизация и кэширование

- [ ] Реализовать кэширование списков клиентов
- [ ] Реализовать кэширование портретов
- [ ] Установить TTL для кэша (5 мин)
- [ ] Добавить очистку кэша при выходе
- [ ] Оптимизировать размеры предпросмотров

### Этап 8: Безопасность

- [ ] Включить SSL/TLS проверку (в prod)
- [ ] Не логировать токены
- [ ] Использовать только HTTPS в production
- [ ] Установить правильные CORS headers
- [ ] Добавить обработку истечения токена
- [ ] Реализовать защиту от man-in-the-middle

### Этап 9: Тестирование

- [ ] Написать unit тесты для API клиента
- [ ] Написать интеграционные тесты
- [ ] Протестировать на slow 3G (DevTools)
- [ ] Протестировать на offline режиме
- [ ] Протестировать на больших наборах данных
- [ ] Провести load testing

### Этап 10: Развертывание

- [ ] Переключить на production URL
- [ ] Включить SSL verification
- [ ] Включить rate limiting
- [ ] Настроить monitoring и alerting
- [ ] Создать процедуру обновления
- [ ] Документировать deployment процесс

### Этап 11: Мониторинг

- [ ] Добавить analytics для API вызовов
- [ ] Отслеживать ошибки (Sentry/Crashlytics)
- [ ] Отслеживать performance (время ответа)
- [ ] Отслеживать сетевой трафик
- [ ] Создать dashboard для мониторинга
- [ ] Установить алерты для критических ошибок

### Этап 12: Документирование

- [ ] Написать API documentation
- [ ] Написать guides для других разработчиков
- [ ] Создать примеры использования
- [ ] Документировать обработку ошибок
- [ ] Создать FAQ
- [ ] Обновить CHANGELOG

---

## Быстрый старт (5 минут)

### 1. Инициализация клиента

```typescript
const api = new VertexARClient({
  baseUrl: 'https://api.vertex-ar.com',
  timeout: 30000
});
```

### 2. Вход

```typescript
const token = await api.login('user@example.com', 'password');
// Токен автоматически сохраняется и добавляется в заголовки
```

### 3. Получить клиентов

```typescript
const clients = await api.getClients();
console.log(clients);  // { items: [...], total: 10, ... }
```

### 4. Создать портрет

```typescript
const portrait = await api.uploadPortrait(
  'client-id-123',
  imageFile
);
console.log(portrait.qr_code_base64);  // Можно показать QR-код
```

### 5. Загрузить видео

```typescript
const video = await api.uploadVideo(
  'portrait-id-456',
  videoFile
);
```

---

## Ссылки

| Ресурс | URL |
|--------|-----|
| API Documentation | `/docs` (на сервере) |
| ReDoc | `/redoc` (на сервере) |
| OpenAPI Schema | `/openapi.json` |
| GitHub Examples | https://github.com/vertex-ar/examples |
| Support Email | support@vertex-ar.com |

---

**Версия:** 1.3.0  
**Последнее обновление:** 2024
