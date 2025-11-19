# Итоговая сводка исправлений

## Описание задачи
Исправлено несколько проблем в админ-панели Vertex AR:

1. Убран блок System Information на странице управления бэкапами
2. Исправлена ошибка при создании бэкапа базы данных
3. Исправлена ошибка при создании новой компании
4. Расширенная статистика перенесена в блок System Information и уменьшена

## Внесенные изменения

### 1. Файл: `vertex-ar/app/api/backups.py`

**Проблема**: Ошибка "'str' object has no attribute 'get'" при создании бэкапа

**Причина**: Функция `require_admin()` возвращает строку (username), а код пытался вызвать метод `.get("username")` на этой строке

**Исправление**:
- Строка 96: заменено `admin=_admin.get("username")` на `admin=_admin`
- Строка 209: заменено `admin=_admin.get("username")` на `admin=_admin`
- Строка 258: заменено `admin=_admin.get("username")` на `admin=_admin`

### 2. Файл: `vertex-ar/templates/admin_backups.html`

**Проблема**: Присутствует блок System Information на странице управления бэкапами

**Исправление**:
- Удалена HTML-секция System Information (строки ~477-508)
- Удалены CSS-стили для `.system-info`, `.system-grid`, `.system-item`, `.progress-bar-small`, `.progress-fill-small`
- Удалена функция `loadSystemInfo()` из JavaScript
- Удалены вызовы `loadSystemInfo()` из инициализации и auto-refresh

### 3. Файл: `vertex-ar/templates/admin_dashboard.html`

**Проблема 1**: При создании компании отображается "[object Object]" вместо текста ошибки

**Исправление** (строки ~1840-1844):
```javascript
// Было:
showToast(`Ошибка: ${error.detail || 'Не удалось создать компанию'}`, 'error');

// Стало:
const errorMessage = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail);
showToast(`Ошибка: ${errorMessage || 'Не удалось создать компанию'}`, 'error');
```

**Проблема 2**: Расширенная статистика в отдельной секции и слишком большие блоки

**Исправление**:
- Удалена отдельная секция `.extended-metrics`
- Секция с расширенной статистикой перемещена внутрь блока `.system-info`
- Уменьшены размеры блоков метрик:
  - `grid-template-columns`: `minmax(250px, 1fr)` → `minmax(180px, 1fr)`
  - `padding`: `1.5rem` → `1rem`
  - `.metric-value font-size`: `2rem` → `1.5rem`
  - `.metric-card h3 font-size`: `0.9rem` → `0.75rem`
  - `.metric-subtitle font-size`: `0.85rem` → `0.75rem`
  - `.metric-bar-label min-width`: `100px` → `60px`
  - `.metric-bar-fill height`: `24px` → `20px`
  - `.metric-bar-value font-size`: `0.75rem` → `0.7rem`

## Результаты

✅ Бэкапы базы данных создаются без ошибок
✅ Страница управления бэкапами не содержит блок System Information
✅ Ошибки создания компании отображаются корректно (без [object Object])
✅ Расширенная статистика теперь находится в блоке System Information
✅ Блоки метрик уменьшены и более компактны
✅ Сервер запускается без ошибок

## Проверка

Для проверки исправлений:

1. Запустить сервер:
```bash
cd vertex-ar
source ../.venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

2. Проверить страницу бэкапов: http://localhost:8000/admin/backups
   - Блок "System Information" не должен отображаться
   - Кнопка "Database Backup" должна работать без ошибок

3. Проверить создание компании: http://localhost:8000/admin
   - При ошибке должно показываться читаемое сообщение
   - Не должно быть текста "[object Object]"

4. Проверить расширенную статистику: http://localhost:8000/admin
   - Блок "Расширенная статистика" должен находиться внутри секции "System Information"
   - Метрики должны быть более компактными

## Файлы изменены

- `vertex-ar/app/api/backups.py` - 3 изменения
- `vertex-ar/templates/admin_backups.html` - удален блок System Information
- `vertex-ar/templates/admin_dashboard.html` - исправлена ошибка создания компании, перенесена расширенная статистика
