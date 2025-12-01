# Анализ: Генерация NFT маркеров, загрузка и хранение файлов в Vertex AR

## Обзор

Этот документ содержит подробный анализ ключевых процессов Vertex AR:
1. Генерация NFT маркеров для AR-отслеживания
2. Загрузка и хранение портретов (фотографий)
3. Загрузка и хранение видео
4. Генерация и хранение превью

---

## 1. Генерация NFT маркеров

### 1.1. Назначение

NFT (Natural Feature Tracking) маркеры позволяют AR.js отслеживать изображения по естественным особенностям вместо QR-кодов. Для каждого портрета генерируется набор файлов маркеров, которые браузер использует для распознавания изображения через камеру.

### 1.2. Расположение модулей

**Основные файлы:**
- `vertex-ar/nft_marker_generator.py` - Главный генератор маркеров (1132 строки)
- `vertex-ar/nft_maker.py` - CLI-обёртка для генерации (159 строк)

**Связанные модули:**
- `vertex-ar/app/api/portraits.py` - Интеграция генерации при загрузке портретов
- `vertex-ar/logging_setup.py` - Логирование процесса

### 1.3. Алгоритм генерации

#### Библиотеки
- **PIL/Pillow** - Обработка изображений
- **struct** - Создание бинарных файлов
- **hashlib** - Кеширование анализа изображений

#### Процесс генерации

```python
# Из nft_marker_generator.py, строки 211-255
class NFTMarkerGenerator:
    def __init__(self, storage_root: Path, enable_cache: bool = True, cache_ttl_days: int = 7):
        """
        Инициализация генератора NFT маркеров.
        
        Args:
            storage_root: Корневая директория для хранения
            enable_cache: Включить кеширование анализа
            cache_ttl_days: Время жизни кеша в днях
        """
        self.storage_root = storage_root
        self.markers_dir = storage_root / "nft_markers"
        self.markers_dir.mkdir(parents=True, exist_ok=True)
        
        # Инициализация кеша
        if enable_cache:
            cache_dir = storage_root / "nft_cache"
            self.cache = NFTAnalysisCache(cache_dir, ttl_days=cache_ttl_days)
```

**Шаги генерации:**

1. **Валидация изображения** (строки 257-294):
   ```python
   def _validate_image(self, image_path: Path, config: NFTMarkerConfig):
       # Проверка существования файла
       # Минимальный размер: 480x480 пикселей
       # Максимальный размер: 8192x8192 пикселей
       # Максимальная площадь: 50,000,000 пикселей
   ```

2. **Анализ особенностей изображения** (строки 296-344):
   ```python
   def _analyze_image_features(self, image_path: Path):
       # Конвертация в градации серого
       # Расчёт яркости и контраста
       # Оценка качества для AR-отслеживания
       # Возвращает рекомендации на русском языке
   ```

3. **Генерация .fset файла** (строки 408-477):
   ```python
   def _generate_fset(self, image_path: Path, output_path: Path, config: NFTMarkerConfig):
       # Feature Set - набор характерных точек
       # Используется упрощённый алгоритм детекции углов (Harris-like)
       # Формат: заголовок + данные о точках
       # Бинарный формат с magic number "ARJS"
   ```
   
   **Алгоритм детекции углов** (строки 445-469):
   ```python
   step = 20 if config.feature_density == "low" else 10 if config.feature_density == "medium" else 5
   
   for y in range(0, height - 8, step):
       for x in range(0, width - 8, step):
           # Простая детекция углов (Harris-like)
           dx = abs(pixels[x+1, y] - pixels[x, y])
           dy = abs(pixels[x, y+1] - pixels[x, y])
           score = dx * dy
           
           if score > 100:  # Порог для детекции углов
               features.append((x, y, score))
   ```

4. **Генерация .fset3 файла** (строки 479-523):
   ```python
   def _generate_fset3(self, image_path: Path, output_path: Path, config: NFTMarkerConfig):
       # 3D Feature Set - данные для 3D отслеживания
       # Пирамида изображений для разных масштабов
       # Расширенный бинарный формат
   ```

5. **Генерация .iset файла** (строки 525-600):
   ```python
   def _generate_iset(self, image_path: Path, output_path: Path, config: NFTMarkerConfig):
       # Image Set - метаданные изображения
       # Размеры, DPI, путь к файлу
       # Используется AR.js для загрузки маркера
   ```

### 1.4. Конфигурация генерации

```python
# Из nft_marker_generator.py, строки 45-65
@dataclass
class NFTMarkerConfig:
    """Конфигурация для генерации NFT маркеров."""
    min_dpi: int = 72                    # Минимальный DPI
    max_dpi: int = 300                   # Максимальный DPI
    levels: int = 3                      # Уровни пирамиды (1-3)
    feature_density: str = "medium"      # low, medium, high
    auto_enhance_contrast: bool = False  # Автоулучшение контраста
    contrast_factor: float = 1.5         # Коэффициент контраста
    max_image_size: int = 8192          # Максимальный размер (ширина/высота)
    max_image_area: int = 50_000_000    # Максимальная площадь
```

**Используемая конфигурация при загрузке портрета** (из `portraits.py`, строки 148-154):
```python
config = NFTMarkerConfig(
    feature_density="high",        # Высокая плотность точек
    levels=3,                      # 3 уровня пирамиды
    max_image_size=8192,          # До 8К изображений
    max_image_area=50_000_000     # ~7000x7000 пикселей
)
```

### 1.5. Связь маркеров с портретами

**В API portraits.py** (строки 166-180):
```python
# Генерация маркера с временным файлом
marker_result = nft_generator.generate_marker(str(temp_image_path), portrait_id, config)

# Сохранение путей в базе данных
db_portrait = database.create_portrait(
    portrait_id=portrait_id,
    client_id=client_id,
    image_path=portrait_image_path,
    marker_fset=marker_result.fset_path,    # Путь к .fset
    marker_fset3=marker_result.fset3_path,  # Путь к .fset3
    marker_iset=marker_result.iset_path,    # Путь к .iset
    permanent_link=permanent_link,
    qr_code=qr_base64,
    image_preview_path=image_preview_path_saved,
    folder_id=folder_id,
)
```

