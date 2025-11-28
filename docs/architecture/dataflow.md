# Диаграммы потоков данных Vertex AR

## 1. Архитектура системы хранения

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Vertex AR Application                           │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                        FastAPI Routers                              │ │
│  │                                                                      │ │
│  │   /api/portraits    /api/videos    /api/ar    /api/admin           │ │
│  │        │                 │             │            │               │ │
│  └────────┼─────────────────┼─────────────┼────────────┼───────────────┘ │
│           │                 │             │            │                 │
│           └─────────────────┴─────────────┴────────────┘                 │
│                             │                                            │
│                             ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                      Storage Manager                              │  │
│  │                                                                    │  │
│  │  Content Types: portraits | videos | previews | nft_markers      │  │
│  │                                                                    │  │
│  │  Methods:                                                          │  │
│  │    • save_file(file_data, path, content_type)                    │  │
│  │    • get_file(path, content_type)                                │  │
│  │    • delete_file(path, content_type)                             │  │
│  │    • file_exists(path, content_type)                             │  │
│  │    • get_public_url(path, content_type)                          │  │
│  │                                                                    │  │
│  └────────┬────────────────────┬──────────────────────┬──────────────┘  │
│           │                    │                      │                 │
└───────────┼────────────────────┼──────────────────────┼─────────────────┘
            │                    │                      │
            ▼                    ▼                      ▼
   ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐
   │ LocalStorage    │  │ MinioStorage    │  │ YandexDisk       │
   │ Adapter         │  │ Adapter         │  │ Adapter          │
   │                 │  │                 │  │                  │
   │ storage_root/   │  │ endpoint        │  │ oauth_token      │
   │ └─portraits/    │  │ access_key      │  │ base_path        │
   │ └─videos/       │  │ secret_key      │  │                  │
   │ └─previews/     │  │ bucket          │  │                  │
   │ └─nft_markers/  │  │                 │  │                  │
   └────────┬────────┘  └────────┬────────┘  └────────┬─────────┘
            │                    │                     │
            ▼                    ▼                     ▼
    ┌───────────────┐   ┌───────────────┐    ┌────────────────┐
    │  Local Disk   │   │   MinIO S3    │    │  Yandex Cloud  │
    │               │   │   Compatible  │    │                │
    └───────────────┘   └───────────────┘    └────────────────┘
```

## 2. Поток загрузки портрета

```
┌──────────────┐
│   Client     │ Browser / Mobile App
│   Upload     │
└──────┬───────┘
       │ POST /api/portraits/
       │ FormData: { image, client_id, folder_id }
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Portraits API                             │
│                                                               │
│  1. Валидация                                                │
│     ├─ client_id exists?                                     │
│     ├─ folder_id exists? (optional)                          │
│     └─ image content_type == "image/*"                       │
│                                                               │
│  2. Генерация UUID                                           │
│     portrait_id = uuid.uuid4()                               │
│     permanent_link = f"portrait_{portrait_id}"               │
│                                                               │
│  3. Определение путей                                        │
│     image_path = portraits/{client_id}/{portrait_id}.jpg     │
│     preview_path = portraits/{client_id}/{portrait_id}_preview.webp │
│                                                               │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┴────────────────┬──────────────────────┐
        │                                │                      │
        ▼                                ▼                      ▼
