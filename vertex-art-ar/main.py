"""
Simplified AR Backend for Vertex-Art-AR - Focus on core AR functionality
Based on Stogram approach: No blockchain, no IPFS, no NFT - just image + video AR content
"""
from __future__ import annotations

import secrets
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
import uuid
import qrcode
from io import BytesIO
import base64
import tempfile
import logging
from typing import List

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
                    marker_fset TEXT NOT NULL,
                    marker_fset3 TEXT NOT NULL,
                    marker_iset TEXT NOT NULL,
                    ar_url TEXT NOT NULL,
                    qr_code TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(username) REFERENCES users(username)
                )
                """
            )
    
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
    ) -> Dict[str, Any]:
        self._execute(
            """
            INSERT INTO ar_content (
                id, username, image_path, video_path,
                marker_fset, marker_fset3, marker_iset,
                ar_url, qr_code
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (content_id, username, image_path, video_path,
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
    title="Vertex Art AR - Simplified",
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
templates = Jinja2Templates(directory="templates")


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
    return {"Hello": "Vertex Art AR (Simplified)"}


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
    
    # Сохраняем изображение
    image_path = content_dir / f"{content_id}.jpg"
    with open(image_path, "wb") as f:
        f.write(await image.read())
    
    # Сохраняем видео
    video_path = content_dir / f"{content_id}.mp4"
    with open(video_path, "wb") as f:
        f.write(await video.read())
    
    # Генерируем QR-код
    ar_url = f"http://localhost:8000/ar/{content_id}"
    qr_img = qrcode.make(ar_url)
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode()
    
    # Создаем директорию для маркеров
    markers_dir = STORAGE_ROOT / "nft-markers" / content_id
    markers_dir.mkdir(parents=True, exist_ok=True)
    
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
async def view_ar_content(content_id: str) -> HTMLResponse:
    """View AR content page (public access)."""
    content = database.get_ar_content(content_id)
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AR content not found")
    
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
        background-color: rgba(0, 0, 0, 0.7);
        color: #ffffff;
        cursor: pointer;
      }}
    </style>
  </head>
  <body>
    <button id="start-btn" onclick="startVideo()">Start Video</button>
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
    disk_info: Dict[str, any]
    storage_info: Dict[str, any]


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


# Модифицируем существующий эндпоинт AR-страницы, чтобы добавить счётчик просмотров
@app.get("/ar/{content_id}", response_class=HTMLResponse, tags=["ar"])
async def view_ar_content(content_id: str) -> HTMLResponse:
    """View AR content page (public access)."""
    content = database.get_ar_content(content_id)
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AR content not found")
    
    # Увеличиваем счётчик просмотров
    view_count = content_views.increment_view(content_id)
    logger.info(f"AR content {content_id} viewed. Total views: {view_count}")
    
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
        background-color: rgba(0, 0, 0, 0.7);
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
    <div id="view-count">Views: {view_count}</div>
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


# Добавляем эндпоинт для получения статистики просмотров
@app.get("/admin/content-stats", tags=["admin"])
async def get_content_stats(username: str = Depends(require_admin)) -> List[Dict[str, any]]:
    """Получить статистику просмотров для всего контента"""
    all_views = content_views.get_all_views()
    content_list = database.list_ar_content()
    
    stats = []
    for content in content_list:
        content_id = content["id"]
        view_count = all_views.get(content_id, 0)
        stats.append({
            "id": content_id,
            "title": content_id,  # В реальном приложении можно добавить поле title
            "views": view_count,
            "created_at": content["created_at"]
        })
    
    # Сортируем по количеству просмотров (по убыванию)
    stats.sort(key=lambda x: x["views"], reverse=True)
    return stats


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)