### 1.6. Хранение маркеров

**Структура директорий:**
```
storage/
└── nft_markers/
    └── {portrait_id}/         # UUID портрета
        ├── {portrait_id}.fset  # Feature set
        ├── {portrait_id}.fset3 # 3D feature set
        └── {portrait_id}.iset  # Image set
```

**Пример путей:**
```
storage/nft_markers/a1b2c3d4-e5f6-7890-abcd-ef1234567890/
├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.fset
├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.fset3
└── a1b2c3d4-e5f6-7890-abcd-ef1234567890.iset
```

### 1.7. Кеширование анализа

**NFTAnalysisCache** (строки 81-208):
```python
class NFTAnalysisCache:
    """Кеш для результатов анализа изображений с поддержкой TTL."""
    
    def __init__(self, cache_dir: Path, ttl_days: int = 7):
        # Кеширует результаты анализа на 7 дней
        # Ключ кеша: MD5(путь + время_модификации + размер)
        # Формат: JSON файлы
        
    def get(self, image_path: Path) -> Optional[Dict[str, Any]]:
        # Проверяет TTL и возвращает кешированный результат
        
    def set(self, image_path: Path, analysis: Dict[str, Any]):
        # Сохраняет результат анализа в кеш
```

**Кеш директория:**
```
storage/
└── nft_cache/
    └── {md5_hash}.json  # Результаты анализа
```

### 1.8. Регенерация маркеров

**API endpoint** для регенерации (`portraits.py`, строки 391-529):
```python
@router.post("/{portrait_id}/regenerate-marker")
async def regenerate_portrait_marker(portrait_id: str):
    # 1. Создаёт резервную копию старых маркеров
    # 2. Генерирует новые маркеры
    # 3. Обновляет пути в базе данных
    # 4. Удаляет резервную копию при успехе
    # 5. Восстанавливает из резервной копии при ошибке
```

---

## 2. Загрузка и хранение портретов (фото)

### 2.1. API endpoint загрузки

**Путь:** `POST /api/portraits/`  
**Файл:** `vertex-ar/app/api/portraits.py`, строки 64-196

**Параметры запроса:**
```python
async def create_portrait(
    client_id: str,                      # ID клиента (обязательно)
    image: UploadFile = File(...),       # Файл изображения (обязательно)
    folder_id: Optional[str] = Form(None),  # ID папки (опционально)
    username: str = Depends(get_current_user)  # Аутентификация
) -> PortraitResponse:
```

### 2.2. Процесс загрузки

**Шаги обработки:**

1. **Валидация** (строки 74-92):
   ```python
   # Проверка существования клиента
   client = database.get_client(client_id)
   
   # Проверка существования папки (если указана)
   if folder_id:
       folder = database.get_folder(folder_id)
   
   # Проверка типа файла
   if not image.content_type or not image.content_type.startswith("image/"):
       raise HTTPException(status_code=400, detail="Invalid image file")
   ```

2. **Генерация UUID и путей** (строки 94-108):
   ```python
   portrait_id = str(uuid.uuid4())
   permanent_link = f"portrait_{portrait_id}"
   
   # Получение storage manager
   storage_manager = app.state.storage_manager
   company_id = client.get('company_id')
   
   # Пути хранения
   portrait_image_path = f"portraits/{client_id}/{portrait_id}.jpg"
   portrait_preview_path = f"portraits/{client_id}/{portrait_id}_preview.webp"
   ```

3. **Сохранение изображения** (строки 110-120):
   ```python
   image_content = await image.read()
   
   # Выбор адаптера хранилища (company-specific или default)
   if company_id:
       storage_adapter = storage_manager.get_adapter_for_content(company_id, "portraits")
   else:
       storage_adapter = storage_manager.get_adapter("portraits")
   
   await storage_adapter.save_file(image_content, portrait_image_path)
   ```

4. **Генерация превью** (строки 122-137):
   ```python
   from preview_generator import PreviewGenerator
   
   image_preview = PreviewGenerator.generate_image_preview(
       image_content, 
       size=(300, 300), 
       format='webp'
   )
   
   if image_preview:
       await storage_adapter.save_file(image_preview, portrait_preview_path)
   ```

5. **Генерация QR-кода** (строки 139-144):
   ```python
   portrait_url = f"{base_url}/portrait/{permanent_link}"
   qr_img = qrcode.make(portrait_url)
   qr_buffer = BytesIO()
   qr_img.save(qr_buffer, format="PNG")
   qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode()
   ```

6. **Генерация NFT маркеров** (строки 146-171) - см. раздел 1

7. **Создание записи в БД** (строки 173-185):
   ```python
   db_portrait = database.create_portrait(
       portrait_id=portrait_id,
       client_id=client_id,
       image_path=portrait_image_path,
       marker_fset=marker_result.fset_path,
       marker_fset3=marker_result.fset3_path,
       marker_iset=marker_result.iset_path,
       permanent_link=permanent_link,
       qr_code=qr_base64,
       image_preview_path=image_preview_path_saved,
       folder_id=folder_id,
   )
   ```

### 2.3. Структура хранения портретов

**Директории:**
```
storage/
└── portraits/
    └── {client_id}/
        ├── {portrait_id}.jpg           # Оригинальное изображение
        └── {portrait_id}_preview.webp  # Превью 300x300
```

**Пример:**
```
storage/portraits/client-123/
├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg
└── a1b2c3d4-e5f6-7890-abcd-ef1234567890_preview.webp
```

### 2.4. Storage Manager - адаптер хранилища

**Модуль:** `vertex-ar/storage_manager.py`

**Архитектура:**
```python
StorageManager
├── LocalStorageAdapter     # Локальный диск
├── MinioStorageAdapter     # MinIO/S3
└── YandexDiskStorageAdapter  # Яндекс.Диск
```