┌───────────────┐              ┌────────────────┐     ┌──────────────────┐
│ Storage       │              │ Preview        │     │ NFT Marker       │
│ Manager       │              │ Generator      │     │ Generator        │
│               │              │                │     │                  │
│ save_file(    │              │ generate_      │     │ generate_marker( │
│   image_data, │              │   image_       │     │   image_path,    │
│   image_path, │              │   preview(     │     │   portrait_id,   │
│   "portraits")│              │   image_data,  │     │   config)        │
│               │              │   (300,300),   │     │                  │
│ ✓ Saved       │              │   'webp')      │     │ Steps:           │
└───────┬───────┘              │                │     │ 1. Validate      │
        │                      │ ✓ 300x300      │     │    480x480 min   │
        │                      │   WebP         │     │    8192x8192 max │
        │                      │   quality=85   │     │                  │
        │                      └────────┬───────┘     │ 2. Analyze       │
        │                               │             │    - contrast    │
        │                               │             │    - quality     │
        │                      ┌────────▼───────┐     │                  │
        │                      │ Storage        │     │ 3. Extract       │
        │                      │ Manager        │     │    features      │
        │                      │                │     │    (corners)     │
        │                      │ save_file(     │     │                  │
        │                      │   preview_data,│     │ 4. Generate      │
        │                      │   preview_path,│     │    .fset         │
        │                      │   "previews")  │     │    .fset3        │
        │                      │                │     │    .iset         │
        │                      │ ✓ Saved        │     │                  │
        │                      └────────┬───────┘     │ ✓ 3 files saved  │
        │                               │             └────────┬─────────┘
        │                               │                      │
        └───────────────┬───────────────┴──────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │         QR Code Generator              │
        │                                        │
        │  portrait_url = BASE_URL +             │
        │                 "/portrait/" +         │
        │                 permanent_link         │
        │                                        │
        │  qr_img = qrcode.make(portrait_url)    │
        │  qr_base64 = base64.encode(qr_img)     │
        │                                        │
        │  ✓ QR Code generated                   │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │         Database Insert                │
        │                                        │
        │  CREATE portrait:                      │
        │    - portrait_id                       │
        │    - client_id                         │
        │    - folder_id (optional)              │
        │    - image_path                        │
        │    - image_preview_path                │
        │    - marker_fset                       │
        │    - marker_fset3                      │
        │    - marker_iset                       │
        │    - permanent_link                    │
        │    - qr_code (base64)                  │
        │    - view_count = 0                    │
        │    - created_at = NOW()                │
        │                                        │
        │  ✓ Portrait record created             │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │         API Response                   │
        │                                        │
        │  PortraitResponse {                    │
        │    id: portrait_id,                    │
        │    client_id: client_id,               │
        │    folder_id: folder_id,               │
        │    permanent_link: permanent_link,     │
        │    qr_code_base64: qr_base64,          │
        │    image_path: image_path,             │
        │    image_url: public_url,              │
        │    preview_url: preview_public_url,    │
        │    view_count: 0,                      │
        │    created_at: timestamp               │
        │  }                                     │
        │                                        │
        └────────────────────────────────────────┘
```

## 3. Поток загрузки видео

```
┌──────────────┐
│   Client     │ Browser / Mobile App
│   Upload     │
└──────┬───────┘
       │ POST /api/videos/
       │ FormData: { video, portrait_id, is_active, description }
       ▼
┌─────────────────────────────────────────────────────────────┐
│                      Videos API                              │
│                                                               │
│  1. Валидация                                                │
│     ├─ portrait_id exists?                                   │
│     └─ video content_type == "video/*"                       │
│                                                               │
│  2. Генерация UUID                                           │
│     video_id = uuid.uuid4()                                  │
│                                                               │
│  3. Получение контекста                                      │
│     portrait = get_portrait(portrait_id)                     │
│     client_id = portrait.client_id                           │
│                                                               │
│  4. Определение путей                                        │
│     video_path = portraits/{client_id}/{portrait_id}/{video_id}.mp4 │
│     preview_path = portraits/{client_id}/{portrait_id}/{video_id}_preview.webp │
│                                                               │
│  5. Расчёт размера                                           │
│     file_size_bytes = len(video_content)                     │
│     file_size_mb = file_size_bytes / (1024 * 1024)          │
│                                                               │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┴──────────────┐
        │                              │
        ▼                              ▼
