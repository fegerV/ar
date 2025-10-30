# NFT Marker Generator - Руководство

## Описание

NFT Marker Generator - это модуль для генерации Natural Feature Tracking (NFT) маркеров, совместимых с AR.js. NFT маркеры позволяют отслеживать изображения с естественными особенностями вместо QR-кодов.

## Компоненты

### 1. `nft_marker_generator.py`

Основной модуль с классами:
- **NFTMarkerGenerator** - генератор маркеров
- **NFTMarkerConfig** - конфигурация генератора
- **NFTMarker** - данные о сгенерированном маркере

### 2. `nft_maker.py`

CLI инструмент для генерации маркеров из командной строки.

## Использование

### Командная строка

```bash
# Базовая генерация
python3 nft_maker.py -i input_image.jpg -o ./output

# С загрузкой в MinIO
python3 nft_maker.py -i input_image.jpg -o ./output --save-to-minio
```

### Python API

```python
from pathlib import Path
from nft_marker_generator import NFTMarkerGenerator, NFTMarkerConfig

# Создать генератор
generator = NFTMarkerGenerator(Path("/path/to/storage"))

# Анализ изображения
analysis = generator.analyze_image("photo.jpg")
print(f"Качество: {analysis['quality']}")
print(f"Контраст: {analysis['contrast']}")
print(f"Рекомендация: {analysis['recommendation']}")

# Генерация маркера с настройками по умолчанию
marker = generator.generate_marker("photo.jpg", "marker_name")

# Генерация с кастомной конфигурацией
config = NFTMarkerConfig(
    min_dpi=150,
    max_dpi=300,
    levels=3,
    feature_density="high"
)
marker = generator.generate_marker("photo.jpg", "marker_name", config)

# Информация о маркере
print(f"FSET: {marker.fset_path}")
print(f"FSET3: {marker.fset3_path}")
print(f"ISET: {marker.iset_path}")
print(f"Размер: {marker.width}x{marker.height}")
```

### HTTP API

```bash
# Анализ изображения
curl -X POST "http://localhost:8000/nft-marker/analyze" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "image=@photo.jpg"

# Ответ:
{
  "valid": true,
  "width": 800,
  "height": 600,
  "brightness": 128.5,
  "contrast": 82.04,
  "quality": "good",
  "recommendation": "Image should track well in most conditions."
}

# Генерация маркера
curl -X POST "http://localhost:8000/nft-marker/generate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "image=@photo.jpg" \
  -F "marker_name=my_marker" \
  -F 'config={"feature_density":"high","levels":3}'

# Ответ:
{
  "name": "my_marker",
  "width": 800,
  "height": 600,
  "dpi": 72,
  "fset_path": "/path/to/storage/nft_markers/my_marker/my_marker.fset",
  "fset3_path": "/path/to/storage/nft_markers/my_marker/my_marker.fset3",
  "iset_path": "/path/to/storage/nft_markers/my_marker/my_marker.iset"
}

# Список всех маркеров
curl -X GET "http://localhost:8000/nft-marker/list" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Конфигурация

### NFTMarkerConfig параметры

```python
config = NFTMarkerConfig(
    min_dpi=72,              # Минимальное разрешение (по умолчанию: 72)
    max_dpi=300,             # Максимальное разрешение (по умолчанию: 300)
    levels=3,                # Уровни пирамиды изображений (по умолчанию: 3)
    feature_density="medium" # Плотность точек: "low", "medium", "high"
)
```

#### feature_density

- **"low"** - Низкая плотность (шаг 20px), меньше файлы, быстрая обработка
- **"medium"** - Средняя плотность (шаг 10px), баланс между размером и качеством
- **"high"** - Высокая плотность (шаг 5px), лучшее качество трекинга

## Требования к изображениям

### ✅ Хорошо работают

- Логотипы с четкими краями
- Геометрические фигуры
- Текст с высоким контрастом
- Изображения с деталями
- Размер: 480x480 до 4096x4096 пикселей

### ❌ Плохо работают

- Однотонные изображения
- Размытые фотографии
- Очень маленькие изображения (<480px)
- Изображения с низким контрастом (<30)

## Оценка качества

Анализатор возвращает оценку качества:

- **"poor"** (контраст <30) - Изображение не рекомендуется
- **"fair"** (контраст 30-60) - Может работать, но возможны проблемы
- **"good"** (контраст 60-90) - Хорошо работает в большинстве условий
- **"excellent"** (контраст >90) - Отличное качество трекинга

## Генерируемые файлы

Для каждого маркера создаются 3 файла:

1. **`.fset`** - Feature Set (набор признаков)
   - Magic number: `ARJS`
   - Содержит координаты точек особенностей

2. **`.fset3`** - 3D Feature Set (3D набор признаков)
   - Magic number: `AR3D`
   - Содержит иерархию пирамиды признаков

3. **`.iset`** - Image Set (набор изображений)
   - Magic number: `ARIS`
   - Содержит пирамиду масштабированных изображений

## Примеры

### Простая генерация

```python
from pathlib import Path
from nft_marker_generator import NFTMarkerGenerator

