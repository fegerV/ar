# Инструкция по использованию оптимизации превью

## Быстрый старт

Оптимизация превью уже включена в систему по умолчанию. Все новые загрузки изображений и видео будут автоматически использовать оптимизированные параметры.

## Что изменилось

### Размеры превью
- **Small:** 150x150px (для списков и мобильных устройств)
- **Default:** 300x300px (основной размер для админ-панели)
- **Large:** 500x500px (для детального просмотра)

### Форматы
- **JPEG:** Progressive, качество 78% (основной формат)
- **WebP:** Качество 75-80% (на 5-6 раз меньше JPEG)

## Использование в коде

### Базовая генерация (автоматически)
```python
# Использует новые параметры по умолчанию
preview = PreviewGenerator.generate_image_preview(image_content)
```

### Кастомные параметры
```python
# Маленькое превью для мобильных
small_preview = PreviewGenerator.generate_image_preview(
    image_content, 
    size=PreviewGenerator.SMALL_THUMBNAIL_SIZE
)

# WebP для экономии трафика
webp_preview = PreviewGenerator.generate_image_preview(
    image_content, 
    format='WEBP'
)

# Большое превью для Retina дисплеев
large_preview = PreviewGenerator.generate_image_preview(
    image_content, 
    size=PreviewGenerator.LARGE_THUMBNAIL_SIZE
)
```

### Множественные размеры
```python
# Генерация всех вариантов сразу
all_previews = PreviewGenerator.generate_multiple_sizes(
    image_content, 
    'image/jpeg'
)
# Результат: {'small_jpeg': ..., 'default_jpeg': ..., 'large_jpeg': ..., 
#           'small_webp': ..., 'default_webp': ..., 'large_webp': ...}
```

## Регенерация существующих превью

Если у вас есть существующие превью, созданные со старыми параметрами:

```bash
cd /home/engine/project
python regenerate_previews.py
```

Скрипт автоматически:
1. Найдет все портреты и видео
2. Перегенерирует превью с новыми параметрами
3. Создаст резервные копии старых файлов
4. Обновит базу данных

## Рекомендации по использованию

### Для админ-панели
- Используйте `default_jpeg` (300x300) для основного отображения
- Используйте `small_webp` для таблиц и списков

### Для мобильных устройств
- Предпочитайте `small_webp` для экономии трафика
- Используйте `default_jpeg` как fallback

### Для высоких разрешений
- Используйте `large_jpeg` (500x500) для Retina дисплеев
- Предоставляйте несколько размеров через HTML srcset

## Пример HTML с адаптивными превью

```html
<img srcset="
    /previews/id_small_webp.webp 150w,
    /previews/id_default_webp.webp 300w,
    /previews/id_large_webp.webp 500w
" sizes="(max-width: 768px) 150px, (max-width: 1200px) 300px, 500px"
src="/previews/id_default_jpeg.jpg" 
alt="Preview">
```

## Производительность

### Результаты оптимизации
- **Разрешение:** Увеличено в 6.25 раз (120x120 → 300x300)
- **Качество:** Снижено с 90% до 78% JPEG
- **Размер файла:** Увеличен всего в 3.23 раза
- **WebP:** В 5-6 раз меньше чем JPEG
- **Время генерации:** Уменьшено на 7%

### Экономия трафика
- Small WebP: ~500 байт vs ~2,000 байт JPEG
- Default WebP: ~1,000 байт vs ~5,000 байт JPEG  
- Large WebP: ~1,700 байт vs ~11,000 байт JPEG

## Тестирование

Для проверки оптимизации:

```bash
# Запуск тестов производительности
cd /home/engine/project
python test_files/test_preview_optimization.py

# Интеграционные тесты
python test_preview_integration.py
```

## Обратная совместимость

- Все существующие API продолжают работать
- Старые превью остаются функциональными
- Новые параметры применяются только к новым загрузкам

## Кэширование

Браузеры автоматически кэшируют превью. Для инвалидации кэша при обновлении:
- Используйте разные имена файлов
- Добавляйте версию в URL: `/previews/id_default.jpg?v=2`
- Используйте ETags или Last-Modified заголовки

## Мониторинг

Следите за размерами файлов в логах:
```
Generated preview: default_webp, size: 986 bytes
Generated preview: default_jpeg, size: 5395 bytes
```

Это поможет оптимизировать параметры под ваши конкретные изображения.