**Инициализация** (строки 18-47):
```python
class StorageManager:
    def __init__(self, storage_root: Optional[Path] = None):
        self.storage_root = storage_root or Path("storage")
        self.config = get_storage_config()
        self.adapters: Dict[str, StorageAdapter] = {}
        
        # Инициализация адаптеров для типов контента
        # Note: Modern system uses category-based organization via projects table
        content_categories = ["portraits", "videos", "previews", "nft_markers"]
        
        for category in content_categories:
            storage_type = self.config.get_storage_type(category)
            adapter = self._create_adapter(storage_type, category)
            self.adapters[category] = adapter
```

**Примечание**: В современной версии система использует управление категориями через проекты (`/api/companies/{id}/categories`).

**Типы хранилищ:**

1. **Local Storage** (`storage_local.py`, строки 24-40):
   ```python
   async def save_file(self, file_data: bytes, file_path: str) -> str:
       full_path = self.storage_root / file_path
       full_path.parent.mkdir(parents=True, exist_ok=True)
       
       with open(full_path, 'wb') as f:
           f.write(file_data)
       
       return self.get_public_url(file_path)
   ```

2. **MinIO/S3 Storage** (`storage_minio.py`, строки 43-65):
   ```python
   async def save_file(self, file_data: bytes, file_path: str) -> str:
       from io import BytesIO
       
       self.client.put_object(
           self.bucket,
           file_path,
           BytesIO(file_data),
           length=len(file_data)
       )
       return self.get_public_url(file_path)
   ```

3. **Yandex Disk Storage** (не показан, но аналогичен)

### 2.5. Валидация и ограничения

**Из .env.example:**
```bash
# Максимальный размер изображения в МБ
MAX_IMAGE_SIZE_MB=10

# Разрешённые форматы (через запятую)
ALLOWED_IMAGE_FORMATS=jpg,jpeg,png
```

**Валидация** (`validators.py`, строки 140-148):
```python
def validate_file_size(size_bytes: int, max_size_bytes: int) -> None:
    """Валидация размера файла."""
    if size_bytes <= 0:
        raise ValueError("File size must be greater than 0 bytes")
    
    if size_bytes > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise ValueError(f"File size exceeds maximum allowed size of {max_mb:.1f}MB")
```

**Требования к изображениям:**
- Минимальный размер: **480×480 пикселей** (для качественного AR-отслеживания)
- Максимальный размер: **8192×8192 пикселей**
- Максимальная площадь: **50,000,000 пикселей** (~7000×7000)
- Поддерживаемые форматы: **JPG, JPEG, PNG**
- Максимальный размер файла: **10 МБ** (по умолчанию)

### 2.6. Получение публичных URL

**Для локального хранилища** (`storage_local.py`, строки 101-111):
```python
def get_public_url(self, file_path: str) -> str:
    from app.config import settings
    return f"{settings.BASE_URL}/storage/{file_path}"
```

**Пример URL:**
```
http://localhost:8000/storage/portraits/client-123/a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg
```

**Для MinIO/S3** (`storage_minio.py`, строки 118-134):
```python
def get_public_url(self, file_path: str) -> str:
    if not self.endpoint.startswith('http'):
        protocol = 'https' if self.endpoint.endswith(':443') else 'http'
        base_url = f"{protocol}://{self.endpoint}"
    else:
        base_url = self.endpoint
        
    return f"{base_url}/{self.bucket}/{file_path}"
```

---

## 3. Загрузка и хранение видео

### 3.1. API endpoint загрузки

**Путь:** `POST /api/videos/`  
**Файл:** `vertex-ar/app/api/videos.py`, строки 68-165

**Параметры запроса:**
```python
async def create_video(
    portrait_id: str = Form(...),        # ID портрета (обязательно)
    video: UploadFile = File(...),       # Файл видео (обязательно)
    is_active: bool = Form(False),       # Активно по умолчанию?
    description: str = Form(None),       # Описание (опционально)
    username: str = Depends(get_current_user)  # Аутентификация
) -> VideoResponse:
```

### 3.2. Процесс загрузки

**Шаги обработки:**

1. **Валидация** (строки 79-88):
   ```python
   # Проверка существования портрета
   portrait = database.get_portrait(portrait_id)
   if not portrait:
       raise HTTPException(status_code=404, detail="Portrait not found")
   
   # Проверка типа файла
   if not video.content_type or not video.content_type.startswith("video/"):
       raise HTTPException(status_code=400, detail="Invalid video file")
   ```

2. **Генерация UUID и путей** (строки 90-101):
   ```python
   video_id = str(uuid.uuid4())
   
   portrait = database.get_portrait(portrait_id)
   client_id = portrait["client_id"]
   
   # Пути хранения
   video_path = f"portraits/{client_id}/{portrait_id}/{video_id}.mp4"
   video_preview_path = f"portraits/{client_id}/{portrait_id}/{video_id}_preview.webp"
   ```

3. **Чтение и расчёт размера** (строки 103-111):
   ```python
   video_content = await video.read()
   
   # Расчёт размера в МБ
   file_size_bytes = len(video_content)
   file_size_mb = int(file_size_bytes / (1024 * 1024))
   
   logger.info(f"Video file size: {file_size_bytes} bytes = {file_size_mb} MB")
   ```

4. **Сохранение видео** (строка 114):
   ```python
   await storage_manager.save_file(video_content, video_path, "videos")
   ```

5. **Генерация превью** (строки 116-129):
   ```python
   from preview_generator import PreviewGenerator
   
   video_preview = PreviewGenerator.generate_video_preview(
       video_content, 
       size=(300, 300), 
       format='webp'
   )
   
   if video_preview and len(video_preview) > 0:
       await storage_manager.save_file(video_preview, video_preview_path, "previews")
       video_preview_path_saved = video_preview_path
       logger.info(f"Video preview created: {video_preview_path}, size: {len(video_preview)} bytes")
   ```

6. **Создание записи в БД** (строки 131-141):
   ```python
   db_video = database.create_video(
       video_id=video_id,
       portrait_id=portrait_id,
       video_path=video_path,
       is_active=is_active,
       video_preview_path=video_preview_path_saved,
       description=description,
       file_size_mb=file_size_mb,
   )
   ```

