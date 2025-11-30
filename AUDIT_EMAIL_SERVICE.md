# Аудит: EmailService модуль и SMTP настройки

**Дата аудита:** 2025-01-30  
**Версия системы:** Vertex AR v1.5.1  
**Аудитор:** AI System Analysis

---

## 📊 Краткое резюме

| Категория | Статус | Комментарий |
|-----------|--------|-------------|
| **Общее состояние** | 🟡 **ЧАСТИЧНО РЕАЛИЗОВАНО** | Функционал работает, но требует улучшений |
| **EmailService модуль** | ❌ **ОТСУТСТВУЕТ** | Нет выделенного сервиса, код встроен в alerting.py |
| **SMTP конфигурация** | ✅ **РЕАЛИЗОВАНО** | Двухуровневая система (env + database) |
| **Безопасность паролей** | ✅ **РЕАЛИЗОВАНО** | Шифрование через encryption_manager |
| **Retry логика** | ❌ **ОТСУТСТВУЕТ** | Нет повторных попыток при ошибках |
| **Admin UI** | ✅ **РЕАЛИЗОВАНО** | Страница /admin/notification-settings |
| **Интеграция** | ✅ **ШИРОКАЯ** | Используется в lifecycle, alerting, reports |
| **Email Templates** | ✅ **РЕАЛИЗОВАНО** | БД + API + CRUD операции |

---

## 🔍 Детальный анализ

### 1. EmailService модуль

| Компонент | Статус | Путь | Замечания |
|-----------|--------|------|-----------|
| **Dedicated Service** | ❌ | `app/services/email_service.py` | **НЕ СУЩЕСТВУЕТ** - нет выделенного модуля |
| **Inline Implementation** | ✅ | `app/alerting.py:120-240` | Метод `send_email_alert()` в AlertManager |
| **Используемая библиотека** | 🟡 | `smtplib` (stdlib) | Установлена `aiosmtplib==3.0.0`, но **НЕ используется** |
| **Async Support** | ⚠️ | Thread pool executor | Блокирующий smtplib в `run_in_executor()` |
| **Retry механизм** | ❌ | - | **ОТСУТСТВУЕТ полностью** |
| **Error Handling** | 🟡 | Try/except + logging | Базовая обработка ошибок, без восстановления |
| **Logging** | ✅ | `notification_history` table | Успешные и неудачные отправки логируются |

**Критические находки:**
- ⚠️ `aiosmtplib>=3.0.0` установлена в `requirements.txt:61`, но **не используется**
- ❌ Используется синхронный `smtplib` через `_send_email_sync()` метод
- ❌ Нет retry логики при временных сбоях (network timeout, SMTP 4xx errors)
- ❌ Нет rate limiting для отправки писем
- ❌ Нет batch sending или queue механизма

---

### 2. SMTP конфигурация

#### 2.1 Конфигурация в коде

**Файл:** `vertex-ar/app/config.py` (строки 74-80)

```python
# Email notifications
self.SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
self.SMTP_USERNAME = os.getenv("SMTP_USERNAME")
self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
self.EMAIL_FROM = os.getenv("EMAIL_FROM", self.SMTP_USERNAME)
self.ADMIN_EMAILS = [email.strip() for email in os.getenv("ADMIN_EMAILS", "").split(",") if email.strip()]
```

| Параметр | Источник | Значение по умолчанию | Комментарий |
|----------|----------|-----------------------|-------------|
| SMTP_SERVER | env | `smtp.gmail.com` | Gmail по умолчанию |
| SMTP_PORT | env | `587` | STARTTLS порт |
| SMTP_USERNAME | env | None | Обязательный |
| SMTP_PASSWORD | env | None | Обязательный, **НЕ зашифрован** |
| EMAIL_FROM | env | SMTP_USERNAME | Отправитель |
| ADMIN_EMAILS | env | [] | Список через запятую |