generator = NFTMarkerGenerator(Path("./storage"))
marker = generator.generate_marker("logo.png", "company_logo")
print(f"Маркер создан: {marker.fset_path}")
```

### С анализом перед генерацией

```python
from pathlib import Path
from nft_marker_generator import NFTMarkerGenerator

generator = NFTMarkerGenerator(Path("./storage"))

# Сначала анализируем
analysis = generator.analyze_image("photo.jpg")
if analysis["quality"] in ["good", "excellent"]:
    # Если качество хорошее - генерируем
    marker = generator.generate_marker("photo.jpg", "my_marker")
    print("Маркер успешно создан!")
else:
    print(f"Предупреждение: {analysis['recommendation']}")
```

### Настройка для сложного изображения

```python
from pathlib import Path
from nft_marker_generator import NFTMarkerGenerator, NFTMarkerConfig

generator = NFTMarkerGenerator(Path("./storage"))

# Для сложных изображений используем высокую плотность
config = NFTMarkerConfig(
    feature_density="high",
    levels=4  # Больше уровней для лучшего трекинга
)

marker = generator.generate_marker("complex_image.jpg", "complex_marker", config)
```

## Тестирование

```bash
# Unit тесты
python3 -m unittest tests.test_nft_generation

# Интеграционные тесты
python3 test_nft_marker_integration.py
```

## Использование с AR.js

После генерации маркеров, используйте их в AR.js:

```html
<a-scene embedded arjs="sourceType: webcam; debugUIEnabled: false;">
  <!-- NFT Marker -->
  <a-nft
    type="nft"
    url="./markers/my_marker"
    smooth="true"
    smoothCount="10"
    smoothTolerance="0.01"
    smoothThreshold="5"
  >
    <a-entity
      gltf-model="./model.gltf"
      scale="100 100 100"
      position="0 0 0"
    ></a-entity>
  </a-nft>
  
  <a-entity camera></a-entity>
</a-scene>
```

**Важно:** URL должен указывать на базовое имя файлов без расширения (AR.js автоматически добавит .fset, .fset3, .iset).

## Troubleshooting

### Проблема: "Image too small"

**Решение:** Используйте изображение размером минимум 480x480 пикселей.

### Проблема: "Low contrast" / Quality "poor"

**Решение:** 
- Увеличьте контраст изображения
- Добавьте больше деталей
- Используйте изображение с четкими краями

### Проблема: Трекинг не работает в AR.js

**Возможные причины:**
- Изображение имеет низкий контраст (проверьте анализ)
- Недостаточное освещение при использовании
- Изображение слишком мелкое или размытое

**Рекомендации:**
- Используйте `feature_density="high"` для сложных изображений
- Увеличьте `levels` до 4-5 для лучшего трекинга
- Тестируйте в условиях, близких к реальному использованию

## Производительность

- **Время генерации:** ~0.1-0.5 секунды для изображения 800x600
- **Размер файлов:** 
  - FSET: ~500-2000 bytes
  - FSET3: ~50-200 bytes
  - ISET: ~100KB-2MB (зависит от размера и levels)

## Лицензия

Часть проекта Vertex Art AR.
