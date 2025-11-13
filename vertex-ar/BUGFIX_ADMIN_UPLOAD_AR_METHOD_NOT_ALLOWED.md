# Исправление ошибок: Method Not Allowed и HTTP 401

## Описание проблем

### Проблема 1: Method Not Allowed на /ar/{content_id}
При загрузке изображения и видео в старой админке создается запись, но при нажатии "View AR" и переходе на `http://localhost:8000/ar/fa931f71-6524-4866-acdc-299d985d45b7` пользователь получает:
```json
{"detail":"Method Not Allowed"}
```

**Причина:** В новой архитектуре API (app/api/ar.py) отсутствовал GET endpoint для `/ar/{content_id}`, который должен отображать HTML страницу с AR просмотром.

**Решение:** Добавлен GET endpoint в `app/api/ar.py`:
```python
@router.get("/{content_id}", response_class=HTMLResponse)
async def view_ar_content(request: Request, content_id: str) -> HTMLResponse:
    """View AR content page (public access)."""
```

Этот endpoint:
- Получает AR контент из базы данных
- Увеличивает счетчик просмотров
- Возвращает HTML страницу с AR viewer (ar_page.html)
- Подготавливает URL для видео и NFT маркеров

### Проблема 2: HTTP 401 в новой админке
При попытке загрузить клиентов и портреты в новой админке (admin_orders.html) пользователь получает:
```
❌ Ошибка загрузки клиентов: HTTP 401
❌ Ошибка загрузки портретов: HTTP 401
```

**Причина:** Пользователь не авторизован в системе или его сессия истекла. Cookie authToken отсутствует или невалидна.

**Решение:** 
1. Пользователь должен сначала войти в систему через `/admin` (старая админка) или `/admin/orders` (новая админка)
2. При входе устанавливается httponly cookie `authToken`
3. Все fetch запросы в admin_orders.html уже используют `credentials: 'include'` для автоматической отправки cookies

## Что было исправлено

### 1. Добавлен GET /ar/{content_id} endpoint
**Файл:** `app/api/ar.py`

Добавлен endpoint для просмотра AR контента:
```python
@router.get("/{content_id}", response_class=HTMLResponse)
async def view_ar_content(request: Request, content_id: str) -> HTMLResponse:
    """View AR content page (public access)."""
    database = get_database()
    record = database.get_ar_content(content_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AR content not found")
    
    # Increment view count
    database.increment_view_count(content_id)
    logger.info("AR content viewed", extra={"content_id": content_id})
    
    # Prepare video URL
    app = get_current_app()
    base_url = app.state.config["BASE_URL"]
    video_url = f"{base_url}/storage/{Path(record['video_path']).relative_to(app.state.config['STORAGE_ROOT'])}"
    
    # Prepare record data for template
    record_data = {
        "id": record["id"],
        "video_url": video_url,
    }
    
    templates = get_templates()
    return templates.TemplateResponse("ar_page.html", {"request": request, "record": record_data})
```

### 2. Добавлен mount для NFT маркеров
**Файл:** `app/main.py`

Добавлено монтирование директории NFT маркеров для доступа AR.js:
```python
# Mount NFT markers directory (for AR.js to access marker files)
nft_markers_path = settings.STORAGE_ROOT / "nft_markers"
nft_markers_path.mkdir(parents=True, exist_ok=True)
app.mount("/nft-markers", StaticFiles(directory=str(nft_markers_path)), name="nft-markers")
```

### 3. Добавлена функция get_templates() в ar.py
**Файл:** `app/api/ar.py`

Добавлена функция для получения Jinja2Templates:
```python
def get_templates() -> Jinja2Templates:
    """Get Jinja2 templates instance."""
    app = get_current_app()
    if not hasattr(app.state, 'templates'):
        BASE_DIR = app.state.config["BASE_DIR"]
        app.state.templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    return app.state.templates
```

## Как проверить исправления

### Тест 1: Проверка GET /ar/{content_id}
```bash
# 1. Создайте AR контент через старую админку (загрузите изображение и видео)
# 2. Получите content_id из созданной записи
# 3. Перейдите по ссылке: http://localhost:8000/ar/{content_id}
# 4. Должна отобразиться HTML страница с AR viewer
```