**Проблемы:**
- ❌ Пароль в `.env` файле **не зашифрован** (plain text)
- ⚠️ Нет поддержки SSL (порт 465)
- ⚠️ Жестко заданы протоколы (TLS/SSL определяются только по порту)

#### 2.2 Конфигурация в базе данных

**Файл:** `vertex-ar/app/database.py` (строки 506-534)

**Таблица:** `notification_settings`

```sql
CREATE TABLE IF NOT EXISTS notification_settings (
    id TEXT PRIMARY KEY,
    smtp_host TEXT,
    smtp_port INTEGER,
    smtp_username TEXT,
    smtp_password_encrypted TEXT,          -- ✅ Зашифровано
    smtp_from_email TEXT,
    smtp_use_tls INTEGER DEFAULT 1,        -- ✅ Явный флаг
    smtp_use_ssl INTEGER DEFAULT 0,        -- ✅ Явный флаг
    telegram_bot_token_encrypted TEXT,     -- ✅ Зашифровано
    telegram_chat_ids TEXT,
    event_log_errors INTEGER DEFAULT 1,
    event_db_issues INTEGER DEFAULT 1,
    event_disk_space INTEGER DEFAULT 1,
    event_resource_monitoring INTEGER DEFAULT 1,
    event_backup_success INTEGER DEFAULT 1,
    event_info_notifications INTEGER DEFAULT 1,
    disk_threshold_percent INTEGER DEFAULT 90,
    cpu_threshold_percent INTEGER DEFAULT 80,
    memory_threshold_percent INTEGER DEFAULT 85,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
```

**Особенности:**
- ✅ Все чувствительные данные шифруются (`smtp_password_encrypted`, `telegram_bot_token_encrypted`)
- ✅ Явные флаги для TLS/SSL протоколов
- ✅ Расширенная конфигурация событий и порогов
- ✅ Единственная строка настроек (singleton design через `id TEXT PRIMARY KEY`)
- ✅ Timestamps для аудита

#### 2.3 Fallback система

**Файл:** `vertex-ar/app/alerting.py` (строки 122-147)

```python
# Try to get settings from database first
from app.notification_config import get_notification_config
notification_config = get_notification_config()
smtp_config = notification_config.get_smtp_config()

if smtp_config:
    # Use database settings
    smtp_host = smtp_config['host']
    smtp_port = smtp_config['port']
    # ... (database values)
else:
    # Fallback to environment variables
    smtp_host = settings.SMTP_SERVER
    smtp_port = settings.SMTP_PORT
    # ... (env values)
```

**Приоритет:**
1. **Database settings** (`notification_settings` table)
2. **Environment variables** (`.env` file)

✅ **Хорошо:** Гибкая двухуровневая система  
⚠️ **Риск:** Неясное поведение при частично заполненных настройках

---

### 3. UI на /admin/settings

| Компонент | Статус | Путь | Замечания |
|-----------|--------|------|-----------|
| **Main Settings Page** | ✅ | `templates/admin_settings.html` | Есть, но **без SMTP секции** |
| **Notification Settings Page** | ✅ | `templates/admin_notification_settings.html` | Отдельная страница для SMTP/Telegram |
| **API Endpoints** | ✅ | `app/api/notification_settings.py` | REST API с CRUD операциями |
| **SMTP Fields** | ✅ | - | host, port, username, password, from_email, use_tls, use_ssl |
| **Test Connection Button** | ✅ | `/api/notification-settings/test` | Есть endpoint для тестирования |
| **Password Masking** | ✅ | `_mask_sensitive_data()` | Пароли маскируются в UI (****) |

**Найденные UI компоненты:**

#### 3.1 Страница настроек уведомлений

**URL:** `/admin/notification-settings`  
**Template:** `vertex-ar/templates/admin_notification_settings.html`

**Поля формы:**
- SMTP Host
- SMTP Port
- SMTP Username
- SMTP Password (masked)
- SMTP From Email
- Use TLS (checkbox)
- Use SSL (checkbox)
- Telegram Bot Token (masked)
- Telegram Chat IDs
- Event Settings (6 checkboxes для типов событий)
- Thresholds (CPU, Memory, Disk в %)

