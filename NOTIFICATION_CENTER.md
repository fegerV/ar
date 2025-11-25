# Центр уведомлений Vertex AR - Расширенные функции

## Обзор

Центр уведомлений Vertex AR теперь включает расширенные функции для управления, агрегации, фильтрации и интеграции уведомлений. Новые возможности обеспечивают лучший контроль над потоком уведомлений и их обработкой.

## Новые функции

### 1. Управление приоритетами

Уведомления теперь поддерживают 5 уровней приоритета:

- **IGNORE** - Игнорировать (не отображать в интерфейсе)
- **LOW** - Низкий приоритет
- **MEDIUM** - Средний приоритет (по умолчанию)
- **HIGH** - Высокий приоритет
- **CRITICAL** - Критический приоритет

### 2. Статусы обработки

Каждое уведомление проходит через статусы:

- **NEW** - Новое уведомление
- **READ** - Прочитано
- **PROCESSED** - Обработано
- **ARCHIVED** - Архивировано

### 3. Расширенная фильтрация и поиск

Поддерживается фильтрация по:

- ID пользователя
- Типу уведомления
- Приоритету
- Статусу
- Источнику события
- Имени сервиса
- Группе уведомлений
- Временному интервалу
- Текстовому поиску по заголовку и сообщению

### 4. Автоматическая агрегация

Одинаковые алерты автоматически группируются на основе:

- Заголовка
- Типа уведомления
- Источника
- Сервиса

### 5. Интеграции

Поддерживаются следующие каналы доставки:

- **Telegram** - Уведомления в Telegram
- **Email** - Email уведомления
- **Webhook** - HTTP вебхуки

### 6. Экспорт данных

Возможность экспорта уведомлений в:

- **CSV** формат
- **JSON** формат

### 7. Автоматическая синхронизация и очистка

- Автоархивация прочитанных уведомлений (через 24 часа)
- Очистка старых уведомлений (через 30 дней)
- Периодическая синхронизация (каждые 5 минут)

## API эндпоинты

### Основные уведомления

```
GET /notifications                    # Получить список уведомлений с фильтрацией
POST /notifications                   # Создать новое уведомление
GET /notifications/{id}              # Получить уведомление по ID
PUT /notifications/{id}               # Обновить уведомление
DELETE /notifications/{id}            # Удалить уведомление
PUT /notifications/{id}/priority     # Обновить приоритет уведомления
PUT /notifications/bulk-status       # Массовое обновление статуса
PUT /notifications/mark-all-read      # Пометить все как прочитанные
DELETE /notifications                 # Удалить все уведомления
```

### Группировка и статистика

```
GET /notifications/groups            # Получить сгруппированные уведомления
GET /notifications/groups/{id}       # Получить уведомления группы
GET /notifications/statistics        # Получить статистику
```

### Экспорт

```
GET /notifications/export/csv        # Экспорт в CSV
GET /notifications/export/json       # Экспорт в JSON
```

### Управление интеграциями

```
GET /notifications-management/integrations/status     # Статус интеграций
POST /notifications-management/webhooks/test          # Тест вебхука
POST /notifications-management/test-routing           # Тест маршрутизации
GET /notifications-management/webhooks/queue          # Очередь вебхуков
```

### Синхронизация и агрегация

```
GET /notifications-management/sync/status             # Статус синхронизации
POST /notifications-management/sync/trigger-cleanup  # Запуск очистки
GET /notifications-management/aggregation/rules       # Правила агрегации
POST /notifications-management/aggregation/rules      # Добавить правило
DELETE /notifications-management/aggregation/rules/{name}  # Удалить правило
```

### Планировщик

```
POST /notifications-management/schedule/notification  # Запланировать уведомление
GET /notifications-management/schedule/tasks          # Получить задачи
DELETE /notifications-management/schedule/tasks      # Очистить задачи
```

## Конфигурация

### Переменные окружения