┌───────────────┐            ┌──────────────────────┐
│ Storage       │            │ Video Preview        │
│ Manager       │            │ Generator            │
│               │            │                      │
│ save_file(    │            │ Steps:               │
│   video_data, │            │ 1. Save temp file    │
│   video_path, │            │    video.mp4         │
│   "videos")   │            │                      │
│               │            │ 2. Open with OpenCV  │
│ ✓ Video saved │            │    cv2.VideoCapture  │
└───────┬───────┘            │                      │
        │                    │ 3. Get metadata      │
        │                    │    total_frames      │
        │                    │    fps               │
        │                    │                      │
        │                    │ 4. Extract frame     │
        │                    │    middle_frame =    │
        │                    │    total_frames // 2 │
        │                    │                      │
        │                    │ 5. Process frame     │
        │                    │    - GaussianBlur    │
        │                    │    - BGR → RGB       │
        │                    │    - Resize 300x300  │
        │                    │    - Center on black │
        │                    │                      │
        │                    │ 6. Add play icon     │
        │                    │    Draw triangle ▶   │
        │                    │                      │
        │                    │ 7. Save as WebP      │
        │                    │    quality=85        │
        │                    │                      │
        │                    │ ✓ Preview generated  │
        │                    └──────────┬───────────┘
        │                               │
        │                      ┌────────▼───────┐
        │                      │ Storage        │
        │                      │ Manager        │
        │                      │                │
        │                      │ save_file(     │
        │                      │   preview_data,│
        │                      │   preview_path,│
        │                      │   "previews")  │
        │                      │                │
        │                      │ ✓ Preview saved│
        │                      └────────┬───────┘
        │                               │
        └───────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │         Database Insert                │
        │                                        │
        │  CREATE video:                         │
        │    - video_id                          │
        │    - portrait_id                       │
        │    - video_path                        │
        │    - video_preview_path                │
        │    - is_active                         │
        │    - description                       │
        │    - file_size_mb                      │
        │    - start_datetime (NULL)             │
        │    - end_datetime (NULL)               │
        │    - rotation_type (NULL)              │
        │    - status ('active' / 'inactive')    │
        │    - created_at = NOW()                │
        │                                        │
        │  IF is_active = TRUE:                  │
        │    DEACTIVATE other videos for portrait│
        │                                        │
        │  ✓ Video record created                │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │         API Response                   │
        │                                        │
        │  VideoResponse {                       │
        │    id: video_id,                       │
        │    portrait_id: portrait_id,           │
        │    video_path: video_path,             │
        │    video_url: public_url,              │
        │    preview_url: preview_public_url,    │
        │    is_active: boolean,                 │
        │    file_size_mb: integer,              │
        │    description: string,                │
        │    created_at: timestamp,              │
        │    start_datetime: null,               │
        │    end_datetime: null,                 │
        │    rotation_type: null,                │
        │    status: 'active' | 'inactive'       │
        │  }                                     │
        │                                        │
        └────────────────────────────────────────┘