#### 3.2 API Endpoints

**Файл:** `vertex-ar/app/api/notification_settings.py`

| Метод | Endpoint | Описание | Auth |
|-------|----------|----------|------|
| GET | `/api/notification-settings` | Получить настройки | Admin |
| PUT | `/api/notification-settings` | Обновить настройки | Admin |
| POST | `/api/notification-settings/test` | Тест подключения | Admin |
| GET | `/api/notification-settings/history` | История отправок | Admin |

**Ключевые методы:**

```python
@router.put("", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    settings_update: NotificationSettingsUpdate,
    _admin: str = Depends(require_admin)
):
    # Encrypts passwords before saving to DB
    if settings_update.smtp_password:
        encrypted = encryption_manager.encrypt(settings_update.smtp_password)
        db.update_notification_settings(smtp_password_encrypted=encrypted)
```

✅ **Безопасность:** Пароли шифруются перед сохранением в БД

---

### 4. Интеграция в коде

#### 4.1 Где используется отправка писем

| Модуль | Файл | Метод | Назначение |
|--------|------|-------|-----------|
| **Lifecycle Notifications** | `app/project_lifecycle.py` | `send_7day_notification()` | Уведомление за 7 дней |
| | | `send_24hour_notification()` | Уведомление за 24 часа |
| | | `send_expired_notification()` | Уведомление после истечения |
| **System Alerts** | `app/alerting.py` | `send_email_alert()` | Критические алерты системы |
| **Weekly Reports** | `app/weekly_reports.py` | `send_weekly_report()` | Еженедельные отчеты |
| **Notification Routing** | `notification_integrations.py` | `_handle_email()` | Маршрутизация уведомлений |

#### 4.2 Примеры использования

**Пример 1: Lifecycle notifications** (`app/project_lifecycle.py:176-250`)

```python
async def send_7day_notification(self, portrait: Dict[str, Any], subscription_end: datetime) -> None:
    # Get client info
    client = database.get_client(portrait['client_id'])
    
    # Prepare bilingual message
    message_ru = f"Ваша подписка истекает через {int(days_remaining)} дней."
    message_en = f"Your subscription expires in {int(days_remaining)} days."
    
    # Send via AlertManager
    await alert_manager.send_email_alert(
        subject=subject_ru,
        message=f"{message_ru}\n\n---\n\n{message_en}"
    )
    
    # Mark as sent
    database.record_lifecycle_notification(portrait['id'], '7days')
```

**Пример 2: System monitoring alerts** (`app/alerting.py:253-277`)

```python
async def send_alert(self, alert_type: str, subject: str, message: str, severity: str = "high"):
    if not self.enabled:
        return False
    
    # Check cooldown
    if not self.should_send_alert(alert_type):
        return False
    
    # Send Telegram + Email
    if settings.SMTP_USERNAME and settings.ADMIN_EMAILS:
        email_success = await self.send_email_alert(subject, formatted_message)
    
    # Store in notifications table
    send_notification(title=f"Alert: {subject}", message=message, ...)
```

#### 4.3 Интеграция с Notification System

**Файл:** `notification_integrations.py:187-196`

```python
async def _handle_email(self, notification_data: Dict[str, Any], priority: str) -> bool:
    """Handle email integration."""
    try:
        from app.alerting import alert_manager
        subject = f"[{priority.upper()}] {notification_data.get('title', 'Notification')}"
        message = self._format_message(notification_data, priority)
        return await alert_manager.send_email_alert(subject, message)
    except Exception as e:
        logger.error(f"Email integration error: {e}")
        return False
```

✅ **Архитектура:** Централизованная отправка через `alert_manager`  
✅ **Priority Routing:** Разные приоритеты → разные каналы (email/telegram/webhook)

---

### 5. Безопасное хранение паролей