```bash
# Интервалы синхронизации
NOTIFICATION_SYNC_INTERVAL=300                    # 5 минут
NOTIFICATION_CLEANUP_INTERVAL=3600                # 1 час
NOTIFICATION_RETENTION_DAYS=30                    # 30 дней
NOTIFICATION_AUTO_ARCHIVE_HOURS=24                # 24 часа
NOTIFICATION_DEDUP_WINDOW=300                     # 5 минут

# Вебхуки
WEBHOOK_URLS=https://webhook.example.com/notify
WEBHOOK_TIMEOUT=30
WEBHOOK_MAX_RETRIES=3

# Маршрутизация по приоритетам
CRITICAL_NOTIFICATION_ROUTES=telegram,email,webhook
HIGH_NOTIFICATION_ROUTES=telegram,email
MEDIUM_NOTIFICATION_ROUTES=email
LOW_NOTIFICATION_ROUTES=

# Включение интеграций
NOTIFICATION_TELEGRAM_ENABLED=true
NOTIFICATION_EMAIL_ENABLED=true
NOTIFICATION_WEBHOOK_ENABLED=false
```

## Примеры использования

### Создание уведомления с высоким приоритетом

```bash
curl -X POST "http://localhost:8000/notifications" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "High CPU Usage",
    "message": "CPU usage exceeded 90% threshold",
    "priority": "HIGH",
    "source": "monitoring",
    "service_name": "web_server",
    "event_data": {
      "cpu_usage": 92.5,
      "threshold": 90.0
    }
  }'
```

### Фильтрация уведомлений

```bash
curl "http://localhost:8000/notifications?priority=HIGH&status=NEW&date_from=2024-01-01T00:00:00Z" \
  -H "Authorization: Bearer <token>"
```

### Экспорт уведомлений

```bash
curl "http://localhost:8000/notifications/export/csv?date_from=2024-01-01&date_to=2024-01-31" \
  -H "Authorization: Bearer <token>" \
  -o notifications.csv
```

### Тест вебхука

```bash
curl -X POST "http://localhost:8000/notifications-management/webhooks/test" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://webhook.example.com/notify",
    "payload": {
      "test": true,
      "message": "Test from Vertex AR"
    }
  }'
```

### Добавление правила агрегации

```bash
curl -X POST "http://localhost:8000/notifications-management/aggregation/rules" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "database_errors",
    "pattern": "database error",
    "max_count": 5,
    "time_window": 600
  }'
```

## Архитектура

### Компоненты

1. **notifications.py** - Основная модель и функции работы с уведомлениями
2. **notification_integrations.py** - Управление интеграциями и вебхуками
3. **notification_sync.py** - Синхронизация и агрегация
4. **app/api/notifications.py** - Основные API эндпоинты
5. **app/api/notifications_management.py** - Управление интеграциями

### Поток обработки уведомлений

1. **Создание** - Уведомление создается с указанием приоритета и метаданных
2. **Агрегация** - Проверка правил агрегации
3. **Маршрутизация** - Определение каналов доставки на основе приоритета
4. **Доставка** - Отправка через настроенные интеграции
5. **Синхронизация** - Периодическая очистка и архивация

### Фоновые задачи

- **NotificationScheduler** - Управление запланированными уведомлениями
- **NotificationSyncManager** - Автоматическая синхронизация и очистка
- **WebhookQueue** - Очередь и повторная доставка вебхуков

## Мониторинг

### Статистика

Система собирает статистику по:

- Общему количеству уведомлений
- Распределению по приоритетам
- Распределению по статусам
- Распределению по типам
- Успешности доставки вебхуков

### Логирование

Все операции логируются с уровнем детализации:

- **INFO** - Основные операции
- **WARNING** - Проблемы с доставкой
- **ERROR** - Критические ошибки

## Безопасность

- Все эндпоинты требуют аутентификации администратора
- Вебхуки поддерживают retry механизм с экспоненциальным бэкофом
- Ограничения на количество уведомлений в запросах
- Валидация всех входных данных

## Производительность

- Пагинация для больших списков уведомлений
- Индексация по ключевым полям в базе данных
- Асинхронная обработка вебхуков
- Оптимизированные запросы к базе данных

## Будущие улучшения

1. **WebSocket** для реальных уведомлений
2. **Шаблоны** уведомлений
3. **Правила маршрутизации** на основе контента
4. **Аналитика** и дашборды
5. **Интеграция** с внешними системами мониторинга