```

## 4. Процесс генерации NFT маркеров (детально)

```
┌─────────────────────────────────────────────────────────────┐
│              NFT Marker Generation Process                   │
│                                                               │
│  Input: image_path, marker_name, config                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │  Step 1: Validate Image               │
        │                                        │
        │  ├─ File exists?                       │
        │  ├─ PIL can open?                      │
        │  ├─ Size >= 480x480?                   │
        │  ├─ Size <= 8192x8192?                 │
        │  └─ Area <= 50,000,000 pixels?         │
        │                                        │
        │  ✓ Valid OR ✗ Exception                │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │  Step 2: Check Cache                  │
        │                                        │
        │  cache_key = MD5(                      │
        │    path + mtime + size                 │
        │  )                                     │
        │                                        │
        │  IF cache.get(cache_key):              │
        │    └─ Return cached analysis           │
        │  ELSE:                                 │
        │    └─ Continue to Step 3               │
        │                                        │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │  Step 3: Analyze Image Features       │
        │                                        │
        │  1. Convert to grayscale               │
        │     img_gray = img.convert('L')        │
        │                                        │
        │  2. Calculate statistics               │
        │     pixels = img_gray.getdata()        │
        │     avg_brightness = mean(pixels)      │
        │     variance = var(pixels)             │
        │     contrast = sqrt(variance)          │
        │                                        │
        │  3. Assess quality                     │
        │     IF contrast < 30:                  │
        │        quality = "плохое"              │
        │     ELIF contrast < 60:                │
        │        quality = "удовлетворительное"  │
        │     ELIF contrast < 90:                │
        │        quality = "хорошее"             │
        │     ELSE:                              │
        │        quality = "отличное"            │
        │                                        │
        │  4. Cache result                       │
        │     cache.set(cache_key, analysis)     │
        │                                        │
        │  ✓ Analysis complete                   │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │  Step 4: Generate .fset                │
        │          (Feature Set)                 │
        │                                        │
        │  1. Create binary header               │
        │     magic = b"ARJS"                    │
        │     version = 1                        │
        │     width, height                      │
        │     dpi = config.min_dpi               │
        │     density = config.feature_density   │
        │                                        │
        │  2. Detect corners (Harris-like)       │
        │     step = {low: 20, med: 10, high: 5} │
        │                                        │
        │     FOR each (x, y) in grid:           │
        │       dx = |pixel[x+1,y] - pixel[x,y]| │
        │       dy = |pixel[x,y+1] - pixel[x,y]| │
        │       score = dx * dy                  │
        │                                        │
        │       IF score > 100:                  │
        │         features.append((x, y, score)) │
        │                                        │
        │  3. Write to binary file               │
        │     FOR each feature:                  │
        │       write(float(x))                  │
        │       write(float(y))                  │
        │       write(float(score))              │
        │                                        │
        │  ✓ .fset saved to:                     │
        │    nft_markers/{name}/{name}.fset      │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │  Step 5: Generate .fset3               │
        │          (3D Feature Set)              │
        │                                        │
        │  1. Create image pyramid               │
        │     levels = config.levels (1-3)       │
        │                                        │
        │     FOR level in range(levels):        │
        │       scale = 2 ** level               │
        │       scaled_img = resize(img, 1/scale)│
        │       extract_features(scaled_img)     │
        │                                        │
        │  2. Write multi-scale data             │
        │     magic = b"ARS3"                    │
        │     num_levels = levels                │
        │                                        │
        │     FOR each level:                    │
        │       write(level_features)            │
        │                                        │
        │  ✓ .fset3 saved to:                    │
        │    nft_markers/{name}/{name}.fset3     │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │  Step 6: Generate .iset                │
        │          (Image Set / Metadata)        │
        │                                        │
        │  1. Collect metadata                   │
        │     - image dimensions                 │
        │     - DPI                               │
        │     - file path                        │
        │     - feature count                    │
        │                                        │
        │  2. Write as JSON/binary               │
        │     {                                  │
        │       "width": width,                  │
        │       "height": height,                │
        │       "dpi": dpi,                      │
        │       "image_path": path,              │
        │       "feature_count": count           │
        │     }                                  │
        │                                        │
        │  ✓ .iset saved to:                     │
        │    nft_markers/{name}/{name}.iset      │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │  Step 7: Return NFTMarker Result      │
        │                                        │
        │  NFTMarker {                           │
        │    image_path: string,                 │
        │    fset_path: string,                  │
        │    fset3_path: string,                 │
        │    iset_path: string,                  │
        │    width: int,                         │
        │    height: int,                        │
        │    dpi: int,                           │
        │    quality_score: float,               │
        │    generation_time: float              │
        │  }                                     │
        │                                        │
        └────────────────────────────────────────┘