### 3.3. Структура хранения видео

**Директории:**
```
storage/
└── portraits/
    └── {client_id}/
        └── {portrait_id}/
            ├── {video_id}.mp4           # Оригинальное видео
            └── {video_id}_preview.webp  # Превью 300x300
```

**Пример:**
```
storage/portraits/client-123/a1b2c3d4-e5f6-7890-abcd-ef1234567890/
├── v1v2v3v4-e5f6-7890-abcd-ef1234567890.mp4
└── v1v2v3v4-e5f6-7890-abcd-ef1234567890_preview.webp
```

### 3.4. Параметры видео

**Из .env.example:**
```bash
# Максимальный размер видео в МБ
MAX_VIDEO_SIZE_MB=50

# Разрешённые форматы видео (через запятую)
ALLOWED_VIDEO_FORMATS=mp4,webm
```

**Требования к видео:**
- Поддерживаемые форматы: **MP4, WebM**
- Максимальный размер файла: **50 МБ** (по умолчанию)
- Кодеки: Любые, поддерживаемые HTML5 `<video>` (рекомендуется H.264/AAC для MP4)
- Разрешение: Не ограничено, но рекомендуется до Full HD (1920×1080) для оптимальной производительности
- Битрейт: Не ограничен, рекомендуется 2-5 Мбит/с

**Обработка при загрузке:**
- Файл сохраняется "как есть" без перекодирования
- Расчёт размера файла в МБ
- Генерация превью из среднего кадра
- Сохранение метаданных в БД

### 3.5. Управление активным видео

**Установка активного видео** (`videos.py`, строки 242-282):
```python
@router.put("/{video_id}/active")
async def set_active_video(video_id: str):
    # Деактивирует все другие видео для портрета
    # Активирует указанное видео
    database.set_active_video(video_id, portrait_id)
```

**Только одно видео активно для каждого портрета** - при активации нового видео, предыдущее автоматически деактивируется.

### 3.6. Планировщик видео (Video Scheduler)

**Расширенные возможности:**
- **Автоматическая активация/деактивация** по расписанию
- **Ротация видео:** последовательная (sequential) или циклическая (cyclic)
- **Статусы:** active, inactive, archived
- **История изменений** с аудитом
- **Уведомления** о смене видео

**Из .env.example:**
```bash
# Включить планировщик видео
VIDEO_SCHEDULER_ENABLED=true

# Интервал проверки (секунды)
VIDEO_SCHEDULER_CHECK_INTERVAL=300

# Интервал ротации (секунды)
VIDEO_SCHEDULER_ROTATION_INTERVAL=3600

# Авто-архивирование после (часы)
VIDEO_SCHEDULER_ARCHIVE_AFTER_HOURS=168

# Уведомления
VIDEO_SCHEDULER_NOTIFICATIONS_ENABLED=true
```

---

## 4. Генерация и хранение превью

### 4.1. Модуль генерации

**Файл:** `vertex-ar/preview_generator.py` (326 строк)

**Класс:** `PreviewGenerator` - статические методы для генерации превью

### 4.2. Генерация превью изображений

**Метод** (строки 21-67):
```python
@staticmethod
def generate_image_preview(image_content: bytes, size=(300, 300), format='webp') -> Optional[bytes]:
    """Генерирует превью для изображений с улучшенным качеством и поддержкой WebP"""
```

**Процесс:**

1. **Открытие изображения** (строки 25-27):
   ```python
   image = Image.open(BytesIO(image_content))
   logger.info(f"Изображение открыто: {image.size}, формат: {image.format}")
   ```

2. **Конвертация в RGB** (строки 29-36):
   ```python
   if image.mode in ('RGBA', 'LA', 'P'):
       # Создание белого фона для полупрозрачных изображений
       background = Image.new('RGB', image.size, (255, 255, 255))
       if image.mode == 'P':
           image = image.convert('RGBA')
       background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
       image = background
   ```

3. **Создание thumbnail с сохранением пропорций** (строки 38-49):
   ```python
   # LANCZOS resampling - высокое качество
   image.thumbnail(size, Image.Resampling.LANCZOS)
   
   # Создание изображения с белым фоном
   preview = Image.new('RGB', size, (255, 255, 255))
   
   # Центрирование изображения
   x = (size[0] - image.size[0]) // 2
   y = (size[1] - image.size[1]) // 2
   preview.paste(image, (x, y))
   ```

4. **Сохранение с оптимальными настройками** (строки 51-63):
   ```python
   buffer = BytesIO()
   
   if format.lower() == 'webp':
       # WebP с лучшим сжатием
       preview.save(buffer, format='WEBP', quality=85, method=6)
   else:
       # JPEG с высоким качеством
       preview.save(buffer, format='JPEG', quality=92, optimize=True)
   
   buffer.seek(0)
   return buffer.getvalue()
   ```

**Параметры качества:**
- **WebP:** quality=85, method=6 (лучшее сжатие)
- **JPEG:** quality=92, optimize=True

### 4.3. Генерация превью видео

**Метод** (строки 70-197):
```python
@staticmethod
def generate_video_preview(video_content: bytes, size=(300, 300), frame_time=None, format='webp') -> Optional[bytes]:
    """Генерирует превью для видео с улучшенным качеством и поддержкой WebP"""
```

**Процесс:**

1. **Сохранение во временный файл** (строки 82-84):
   ```python
   with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
       temp_video.write(video_content)
       temp_video_path = temp_video.name
   ```

2. **Открытие видео с OpenCV** (строки 87-102):
   ```python
   cap = cv2.VideoCapture(temp_video_path)
   
   if not cap.isOpened():
       logger.error("Не удалось открыть видео")
       return PreviewGenerator.generate_video_preview_stub(size, format)
   
   # Получение метаданных
   total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
   fps = cap.get(cv2.CAP_PROP_FPS)
   
   logger.info(f"Видео: кадров={total_frames}, FPS={fps}")
   ```

