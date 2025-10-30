"""
Simplified AR Backend for Vertex-AR - Focus on core AR functionality
Based on Stogram approach: No blockchain, no IPFS, no NFT - just image + video AR content
"""
from __future__ import annotations

import secrets
import shutil
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import uuid
import qrcode
from io import BytesIO
import base64
import logging

# Добавляем импорт для новых функций
from utils import get_disk_usage, get_storage_usage, format_bytes

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Настройка логирования для всего приложения
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app_data.db"
STORAGE_ROOT = BASE_DIR / "storage"
STATIC_ROOT = BASE_DIR / "static"
STATIC_ROOT.mkdir(parents=True, exist_ok=True)

# Get base URL from environment or use default
import os
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

VERSION_FILE = BASE_DIR / "VERSION"
try:
    VERSION = VERSION_FILE.read_text().strip()
except FileNotFoundError:
    VERSION = "1.0.0"


class Database:
    """Simplified database with just users and AR content."""
    
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._initialise_schema()
    
    def _initialise_schema(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    hashed_password TEXT NOT NULL,
                    is_admin INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ar_content (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    image_path TEXT NOT NULL,
                    video_path TEXT NOT NULL,
                    image_preview_path TEXT,
                    video_preview_path TEXT,
                    marker_fset TEXT NOT NULL,
                    marker_fset3 TEXT NOT NULL,
                    marker_iset TEXT NOT NULL,
                    ar_url TEXT NOT NULL,
                    qr_code TEXT,
                    view_count INTEGER NOT NULL DEFAULT 0,
                    click_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(username) REFERENCES users(username)
                )
                """
            )
            # Add columns to existing tables if they don't exist
            try:
                self._connection.execute("ALTER TABLE ar_content ADD COLUMN image_preview_path TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE ar_content ADD COLUMN video_preview_path TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE ar_content ADD COLUMN view_count INTEGER NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            try:
                self._connection.execute("ALTER TABLE ar_content ADD COLUMN click_count INTEGER NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                pass
    
    def _execute(self, query: str, parameters: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        with self._lock:
            cursor = self._connection.execute(query, parameters)
            self._connection.commit()
            return cursor
    
    def create_user(self, username: str, hashed_password: str, is_admin: bool = False) -> None:
        try:
            self._execute(
                "INSERT INTO users (username, hashed_password, is_admin) VALUES (?, ?, ?)",
                (username, hashed_password, int(is_admin)),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("user_already_exists") from exc
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        cursor = self._execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    
    def create_ar_content(
        self,
        content_id: str,
        username: str,
        image_path: str,
        video_path: str,
        marker_fset: str,
        marker_fset3: str,
        marker_iset: str,
        ar_url: str,
        qr_code: Optional[str],
        image_preview_path: Optional[str] = None,
        video_preview_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._execute(
            """
            INSERT INTO ar_content (
                id, username, image_path, video_path,
                image_preview_path, video_preview_path,
                marker_fset, marker_fset3, marker_iset,
                ar_url, qr_code
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (content_id, username, image_path, video_path,
             image_preview_path, video_preview_path,
             marker_fset, marker_fset3, marker_iset, ar_url, qr_code),
        )
        return self.get_ar_content(content_id)
    
    def get_ar_content(self, content_id: str) -> Optional[Dict[str, Any]]:
        cursor = self._execute("SELECT * FROM ar_content WHERE id = ?", (content_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    
    def list_ar_content(self, username: Optional[str] = None) -> List[Dict[str, Any]]:
        if username:
            cursor = self._execute(
                "SELECT * FROM ar_content WHERE username = ? ORDER BY created_at DESC",
                (username,),
            )
        else:
            cursor = self._execute("SELECT * FROM ar_content ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]
    
    def increment_view_count(self, content_id: str) -> None:
        """Увеличить счетчик просмотров AR контента."""
        self._execute(
            "UPDATE ar_content SET view_count = view_count + 1 WHERE id = ?",
            (content_id,),
        )
    
    def increment_click_count(self, content_id: str) -> None:
        """Увеличить счетчик кликов по ссылкам AR контента."""
        self._execute(
            "UPDATE ar_content SET click_count = click_count + 1 WHERE id = ?",
            (content_id,),
        )
    
    def delete_ar_content(self, content_id: str) -> bool:
        """Удалить AR контент из базы данных."""
        cursor = self._execute("DELETE FROM ar_content WHERE id = ?", (content_id,))
        return cursor.rowcount > 0


def _hash_password(password: str) -> str:
    """Simple password hashing (use proper hashing in production)."""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


def _verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return _hash_password(password) == hashed


class TokenManager:
    """Simple token management."""
    
    def __init__(self) -> None:
        self._tokens: Dict[str, str] = {}
        self._lock = threading.Lock()
    
    def issue_token(self, username: str) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._tokens[token] = username
        return token
    
    def verify_token(self, token: str) -> Optional[str]:
        with self._lock:
            return self._tokens.get(token)
    
    def revoke_token(self, token: str) -> None:
        with self._lock:
            self._tokens.pop(token, None)


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=1, max_length=256)


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ARContentResponse(BaseModel):
    id: str
    ar_url: str
    qr_code_base64: Optional[str]
    image_path: str
    video_path: str
    created_at: str


app = FastAPI(
    title="Vertex AR - Simplified",
    version=VERSION,
    description="A lightweight AR backend for creating augmented reality experiences from image + video pairs"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_ROOT)), name="static")
app.mount("/storage", StaticFiles(directory=str(STORAGE_ROOT)), name="storage")

security = HTTPBearer()
database = Database(DB_PATH)
tokens = TokenManager()

# Монтируем шаблоны
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    username = tokens.verify_token(credentials.credentials)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return username


def require_admin(username: str = Depends(get_current_user)) -> str:
    user = database.get_user(username)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return username


@app.get("/")
def read_root():
    return {"Hello": "Vertex AR (Simplified)"}


@app.get("/health", tags=["health"])
async def health_check() -> Dict[str, str]:
    """Health check endpoint for Docker and load balancers"""
    return {"status": "healthy", "version": VERSION}


@app.get("/version", tags=["health"])
async def get_version() -> Dict[str, str]:
    """Get API version"""
    return {"version": VERSION}


@app.get("/admin", response_class=HTMLResponse, tags=["admin"])
async def admin_panel(request: Request) -> HTMLResponse:
    """Serve admin panel HTML page."""
    # Получаем список AR контента для отображения в админке
    records = database.list_ar_content()
    return templates.TemplateResponse("admin.html", {"request": request, "records": records})


@app.post("/auth/register", status_code=status.HTTP_201_CREATED, tags=["auth"])
async def register_user(user: UserCreate) -> Dict[str, str]:
    existing = database.get_user(user.username)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
    try:
        database.create_user(user.username, _hash_password(user.password), is_admin=True)  # Создаем администратора
    except ValueError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
    return {"username": user.username}


@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
async def login_user(credentials: UserLogin) -> TokenResponse:
    user = database.get_user(credentials.username)
    if user is None or not _verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = tokens.issue_token(credentials.username)
    return TokenResponse(access_token=token)


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
async def logout_user(username: str = Depends(get_current_user)) -> Response:
    tokens.revoke_token(username)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/ar/upload", response_model=ARContentResponse, tags=["ar"])
async def upload_ar_content(
    image: UploadFile = File(...),
    video: UploadFile = File(...),
    username: str = Depends(require_admin),
) -> ARContentResponse:
    """
    Upload image and video to create AR content.
    Only admins can upload.
    """
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file")
    
    if not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid video file")
    
    # Генерируем UUID для файлов
    content_id = str(uuid.uuid4())
    
    # Создаем директории для хранения файлов
    user_storage = STORAGE_ROOT / "ar_content" / username
    user_storage.mkdir(parents=True, exist_ok=True)
    content_dir = user_storage / content_id
    content_dir.mkdir(parents=True, exist_ok=True)
    
    # Читаем содержимое файлов для генерации превью
    image.file.seek(0)
    image_content = await image.read()
    video.file.seek(0)
    video_content = await video.read()
    
    # Сохраняем изображение
    image_path = content_dir / f"{content_id}.jpg"
    with open(image_path, "wb") as f:
        f.write(image_content)
    
    # Сохраняем видео
    video_path = content_dir / f"{content_id}.mp4"
    with open(video_path, "wb") as f:
        f.write(video_content)
    
    # Генерируем превью
    from preview_generator import PreviewGenerator
    image_preview_path = None
    video_preview_path = None
    
    try:
        # Генерируем превью изображения
        image_preview = PreviewGenerator.generate_image_preview(image_content)
        if image_preview:
            image_preview_path = content_dir / f"{content_id}_preview.jpg"
            with open(image_preview_path, "wb") as f:
                f.write(image_preview)
            logger.info(f"Превью изображения создано: {image_preview_path}")
    except Exception as e:
        logger.error(f"Ошибка при генерации превью изображения: {e}")
    
    try:
        # Генерируем превью видео
        video_preview = PreviewGenerator.generate_video_preview(video_content)
        if video_preview:
            video_preview_path = content_dir / f"{content_id}_video_preview.jpg"
            with open(video_preview_path, "wb") as f:
                f.write(video_preview)
            logger.info(f"Превью видео создано: {video_preview_path}")
    except Exception as e:
        logger.error(f"Ошибка при генерации превью видео: {e}")
    
    # Генерируем QR-код
    ar_url = f"{BASE_URL}/ar/{content_id}"
    qr_img = qrcode.make(ar_url)
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode()
    
    # Генерируем NFT-маркеры
    from nft_marker_generator import NFTMarkerConfig, NFTMarkerGenerator
    nft_generator = NFTMarkerGenerator(STORAGE_ROOT)
    config = NFTMarkerConfig(feature_density="high", levels=3)
    marker_result = nft_generator.generate_marker(str(image_path), content_id, config)
    
    # Создаем запись в базе данных
    db_record = database.create_ar_content(
        content_id=content_id,
        username=username,
        image_path=str(image_path),
        video_path=str(video_path),
        image_preview_path=str(image_preview_path) if image_preview_path else None,
        video_preview_path=str(video_preview_path) if video_preview_path else None,
        marker_fset=marker_result.fset_path,
        marker_fset3=marker_result.fset3_path,
        marker_iset=marker_result.iset_path,
        ar_url=ar_url,
        qr_code=qr_base64,
    )
    
    return ARContentResponse(
        id=content_id,
        ar_url=ar_url,
        qr_code_base64=qr_base64,
        image_path=str(image_path),
        video_path=str(video_path),
        created_at=db_record["created_at"],
    )


@app.get("/ar/list", tags=["ar"])
async def list_ar_content(username: str = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """List all AR content (admins see all, users see their own)."""
    user = database.get_user(username)
    if user and user.get("is_admin"):
        return database.list_ar_content()
    return database.list_ar_content(username)


@app.get("/ar/{content_id}", response_class=HTMLResponse, tags=["ar"])
async def view_ar_content(content_id: str, animation: bool = False) -> HTMLResponse:
    """View AR content page (public access)."""
    content = database.get_ar_content(content_id)
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AR content not found")
    
    # Увеличиваем счетчик просмотров
    database.increment_view_count(content_id)
    
    if animation:
        # Возвращаем HTML для анимированного портрета
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no">
    <title>Vertex AR Portrait Animation</title>
    <!-- A-Frame и AR.js библиотеки -->
    <script src="https://aframe.io/releases/1.6.0/aframe.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/ar.js@3.4.2/aframe/build/aframe-ar-nft.js"></script>
    <!-- Anime.js для анимаций -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/animejs/3.2.1/anime.min.js"></script>
    
    <style>
        body {{
            margin: 0;
            overflow: hidden;
            font-family: Arial, sans-serif;
            background-color: #000;
        }}
        
        #start-btn {{
            position: fixed;
            top: 10px;
            left: 10px;
            z-index: 100;
            padding: 10px 15px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            display: none;
        }}
        
        #start-btn:hover {{
            background-color: #45a049;
        }}
        
        #start-btn:disabled {{
            background-color: #cccccc;
            cursor: not-allowed;
        }}
        
        .arjs-loader {{
            height: 100%;
            width: 100%;
            position: absolute;
            top: 0;
            left: 0;
            background-color: rgba(0, 0, 0, 0.8);
            z-index: 99;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        
        .arjs-loader div {{
            text-align: center;
            font-size: 1.25em;
            color: white;
        }}
        
        .status-indicator {{
            position: fixed;
            top: 10px;
            right: 10px;
            z-index: 100;
            padding: 8px 12px;
            background-color: rgba(0, 0, 0, 0.7);
            color: white;
            border-radius: 4px;
            font-size: 14px;
        }}
        
        .animation-controls {{
            position: fixed;
            bottom: 10px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 100;
            display: flex;
            gap: 10px;
        }}
        
        .animation-btn {{
            padding: 8px 12px;
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}
        
        .animation-btn:hover {{
            background-color: #0b7dda;
        }}
        
        .animation-btn:disabled {{
            background-color: #cccccc;
            cursor: not-allowed;
        }}
    </style>
</head>
<body>
    <!-- Кнопка запуска видео, необходима для мобильных браузеров -->
    <button id="start-btn" onclick="startAnimation()" disabled>Запустить анимацию</button>
    
    <!-- Индикатор статуса -->
    <div class="status-indicator" id="status-indicator">Загрузка AR-опыта...</div>
    
    <!-- Кнопки управления анимацией -->
    <div class="animation-controls" id="animation-controls" style="display: none;">
        <button class="animation-btn" onclick="triggerBlinkAnimation()">Моргание</button>
        <button class="animation-btn" onclick="triggerHeadTurn()">Поворот головы</button>
        <button class="animation-btn" onclick="triggerSmile()">Улыбка</button>
        <button class="animation-btn" onclick="triggerWink()">Подмигивание</button>
    </div>
    
    <!-- Индикатор загрузки -->
    <div class="arjs-loader" id="loader">
        <div>
            <div>Загрузка AR-опыта</div>
            <div>Пожалуйста, подождите</div>
            <div class="loading-spinner">●●●</div>
        </div>
    </div>

    <!-- AR Сцена -->
    <a-scene
        vr-mode-ui="enabled: false"
        embedded
        arjs="trackingMethod: best; sourceType: webcam; debugUIEnabled: false;"
        renderer="logarithmicDepthBuffer: true;"
        id="ar-scene"
    >
        <!-- NFT Маркер для обнаружения изображения -->
        <a-nft
            type="nft"
            url="/ar/markers/{content_id}"
            smooth="true"
            smoothCount="10"
            smoothTolerance="0.01"
            smoothThreshold="5"
            id="nft-marker"
        >
            <!-- 3D модель портрета -->
            <a-entity
                id="portrait-entity"
                position="0 0 0"
                scale="1 1 1"
                rotation="0 0 0"
            >
                <!-- Основной элемент портрета -->
                <a-image
                    id="portrait-base"
                    src="/ar/image/{content_id}"
                    width="1.5"
                    height="2"
                    position="0 0 0"
                    material="shader: flat; transparent: true;"
                ></a-image>
                
                <!-- Элементы для анимации (глаза, рот и т.д.) -->
                <a-entity id="eyes-container" position="0 0.2 0.01">
                    <a-entity id="left-eye" position="-0.2 0 0">
                        <a-box id="left-eye-blink" position="0 0" width="0.1" height="0.05" depth="0.01" color="black" visible="false"></a-box>
                    </a-entity>
                    <a-entity id="right-eye" position="0.2 0 0">
                        <a-box id="right-eye-blink" position="0 0 0" width="0.1" height="0.05" depth="0.01" color="black" visible="false"></a-box>
                    </a-entity>
                </a-entity>
                
                <a-entity id="mouth-container" position="0 -0.3 0.01">
                    <a-box id="mouth" position="0 0 0" width="0.3" height="0.1" depth="0.01" color="pink" visible="false"></a-box>
                </a-entity>
            </a-entity>
        </a-nft>

        <!-- Камера -->
        <a-entity camera></a-entity>
    </a-scene>

    <script>
        // Состояния для отслеживания процесса
        let isAnimationPlaying = false;
        let isMarkerDetected = false;
        let currentAnimation = null;
        
        // Обновляем индикатор статуса
        function updateStatus(message) {{
            const statusEl = document.getElementById('status-indicator');
            if (statusEl) {{
                statusEl.textContent = message;
            }}
        }}
        
        // Инициализация анимаций при загрузке сцены
        function initAnimations() {{
            // Анимация моргания
            window.blinkAnimation = anime({{
                targets: ['#left-eye-blink', '#right-eye-blink'],
                height: [
                    {{ value: '0.05', duration: 50, easing: 'linear' }},
                    {{ value: '0.01', duration: 50, easing: 'linear' }},
                    {{ value: '0.05', duration: 50, easing: 'linear' }}
                ],
                opacity: [
                    {{ value: 1, duration: 50, easing: 'linear' }},
                    {{ value: 0, duration: 10, easing: 'linear' }}
                ],
                autoplay: false,
                duration: 200
            }});
            
            // Анимация улыбки
            window.smileAnimation = anime({{
                targets: '#mouth',
                height: [
                    {{ value: 0.1, duration: 200, easing: 'easeInOutQuad' }},
                    {{ value: 0.15, duration: 300, easing: 'easeInOutQuad' }},
                    {{ value: 0.1, duration: 200, easing: 'easeInOutQuad' }}
                ],
                width: [
                    {{ value: 0.3, duration: 200, easing: 'easeInOutQuad' }},
                    {{ value: 0.4, duration: 300, easing: 'easeInOutQuad' }},
                    {{ value: 0.3, duration: 200, easing: 'easeInOutQuad' }}
                ],
                autoplay: false,
                duration: 700
            }});
            
            // Анимация поворота головы
            window.headTurnAnimation = anime({{
                targets: '#portrait-entity',
                rotation: [
                    {{ y: 0, duration: 300, easing: 'easeInOutQuad' }},
                    {{ y: 15, duration: 400, easing: 'easeInOutQuad' }},
                    {{ y: -15, duration: 800, easing: 'easeInOutQuad' }},
                    {{ y: 0, duration: 400, easing: 'easeInOutQuad' }}
                ],
                autoplay: false,
                duration: 1900
            }});
            
            // Анимация подмигивания
            window.winkAnimation = anime({{
                targets: '#right-eye-blink',
                height: [
                    {{ value: '0.05', duration: 50, easing: 'linear' }},
                    {{ value: '0.01', duration: 100, easing: 'linear' }},
                    {{ value: '0.05', duration: 50, easing: 'linear' }}
                ],
                opacity: [
                    {{ value: 1, duration: 50, easing: 'linear' }},
                    {{ value: 0, duration: 150, easing: 'linear' }}
                ],
                autoplay: false,
                duration: 300
            }});
        }}
        
        // Функция запуска анимации
        function startAnimation() {{
            if (!isMarkerDetected) return;
            
            // Показываем элементы анимации
            document.getElementById('left-eye-blink').setAttribute('visible', 'true');
            document.getElementById('right-eye-blink').setAttribute('visible', 'true');
            document.getElementById('mouth').setAttribute('visible', 'true');
            
            // Запускаем случайную анимацию
            const animations = [window.blinkAnimation, window.smileAnimation, window.headTurnAnimation];
            const randomAnimation = animations[Math.floor(Math.random() * animations.length)];
            
            if (currentAnimation) {{
                currentAnimation.pause();
            }}
            
            currentAnimation = randomAnimation;
            currentAnimation.restart();
            
            isAnimationPlaying = true;
            updateStatus('Анимация запущена');
        }}
        
        // Триггер анимации моргания
        function triggerBlinkAnimation() {{
            if (!isMarkerDetected) return;
            
            document.getElementById('left-eye-blink').setAttribute('visible', 'true');
            document.getElementById('right-eye-blink').setAttribute('visible', 'true');
            
            if (currentAnimation) {{
                currentAnimation.pause();
            }}
            
            currentAnimation = window.blinkAnimation;
            currentAnimation.restart();
            
            updateStatus('Анимация моргания');
        }}
        
        // Триггер анимации поворота головы
        function triggerHeadTurn() {{
            if (!isMarkerDetected) return;
            
            if (currentAnimation) {{
                currentAnimation.pause();
            }}
            
            currentAnimation = window.headTurnAnimation;
            currentAnimation.restart();
            
            updateStatus('Анимация поворота головы');
        }}
        
        // Триггер анимации улыбки
        function triggerSmile() {{
            if (!isMarkerDetected) return;
            
            document.getElementById('mouth').setAttribute('visible', 'true');
            
            if (currentAnimation) {{
                currentAnimation.pause();
            }}
            
            currentAnimation = window.smileAnimation;
            currentAnimation.restart();
            
            updateStatus('Анимация улыбки');
        }}
        
        // Триггер анимации подмигивания
        function triggerWink() {{
            if (!isMarkerDetected) return;
            
            document.getElementById('right-eye-blink').setAttribute('visible', 'true');
            
            if (currentAnimation) {{
                currentAnimation.pause();
            }}
            
            currentAnimation = window.winkAnimation;
            currentAnimation.restart();
            
            updateStatus('Анимация подмигивания');
        }}
        
        // Обработка события загрузки сцены
        document.querySelector('a-scene').addEventListener('loaded', function() {{
            // Инициализируем анимации
            initAnimations();
            
            // Скрываем лоадер
            const loader = document.getElementById('loader');
            if (loader) {{
                loader.style.display = 'none';
            }}
            
            // Активируем кнопку запуска
            const startBtn = document.getElementById('start-btn');
            if (startBtn) {{
                startBtn.style.display = 'block';
                startBtn.disabled = false;
            }}
            
            updateStatus('Сцена загружена, ожидание маркера...');
        }});
        
        // Обработка события обнаружения маркера
        document.querySelector('a-scene').addEventListener('markerFound', function() {{
            isMarkerDetected = true;
            updateStatus('Маркер обнаружен! Активируйте анимацию');
            
            // Показываем кнопки управления анимацией
            const controls = document.getElementById('animation-controls');
            if (controls) {{
                controls.style.display = 'flex';
            }}
            
            // На десктопе можем автостартовать ненавязчивую анимацию
            if (!/Android|iPhone|iPad/i.test(navigator.userAgent)) {{
                // Небольшая задержка для стабильности
                setTimeout(() => {{
                    // Автоматически запускаем моргание каждые 3-5 секунд
                    setInterval(() => {{
                        if (isMarkerDetected && !isAnimationPlaying) {{
                            triggerBlinkAnimation();
                        }}
                    }}, 3000 + Math.random() * 2000);
                }}, 500);
            }}
        }});
        
        // Обработка события потери маркера
        document.querySelector('a-scene').addEventListener('markerLost', function() {{
            isMarkerDetected = false;
            
            // Останавливаем текущую анимацию
            if (currentAnimation) {{
                currentAnimation.pause();
                currentAnimation = null;
            }}
            
            isAnimationPlaying = false;
            updateStatus('Маркер потерян');
            
            // Скрываем кнопки управления анимацией
            const controls = document.getElementById('animation-controls');
            if (controls) {{
                controls.style.display = 'none';
            }}
            
            // Скрываем элементы анимации
            document.getElementById('left-eye-blink').setAttribute('visible', 'false');
            document.getElementById('right-eye-blink').setAttribute('visible', 'false');
            document.getElementById('mouth').setAttribute('visible', 'false');
        }});
        
        // Обработка окончания анимации
        if (window.blinkAnimation) {{
            window.blinkAnimation.finished.then(() => {{
                isAnimationPlaying = false;
                document.getElementById('left-eye-blink').setAttribute('visible', 'false');
                document.getElementById('right-eye-blink').setAttribute('visible', 'false');
            }});
        }}
        
        if (window.smileAnimation) {{
            window.smileAnimation.finished.then(() => {{
                isAnimationPlaying = false;
                document.getElementById('mouth').setAttribute('visible', 'false');
            }});
        }}
        
        if (window.winkAnimation) {{
            window.winkAnimation.finished.then(() => {{
                isAnimationPlaying = false;
                document.getElementById('right-eye-blink').setAttribute('visible', 'false');
            }});
        }}
        
        // Автостарт на десктопах
        window.onload = function() {{
            if (!/Android|iPhone|iPad/i.test(navigator.userAgent)) {{
                updateStatus('Ожидание загрузки...');
            }} else {{
                updateStatus('Наведите камеру на портрет');
            }}
        }};
    </script>
</body>
</html>
        """
    else:
        # Возвращаем HTML для обычного видео-AR
        html = f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>AR Content - {content_id}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <script src="https://aframe.io/releases/1.4.2/aframe.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/ar.js@3.4.2/aframe/build/aframe-ar-nft.js"></script>
    <style>
      body {{
        margin: 0;
        overflow: hidden;
      }}
      #start-btn {{
        position: fixed;
        top: 10px;
        left: 10px;
        z-index: 100;
        padding: 10px 16px;
        font-size: 14px;
        border: none;
        border-radius: 4px;
        background-color: rgba(0, 0, 0.7);
        color: #ffffff;
        cursor: pointer;
      }}
      #view-count {{
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 100;
        padding: 10px 16px;
        font-size: 14px;
        border: none;
        border-radius: 4px;
        background-color: rgba(0, 0, 0, 0.7);
        color: #ffffff;
      }}
    </style>
  </head>
  <body>
    <button id="start-btn" onclick="startVideo()">Start Video</button>
    <div id="view-count">Views: {content_views.increment_view(content_id)}</div>
    <a-scene
      vr-mode-ui="enabled: false"
      embedded
      arjs="trackingMethod: best; sourceType: webcam; debugUIEnabled: false;"
    >
      <a-nft
        type="nft"
        url="/ar/markers/{content_id}"
        smooth="true"
        smoothCount="10"
        smoothTolerance="0.01"
        smoothThreshold="5"
      >
        <a-video
          id="video-content"
          src="#myvideo"
          width="1.5"
          height="1"
          position="0 0 0"
          rotation="-90 0 0"
        ></a-video>
      </a-nft>
      <a-assets>
        <video
          id="myvideo"
          src="/ar/video/{content_id}"
          preload="auto"
          crossorigin="anonymous"
          webkit-playsinline
          playsinline
          muted
          loop="false"
        ></video>
      </a-assets>
      <a-entity camera></a-entity>
    </a-scene>
    <script>
      function startVideo() {{
        const vid = document.getElementById('myvideo');
        if (!vid) return;
        const playPromise = vid.play();
        if (playPromise && typeof playPromise.then === 'function') {{
          playPromise.catch((error) => console.warn('Autoplay prevented:', error));
        }}
      }}
      window.onload = function () {{
        if (!/Android|iPhone|iPad/i.test(navigator.userAgent)) {{
          startVideo();
        }}
      }};
    </script>
  </body>
</html>
        """
    
    return HTMLResponse(content=html)


@app.get("/ar/image/{content_id}", tags=["ar"])
async def get_ar_image(content_id: str) -> FileResponse:
    """Get AR content image."""
    content = database.get_ar_content(content_id)
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AR content not found")
    
    image_path = Path(content["image_path"])
    if not image_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image file not found")
    
    return FileResponse(image_path)


@app.get("/ar/video/{content_id}", tags=["ar"])
async def get_ar_video(content_id: str) -> FileResponse:
    """Get AR content video."""
    content = database.get_ar_content(content_id)
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AR content not found")
    
    video_path = Path(content["video_path"])
    if not video_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video file not found")
    
    return FileResponse(video_path, media_type="video/mp4")


@app.get("/ar/markers/{content_id}.{marker_type}", tags=["ar"])
async def get_ar_marker(content_id: str, marker_type: str) -> FileResponse:
    """Get AR marker files (fset, fset3, iset)."""
    if marker_type not in ["fset", "fset3", "iset"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid marker type")
    
    content = database.get_ar_content(content_id)
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AR content not found")
    
    marker_path = Path(content[f"marker_{marker_type}"])
    if not marker_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Marker file not found")
    
    return FileResponse(marker_path)


@app.get("/ar/qr/{content_id}", tags=["ar"])
async def get_qr_code(content_id: str) -> Dict[str, Any]:
    """Get QR code for AR content."""
    content = database.get_ar_content(content_id)
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AR content not found")
    
    return {
        "content_id": content_id,
        "ar_url": content["ar_url"],
        "qr_code_base64": content["qr_code"],
    }


@app.post("/nft-marker/analyze", tags=["nft-marker"])
async def analyze_nft_marker_image(
    image: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """Analyze image for NFT marker suitability."""
    import tempfile
    
    temp_dir = Path(tempfile.mkdtemp())
    try:
        image_path = temp_dir / image.filename
        content = await image.read()
        image_path.write_bytes(content)
        
        from nft_marker_generator import NFTMarkerGenerator
        nft_generator = NFTMarkerGenerator(STORAGE_ROOT)
        analysis = nft_generator.analyze_image(image_path)
        return analysis
        
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.post("/nft-marker/generate", tags=["nft-marker"])
async def generate_nft_marker(
    image: UploadFile = File(...),
    marker_name: str = "",
    config: str = "{}",
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """Generate NFT marker files from an image."""
    import tempfile
    import json
    
    if not marker_name or marker_name.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Marker name is required"
        )
    
    temp_dir = Path(tempfile.mkdtemp())
    try:
        image_path = temp_dir / image.filename
        content = await image.read()
        image_path.write_bytes(content)
        
        from nft_marker_generator import NFTMarkerConfig, NFTMarkerGenerator
        nft_generator = NFTMarkerGenerator(STORAGE_ROOT)
        config_dict = json.loads(config) if config else {}
        marker_config = NFTMarkerConfig(
            min_dpi=config_dict.get("min_dpi", 72),
            max_dpi=config_dict.get("max_dpi", 300),
            levels=config_dict.get("levels", 3),
            feature_density=config_dict.get("feature_density", "medium")
        )
        
        marker = nft_generator.generate_marker(
            str(image_path),
            marker_name.strip(),
            marker_config
        )
        
        return {
            "name": marker_name.strip(),
            "width": marker.width,
            "height": marker.height,
            "dpi": marker.dpi,
            "fset_path": marker.fset_path,
            "fset3_path": marker.fset3_path,
            "iset_path": marker.iset_path,
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.get("/nft-marker/list", tags=["nft-marker"])
async def list_nft_markers(
    current_user: str = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List all generated NFT markers."""
    markers = []
    markers_dir = STORAGE_ROOT / "nft-markers"
    
    if markers_dir.exists():
        from nft_marker_generator import NFTMarkerGenerator
        nft_generator = NFTMarkerGenerator(STORAGE_ROOT)
        for marker_dir in markers_dir.iterdir():
            if marker_dir.is_dir():
                marker_info = nft_generator.get_marker_info(marker_dir.name)
                if marker_info:
                    markers.append(marker_info)
    
    return markers


# Добавляем новые эндпоинты для админ-панели

class StorageInfoResponse(BaseModel):
    disk_total: str
    disk_used: str
    disk_free: str
    disk_used_percent: float
    storage_total_size: str
    storage_file_count: int
    storage_path: str


class SystemInfoResponse(BaseModel):
    disk_info: Dict[str, Any]
    storage_info: Dict[str, Any]


@app.get("/admin/system-info", response_model=SystemInfoResponse, tags=["admin"])
async def get_system_info(username: str = Depends(require_admin)) -> SystemInfoResponse:
    """Получить информацию о системных ресурсах"""
    disk_info = get_disk_usage()
    storage_info = get_storage_usage()
    
    return SystemInfoResponse(
        disk_info={
            "total": format_bytes(disk_info["total"]),
            "used": format_bytes(disk_info["used"]),
            "free": format_bytes(disk_info["free"]),
            "used_percent": disk_info["used_percent"]
        },
        storage_info={
            "total_size": storage_info["formatted_size"],
            "file_count": storage_info["file_count"],
            "path": "storage/"
        }
    )


@app.get("/admin/storage-info", response_model=StorageInfoResponse, tags=["admin"])
async def get_storage_info(username: str = Depends(require_admin)) -> StorageInfoResponse:
    """Получить информацию о занятом и свободном дисковом пространстве"""
    disk_info = get_disk_usage()
    storage_info = get_storage_usage()
    
    return StorageInfoResponse(
        disk_total=format_bytes(disk_info["total"]),
        disk_used=format_bytes(disk_info["used"]),
        disk_free=format_bytes(disk_info["free"]),
        disk_used_percent=disk_info["used_percent"],
        storage_total_size=storage_info["formatted_size"],
        storage_file_count=storage_info["file_count"],
        storage_path="storage/"
    )


# Добавляем счётчик просмотров AR-контента
class ARContentView:
    def __init__(self):
        self._views = {}
        self._lock = threading.Lock()
    
    def increment_view(self, content_id: str) -> int:
        with self._lock:
            if content_id not in self._views:
                self._views[content_id] = 0
            self._views[content_id] += 1
            return self._views[content_id]
    
    def get_views(self, content_id: str) -> int:
        with self._lock:
            return self._views.get(content_id, 0)
    
    def get_all_views(self) -> Dict[str, int]:
        with self._lock:
            return self._views.copy()


# Создаем глобальный экземпляр счётчика просмотров
content_views = ARContentView()


# Удалено - дублированный эндпоинт выше уже обрабатывает это


# Добавляем эндпоинт для получения статистики просмотров
@app.get("/admin/content-stats", tags=["admin"])
async def get_content_stats(username: str = Depends(require_admin)) -> List[Dict[str, Any]]:
    """Получить статистику просмотров и кликов для всего контента"""
    content_list = database.list_ar_content()
    
    stats = []
    for content in content_list:
        stats.append({
            "id": content["id"],
            "title": content["id"],  # В реальном приложении можно добавить поле title
            "views": content.get("view_count", 0),
            "clicks": content.get("click_count", 0),
            "created_at": content["created_at"],
            "ar_url": content["ar_url"]
        })
    
    # Сортируем по количеству просмотров (по убыванию)
    stats.sort(key=lambda x: x["views"], reverse=True)
    return stats


@app.post("/ar/{content_id}/click", tags=["ar"])
async def track_click(content_id: str) -> Dict[str, Any]:
    """Отследить клик по ссылке AR контента (публичный доступ)"""
    content = database.get_ar_content(content_id)
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AR content not found")
    
    database.increment_click_count(content_id)
    return {"status": "success", "content_id": content_id}


@app.delete("/ar/{content_id}", tags=["ar"])
async def delete_ar_content(content_id: str, username: str = Depends(require_admin)) -> Dict[str, str]:
    """Удалить AR контент (только для администраторов)"""
    content = database.get_ar_content(content_id)
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AR content not found")
    
    # Удаляем файлы из хранилища
    try:
        image_path = Path(content["image_path"])
        if image_path.exists():
            # Удаляем всю директорию с контентом
            content_dir = image_path.parent
            if content_dir.exists():
                shutil.rmtree(content_dir)
                logger.info(f"Удалена директория с контентом: {content_dir}")
    except Exception as e:
        logger.error(f"Ошибка при удалении файлов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении файлов: {str(e)}"
        )
    
    # Удаляем запись из базы данных
    if database.delete_ar_content(content_id):
        logger.info(f"AR контент {content_id} успешно удален")
        return {"status": "success", "message": f"AR content {content_id} deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось удалить контент из базы данных"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)