```

## 5. Структура файловой системы

```
vertex-ar/
│
├── storage/                           # Хранилище файлов
│   │
│   ├── portraits/                     # Портреты (изображения)
│   │   └── {client_id}/
│   │       ├── {portrait_id}.jpg      # Оригинальное фото
│   │       └── {portrait_id}_preview.webp  # Превью 300x300
│   │
│   ├── nft_markers/                   # NFT маркеры для AR
│   │   └── {portrait_id}/
│   │       ├── {portrait_id}.fset     # Feature set
│   │       ├── {portrait_id}.fset3    # 3D feature set
│   │       └── {portrait_id}.iset     # Image metadata
│   │
│   ├── nft_cache/                     # Кеш анализа маркеров
│   │   └── {md5_hash}.json            # Результаты анализа (TTL: 7 дней)
│   │
│   └── qrcodes/                       # QR-коды (опционально)
│       └── {portrait_id}.png
│
├── app_data.db                        # База данных SQLite
│
├── app/                               # Приложение
│   ├── main.py                        # FastAPI app
│   ├── database.py                    # Database layer
│   ├── models.py                      # Pydantic models
│   ├── config.py                      # Configuration
│   │
│   ├── api/                           # API endpoints
│   │   ├── portraits.py               # Portraits CRUD
│   │   ├── videos.py                  # Videos CRUD
│   │   ├── ar.py                      # AR viewer
│   │   └── admin.py                   # Admin panel
│   │
│   ├── storage.py                     # Storage adapter interface
│   ├── storage_local.py               # Local filesystem adapter
│   ├── storage_minio.py               # MinIO/S3 adapter
│   └── storage_yandex.py              # Yandex Disk adapter
│
├── nft_marker_generator.py           # NFT marker generator
├── nft_maker.py                       # CLI for NFT generation
├── preview_generator.py               # Preview generator
├── storage_manager.py                 # Storage manager
├── storage_config.py                  # Storage configuration
│
└── .env                               # Environment variables
```

## 6. База данных (SQLite Schema)

```sql
-- Companies table
CREATE TABLE companies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    storage_type TEXT DEFAULT 'local',
    storage_connection_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