3. **Извлечение кадра из середины** (строки 104-122):
   ```python
   # Середина видео
   middle_frame = total_frames // 2
   cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)
   
   ret, frame = cap.read()
   
   if not ret or frame is None:
       # Fallback к первому кадру
       cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
       ret, frame = cap.read()
       if not ret:
           return PreviewGenerator.generate_video_preview_stub(size, format)
   ```

4. **Обработка кадра** (строки 124-144):
   ```python
   # Размытие для уменьшения артефактов
   frame = cv2.GaussianBlur(frame, (3, 3), 0)
   
   # Конвертация BGR → RGB
   frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
   
   # PIL Image
   pil_image = Image.fromarray(frame_rgb)
   pil_image.thumbnail(size, Image.Resampling.LANCZOS)
   
   # Чёрный фон для видео
   preview = Image.new('RGB', size, (0, 0, 0))
   
   # Центрирование
   x = (size[0] - pil_image.size[0]) // 2
   y = (size[1] - pil_image.size[1]) // 2
   preview.paste(pil_image, (x, y))
   ```

5. **Добавление иконки воспроизведения** (строки 146-161):
   ```python
   from PIL import ImageDraw
   draw = ImageDraw.Draw(preview)
   
   # Треугольник воспроизведения в центре
   center_x, center_y = size[0] // 2, size[1] // 2
   triangle_size = min(size) // 8
   
   triangle_points = [
       (center_x - triangle_size//2, center_y - triangle_size//2),  # Левая
       (center_x - triangle_size//2, center_y + triangle_size//2),  # Нижняя
       (center_x + triangle_size//2, center_y)                      # Правая
   ]
   draw.polygon(triangle_points, fill=(255, 255, 255))  # Белый треугольник
   ```

6. **Сохранение** (строки 163-182):
   ```python
   buffer = BytesIO()
   
   if format.lower() == 'webp':
       preview.save(buffer, format='WEBP', quality=85, method=6)
   else:
       preview.save(buffer, format='JPEG', quality=92, optimize=True)
   
   buffer.seek(0)
   preview_bytes = buffer.getvalue()
   
   # Валидация
   if len(preview_bytes) == 0:
       return PreviewGenerator.generate_video_preview_stub(size, format)
   
   return preview_bytes
   ```

7. **Очистка ресурсов** (строки 184-192):
   ```python
   finally:
       if 'cap' in locals():
           cap.release()
       try:
           os.unlink(temp_video_path)
       except:
           pass
   ```

### 4.4. Заглушка для превью видео

**Метод** (строки 199-239):
```python
@staticmethod
def generate_video_preview_stub(size=(300, 300), format='webp') -> Optional[bytes]:
    """Создаёт заглушку при ошибке генерации превью"""
```

**Генерирует:**
- Тёмный фон (30, 30, 30)
- Белый треугольник воспроизведения
- Размер 300×300
- Формат WebP или JPEG

### 4.5. Хранение превью

**Структура директорий:**

**Для портретов:**
```
storage/
└── portraits/
    └── {client_id}/
        └── {portrait_id}_preview.webp
```

**Для видео:**
```
storage/
└── portraits/
    └── {client_id}/
        └── {portrait_id}/
            └── {video_id}_preview.webp
```

**Альтернативная структура** (если используется отдельная директория previews):
```
storage/
└── previews/
    ├── {portrait_id}_thumbnail.webp
    └── {video_id}_thumbnail.webp
```

### 4.6. Размеры и форматы

**Стандартные параметры:**
- **Размер:** 300×300 пикселей
- **Формат по умолчанию:** WebP
- **Альтернативный формат:** JPEG
- **Пропорции:** Сохраняются (изображение центрируется)

**Качество:**
- **WebP:** quality=85, method=6
- **JPEG:** quality=92, optimize=True

**Размер файлов:**
- WebP изображения: ~5-15 КБ
- WebP видео: ~10-30 КБ
- JPEG: ~20-50 КБ (больше чем WebP)

### 4.7. Использование в API

**Получение превью в списке портретов** (`portraits.py`, строки 256-354):
```python
@router.get("/admin/list-with-preview")
async def list_portraits_with_preview(company_id: Optional[str] = None):
    """Получить портреты с превью для админ-панели."""
    
    for portrait in portraits:
        # Загрузка превью
        image_preview_path = portrait.get("image_preview_path")
        if image_preview_path:
            preview_path = Path(image_preview_path)
            if preview_path.exists():
                with open(preview_path, "rb") as f:
                    preview_data = base64.b64encode(f.read()).decode()
                    
        # Формат data URL
        if preview_data and image_preview_path.endswith('.webp'):
            image_preview_data = f"data:image/webp;base64,{preview_data}"
        else:
            image_preview_data = f"data:image/jpeg;base64,{preview_data}"
```

**Получение превью видео** (`videos.py`, строки 285-368):
```python
@router.get("/{video_id}/preview")
async def get_video_preview(video_id: str):
    """Получить превью видео как base64."""
    
    video_preview_path = video.get("video_preview_path")
    preview_path = Path(video_preview_path)
    
    if preview_path.exists():
        with open(preview_path, "rb") as f:
            preview_bytes = f.read()
            preview_data = base64.b64encode(preview_bytes).decode('utf-8')
            
        if video_preview_path.endswith('.webp'):
            return {"preview_data": f"data:image/webp;base64,{preview_data}"}
        else:
            return {"preview_data": f"data:image/jpeg;base64,{preview_data}"}
```

---

## 5. Схема потоков данных

### 5.1. Поток загрузки портрета

