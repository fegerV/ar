# Изменения: Исправление превью портретов и номеров заказов

## Описание проблем

### 1. Превью портретов не отображаются в карточке клиента
В разделе "Клиенты" при открытии детальной информации о клиенте, портреты отображались с градиентом вместо превью изображений.

### 2. Неправильный номер заказа в Content Records
В блоке Content Records последняя запись (которая правильно отображалась сверху) имела номер заказа 000001, хотя должна была иметь номер 000005.

## Решение

### 1. API: Добавлен параметр для загрузки превью портретов

**Файл:** `vertex-ar/app/api/portraits.py`

**Изменения:**
- Добавлен необязательный параметр `include_preview: bool = False` в эндпоинт `GET /portraits`
- Когда `include_preview=true`, API загружает preview изображения из файловой системы
- Формат данных: `data:image/webp;base64,{base64_data}` или `data:image/jpeg;base64,{base64_data}`
- Возвращается новое поле `image_preview_data` в ответе для каждого портрета

**Пример использования:**
```
GET /portraits?client_id=xxx&include_preview=true
```

### 2. Шаблон: Отображение превью портретов в карточке клиента

**Файл:** `vertex-ar/templates/admin_clients.html`

**Изменения:**
- Обновлен fetch запрос для загрузки портретов с параметром `include_preview=true`
- Заменен код отображения портретов: вместо градиента теперь отображается реальное изображение
- Добавлен fallback на placeholder изображение при ошибке загрузки
- Номер заказа теперь отображается как текст под превью

**До:**
```javascript
<div class="portrait-preview" style="background: linear-gradient(...)">
    #${orderNumber}
</div>
```

**После:**
```javascript
<img src="${previewSrc}" class="portrait-preview" alt="Portrait #${orderNumber}">
<div style="margin-top: 0.5rem; font-weight: 600;">#${orderNumber}</div>
```

### 3. Оптимизация: Исправление логики номеров заказов

**Файл:** `vertex-ar/templates/admin_dashboard.html`

**Изменения:**
- Вынесена сортировка записей за пределы цикла (выполняется один раз вместо N раз)
- Создается Map для быстрого поиска позиции заказа по ID
- Теперь используются отсортированные записи для отображения страницы

**До:**
```javascript
pageRecords.forEach((record, index) => {
    const sortedRecords = [...allRecords].sort(...);  // Сортировка в цикле!
    const orderPosition = sortedRecords.findIndex(r => r.id === record.id) + 1;
});
```

**После:**
```javascript
// Сортировка один раз
const sortedRecords = [...allRecords].sort((a, b) => 
    new Date(b.created_at || 0) - new Date(a.created_at || 0)
);

// Создание Map для быстрого поиска
const orderPositionMap = new Map();
sortedRecords.forEach((record, index) => {
    orderPositionMap.set(record.id, index + 1);
});

// Нарезка отсортированных записей для текущей страницы
const pageRecords = sortedRecords.slice(startIndex, endIndex);

pageRecords.forEach((record) => {
    const orderPosition = orderPositionMap.get(record.id) || 1;
    // ...
});
```

### 4. Конфигурация: Экспорт app instance

**Файл:** `vertex-ar/app/main.py`

**Изменения:**
- Добавлен экспорт `app` на уровне модуля для работы с uvicorn
- Теперь можно запускать приложение через `uvicorn app.main:app`

**Добавлено:**
```python
# Create app instance for uvicorn
app = create_app()
```

## Результаты

1. ✅ Превью портретов теперь отображаются в карточке клиента
2. ✅ Номера заказов в Content Records корректны (000005 для последней записи)
3. ✅ Оптимизирована производительность отображения списка заказов
4. ✅ Приложение запускается через uvicorn без ошибок

## Совместимость

- Изменения обратно совместимы
- Параметр `include_preview` необязательный (по умолчанию `false`)
- Старые вызовы API будут работать как прежде
- Оптимизация не меняет визуальное отображение, только улучшает производительность

## Тестирование

Создан тестовый скрипт `test_changes.py` для проверки изменений:

```bash
python test_changes.py
```

Все тесты пройдены успешно:
- ✅ Template Changes
- ✅ API Changes  
- ✅ Main App
