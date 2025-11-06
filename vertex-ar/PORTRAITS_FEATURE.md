# Функционал Портретов с Постоянными Ссылками

## Обзор

Реализована система управления портретами клиентов с поддержкой:
- Постоянных ссылок для каждого портрета
- Множественных видео для одного портрета
- Выбора активного видео
- Поиска клиентов по номеру телефона
- Генерации QR-кодов для постоянных ссылок

## Архитектура

### База Данных

#### Таблица `clients`
```sql
CREATE TABLE clients (
    id TEXT PRIMARY KEY,
    phone TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
CREATE INDEX idx_clients_phone ON clients(phone)
```

#### Таблица `portraits`
```sql
CREATE TABLE portraits (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    image_path TEXT NOT NULL,
    image_preview_path TEXT,
    marker_fset TEXT NOT NULL,
    marker_fset3 TEXT NOT NULL,
    marker_iset TEXT NOT NULL,
    permanent_link TEXT NOT NULL UNIQUE,
    qr_code TEXT,
    view_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
)
```

#### Таблица `videos`
```sql
CREATE TABLE videos (
    id TEXT PRIMARY KEY,
    portrait_id TEXT NOT NULL,
    video_path TEXT NOT NULL,
    video_preview_path TEXT,
    is_active INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(portrait_id) REFERENCES portraits(id) ON DELETE CASCADE
)
```

### API Endpoints

#### Создание заказа
```
POST /orders/create
Content-Type: multipart/form-data
Authorization: Bearer {token}

Parameters:
- phone: string (номер телефона клиента)
- name: string (имя клиента)
- image: file (изображение портрета)
- video: file (видео анимация)

Response: OrderResponse
{
    "client": {...},
    "portrait": {...},
    "video": {...}
}
```

#### Поиск клиентов
```
GET /clients/search?phone={phone}
Authorization: Bearer {token}

Response: ClientResponse[]
```

#### Список клиентов
```
GET /clients/list
Authorization: Bearer {token}

Response: ClientResponse[]
```

#### Получение клиента
```
GET /clients/{client_id}
Authorization: Bearer {token}

Response: ClientResponse
```

#### Обновление клиента
```
PUT /clients/{client_id}
Authorization: Bearer {token}
Content-Type: application/json

Body: ClientUpdate
{
    "phone": "string",
    "name": "string"
}

Response: ClientResponse
```

#### Удаление клиента
```
DELETE /clients/{client_id}
Authorization: Bearer {token}

Response: {"message": "Client deleted successfully"}
```

#### Список портретов
```
GET /portraits/list?client_id={client_id}
Authorization: Bearer {token}

Parameters:
- client_id: optional (фильтр по клиенту)

Response: PortraitResponse[]
```

#### Просмотр портрета (публичный)
```
GET /portrait/{portrait_id}

Response: HTML страница с AR контентом
```

#### Детальная информация о портрете
```
GET /portraits/{portrait_id}/details
Authorization: Bearer {token}

Response: {
    "portrait": PortraitResponse,
    "client": ClientResponse,
    "videos": VideoResponse[]
}
```

#### Удаление портрета
```
DELETE /portraits/{portrait_id}
Authorization: Bearer {token}

Response: {"message": "Portrait deleted successfully"}
```

#### Добавление видео к портрету
```
POST /videos/add
Content-Type: multipart/form-data
Authorization: Bearer {token}

Parameters:
- portrait_id: string
- video: file

Response: VideoResponse
```

#### Список видео портрета
```
GET /videos/list/{portrait_id}
Authorization: Bearer {token}

Response: VideoResponse[]
```

#### Активация видео
```
PUT /videos/{video_id}/activate
Authorization: Bearer {token}

Response: VideoResponse
```

#### Удаление видео
```
DELETE /videos/{video_id}
Authorization: Bearer {token}

Response: {"message": "Video deleted successfully"}
```

## Использование

### 1. Создание нового заказа

Администратор создает заказ через админ-панель:
1. Открывает `/admin/orders`
2. Вводит телефон и имя клиента
3. Загружает изображение портрета
4. Загружает видео анимацию
5. Нажимает "Создать заказ"