```
Клиент (Браузер)
    │
    ▼
POST /api/portraits/
    │
    ├─► Валидация (client_id, folder_id, image type)
    │
    ├─► Генерация UUID (portrait_id)
    │
    ├─► Storage Manager
    │   │
    │   ├─► LocalStorageAdapter
    │   │   └─► storage/portraits/{client_id}/{portrait_id}.jpg
    │   │
    │   ├─► MinioStorageAdapter
    │   │   └─► s3://bucket/portraits/{client_id}/{portrait_id}.jpg
    │   │
    │   └─► YandexDiskStorageAdapter
    │       └─► /vertex-ar/portraits/{client_id}/{portrait_id}.jpg
    │
    ├─► PreviewGenerator.generate_image_preview()
    │   └─► storage/portraits/{client_id}/{portrait_id}_preview.webp
    │
    ├─► QRCode.make()
    │   └─► Base64 PNG
    │
    ├─► NFTMarkerGenerator.generate_marker()
    │   ├─► Validate image (480x480 min, 8192x8192 max)
    │   ├─► Analyze features (contrast, quality)
    │   ├─► Generate .fset (feature points)
    │   ├─► Generate .fset3 (3D features)
    │   └─► Generate .iset (metadata)
    │       └─► storage/nft_markers/{portrait_id}/
    │
    ├─► Database.create_portrait()
    │   └─► SQLite: portraits table
    │       ├─► portrait_id
    │       ├─► client_id
    │       ├─► folder_id
    │       ├─► image_path
    │       ├─► image_preview_path
    │       ├─► marker_fset
    │       ├─► marker_fset3
    │       ├─► marker_iset
    │       ├─► permanent_link
    │       └─► qr_code
    │
    └─► Response: PortraitResponse
```

### 5.2. Поток загрузки видео

```
Клиент (Браузер)
    │
    ▼
POST /api/videos/
    │
    ├─► Валидация (portrait_id, video type)
    │
    ├─► Генерация UUID (video_id)
    │
    ├─► Расчёт размера файла (MB)
    │
    ├─► Storage Manager
    │   └─► storage/portraits/{client_id}/{portrait_id}/{video_id}.mp4
    │
    ├─► PreviewGenerator.generate_video_preview()
    │   │
    │   ├─► Сохранение во временный файл
    │   ├─► OpenCV: открытие видео
    │   ├─► Извлечение среднего кадра
    │   ├─► Обработка кадра (blur, resize)
    │   ├─► Добавление иконки play
    │   └─► Сохранение WebP
    │       └─► storage/portraits/{client_id}/{portrait_id}/{video_id}_preview.webp
    │
    ├─► Database.create_video()
    │   └─► SQLite: videos table
    │       ├─► video_id
    │       ├─► portrait_id
    │       ├─► video_path
    │       ├─► video_preview_path
    │       ├─► is_active
    │       ├─► file_size_mb
    │       ├─► description
    │       ├─► start_datetime
    │       ├─► end_datetime
    │       ├─► rotation_type
    │       └─► status
    │
    └─► Response: VideoResponse
```

### 5.3. Поток просмотра AR

```
Пользователь сканирует QR-код
    │
    ▼
GET /portrait/{permanent_link}
    │
    ├─► Database.get_portrait_by_link()
    │
    ├─► Database.get_active_video()
    │
    ├─► Database.increment_view_count()
    │
    └─► Render: AR viewer page
        │
        ├─► Load AR.js library
        │
        ├─► Load NFT markers
        │   ├─► GET /storage/nft_markers/{portrait_id}/{portrait_id}.fset
        │   ├─► GET /storage/nft_markers/{portrait_id}/{portrait_id}.fset3
        │   └─► GET /storage/nft_markers/{portrait_id}/{portrait_id}.iset
        │
        ├─► Initialize camera
        │
        ├─► Start NFT tracking
        │   └─► AR.js: match portrait with camera feed
        │
        └─► On match: play video
            └─► GET /storage/portraits/{client_id}/{portrait_id}/{video_id}.mp4
```

### 5.4. Диаграмма компонентов

```
┌─────────────────────────────────────────────────────────────────┐
│                          FastAPI Application                      │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                      API Routers                          │  │
│  │                                                            │  │
│  │  ┌──────────┐  ┌───────────┐  ┌─────────┐  ┌──────────┐ │  │
│  │  │ Portraits│  │  Videos   │  │  AR     │  │  Admin   │ │  │
│  │  │   API    │  │   API     │  │  API    │  │   API    │ │  │
│  │  └────┬─────┘  └─────┬─────┘  └────┬────┘  └────┬─────┘ │  │
│  │       │              │             │           │         │  │
│  └───────┼──────────────┼─────────────┼───────────┼─────────┘  │
│          │              │             │           │            │
│          ▼              ▼             ▼           ▼            │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    Storage Manager                         │ │
│  │                                                             │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐    │ │
│  │  │  Local   │  │  MinIO   │  │  Yandex Disk        │    │ │
│  │  │ Adapter  │  │ Adapter  │  │  Adapter            │    │ │
│  │  └────┬─────┘  └────┬─────┘  └───────┬─────────────┘    │ │
│  │       │             │                 │                   │ │
│  └───────┼─────────────┼─────────────────┼───────────────────┘ │
│          │             │                 │                     │
└──────────┼─────────────┼─────────────────┼─────────────────────┘
           │             │                 │
           ▼             ▼                 ▼
    ┌──────────┐  ┌──────────┐  ┌──────────────┐
    │  Local   │  │   MinIO  │  │ Yandex Disk  │
    │  Disk    │  │   S3     │  │   Cloud      │
    └──────────┘  └──────────┘  └──────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     NFT Marker Generator                         │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │   Validate   │  │   Analyze    │  │   Generate         │   │
│  │   Image      │─►│   Features   │─►│   Markers          │   │
│  │              │  │              │  │  (.fset/.fset3/.iset)│  │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│                    ┌──────────────┐                             │
│                    │  Analysis    │                             │
│                    │  Cache       │                             │
│                    │  (7 days TTL)│                             │
│                    └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     Preview Generator                            │
│                                                                   │
│  ┌────────────────────┐         ┌─────────────────────┐         │
│  │  Image Preview     │         │  Video Preview      │         │
│  │                    │         │                     │         │
│  │  • PIL/Pillow      │         │  • OpenCV           │         │
│  │  • LANCZOS resize  │         │  • Middle frame     │         │
│  │  • 300x300         │         │  • Play icon        │         │
│  │  • WebP quality=85 │         │  • 300x300          │         │
│  │                    │         │  • WebP quality=85  │         │
│  └────────────────────┘         └─────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                          Database (SQLite)                       │
│                                                                   │
│  ┌────────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────┐│
│  │ Companies  │  │  Clients  │  │ Portraits│  │   Videos     ││
│  └────────────┘  └───────────┘  └──────────┘  └──────────────┘│
│  ┌────────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────┐│
│  │  Projects  │  │  Folders  │  │  Users   │  │   Orders     ││
│  └────────────┘  └───────────┘  └──────────┘  └──────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Примеры кода

### 6.1. Загрузка портрета через API

**Python:**
```python
import requests