#### 5.1 Encryption Manager

**Файл:** `vertex-ar/app/encryption.py`

```python
class EncryptionManager:
    def __init__(self):
        self.key = self._get_or_create_key()
        self.fernet = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data."""
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data."""
        return self.fernet.decrypt(encrypted_data.encode()).decode()
```

**Используемая библиотека:** `cryptography` (Fernet symmetric encryption)

#### 5.2 Workflow

```
[User Input] 
    ↓ (plain password)
[API Endpoint] → encryption_manager.encrypt()
    ↓ (encrypted string)
[Database] → smtp_password_encrypted column
    ↓ (when loading)
[notification_config.py] → encryption_manager.decrypt()
    ↓ (plain password)
[alerting.py] → smtplib.login()
```

#### 5.3 Оценка безопасности

| Аспект | Статус | Комментарий |
|--------|--------|-------------|
| **Database storage** | ✅ | Пароли хранятся зашифрованными |
| **Encryption algorithm** | ✅ | Fernet (AES-128-CBC + HMAC) |
| **Key management** | 🟡 | Ключ генерируется автоматически, но **где хранится?** |
| **Environment variables** | ❌ | `.env` файл содержит **plain text пароли** |
| **UI masking** | ✅ | Пароли маскируются в responses (****) |
| **Logs** | ⚠️ | Нужно проверить, не логируются ли пароли в ошибках |

**Рекомендация:** Проверить `encryption.py` на безопасность хранения ключа шифрования.

---

### 6. Email Templates система

#### 6.1 Database таблица

**Файл:** `vertex-ar/app/database.py` (строки 566-590)

```sql
CREATE TABLE IF NOT EXISTS email_templates (
    id TEXT PRIMARY KEY,
    template_type TEXT NOT NULL CHECK (template_type IN ('subscription_end', 'system_error', 'admin_report')),
    subject TEXT NOT NULL,
    html_content TEXT NOT NULL,
    variables_used TEXT,                    -- JSON список переменных
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
```

**Типы шаблонов:**
- `subscription_end` - для lifecycle уведомлений
- `system_error` - для системных ошибок
- `admin_report` - для еженедельных отчетов

#### 6.2 API для управления шаблонами

**Файл:** `vertex-ar/app/api/email_templates.py`

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/admin/email-templates` | Список всех шаблонов |
| GET | `/api/admin/email-templates/{id}` | Получить один шаблон |
| POST | `/api/admin/email-templates` | Создать шаблон |
| PUT | `/api/admin/email-templates/{id}` | Обновить шаблон |
| DELETE | `/api/admin/email-templates/{id}` | Удалить шаблон |
| POST | `/api/admin/email-templates/{id}/toggle` | Активировать/деактивировать |
| POST | `/api/admin/email-templates/{id}/preview` | Предпросмотр с переменными |

#### 6.3 Template Rendering

```python
def render_template(template_content: str, variables: dict) -> str:
    """Render template by replacing {{variable}} placeholders."""
    result = template_content
    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"
        result = result.replace(placeholder, str(value))
    return result
