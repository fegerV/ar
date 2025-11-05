# Telegram Integration Guide

Vertex AR поддерживает интеграцию с Telegram для отправки уведомлений о важных событиях.

## Настройка Telegram бота

### Шаг 1: Создание бота

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Следуйте инструкциям:
   - Введите имя вашего бота (например, "Vertex AR Notifications")
   - Введите username бота (должен заканчиваться на "bot", например, "vertex_ar_notify_bot")
4. BotFather пришлет вам токен бота в формате: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
5. Сохраните этот токен - он понадобится для настройки

### Шаг 2: Получение Chat ID

#### Для личных уведомлений:

1. Откройте Telegram и найдите [@userinfobot](https://t.me/userinfobot)
2. Отправьте любое сообщение боту
3. Бот ответит с вашим User ID - это и есть ваш Chat ID

#### Для групповых уведомлений:

1. Создайте группу в Telegram
2. Добавьте в группу вашего бота (которого создали через BotFather)
3. Добавьте в группу [@userinfobot](https://t.me/userinfobot)
4. @userinfobot отправит информацию о группе, включая Chat ID (будет начинаться с минуса, например, `-1001234567890`)

### Шаг 3: Настройка Vertex AR

1. Откройте файл `.env` в директории `vertex-ar/`
2. Добавьте следующие переменные:

```bash
# Telegram Notifications
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

3. Сохраните файл и перезапустите приложение:

```bash
# Если используете Docker
docker-compose restart

# Или если запускаете напрямую
cd vertex-ar
./start.sh
```

## Типы уведомлений

Vertex AR отправляет следующие типы уведомлений в Telegram:

### 1. Создание нового заказа

Отправляется при создании нового заказа через API или админ-панель.

```
📸 Новый заказ создан!
Клиент: Иван Иванов
Телефон: +7 (999) 123-45-67
Ссылка: http://example.com/portrait/uuid
```

### 2. Смена активного видео

Отправляется при активации другого видео для портрета.

```
🎬 Видео изменено!
Клиент: Иван Иванов
Портрет: http://example.com/portrait/uuid
Новое активное видео: uuid
```

## Расширенная интеграция

### Создание интерактивного бота

Вы можете создать полноценного Telegram бота для управления Vertex AR:

```python
# telegram_bot.py
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_BASE = os.getenv("BASE_URL", "http://localhost:8000")
API_TOKEN = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот Vertex AR.\n"
        "Доступные команды:\n"
        "/login <username> <password> - Войти в систему\n"
        "/search <phone> - Поиск клиента по телефону\n"
        "/stats - Статистика системы\n"
    )

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global API_TOKEN
    if len(context.args) != 2:
        await update.message.reply_text("Использование: /login <username> <password>")
        return
    
    username, password = context.args
    response = requests.post(f"{API_BASE}/auth/login", json={
        "username": username,
        "password": password
    })
    
    if response.status_code == 200:
        API_TOKEN = response.json()["access_token"]
        await update.message.reply_text("✅ Успешный вход!")
    else:
        await update.message.reply_text("❌ Ошибка входа")

async def search_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not API_TOKEN:
        await update.message.reply_text("❌ Сначала выполните /login")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("Использование: /search <phone>")
        return
    
    phone = context.args[0]
    response = requests.get(
        f"{API_BASE}/clients/search?phone={phone}",
        headers={"Authorization": f"Bearer {API_TOKEN}"}
    )
    
    if response.status_code == 200:
        clients = response.json()
        if not clients:
            await update.message.reply_text("Клиенты не найдены")
            return
        
        for client in clients:
            await update.message.reply_text(
                f"👤 {client['name']}\n"
                f"📱 {client['phone']}\n"
                f"🆔 {client['id']}"
            )
    else:
        await update.message.reply_text("❌ Ошибка поиска")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not API_TOKEN:
        await update.message.reply_text("❌ Сначала выполните /login")
        return
    
    # Получаем статистику
    clients = requests.get(
        f"{API_BASE}/clients/list",
        headers={"Authorization": f"Bearer {API_TOKEN}"}
    ).json()
    
    portraits = requests.get(
        f"{API_BASE}/portraits/list",
        headers={"Authorization": f"Bearer {API_TOKEN}"}
    ).json()
    
    await update.message.reply_text(
        f"📊 Статистика Vertex AR:\n"
        f"👥 Клиентов: {len(clients)}\n"
        f"🖼️ Портретов: {len(portraits)}"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("search", search_client))
    app.add_handler(CommandHandler("stats", stats))
    
    app.run_polling()

if __name__ == "__main__":
    main()
```

### Установка зависимостей для бота

```bash
pip install python-telegram-bot requests
```

### Запуск бота

```bash
python telegram_bot.py
```

## Webhook интеграция

Для более продвинутой интеграции вы можете использовать webhooks:

```python
# В main.py добавьте:

@app.post("/webhook/telegram", tags=["webhooks"])
async def telegram_webhook(update: dict):
    """Handle Telegram webhook updates"""
    # Обработка webhook от Telegram
    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    
    if text.startswith("/search"):
        phone = text.replace("/search", "").strip()
        clients = database.search_clients(phone)
        
        response_text = f"Найдено клиентов: {len(clients)}\n"
        for client in clients:
            response_text += f"\n👤 {client['name']}\n📱 {client['phone']}"
        
        # Отправляем ответ через Telegram API
        await send_telegram_message(chat_id, response_text)
    
    return {"status": "ok"}

async def send_telegram_message(chat_id: str, text: str):
    """Send message to specific chat"""
    import aiohttp
    
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_bot_token:
        return
    
    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            return await response.json()
```

## Настройка webhook в Telegram

```bash
# Установить webhook
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-domain.com/webhook/telegram"}'

# Проверить webhook
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"

# Удалить webhook
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook"
```

## Групповые уведомления

Для отправки уведомлений в группу:

1. Создайте группу в Telegram
2. Добавьте вашего бота в группу
3. Дайте боту права администратора (необязательно, но рекомендуется)
4. Получите Chat ID группы (будет начинаться с минуса)
5. Используйте этот Chat ID в `.env`

## Форматирование сообщений

Telegram поддерживает форматирование сообщений:

```python
# HTML форматирование
message = (
    "<b>Новый заказ создан!</b>\n"
    "<i>Клиент:</i> Иван Иванов\n"
    "<code>ID: 1234-5678</code>\n"
    '<a href="http://example.com">Открыть</a>'
)

# Markdown форматирование
message = (
    "*Новый заказ создан!*\n"
    "_Клиент:_ Иван Иванов\n"
    "`ID: 1234-5678`\n"
    "[Открыть](http://example.com)"
)
```

## Кнопки и меню

Добавление интерактивных кнопок:

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def send_order_notification(chat_id: str, order_data: dict):
    keyboard = [
        [
            InlineKeyboardButton("Открыть портрет", url=order_data["portrait_link"]),
            InlineKeyboardButton("QR код", callback_data=f"qr_{order_data['id']}")
        ],
        [
            InlineKeyboardButton("Список видео", callback_data=f"videos_{order_data['id']}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"📸 Новый заказ создан!\n"
        f"Клиент: {order_data['client_name']}\n"
        f"Телефон: {order_data['client_phone']}"
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=message,
        reply_markup=reply_markup
    )
```

## Отправка изображений и QR кодов

```python
import base64
from io import BytesIO

async def send_qr_code(chat_id: str, qr_base64: str):
    """Send QR code as image"""
    qr_bytes = base64.b64decode(qr_base64)
    
    async with aiohttp.ClientSession() as session:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        
        data = aiohttp.FormData()
        data.add_field('chat_id', str(chat_id))
        data.add_field('photo', qr_bytes, filename='qr_code.png', content_type='image/png')
        data.add_field('caption', 'QR код для портрета')
        
        async with session.post(url, data=data) as response:
            return await response.json()
```

## Мониторинг и логирование

Добавьте логирование для отслеживания отправленных уведомлений:

```python
import logging

logger = logging.getLogger(__name__)

async def send_telegram_notification(message: str):
    """Send Telegram notification with logging"""
    try:
        telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not telegram_bot_token or not telegram_chat_id:
            logger.warning("Telegram credentials not configured")
            return False
        
        url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": telegram_chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Telegram notification sent: {message[:50]}...")
                    return True
                else:
                    logger.error(f"Failed to send Telegram notification: {response.status}")
                    return False
                    
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")
        return False
```

## Тестирование

Проверьте работу Telegram интеграции:

```bash
# Отправка тестового сообщения
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "<YOUR_CHAT_ID>",
    "text": "🧪 Тестовое сообщение от Vertex AR"
  }'
```

## Troubleshooting

### Проблема: Бот не отправляет сообщения

**Решение:**
1. Проверьте правильность `TELEGRAM_BOT_TOKEN`
2. Проверьте правильность `TELEGRAM_CHAT_ID`
3. Убедитесь, что вы начали диалог с ботом (отправили `/start`)
4. Для групп: убедитесь, что бот добавлен в группу

### Проблема: Ошибка 403 Forbidden

**Решение:**
1. Для личных чатов: отправьте `/start` боту
2. Для групп: убедитесь, что бот добавлен в группу

### Проблема: Ошибка 400 Bad Request

**Решение:**
1. Проверьте формат сообщения
2. Убедитесь, что используете правильный `parse_mode` (HTML или Markdown)
3. Проверьте, что Chat ID имеет правильный формат

## Безопасность

1. **Никогда не коммитьте токены в git:**
   ```bash
   # .gitignore
   .env
   *.env
   ```

2. **Используйте переменные окружения:**
   ```bash
   export TELEGRAM_BOT_TOKEN="your_token"
   export TELEGRAM_CHAT_ID="your_chat_id"
   ```

3. **Ограничьте доступ к боту:**
   - Используйте проверку Chat ID перед выполнением команд
   - Добавьте аутентификацию для критичных операций

```python
ALLOWED_CHAT_IDS = [123456789, -1001234567890]

async def check_access(chat_id: int) -> bool:
    return chat_id in ALLOWED_CHAT_IDS
```

## Дополнительные ресурсы

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [python-telegram-bot Documentation](https://python-telegram-bot.readthedocs.io/)
- [BotFather Commands](https://core.telegram.org/bots#botfather)

## Поддержка

Если у вас возникли вопросы или проблемы с интеграцией Telegram:
1. Проверьте логи приложения
2. Используйте [GetUpdates API](https://core.telegram.org/bots/api#getupdates) для отладки
3. Создайте issue в GitHub репозитории