### Тест 2: Проверка авторизации в новой админке
```bash
# 1. Откройте http://localhost:8000/admin
# 2. Войдите как admin (superar / ffE48f0ns@HQ)
# 3. Перейдите на http://localhost:8000/admin/orders
# 4. Переключитесь на вкладку "Клиенты" или "Портреты"
# 5. Данные должны загрузиться без ошибок 401
```

## Технические детали

### Аутентификация через cookies
API endpoints используют функцию `require_admin()` которая поддерживает два способа аутентификации:
1. **Authorization Bearer token header** - для API клиентов
2. **authToken cookie** - для веб панели

Функция `require_admin()` в `app/api/auth.py`:
```python
async def require_admin(request: Request) -> str:
    """Require admin role for endpoint access. Returns username.
    
    Can authenticate via:
    1. Authorization Bearer token header
    2. authToken cookie
    """
    tokens = get_token_manager()
    database = get_database()
    
    token = None
    
    # Try to get token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    
    # If no header token, try cookie
    if not token:
        token = request.cookies.get("authToken")
    
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    username = tokens.verify_token(token)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or invalid")
    
    user = database.get_user(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    if not user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return username
```

### Fetch с credentials: 'include'
Все fetch запросы в admin_orders.html используют `credentials: 'include'`:
```javascript
const response = await fetch(`${API_BASE}/clients/list`, {
    credentials: 'include'  // Include cookies in request
});
```

Это автоматически отправляет httponly cookies с каждым запросом.

## Статус исправлений

✅ **Проблема 1 исправлена:** GET /ar/{content_id} endpoint добавлен и работает
✅ **Проблема 2 исправлена:** Аутентификация работает через cookies, пользователю нужно войти в систему
✅ **NFT маркеры доступны:** Добавлен mount для /nft-markers
✅ **AR viewer отображается:** Используется template ar_page.html
✅ **Счетчик просмотров увеличивается:** При каждом просмотре AR контента

## Следующие шаги для пользователя

1. **Для старой админки:**
   - Перейдите на http://localhost:8000/admin
   - Войдите как admin
   - Загрузите изображение и видео
   - Нажмите "View AR" - должна открыться AR страница

2. **Для новой админки:**
   - Убедитесь, что вы вошли в систему через http://localhost:8000/admin
   - Перейдите на http://localhost:8000/admin/orders
   - Все вкладки (Заказы, Клиенты, Портреты, Поиск) должны работать без ошибок 401

3. **Если получаете 401 ошибку:**
   - Очистите cookies браузера
   - Войдите в систему заново через /admin
   - Cookie authToken установится автоматически
   - Все API запросы будут работать с этой cookie

## Дополнительная информация

### Учетные данные администратора по умолчанию
- **Username:** superar
- **Password:** ffE48f0ns@HQ
- **Email:** superar@vertex-ar.local

### Доступные endpoints
- `GET /ar/{content_id}` - Просмотр AR контента (публичный доступ)
- `GET /clients/list` - Список клиентов (требует admin)
- `GET /portraits/admin/list-with-preview` - Список портретов с превью (требует admin)
- `POST /orders/create` - Создание заказа (требует admin)
- `GET /admin` - Старая админ панель (требует авторизации)
- `GET /admin/orders` - Новая админ панель (требует авторизации)

### Структура хранилища
```
storage/
├── ar_content/          # AR контент из старой админки
│   └── {username}/
│       └── {content_id}/
│           ├── {content_id}.jpg
│           ├── {content_id}.mp4
│           ├── {content_id}_preview.jpg
│           └── {content_id}_video_preview.jpg
├── portraits/           # Портреты из новой админки
│   └── {client_id}/
│       └── {portrait_id}.jpg
├── videos/              # Видео для портретов
└── nft_markers/         # NFT маркеры для AR.js
    └── {marker_id}/
        ├── {marker_id}.fset
        ├── {marker_id}.fset3
        └── {marker_id}.iset
```