```

**Формат переменных:** `{{variable_name}}`

✅ **Хорошо:** Простой и надежный подход  
⚠️ **Ограничение:** Нет поддержки условных блоков или циклов (можно добавить Jinja2)

---

## 🎯 Выводы и рекомендации

### Критические проблемы (🔴 HIGH)

1. **❌ Отсутствует EmailService модуль**
   - **Проблема:** Код разбросан по `alerting.py`, нет централизованного управления
   - **Риск:** Сложность поддержки, дублирование кода, невозможность unit-тестирования
   - **Решение:** Создать `app/services/email_service.py` с классом `EmailService`

2. **❌ Нет retry логики**
   - **Проблема:** При временных сбоях письмо теряется
   - **Риск:** Потеря критических уведомлений (lifecycle, alerts)
   - **Решение:** Добавить retry механизм с exponential backoff (3-5 попыток)

3. **❌ Используется smtplib вместо aiosmtplib**
   - **Проблема:** `aiosmtplib==3.0.0` установлена, но не используется
   - **Риск:** Блокирующие I/O операции в async приложении
   - **Решение:** Мигрировать на `aiosmtplib` для нативной async поддержки

4. **❌ Пароли в .env не защищены**
   - **Проблема:** `SMTP_PASSWORD` в plain text в `.env` файле
   - **Риск:** Утечка при коммите в git или логировании
   - **Решение:** Использовать только database-based settings с шифрованием

### Важные улучшения (🟡 MEDIUM)

5. **⚠️ Нет email queue системы**
   - **Проблема:** Письма отправляются синхронно, могут тормозить приложение
   - **Решение:** Добавить background task queue (Celery/Redis или asyncio queue)

6. **⚠️ Нет rate limiting для email**
   - **Проблема:** Риск блокировки SMTP провайдером при массовой рассылке
   - **Решение:** Добавить rate limiter (например, 10 писем/минуту)

7. **⚠️ Нет batch sending**
   - **Проблема:** Каждое письмо = отдельное SMTP соединение
   - **Решение:** Реализовать batch отправку для снижения нагрузки

8. **⚠️ Template engine ограничен**
   - **Проблема:** Только простая замена переменных `{{var}}`
   - **Решение:** Интегрировать Jinja2 для условий и циклов

### Низкоприоритетные (🟢 LOW)

9. **ℹ️ Нет метрик для email отправки**
   - **Решение:** Добавить Prometheus метрики (success/fail rate, latency)

10. **ℹ️ Нет email attachments support**
    - **Решение:** Добавить поддержку вложений для отчетов

---

## 📋 План действий

### Фаза 1: Рефакторинг (Высокий приоритет)

**Цель:** Создать централизованный EmailService с retry логикой

**Задачи:**
1. ✅ Создать `app/services/email_service.py`
2. ✅ Реализовать класс `EmailService` с методами:
   - `send_email(to, subject, body, html=None)` - основной метод
   - `send_template_email(to, template_id, variables)` - через templates
   - `send_bulk_email(recipients, subject, body)` - массовая рассылка
3. ✅ Добавить retry логику:
   - Exponential backoff: 1s, 2s, 4s, 8s, 16s
   - Максимум 5 попыток
   - Логирование каждой попытки
4. ✅ Мигрировать с `smtplib` на `aiosmtplib`
5. ✅ Обновить все вызовы в:
   - `app/alerting.py`
   - `app/project_lifecycle.py`
   - `app/weekly_reports.py`
   - `notification_integrations.py`

**Оценка времени:** 4-6 часов

### Фаза 2: Безопасность (Высокий приоритет)

**Цель:** Убрать plain text пароли из environment

**Задачи:**
1. ✅ Удалить fallback на `settings.SMTP_PASSWORD` из `alerting.py`
2. ✅ Обновить документацию: использовать только UI для настройки SMTP
3. ✅ Добавить предупреждение в `.env.example` о deprecated SMTP_PASSWORD
4. ✅ Проверить логи на отсутствие паролей в error messages

**Оценка времени:** 1-2 часа

### Фаза 3: Queue система (Средний приоритет)

**Цель:** Асинхронная отправка через очередь

**Задачи:**
1. ✅ Создать `app/services/email_queue.py`
2. ✅ Реализовать asyncio-based queue
3. ✅ Background worker для обработки очереди
4. ✅ Persistence в БД для несозданных писем
5. ✅ Интегрировать в `EmailService`

**Оценка времени:** 6-8 часов

### Фаза 4: Мониторинг (Низкий приоритет)

**Цель:** Visibility в отправку писем

**Задачи:**
1. ✅ Добавить Prometheus метрики
2. ✅ Dashboard в Grafana (опционально)
3. ✅ Алерты при high failure rate

**Оценка времени:** 2-3 часа

---

## 📁 Файлы для создания/обновления

### Создать новые файлы:

```
vertex-ar/app/services/
├── __init__.py                    # Новый package
├── email_service.py               # ⭐ Основной EmailService
└── email_queue.py                 # Email queue manager
```

### Обновить существующие файлы:

```
vertex-ar/app/
├── alerting.py                    # Рефакторинг: использовать EmailService
├── project_lifecycle.py           # Рефакторинг: использовать EmailService
├── weekly_reports.py              # Рефакторинг: использовать EmailService
├── config.py                      # Добавить EMAIL_RETRY_* настройки
└── main.py                        # Регистрация EmailService в app.state