url = "http://localhost:8000/api/portraits/"
headers = {"Authorization": f"Bearer {token}"}

files = {
    'image': ('portrait.jpg', open('portrait.jpg', 'rb'), 'image/jpeg')
}
data = {
    'client_id': 'client-123',
    'folder_id': 'folder-456'  # опционально
}

response = requests.post(url, headers=headers, files=files, data=data)
portrait = response.json()

print(f"Portrait ID: {portrait['id']}")
print(f"Image URL: {portrait['image_url']}")
print(f"QR Code: {portrait['qr_code_base64']}")
print(f"Permanent Link: {portrait['permanent_link']}")
```

**JavaScript (fetch):**
```javascript
const formData = new FormData();
formData.append('image', fileInput.files[0]);
formData.append('client_id', 'client-123');
formData.append('folder_id', 'folder-456'); // optional

const response = await fetch('http://localhost:8000/api/portraits/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});

const portrait = await response.json();
console.log('Portrait ID:', portrait.id);
console.log('Image URL:', portrait.image_url);
```

### 6.2. Загрузка видео через API

**Python:**
```python
import requests

url = "http://localhost:8000/api/videos/"
headers = {"Authorization": f"Bearer {token}"}

files = {
    'video': ('video.mp4', open('video.mp4', 'rb'), 'video/mp4')
}
data = {
    'portrait_id': 'portrait-uuid',
    'is_active': 'true',
    'description': 'Праздничное видео'
}

response = requests.post(url, headers=headers, files=files, data=data)
video = response.json()

print(f"Video ID: {video['id']}")
print(f"Video URL: {video['video_url']}")
print(f"File size: {video['file_size_mb']} MB")
print(f"Is active: {video['is_active']}")
```

### 6.3. Использование Storage Manager

**Python:**
```python
from pathlib import Path
from storage_manager import get_storage_manager

# Получение глобального экземпляра
storage_manager = get_storage_manager(Path("storage"))

# Сохранение файла
file_data = b"binary content"
file_path = "portraits/client-123/test.jpg"
url = await storage_manager.save_file(file_data, file_path, "portraits")
print(f"Saved to: {url}")

# Получение файла
file_data = await storage_manager.get_file(file_path, "portraits")

# Проверка существования
exists = await storage_manager.file_exists(file_path, "portraits")

# Удаление файла
deleted = await storage_manager.delete_file(file_path, "portraits")

# Получение публичного URL
public_url = storage_manager.get_public_url(file_path, "portraits")
```

### 6.4. Генерация NFT маркеров

**Python:**
```python
from pathlib import Path
from nft_marker_generator import NFTMarkerGenerator, NFTMarkerConfig

# Инициализация генератора
storage_root = Path("storage")
generator = NFTMarkerGenerator(storage_root, enable_cache=True, cache_ttl_days=7)

# Конфигурация
config = NFTMarkerConfig(
    feature_density="high",
    levels=3,
    max_image_size=8192,
    max_image_area=50_000_000
)

# Генерация маркера
image_path = Path("portrait.jpg")
marker_name = "portrait-uuid"

marker = generator.generate_marker(image_path, marker_name, config)

print(f"FSET: {marker.fset_path}")
print(f"FSET3: {marker.fset3_path}")
print(f"ISET: {marker.iset_path}")
print(f"Quality score: {marker.quality_score}")
print(f"Generation time: {marker.generation_time}s")
```

### 6.5. Генерация превью

**Python:**
```python
from preview_generator import PreviewGenerator

# Превью изображения
with open('portrait.jpg', 'rb') as f:
    image_data = f.read()

image_preview = PreviewGenerator.generate_image_preview(
    image_data,
    size=(300, 300),
    format='webp'
)

with open('portrait_preview.webp', 'wb') as f:
    f.write(image_preview)

# Превью видео
with open('video.mp4', 'rb') as f:
    video_data = f.read()

video_preview = PreviewGenerator.generate_video_preview(
    video_data,
    size=(300, 300),
    format='webp'
)

with open('video_preview.webp', 'wb') as f:
    f.write(video_preview)
```

### 6.6. Регенерация маркеров

**Python:**
```python
import requests

url = f"http://localhost:8000/api/portraits/{portrait_id}/regenerate-marker"
headers = {"Authorization": f"Bearer {admin_token}"}

response = requests.post(url, headers=headers)
result = response.json()

print(f"Status: {result['status']}")
print(f"Message: {result['message']}")
print(f"Marker sizes: {result['marker_sizes']}")
print(f"Total size: {result['total_size']}")
print(f"Generated at: {result['marker_updated_at']}")
```

---

## 7. Конфигурация и переменные окружения

### 7.1. Основные настройки

```bash
# Application
BASE_URL=http://localhost:8000
DEBUG=True

# Storage
STORAGE_TYPE=local                    # local, minio, yandex_disk
STORAGE_PATH=./storage

# File limits
MAX_IMAGE_SIZE_MB=10
MAX_VIDEO_SIZE_MB=50
ALLOWED_IMAGE_FORMATS=jpg,jpeg,png
ALLOWED_VIDEO_FORMATS=mp4,webm

# NFT markers
NFT_FEATURE_DENSITY=high              # low, medium, high
NFT_PYRAMID_LEVELS=3                  # 1-3
NFT_TARGET_DPI=150
```

### 7.2. MinIO/S3

```bash
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=vertex-ar
MINIO_SECURE=False
MINIO_PUBLIC_URL=                     # optional
```

### 7.3. Video Scheduler

```bash
VIDEO_SCHEDULER_ENABLED=true
VIDEO_SCHEDULER_CHECK_INTERVAL=300
VIDEO_SCHEDULER_ROTATION_INTERVAL=3600
VIDEO_SCHEDULER_ARCHIVE_AFTER_HOURS=168
VIDEO_SCHEDULER_NOTIFICATIONS_ENABLED=true
```

---

## 8. Оптимизация и рекомендации

### 8.1. Оптимизация хранилища

**Рекомендации:**

1. **Использовать MinIO/S3 для продакшена:**
   - Масштабируемость
   - Высокая доступность
   - CDN интеграция

2. **Настроить кеширование:**
   - NFT маркеры: 7 дней TTL
   - Превью: генерируются один раз
   - Публичные URL: кеширование в CDN

3. **Ротация логов:**
   - Логи генерации маркеров
   - Логи загрузки файлов

### 8.2. Оптимизация изображений

**Рекомендации для пользователей:**

1. **Размер:**
   - Минимум: 480×480 (для AR)
   - Оптимально: 1024×1024 - 2048×2048
   - Максимум: 8192×8192

2. **Контраст:**
   - Высокий контраст = лучшее отслеживание
   - Избегать однотонных изображений
   - Добавить текстуру/детали

3. **Качество:**
   - JPEG quality: 80-92
   - PNG: без прозрачности (конвертируется в RGB)

### 8.3. Оптимизация видео

**Рекомендации:**

1. **Кодек:**
   - H.264 (AVC) для максимальной совместимости
   - VP9 для WebM
   - AAC для аудио

2. **Разрешение:**
   - Мобильные: 720p (1280×720)
   - Десктоп: 1080p (1920×1080)

3. **Битрейт:**
   - 720p: 2-3 Mbps
   - 1080p: 4-5 Mbps
   - Аудио: 128-192 kbps

4. **Длительность:**
   - Оптимально: 10-30 секунд
   - Максимум: зависит от MAX_VIDEO_SIZE_MB

### 8.4. Производительность

**Метрики:**

1. **Генерация NFT маркеров:**
   - Малые изображения (<1MB): ~1-2 сек
   - Средние (1-5MB): ~3-5 сек
   - Большие (>5MB): ~5-10 сек

2. **Генерация превью:**
   - Изображения: <1 сек
   - Видео: 2-5 сек (извлечение кадра)

3. **Загрузка файлов:**
   - Локальное хранилище: зависит от диска
   - MinIO: зависит от сети
   - Yandex Disk: зависит от интернет-соединения

---

## 9. Мониторинг и логирование

### 9.1. Логи

**Модули логирования:**
- `nft_marker_generator.py` - генерация маркеров
- `preview_generator.py` - генерация превью
- `storage_manager.py` - операции хранилища
- `portraits.py` - API портретов
- `videos.py` - API видео

**Уровни логов:**
```python
logger.debug()   # Детальная отладка
logger.info()    # Информационные сообщения
logger.warning() # Предупреждения
logger.error()   # Ошибки
logger.exception()  # Исключения с traceback
```

**Пример логов:**
```
INFO - NFT marker generator initialized at storage
INFO - Portrait preview created: portraits/client-123/uuid_preview.webp
INFO - Video file size: 25165824 bytes = 24 MB
INFO - Video preview created: portraits/client-123/uuid/video-uuid_preview.webp
ERROR - Failed to generate NFT markers: Image too large
```

### 9.2. Метрики производительности

**NFTMarkerGenerator.metrics:**
```python
{
    'total_generated': 0,      # Общее количество
    'total_time': 0.0,         # Общее время (секунды)
    'cache_hits': 0,           # Попадания в кеш
    'cache_misses': 0          # Промахи кеша
}
```

---

## 10. Troubleshooting

### 10.1. Проблемы с NFT маркерами

**Симптом:** "Image too large"
- **Причина:** Изображение превышает max_image_size или max_image_area
- **Решение:** Уменьшить изображение или увеличить лимиты в NFTMarkerConfig

**Симптом:** "Image has low contrast"
- **Причина:** Изображение слишком однотонное
- **Решение:** Выбрать изображение с большей детализацией

**Симптом:** AR не распознаёт портрет
- **Причина:** Недостаточно характерных точек
- **Решение:** 
  - Использовать feature_density="high"
  - Выбрать изображение с высоким контрастом
  - Регенерировать маркеры

### 10.2. Проблемы с превью

**Симптом:** Превью не генерируется для видео
- **Причина:** Видео повреждено или неподдерживаемый кодек
- **Решение:** 
  - Проверить формат видео
  - Убедиться, что OpenCV установлен
  - Перекодировать видео в H.264/AAC

**Симптом:** Превью пустое (0 байт)
- **Причина:** Ошибка при обработке
- **Решение:**
  - Проверить логи
  - Убедиться, что PIL/Pillow установлен
  - Проверить права доступа к директориям

### 10.3. Проблемы с хранилищем

**Симптом:** "Failed to save file"
- **Причина:** Нет места на диске / нет доступа к MinIO / Yandex Disk
- **Решение:**
  - Проверить свободное место
  - Проверить credentials для MinIO/Yandex
  - Проверить права доступа к директориям

**Симптом:** Файлы не доступны по URL
- **Причина:** Неправильная конфигурация BASE_URL или MINIO_PUBLIC_URL
- **Решение:**
  - Проверить BASE_URL в .env
  - Для MinIO: настроить MINIO_PUBLIC_URL
  - Проверить права доступа к bucket

---

## Заключение

Этот документ предоставляет исчерпывающую информацию о процессах генерации NFT маркеров, загрузки и хранения файлов в Vertex AR. 

**Ключевые моменты:**

1. **NFT маркеры** генерируются автоматически при загрузке портрета с использованием собственного алгоритма на основе PIL
2. **Хранилище** поддерживает множественные адаптеры (Local, MinIO, Yandex) через единый интерфейс StorageManager
3. **Превью** генерируются автоматически для портретов и видео в формате WebP для оптимального сжатия
4. **Структура хранения** иерархична: portraits/{client_id}/{portrait_id}/{video_id} для лучшей организации

Для дополнительной информации см. исходный код в репозитории и комментарии в модулях.