Система автоматически:
- Создает или находит клиента по телефону
- Генерирует уникальный ID портрета
- Создает NFT маркеры для AR распознавания
- Генерирует постоянную ссылку: `/portrait/{portrait_id}`
- Создает QR-код для ссылки
- Сохраняет видео как активное

### 2. Поиск клиентов

Администратор может найти клиента по номеру телефона:
1. Переходит на вкладку "Поиск"
2. Вводит номер телефона (минимум 3 символа)
3. Система показывает всех подходящих клиентов с их портретами

### 3. Добавление видео к портрету

Для добавления нового видео к существующему портрету:
1. Находит портрет в списке
2. Нажимает "+ Добавить видео"
3. Выбирает видео файл
4. Видео добавляется, но не активируется автоматически

### 4. Смена активного видео

Для смены видео, которое показывается в AR:
1. Находит портрет в списке
2. Видит список всех видео
3. Нажимает "Активировать" на нужном видео
4. Старое видео деактивируется, новое становится активным
5. Изменения применяются немедленно

### 5. Просмотр портрета клиентом

Клиент получает QR-код и может:
1. Отсканировать QR-код камерой телефона
2. Перейти по постоянной ссылке
3. Навести камеру на физический портрет
4. Увидеть AR анимацию (активное видео)

**Важно:** Ссылка остается постоянной, администратор может менять видео,
но QR-код и ссылка не меняются.

## Ключевые особенности

### Постоянные ссылки
- Каждый портрет имеет уникальную постоянную ссылку
- Ссылка формируется как `/portrait/{portrait_id}`
- QR-код создается один раз при создании портрета
- Ссылка не меняется при смене видео

### Множественные видео
- Один портрет может иметь множество видео
- В любой момент активно только одно видео
- Администратор может добавлять новые видео
- Администратор может переключать активное видео
- Изменение видео не требует замены QR-кода

### Поиск по телефону
- Быстрый поиск клиентов по номеру телефона
- Поиск по частичному совпадению
- Индекс на поле `phone` для быстрого поиска
- Результаты включают все портреты клиента

### Безопасность
- Все административные операции требуют авторизации
- Только администраторы могут управлять портретами
- Публичный доступ только к просмотру портретов
- Счетчик просмотров для аналитики

## Структура файлов

```
storage/
├── clients/
│   └── {client_id}/
│       └── {portrait_id}/
│           ├── {portrait_id}.jpg          # Изображение портрета
│           ├── {portrait_id}_preview.jpg  # Превью изображения
│           ├── {video_id}.mp4             # Видео файлы
│           └── {video_id}_preview.jpg     # Превью видео
└── nft_markers/
    └── {portrait_id}/
        ├── {portrait_id}.fset             # NFT маркер
        ├── {portrait_id}.fset3            # NFT маркер 3D
        └── {portrait_id}.iset             # NFT маркер image set
```

## Telegram уведомления

Система может отправлять уведомления в Telegram:
- При создании нового заказа
- При смене активного видео

Настройка в `.env`:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Пример использования API

### Создание заказа через API
```bash
curl -X POST http://localhost:8000/orders/create \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "phone=+79991234567" \
  -F "name=Иван Иванов" \
  -F "image=@portrait.jpg" \
  -F "video=@animation.mp4"
```

### Поиск клиентов
```bash
curl -X GET "http://localhost:8000/clients/search?phone=999" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Добавление видео
```bash
curl -X POST http://localhost:8000/videos/add \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "portrait_id=uuid-here" \
  -F "video=@new_animation.mp4"
```

### Активация видео
```bash
curl -X PUT http://localhost:8000/videos/{video_id}/activate \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Интеграция с существующей системой

Функционал полностью интегрирован с существующей системой:
- Использует ту же базу данных
- Использует ту же систему аутентификации
- Использует тот же механизм хранения файлов
- Использует те же NFT маркеры для AR

## Будущие улучшения

Возможные направления развития:
1. Статистика просмотров по датам
2. Аналитика популярных видео
3. Автоматическая ротация видео
4. Поддержка групп портретов
5. Экспорт статистики
6. Email уведомления клиентам
7. Предпросмотр видео в админке
8. Массовая загрузка портретов