vertex-ar/
├── .env.example                   # Добавить комментарии о deprecated SMTP_*
└── requirements.txt               # ✅ Уже есть aiosmtplib>=3.0.0

notification_integrations.py       # Обновить _handle_email()

test_files/
└── unit/
    └── test_email_service.py      # Новые unit тесты
```

---

## 🧪 Требуемая миграция БД

**✅ НЕ ТРЕБУЕТСЯ** - все необходимые таблицы уже существуют:
- `notification_settings` - для SMTP конфигурации
- `notification_history` - для логирования отправок
- `email_templates` - для HTML шаблонов

**Опционально (для queue):**

```sql
CREATE TABLE IF NOT EXISTS email_queue (
    id TEXT PRIMARY KEY,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    html_body TEXT,
    template_id TEXT,
    template_variables TEXT,  -- JSON
    status TEXT NOT NULL CHECK (status IN ('pending', 'sending', 'sent', 'failed')),
    priority INTEGER DEFAULT 5,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 5,
    last_error TEXT,
    scheduled_at TIMESTAMP,
    sent_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_email_queue_status ON email_queue(status);
CREATE INDEX idx_email_queue_scheduled ON email_queue(scheduled_at);
```

---

## 📈 Метрики для мониторинга (рекомендуемые)

```python
# app/services/email_service.py
from prometheus_client import Counter, Histogram, Gauge

email_sent_total = Counter('email_sent_total', 'Total emails sent', ['status'])
email_send_duration = Histogram('email_send_duration_seconds', 'Email send duration')
email_queue_size = Gauge('email_queue_size', 'Current email queue size')
email_retry_count = Counter('email_retry_count', 'Email retry attempts', ['attempt'])
```

---

## 🔒 Проверка безопасности

### Что проверили:

✅ **Database encryption** - используется Fernet (AES-128-CBC)  
✅ **UI masking** - пароли маскируются в API responses  
✅ **HTTPS** - зависит от nginx конфигурации (вне scope)  
⚠️ **Encryption key storage** - требует проверки в `encryption.py`  
❌ **Environment variables** - пароли в plain text в `.env`

### Рекомендации:

1. Проверить, где хранится encryption key (`encryption.py`)
2. Убедиться, что key не коммитится в git
3. Использовать secrets management (Vault, AWS Secrets Manager)
4. Добавить rotation для encryption key

---

## 📚 Дополнительные материалы

### Связанные документы:

- `NOTIFICATIONS_MIGRATION_REPORT.md` - архитектура notification system
- `LIFECYCLE_SCHEDULER_NOTIFICATIONS.md` - lifecycle email notifications
- `.env.example` - примеры конфигурации

### Полезные ссылки:

- [aiosmtplib docs](https://aiosmtplib.readthedocs.io/)
- [Fernet encryption](https://cryptography.io/en/latest/fernet/)
- [FastAPI background tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)

---

## ✅ Критерии приемки

- [x] Полный список всех компонентов Email системы
- [x] Понимание текущей архитектуры
- [x] Ясное описание что есть а что отсутствует
- [x] Рекомендации по доработке
- [x] План действий с оценкой времени
- [x] Список файлов для создания/обновления

---

**Подготовлено:** 2025-01-30  
**Следующий аудит:** После внедрения Фазы 1-2 (рекомендуется через 2 недели)