-- Clients table
CREATE TABLE clients (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- Projects table (Hierarchical structure)
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- Folders table (Within projects)
CREATE TABLE folders (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Portraits table
CREATE TABLE portraits (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    folder_id TEXT,  -- Optional folder assignment
    image_path TEXT NOT NULL,
    image_preview_path TEXT,
    marker_fset TEXT,
    marker_fset3 TEXT,
    marker_iset TEXT,
    permanent_link TEXT UNIQUE NOT NULL,
    qr_code TEXT,
    view_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (client_id) REFERENCES clients(id),
    FOREIGN KEY (folder_id) REFERENCES folders(id)
);

-- Videos table
CREATE TABLE videos (
    id TEXT PRIMARY KEY,
    portrait_id TEXT NOT NULL,
    video_path TEXT NOT NULL,
    video_preview_path TEXT,
    is_active INTEGER DEFAULT 0,
    description TEXT,
    file_size_mb INTEGER,
    -- Video scheduler fields
    start_datetime TEXT,
    end_datetime TEXT,
    rotation_type TEXT,  -- 'none', 'sequential', 'cyclic'
    status TEXT DEFAULT 'inactive',  -- 'active', 'inactive', 'archived'
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (portrait_id) REFERENCES portraits(id)
);

-- Orders table
CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    status TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

-- Users table
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    full_name TEXT,
    hashed_password TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    is_admin INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

-- Video schedule history (for audit)
CREATE TABLE video_schedule_history (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL,
    action TEXT NOT NULL,  -- 'activated', 'deactivated', 'scheduled', etc.
    performed_by TEXT,
    performed_at TEXT NOT NULL,
    details TEXT,
    FOREIGN KEY (video_id) REFERENCES videos(id)
);
```

## 7. Поток просмотра AR (End-user)

```
┌──────────────┐
│  End User    │ Smartphone with camera
└──────┬───────┘
       │
       │ 1. Scan QR code on physical portrait
       │
       ▼
┌─────────────────────────────────────────┐
│   QR Code Content                        │
│   http://example.com/portrait/uuid       │
└─────────────┬───────────────────────────┘
              │
              │ 2. Browser opens URL
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│              GET /portrait/{permanent_link}              │
│                                                           │
│  1. Database.get_portrait_by_link(permanent_link)        │
│     └─ Returns portrait record                           │
│                                                           │
│  2. Database.get_active_video(portrait_id)               │
│     └─ Returns active video for this portrait            │
│                                                           │
│  3. Database.increment_view_count(portrait_id)           │
│     └─ view_count += 1                                   │
│                                                           │
│  4. Render AR viewer HTML page                           │
│                                                           │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│                    AR Viewer Page                        │
│                    (HTML + JavaScript)                   │
│                                                           │
│  1. Load AR.js library                                   │
│     <script src="ar.js"></script>                        │
│     <script src="aframe.js"></script>                    │
│                                                           │
│  2. Load NFT marker files                                │
│     ├─ /storage/nft_markers/{id}/{id}.fset              │
│     ├─ /storage/nft_markers/{id}/{id}.fset3             │
│     └─ /storage/nft_markers/{id}/{id}.iset              │
│                                                           │
│  3. Initialize camera                                    │
│     navigator.mediaDevices.getUserMedia({video: true})   │
│                                                           │
│  4. Start AR tracking                                    │
│     AR.js tracks NFT marker in camera feed               │
│                                                           │
│  5. On marker found:                                     │
│     ├─ Show 3D scene overlay                             │
│     ├─ Load video from:                                  │
│     │  /storage/portraits/{client}/{portrait}/{video}.mp4│
│     └─ Play video in AR                                  │
│                                                           │
│  6. On marker lost:                                      │
│     └─ Pause video / hide scene                          │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

## 8. Последовательность вызовов API

### 8.1. Создание портрета с видео

```
Client → POST /api/auth/login
       ← 200 OK { access_token }

Client → POST /api/portraits/
         Authorization: Bearer {token}
         FormData: { image, client_id, folder_id }
       ← 201 Created { 
           id: portrait_id,
           permanent_link: "portrait_uuid",
           qr_code_base64: "data:image/png;base64,...",
           image_url: "http://example.com/storage/portraits/...",
           preview_url: "http://example.com/storage/portraits/..._preview.webp"
         }

Client → POST /api/videos/
         Authorization: Bearer {token}
         FormData: { video, portrait_id, is_active: true }
       ← 201 Created {
           id: video_id,
           portrait_id: portrait_id,
           video_url: "http://example.com/storage/portraits/.../video.mp4",
           preview_url: "http://example.com/storage/portraits/.../video_preview.webp",
           is_active: true,
           file_size_mb: 25
         }

Client → GET /api/portraits/{portrait_id}
         Authorization: Bearer {token}
       ← 200 OK { portrait with all fields }
```

### 8.2. Регенерация маркеров

```
Admin → POST /api/portraits/{portrait_id}/regenerate-marker
        Authorization: Bearer {admin_token}
      ← 200 OK {
          status: "success",
          message: "NFT markers regenerated successfully",
          marker_sizes: {
            fset: "1.2 МБ",
            fset3: "3.5 МБ",
            iset: "500 Б"
          },
          total_size: "5.2 МБ",
          marker_updated_at: "2024-01-15 10:30:45"
        }
```

---

## Заключение

Эти диаграммы визуализируют архитектуру и потоки данных в Vertex AR, дополняя основной документ ANALYSIS_MARKERS_UPLOADS_STORAGE.md. Они помогают понять:

1. **Модульную архитектуру** с адаптерами хранилища
2. **Последовательность обработки** при загрузке файлов
3. **Генерацию NFT маркеров** шаг за шагом
4. **Структуру хранения** файлов и базы данных
5. **Взаимодействие компонентов** в режиме реального времени

Для более детальной информации обратитесь к исходному коду модулей.
