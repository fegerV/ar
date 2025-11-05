"""
Simplified AR Backend for Vertex-AR - Focus on core AR functionality
Based on Stogram approach: No blockchain, no IPFS, no NFT - just image + video AR content
"""
from __future__ import annotations

import base64
import os
import secrets
import shutil
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import qrcode
import sentry_sdk
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from logging_setup import get_logger
from utils import format_bytes, get_disk_usage, get_storage_usage

load_dotenv()

logger = get_logger(__name__)

SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        environment=os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development")),
    )
    logger.info("Sentry initialized", environment=os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development")))

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app_data.db"
STORAGE_ROOT = BASE_DIR / "storage"
STATIC_ROOT = BASE_DIR / "static"
STATIC_ROOT.mkdir(parents=True, exist_ok=True)

# Get base URL from environment or use default
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
AUTH_MAX_ATTEMPTS = int(os.getenv("AUTH_MAX_ATTEMPTS", "5"))
AUTH_LOCKOUT_MINUTES = int(os.getenv("AUTH_LOCKOUT_MINUTES", "15"))
RUNNING_TESTS = os.getenv("RUNNING_TESTS") == "1" or "PYTEST_CURRENT_TEST" in os.environ
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true" and not RUNNING_TESTS
GLOBAL_RATE_LIMIT = os.getenv("GLOBAL_RATE_LIMIT", "100/minute")
AUTH_RATE_LIMIT = os.getenv("AUTH_RATE_LIMIT", "5/minute")
UPLOAD_RATE_LIMIT = os.getenv("UPLOAD_RATE_LIMIT", "10/minute")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    headers_enabled=True,
    enabled=RATE_LIMIT_ENABLED,
)

@limiter.limit(GLOBAL_RATE_LIMIT)
def global_rate_limit_dependency(request: Request) -> None:
    """Global rate limit dependency applied to every request."""
    return None

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
            # Create new tables for clients, portraits and videos
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    id TEXT PRIMARY KEY,
                    phone TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS portraits (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    image_path TEXT NOT NULL,
                    image_preview_path TEXT,
                    marker_fset TEXT NOT NULL,
                    marker_fset3 TEXT NOT NULL,
                    marker_iset TEXT NOT NULL,
                    permanent_link TEXT NOT NULL UNIQUE,
                    qr_code TEXT,
                    view_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS videos (
                    id TEXT PRIMARY KEY,
                    portrait_id TEXT NOT NULL,
                    video_path TEXT NOT NULL,
                    video_preview_path TEXT,
                    is_active INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(portrait_id) REFERENCES portraits(id) ON DELETE CASCADE
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
            # Create index for phone search
            try:
                self._connection.execute("CREATE INDEX IF NOT EXISTS idx_clients_phone ON clients(phone)")
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
    
    # Client methods
    def create_client(self, client_id: str, phone: str, name: str) -> Dict[str, Any]:
        """Создать нового клиента."""
        self._execute(
            "INSERT INTO clients (id, phone, name) VALUES (?, ?, ?)",
            (client_id, phone, name),
        )
        return self.get_client(client_id)
    
    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Получить клиента по ID."""
        cursor = self._execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    
    def get_client_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Получить клиента по номеру телефона."""
        cursor = self._execute("SELECT * FROM clients WHERE phone = ?", (phone,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    
    def search_clients(self, phone: str) -> List[Dict[str, Any]]:
        """Поиск клиентов по телефону (частичное совпадение)."""
        cursor = self._execute(
            "SELECT * FROM clients WHERE phone LIKE ? ORDER BY created_at DESC",
            (f"%{phone}%",),
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def list_clients(self) -> List[Dict[str, Any]]:
        """Получить список всех клиентов."""
        cursor = self._execute("SELECT * FROM clients ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]
    
    def update_client(self, client_id: str, phone: Optional[str] = None, name: Optional[str] = None) -> bool:
        """Обновить данные клиента."""
        updates = []
        params = []
        if phone is not None:
            updates.append("phone = ?")
            params.append(phone)
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if not updates:
            return False
        
        params.append(client_id)
        query = f"UPDATE clients SET {', '.join(updates)} WHERE id = ?"
        cursor = self._execute(query, tuple(params))
        return cursor.rowcount > 0
    
    def delete_client(self, client_id: str) -> bool:
        """Удалить клиента."""
        cursor = self._execute("DELETE FROM clients WHERE id = ?", (client_id,))
        return cursor.rowcount > 0
    
    # Portrait methods
    def create_portrait(
        self,
        portrait_id: str,
        client_id: str,
        image_path: str,
        marker_fset: str,
        marker_fset3: str,
        marker_iset: str,
        permanent_link: str,
        qr_code: Optional[str] = None,
        image_preview_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Создать новый портрет."""
        self._execute(
            """
            INSERT INTO portraits (
                id, client_id, image_path, image_preview_path,
                marker_fset, marker_fset3, marker_iset,
                permanent_link, qr_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (portrait_id, client_id, image_path, image_preview_path,
             marker_fset, marker_fset3, marker_iset, permanent_link, qr_code),
        )
        return self.get_portrait(portrait_id)
    
    def get_portrait(self, portrait_id: str) -> Optional[Dict[str, Any]]:
        """Получить портрет по ID."""
        cursor = self._execute("SELECT * FROM portraits WHERE id = ?", (portrait_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    
    def get_portrait_by_link(self, permanent_link: str) -> Optional[Dict[str, Any]]:
        """Получить портрет по постоянной ссылке."""
        cursor = self._execute("SELECT * FROM portraits WHERE permanent_link = ?", (permanent_link,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    
    def list_portraits(self, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Получить список портретов."""
        if client_id:
            cursor = self._execute(
                "SELECT * FROM portraits WHERE client_id = ? ORDER BY created_at DESC",
                (client_id,),
            )
        else:
            cursor = self._execute("SELECT * FROM portraits ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]
    
    def increment_portrait_views(self, portrait_id: str) -> None:
        """Увеличить счетчик просмотров портрета."""
        self._execute(
            "UPDATE portraits SET view_count = view_count + 1 WHERE id = ?",
            (portrait_id,),
        )
    
    def delete_portrait(self, portrait_id: str) -> bool:
        """Удалить портрет."""
        cursor = self._execute("DELETE FROM portraits WHERE id = ?", (portrait_id,))
        return cursor.rowcount > 0
    
    # Video methods
    def create_video(
        self,
        video_id: str,
        portrait_id: str,
        video_path: str,
        is_active: bool = False,
        video_preview_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Создать новое видео."""
        self._execute(
            """
            INSERT INTO videos (
                id, portrait_id, video_path, video_preview_path, is_active
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (video_id, portrait_id, video_path, video_preview_path, int(is_active)),
        )
        return self.get_video(video_id)
    
    def get_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Получить видео по ID."""
        cursor = self._execute("SELECT * FROM videos WHERE id = ?", (video_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    
    def get_active_video(self, portrait_id: str) -> Optional[Dict[str, Any]]:
        """Получить активное видео для портрета."""
        cursor = self._execute(
            "SELECT * FROM videos WHERE portrait_id = ? AND is_active = 1 LIMIT 1",
            (portrait_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    
    def list_videos(self, portrait_id: str) -> List[Dict[str, Any]]:
        """Получить список видео для портрета."""
        cursor = self._execute(
            "SELECT * FROM videos WHERE portrait_id = ? ORDER BY created_at DESC",
            (portrait_id,),
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def set_active_video(self, video_id: str, portrait_id: str) -> bool:
        """Установить активное видео для портрета."""
        with self._lock:
            # Деактивируем все видео для данного портрета
            self._connection.execute(
                "UPDATE videos SET is_active = 0 WHERE portrait_id = ?",
                (portrait_id,),
            )
            # Активируем выбранное видео
            cursor = self._connection.execute(
                "UPDATE videos SET is_active = 1 WHERE id = ?",
                (video_id,),
            )
            self._connection.commit()
            return cursor.rowcount > 0
    
    def delete_video(self, video_id: str) -> bool:
        """Удалить видео."""
        cursor = self._execute("DELETE FROM videos WHERE id = ?", (video_id,))
        return cursor.rowcount > 0


def _hash_password(password: str) -> str:
    """Simple password hashing (use proper hashing in production)."""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


def _verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return _hash_password(password) == hashed


@dataclass
class SessionData:
    username: str
    issued_at: datetime
    last_seen: datetime


class TokenManager:
    """Manage issued access tokens with session timeouts."""

    def __init__(self, session_timeout_minutes: int = SESSION_TIMEOUT_MINUTES) -> None:
        self._tokens: Dict[str, SessionData] = {}
        self._lock = threading.Lock()
        self._session_timeout = timedelta(minutes=session_timeout_minutes)

    def issue_token(self, username: str) -> str:
        token = secrets.token_urlsafe(32)
        session = SessionData(
            username=username,
            issued_at=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )
        with self._lock:
            self._tokens[token] = session
        return token

    def verify_token(self, token: str) -> Optional[str]:
        with self._lock:
            session = self._tokens.get(token)
            if session is None:
                return None

            if self._session_timeout.total_seconds() > 0:
                now = datetime.utcnow()
                if now - session.last_seen > self._session_timeout:
                    self._tokens.pop(token, None)
                    logger.info("Session expired", username=session.username)
                    return None
                session.last_seen = now

            return session.username

    def revoke_token(self, token: str) -> None:
        with self._lock:
            self._tokens.pop(token, None)

    def revoke_user(self, username: str) -> None:
        with self._lock:
            tokens_to_remove = [token for token, session in self._tokens.items() if session.username == username]
            for token in tokens_to_remove:
                self._tokens.pop(token, None)


class AuthSecurityManager:
    """Track authentication attempts and enforce temporary lockouts."""

    def __init__(self, max_attempts: int = AUTH_MAX_ATTEMPTS, lockout_minutes: int = AUTH_LOCKOUT_MINUTES) -> None:
        self._max_attempts = max_attempts
        self._lockout_duration = timedelta(minutes=lockout_minutes)
        self._failed_attempts: Dict[str, int] = {}
        self._lockouts: Dict[str, datetime] = {}
        self._lock = threading.Lock()

    def is_locked(self, username: str) -> Optional[datetime]:
        with self._lock:
            locked_until = self._lockouts.get(username)
            if locked_until and locked_until > datetime.utcnow():
                return locked_until
            if locked_until:
                # Lock has expired, clean up state
                self._lockouts.pop(username, None)
            return None

    def register_failure(self, username: str) -> Optional[datetime]:
        with self._lock:
            now = datetime.utcnow()
            locked_until = self._lockouts.get(username)
            if locked_until and locked_until > now:
                return locked_until
            if locked_until:
                self._lockouts.pop(username, None)

            attempts = self._failed_attempts.get(username, 0) + 1
            if attempts >= self._max_attempts:
                locked_until = now + self._lockout_duration
                self._lockouts[username] = locked_until
                self._failed_attempts[username] = 0
                logger.warning(
                    "User locked due to repeated failed login attempts",
                    username=username,
                    locked_until=locked_until.isoformat(),
                )
                return locked_until

            self._failed_attempts[username] = attempts
            return None

    def reset(self, username: str) -> None:
        with self._lock:
            self._failed_attempts.pop(username, None)
            self._lockouts.pop(username, None)


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


class ClientCreate(BaseModel):
    phone: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=150)


class ClientUpdate(BaseModel):
    phone: Optional[str] = Field(None, min_length=1, max_length=20)
    name: Optional[str] = Field(None, min_length=1, max_length=150)


class ClientResponse(BaseModel):
    id: str
    phone: str
    name: str
    created_at: str


class OrderCreate(BaseModel):
    phone: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=150)


class PortraitResponse(BaseModel):
    id: str
    client_id: str
    permanent_link: str
    qr_code_base64: Optional[str]
    image_path: str
    view_count: int
    created_at: str


class VideoResponse(BaseModel):
    id: str
    portrait_id: str
    video_path: str
    is_active: bool
    created_at: str


class OrderResponse(BaseModel):
    client: ClientResponse
    portrait: PortraitResponse
    video: VideoResponse


app = FastAPI(
    title="Vertex AR - Simplified",
    version=VERSION,
    description="A lightweight AR backend for creating augmented reality experiences from image + video pairs",
    dependencies=[Depends(global_rate_limit_dependency)],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

Instrumentator().instrument(app).expose(app)

# CORS configuration from environment
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
logger.info("CORS configured", origins=CORS_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_ROOT)), name="static")
app.mount("/storage", StaticFiles(directory=str(STORAGE_ROOT)), name="storage")

security = HTTPBearer()
database = Database(DB_PATH)
tokens = TokenManager(session_timeout_minutes=SESSION_TIMEOUT_MINUTES)
auth_security = AuthSecurityManager(max_attempts=AUTH_MAX_ATTEMPTS, lockout_minutes=AUTH_LOCKOUT_MINUTES)

# Монтируем шаблоны
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    username = tokens.verify_token(credentials.credentials)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or invalid")
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


@app.get("/admin/orders", response_class=HTMLResponse, tags=["admin"])
async def admin_orders_panel(request: Request) -> HTMLResponse:
    """Serve new admin panel for orders management."""
    return templates.TemplateResponse("admin_orders.html", {"request": request})


@app.post("/auth/register", status_code=status.HTTP_201_CREATED, tags=["auth"])
@limiter.limit(AUTH_RATE_LIMIT)
async def register_user(request: Request, user: UserCreate) -> Dict[str, str]:
    existing = database.get_user(user.username)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
    try:
        database.create_user(user.username, _hash_password(user.password), is_admin=True)  # Создаем администратора
        logger.info("Admin user registered", username=user.username)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
    return {"username": user.username}


@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
@limiter.limit(AUTH_RATE_LIMIT)
async def login_user(request: Request, credentials: UserLogin) -> TokenResponse:
    locked_until = auth_security.is_locked(credentials.username)
    if locked_until:
        logger.warning(
            "Attempt to access locked account",
            username=credentials.username,
            locked_until=locked_until.isoformat(),
        )
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked until {locked_until.isoformat()}",
        )

    user = database.get_user(credentials.username)
    if user is None or not _verify_password(credentials.password, user["hashed_password"]):
        locked_until = auth_security.register_failure(credentials.username)
        if locked_until:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account locked due to multiple failed attempts",
            )
        logger.warning("Invalid login attempt", username=credentials.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    auth_security.reset(credentials.username)
    token = tokens.issue_token(credentials.username)
    logger.info("User authenticated", username=credentials.username)
    return TokenResponse(access_token=token)


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
@limiter.limit(AUTH_RATE_LIMIT)
async def logout_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Response:
    username = tokens.verify_token(credentials.credentials)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or invalid")
    tokens.revoke_token(credentials.credentials)
    logger.info("User logged out", username=username)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/ar/upload", response_model=ARContentResponse, tags=["ar"])
@limiter.limit(UPLOAD_RATE_LIMIT)
async def upload_ar_content(
    request: Request,
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


# Orders API - создание и управление заказами

@app.post("/orders/create", response_model=OrderResponse, tags=["orders"])
async def create_order(
    phone: str = Form(...),
    name: str = Form(...),
    image: UploadFile = File(...),
    video: UploadFile = File(...),
    username: str = Depends(require_admin),
) -> OrderResponse:
    """
    Создать новый заказ: клиент + портрет + видео.
    Генерируется постоянная ссылка для портрета.
    """
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file")
    
    if not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid video file")
    
    # Проверяем существование клиента по телефону
    client = database.get_client_by_phone(phone)
    if not client:
        # Создаем нового клиента
        client_id = str(uuid.uuid4())
        client = database.create_client(client_id, phone, name)
    
    # Генерируем ID для портрета и видео
    portrait_id = str(uuid.uuid4())
    video_id = str(uuid.uuid4())
    
    # Создаем директорию для хранения файлов
    client_storage = STORAGE_ROOT / "clients" / client["id"]
    portrait_dir = client_storage / portrait_id
    portrait_dir.mkdir(parents=True, exist_ok=True)
    
    # Читаем содержимое файлов
    image.file.seek(0)
    image_content = await image.read()
    video.file.seek(0)
    video_content = await video.read()
    
    # Сохраняем изображение
    image_path = portrait_dir / f"{portrait_id}.jpg"
    with open(image_path, "wb") as f:
        f.write(image_content)
    
    # Сохраняем видео
    video_path = portrait_dir / f"{video_id}.mp4"
    with open(video_path, "wb") as f:
        f.write(video_content)
    
    # Генерируем превью
    from preview_generator import PreviewGenerator
    image_preview_path = None
    video_preview_path = None
    
    try:
        image_preview = PreviewGenerator.generate_image_preview(image_content)
        if image_preview:
            image_preview_path = portrait_dir / f"{portrait_id}_preview.jpg"
            with open(image_preview_path, "wb") as f:
                f.write(image_preview)
    except Exception as e:
        logger.error(f"Ошибка при генерации превью изображения: {e}")
    
    try:
        video_preview = PreviewGenerator.generate_video_preview(video_content)
        if video_preview:
            video_preview_path = portrait_dir / f"{video_id}_preview.jpg"
            with open(video_preview_path, "wb") as f:
                f.write(video_preview)
    except Exception as e:
        logger.error(f"Ошибка при генерации превью видео: {e}")
    
    # Генерируем NFT-маркеры
    from nft_marker_generator import NFTMarkerConfig, NFTMarkerGenerator
    nft_generator = NFTMarkerGenerator(STORAGE_ROOT)
    config = NFTMarkerConfig(feature_density="high", levels=3)
    marker_result = nft_generator.generate_marker(str(image_path), portrait_id, config)
    
    # Генерируем постоянную ссылку
    permanent_link = f"{BASE_URL}/portrait/{portrait_id}"
    
    # Генерируем QR-код
    qr_img = qrcode.make(permanent_link)
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode()
    
    # Создаем портрет
    portrait = database.create_portrait(
        portrait_id=portrait_id,
        client_id=client["id"],
        image_path=str(image_path),
        marker_fset=marker_result.fset_path,
        marker_fset3=marker_result.fset3_path,
        marker_iset=marker_result.iset_path,
        permanent_link=permanent_link,
        qr_code=qr_base64,
        image_preview_path=str(image_preview_path) if image_preview_path else None,
    )
    
    # Создаем видео (первое видео всегда активно)
    video_record = database.create_video(
        video_id=video_id,
        portrait_id=portrait_id,
        video_path=str(video_path),
        is_active=True,
        video_preview_path=str(video_preview_path) if video_preview_path else None,
    )
    
    # Отправляем Telegram уведомление если настроено
    try:
        await send_telegram_notification(
            f"📸 Новый заказ создан!\n"
            f"Клиент: {client['name']}\n"
            f"Телефон: {client['phone']}\n"
            f"Ссылка: {permanent_link}"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке Telegram уведомления: {e}")
    
    return OrderResponse(
        client=ClientResponse(
            id=client["id"],
            phone=client["phone"],
            name=client["name"],
            created_at=client["created_at"],
        ),
        portrait=PortraitResponse(
            id=portrait["id"],
            client_id=portrait["client_id"],
            permanent_link=portrait["permanent_link"],
            qr_code_base64=qr_base64,
            image_path=str(image_path),
            view_count=portrait["view_count"],
            created_at=portrait["created_at"],
        ),
        video=VideoResponse(
            id=video_record["id"],
            portrait_id=video_record["portrait_id"],
            video_path=str(video_path),
            is_active=bool(video_record["is_active"]),
            created_at=video_record["created_at"],
        ),
    )


# Clients API

@app.get("/clients/search", response_model=List[ClientResponse], tags=["clients"])
async def search_clients_by_phone(
    phone: str,
    username: str = Depends(require_admin),
) -> List[ClientResponse]:
    """Поиск клиентов по номеру телефона."""
    clients = database.search_clients(phone)
    return [
        ClientResponse(
            id=c["id"],
            phone=c["phone"],
            name=c["name"],
            created_at=c["created_at"],
        )
        for c in clients
    ]


@app.get("/clients/list", response_model=List[ClientResponse], tags=["clients"])
async def list_clients(
    username: str = Depends(require_admin),
) -> List[ClientResponse]:
    """Получить список всех клиентов."""
    clients = database.list_clients()
    return [
        ClientResponse(
            id=c["id"],
            phone=c["phone"],
            name=c["name"],
            created_at=c["created_at"],
        )
        for c in clients
    ]


@app.get("/clients/{client_id}", response_model=ClientResponse, tags=["clients"])
async def get_client(
    client_id: str,
    username: str = Depends(require_admin),
) -> ClientResponse:
    """Получить информацию о клиенте."""
    client = database.get_client(client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    
    return ClientResponse(
        id=client["id"],
        phone=client["phone"],
        name=client["name"],
        created_at=client["created_at"],
    )


@app.put("/clients/{client_id}", response_model=ClientResponse, tags=["clients"])
async def update_client(
    client_id: str,
    update_data: ClientUpdate,
    username: str = Depends(require_admin),
) -> ClientResponse:
    """Обновить данные клиента."""
    client = database.get_client(client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    
    database.update_client(client_id, update_data.phone, update_data.name)
    updated_client = database.get_client(client_id)
    
    return ClientResponse(
        id=updated_client["id"],
        phone=updated_client["phone"],
        name=updated_client["name"],
        created_at=updated_client["created_at"],
    )


@app.delete("/clients/{client_id}", tags=["clients"])
async def delete_client(
    client_id: str,
    username: str = Depends(require_admin),
) -> Dict[str, str]:
    """Удалить клиента."""
    if not database.delete_client(client_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    
    return {"message": "Client deleted successfully"}


# Portraits API

@app.get("/portraits/list", response_model=List[PortraitResponse], tags=["portraits"])
async def list_portraits(
    client_id: Optional[str] = None,
    username: str = Depends(require_admin),
) -> List[PortraitResponse]:
    """Получить список портретов."""
    portraits = database.list_portraits(client_id)
    return [
        PortraitResponse(
            id=p["id"],
            client_id=p["client_id"],
            permanent_link=p["permanent_link"],
            qr_code_base64=p["qr_code"],
            image_path=p["image_path"],
            view_count=p["view_count"],
            created_at=p["created_at"],
        )
        for p in portraits
    ]


@app.get("/portrait/{portrait_id}", response_class=HTMLResponse, tags=["portraits"])
async def view_portrait(portrait_id: str) -> HTMLResponse:
    """
    Просмотр портрета по постоянной ссылке (публичный доступ).
    Отображается активное видео для данного портрета.
    """
    portrait = database.get_portrait(portrait_id)
    if not portrait:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portrait not found")
    
    # Получаем активное видео
    active_video = database.get_active_video(portrait_id)
    if not active_video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active video found for this portrait")
    
    # Увеличиваем счетчик просмотров
    database.increment_portrait_views(portrait_id)
    
    # Возвращаем HTML страницу с AR контентом
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no">
    <title>Vertex AR Portrait</title>
    <script src="https://aframe.io/releases/1.6.0/aframe.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/ar.js@3.4.2/aframe/build/aframe-ar-nft.js"></script>
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
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }}
        
        #info {{
            position: fixed;
            bottom: 10px;
            left: 10px;
            z-index: 100;
            color: white;
            background-color: rgba(0, 0, 0, 0.7);
            padding: 10px;
            border-radius: 5px;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <button id="start-btn">Start AR</button>
    <div id="info">Наведите камеру на портрет</div>
    
    <a-scene
        embedded
        arjs="sourceType: webcam; debugUIEnabled: false; detectionMode: mono_and_matrix; matrixCodeType: 3x3;"
        vr-mode-ui="enabled: false"
        renderer="logarithmicDepthBuffer: true; precision: medium; antialias: true; alpha: true"
        loading-screen="enabled: false">
        
        <a-assets>
            <video id="ar-video" src="/{active_video['video_path']}" preload="auto" loop crossorigin="anonymous" playsinline webkit-playsinline></video>
        </a-assets>
        
        <a-nft
            type="nft"
            url="/storage/nft-markers/{portrait_id}/{portrait_id}"
            smooth="true"
            smoothCount="10"
            smoothTolerance=".01"
            smoothThreshold="5">
            
            <a-video
                src="#ar-video"
                width="1"
                height="1"
                position="0 0.5 0"
                rotation="-90 0 0"
                play="true">
            </a-video>
        </a-nft>
        
        <a-entity camera></a-entity>
    </a-scene>
    
    <script>
        const video = document.getElementById('ar-video');
        const startBtn = document.getElementById('start-btn');
        
        startBtn.addEventListener('click', function() {{
            video.play();
            startBtn.style.display = 'none';
        }});
        
        // Auto-play when marker detected
        document.querySelector('a-scene').addEventListener('markerFound', function() {{
            video.play();
        }});
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.delete("/portraits/{portrait_id}", tags=["portraits"])
async def delete_portrait(
    portrait_id: str,
    username: str = Depends(require_admin),
) -> Dict[str, str]:
    """Удалить портрет."""
    if not database.delete_portrait(portrait_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portrait not found")
    
    return {"message": "Portrait deleted successfully"}


# Videos API

@app.post("/videos/add", response_model=VideoResponse, tags=["videos"])
async def add_video_to_portrait(
    portrait_id: str = Form(...),
    video: UploadFile = File(...),
    username: str = Depends(require_admin),
) -> VideoResponse:
    """Добавить новое видео к портрету."""
    if not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid video file")
    
    portrait = database.get_portrait(portrait_id)
    if not portrait:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portrait not found")
    
    # Генерируем ID для видео
    video_id = str(uuid.uuid4())
    
    # Получаем путь к директории портрета
    portrait_path = Path(portrait["image_path"]).parent
    
    # Сохраняем видео
    video.file.seek(0)
    video_content = await video.read()
    video_path = portrait_path / f"{video_id}.mp4"
    with open(video_path, "wb") as f:
        f.write(video_content)
    
    # Генерируем превью видео
    video_preview_path = None
    try:
        from preview_generator import PreviewGenerator
        video_preview = PreviewGenerator.generate_video_preview(video_content)
        if video_preview:
            video_preview_path = portrait_path / f"{video_id}_preview.jpg"
            with open(video_preview_path, "wb") as f:
                f.write(video_preview)
    except Exception as e:
        logger.error(f"Ошибка при генерации превью видео: {e}")
    
    # Создаем запись о видео (по умолчанию не активно)
    video_record = database.create_video(
        video_id=video_id,
        portrait_id=portrait_id,
        video_path=str(video_path),
        is_active=False,
        video_preview_path=str(video_preview_path) if video_preview_path else None,
    )
    
    return VideoResponse(
        id=video_record["id"],
        portrait_id=video_record["portrait_id"],
        video_path=str(video_path),
        is_active=bool(video_record["is_active"]),
        created_at=video_record["created_at"],
    )


@app.get("/videos/list/{portrait_id}", response_model=List[VideoResponse], tags=["videos"])
async def list_videos(
    portrait_id: str,
    username: str = Depends(require_admin),
) -> List[VideoResponse]:
    """Получить список видео для портрета."""
    videos = database.list_videos(portrait_id)
    return [
        VideoResponse(
            id=v["id"],
            portrait_id=v["portrait_id"],
            video_path=v["video_path"],
            is_active=bool(v["is_active"]),
            created_at=v["created_at"],
        )
        for v in videos
    ]


@app.put("/videos/{video_id}/activate", response_model=VideoResponse, tags=["videos"])
async def activate_video(
    video_id: str,
    username: str = Depends(require_admin),
) -> VideoResponse:
    """Сделать видео активным (деактивирует остальные видео портрета)."""
    video = database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    
    database.set_active_video(video_id, video["portrait_id"])
    
    # Отправляем Telegram уведомление
    try:
        portrait = database.get_portrait(video["portrait_id"])
        if portrait:
            client = database.get_client(portrait["client_id"])
            await send_telegram_notification(
                f"🎬 Видео изменено!\n"
                f"Клиент: {client['name']}\n"
                f"Портрет: {portrait['permanent_link']}\n"
                f"Новое активное видео: {video_id}"
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке Telegram уведомления: {e}")
    
    updated_video = database.get_video(video_id)
    return VideoResponse(
        id=updated_video["id"],
        portrait_id=updated_video["portrait_id"],
        video_path=updated_video["video_path"],
        is_active=bool(updated_video["is_active"]),
        created_at=updated_video["created_at"],
    )


@app.delete("/videos/{video_id}", tags=["videos"])
async def delete_video(
    video_id: str,
    username: str = Depends(require_admin),
) -> Dict[str, str]:
    """Удалить видео."""
    video = database.get_video(video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    
    # Проверяем, что это не последнее активное видео
    if video["is_active"]:
        videos = database.list_videos(video["portrait_id"])
        if len(videos) == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last active video"
            )
    
    if not database.delete_video(video_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    
    return {"message": "Video deleted successfully"}


# Telegram notification helper
async def send_telegram_notification(message: str):
    """Отправить уведомление в Telegram."""
    import aiohttp
    
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not telegram_bot_token or not telegram_chat_id:
        logger.warning("Telegram credentials not configured")
        return
    
    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": telegram_chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info("Telegram notification sent successfully")
                else:
                    logger.error(f"Failed to send Telegram notification: {response.status}")
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")


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


# ========================================
# NFT Marker Enhanced API Endpoints
# ========================================

class NFTBatchGenerateRequest(BaseModel):
    """Request for batch NFT marker generation."""
    images: List[Dict[str, str]]  # List of {image_path, marker_name}
    config: Optional[Dict[str, Any]] = None
    max_workers: int = Field(default=4, ge=1, le=8)


class NFTBatchGenerateResponse(BaseModel):
    """Response for batch generation."""
    results: Dict[str, Any]
    successful: int
    failed: int
    total_time: float


@app.post("/api/nft-markers/batch-generate", response_model=NFTBatchGenerateResponse, tags=["nft-markers"])
async def batch_generate_nft_markers(
    request: NFTBatchGenerateRequest,
    username: str = Depends(require_admin)
) -> NFTBatchGenerateResponse:
    """
    Generate NFT markers for multiple images in parallel.
    """
    from nft_marker_generator import NFTMarkerConfig, NFTMarkerGenerator
    
    nft_generator = NFTMarkerGenerator(STORAGE_ROOT)
    
    # Convert image list
    images = [(img['image_path'], img['marker_name']) for img in request.images]
    
    # Parse config if provided
    config = None
    if request.config:
        config = NFTMarkerConfig.from_dict(request.config)
    
    # Generate markers
    start_time = time.time()
    results = nft_generator.generate_markers_batch(
        images=images,
        config=config,
        max_workers=request.max_workers
    )
    elapsed = time.time() - start_time
    
    # Count successful/failed
    successful = sum(1 for r in results.values() if not isinstance(r, Exception))
    failed = len(results) - successful
    
    # Convert results for JSON
    json_results = {}
    for path, result in results.items():
        if isinstance(result, Exception):
            json_results[path] = {"error": str(result)}
        else:
            json_results[path] = {
                "fset_path": result.fset_path,
                "fset3_path": result.fset3_path,
                "iset_path": result.iset_path,
                "width": result.width,
                "height": result.height
            }
    
    return NFTBatchGenerateResponse(
        results=json_results,
        successful=successful,
        failed=failed,
        total_time=elapsed
    )


class NFTAnalysisResponse(BaseModel):
    """Response for image analysis."""
    valid: bool
    message: str
    width: Optional[int] = None
    height: Optional[int] = None
    brightness: Optional[float] = None
    contrast: Optional[float] = None
    quality: Optional[str] = None
    recommendation: Optional[str] = None
    cached: bool = False


@app.get("/api/nft-markers/analyze", response_model=NFTAnalysisResponse, tags=["nft-markers"])
async def analyze_image_for_nft(
    image_path: str,
    use_cache: bool = True,
    username: str = Depends(require_admin)
) -> NFTAnalysisResponse:
    """
    Analyze an image for NFT marker suitability with caching.
    """
    from nft_marker_generator import NFTMarkerGenerator
    
    nft_generator = NFTMarkerGenerator(STORAGE_ROOT)
    
    # Check cache first
    cached = False
    if use_cache and nft_generator.cache:
        from pathlib import Path
        img_path = Path(image_path)
        cached_result = nft_generator.cache.get(img_path)
        if cached_result:
            cached = True
            result = cached_result
        else:
            result = nft_generator.analyze_image(image_path, use_cache=use_cache)
    else:
        result = nft_generator.analyze_image(image_path, use_cache=use_cache)
    
    return NFTAnalysisResponse(
        **result,
        cached=cached
    )


class NFTPreviewResponse(BaseModel):
    """Response for feature preview."""
    preview_path: str
    analysis: Dict[str, Any]
    feature_count: int


@app.post("/api/nft-markers/preview", response_model=NFTPreviewResponse, tags=["nft-markers"])
async def generate_nft_preview(
    image_path: str,
    username: str = Depends(require_admin)
) -> NFTPreviewResponse:
    """
    Generate a preview image showing detected feature points.
    """
    from nft_marker_generator import NFTMarkerGenerator
    
    nft_generator = NFTMarkerGenerator(STORAGE_ROOT)
    
    try:
        preview_path, analysis = nft_generator.generate_feature_preview(image_path)
        
        return NFTPreviewResponse(
            preview_path=str(preview_path),
            analysis=analysis,
            feature_count=analysis.get('feature_count', 0)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate preview: {str(e)}"
        )


class NFTMetricsResponse(BaseModel):
    """Response for NFT generation metrics."""
    total_generated: int
    total_time: float
    avg_time_per_marker: float
    cache_hits: int
    cache_misses: int
    cache_hit_rate: Optional[float] = None


@app.get("/api/nft-markers/metrics", response_model=NFTMetricsResponse, tags=["nft-markers"])
async def get_nft_metrics(
    username: str = Depends(require_admin)
) -> NFTMetricsResponse:
    """
    Get NFT marker generation performance metrics.
    """
    from nft_marker_generator import NFTMarkerGenerator
    
    nft_generator = NFTMarkerGenerator(STORAGE_ROOT)
    metrics = nft_generator.get_metrics()
    
    return NFTMetricsResponse(**metrics)


class NFTCleanupRequest(BaseModel):
    """Request for marker cleanup."""
    dry_run: bool = True


class NFTCleanupResponse(BaseModel):
    """Response for cleanup operation."""
    total_markers: int
    used_markers: int
    unused_markers: int
    deleted_count: int
    freed_bytes: int
    dry_run: bool
    errors: List[Dict[str, str]]


@app.post("/api/nft-markers/cleanup", response_model=NFTCleanupResponse, tags=["nft-markers"])
async def cleanup_nft_markers(
    request: NFTCleanupRequest,
    username: str = Depends(require_admin)
) -> NFTCleanupResponse:
    """
    Clean up unused NFT markers.
    """
    from nft_marker_generator import NFTMarkerGenerator
    
    nft_generator = NFTMarkerGenerator(STORAGE_ROOT)
    
    # Get list of used markers from database
    all_content = database.list_ar_content()
    used_markers = set()
    
    for content in all_content:
        # Extract marker name from paths
        marker_fset = content.get('marker_fset', '')
        if marker_fset:
            # Extract marker name from path like "storage/nft_markers/marker_name/marker_name.fset"
            parts = marker_fset.split('/')
            if len(parts) >= 3:
                used_markers.add(parts[-2])
    
    result = nft_generator.cleanup_unused_markers(
        used_marker_names=list(used_markers),
        dry_run=request.dry_run
    )
    
    return NFTCleanupResponse(**result)


class NFTConfigPresetRequest(BaseModel):
    """Request to save a config preset."""
    preset_name: str
    config: Dict[str, Any]


class NFTConfigPresetResponse(BaseModel):
    """Response for config preset operations."""
    name: str
    preset_path: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


@app.get("/api/nft-markers/config-presets", response_model=List[NFTConfigPresetResponse], tags=["nft-markers"])
async def list_nft_config_presets(
    username: str = Depends(require_admin)
) -> List[NFTConfigPresetResponse]:
    """
    List all available NFT marker config presets.
    """
    from nft_marker_generator import NFTMarkerGenerator
    
    nft_generator = NFTMarkerGenerator(STORAGE_ROOT)
    presets = nft_generator.list_presets()
    
    return [
        NFTConfigPresetResponse(
            name=preset['name'],
            created_at=preset.get('created_at'),
            preset_path=preset.get('file_path')
        )
        for preset in presets
    ]


@app.post("/api/nft-markers/config-presets", response_model=NFTConfigPresetResponse, tags=["nft-markers"])
async def save_nft_config_preset(
    request: NFTConfigPresetRequest,
    username: str = Depends(require_admin)
) -> NFTConfigPresetResponse:
    """
    Save a new NFT marker config preset.
    """
    from nft_marker_generator import NFTMarkerConfig, NFTMarkerGenerator
    
    nft_generator = NFTMarkerGenerator(STORAGE_ROOT)
    
    try:
        config = NFTMarkerConfig.from_dict(request.config)
        preset_path = nft_generator.export_config(config, request.preset_name)
        
        return NFTConfigPresetResponse(
            name=request.preset_name,
            preset_path=str(preset_path),
            config=request.config
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save preset: {str(e)}"
        )


@app.get("/api/nft-markers/config-presets/{preset_name}", response_model=NFTConfigPresetResponse, tags=["nft-markers"])
async def get_nft_config_preset(
    preset_name: str,
    username: str = Depends(require_admin)
) -> NFTConfigPresetResponse:
    """
    Get a specific NFT marker config preset.
    """
    from nft_marker_generator import NFTMarkerGenerator
    
    nft_generator = NFTMarkerGenerator(STORAGE_ROOT)
    
    try:
        config = nft_generator.import_config(preset_name)
        
        return NFTConfigPresetResponse(
            name=preset_name,
            config=config.to_dict()
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preset '{preset_name}' not found"
        )


@app.delete("/api/nft-markers/config-presets/{preset_name}", tags=["nft-markers"])
async def delete_nft_config_preset(
    preset_name: str,
    username: str = Depends(require_admin)
) -> Dict[str, str]:
    """
    Delete an NFT marker config preset.
    """
    from pathlib import Path
    
    presets_dir = STORAGE_ROOT / "nft_presets"
    preset_path = presets_dir / f"{preset_name}.json"
    
    if not preset_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preset '{preset_name}' not found"
        )
    
    try:
        preset_path.unlink()
        return {"message": f"Preset '{preset_name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete preset: {str(e)}"
        )


class NFTAnalyticsResponse(BaseModel):
    """Response for NFT analytics."""
    total_markers: int
    quality_distribution: Dict[str, int]
    avg_file_sizes: Dict[str, float]
    total_storage_used: int


@app.get("/api/nft-markers/analytics", response_model=NFTAnalyticsResponse, tags=["nft-markers"])
async def get_nft_analytics(
    username: str = Depends(require_admin)
) -> NFTAnalyticsResponse:
    """
    Get NFT marker usage analytics.
    """
    from nft_marker_generator import NFTMarkerGenerator
    from pathlib import Path
    
    nft_generator = NFTMarkerGenerator(STORAGE_ROOT)
    markers_dir = nft_generator.markers_dir
    
    if not markers_dir.exists():
        return NFTAnalyticsResponse(
            total_markers=0,
            quality_distribution={},
            avg_file_sizes={},
            total_storage_used=0
        )
    
    # Analyze markers
    total_markers = 0
    fset_sizes = []
    fset3_sizes = []
    iset_sizes = []
    total_storage = 0
    
    for marker_dir in markers_dir.iterdir():
        if not marker_dir.is_dir():
            continue
        
        total_markers += 1
        
        for file_path in marker_dir.rglob('*'):
            if file_path.is_file():
                size = file_path.stat().st_size
                total_storage += size
                
                if file_path.suffix == '.fset':
                    fset_sizes.append(size)
                elif file_path.suffix == '.fset3':
                    fset3_sizes.append(size)
                elif file_path.suffix == '.iset':
                    iset_sizes.append(size)
    
    # Calculate averages
    avg_file_sizes = {
        'fset': sum(fset_sizes) / len(fset_sizes) if fset_sizes else 0,
        'fset3': sum(fset3_sizes) / len(fset3_sizes) if fset3_sizes else 0,
        'iset': sum(iset_sizes) / len(iset_sizes) if iset_sizes else 0
    }
    
    return NFTAnalyticsResponse(
        total_markers=total_markers,
        quality_distribution={},  # Could be enhanced with quality analysis
        avg_file_sizes=avg_file_sizes,
        total_storage_used=total_storage
    )


@app.post("/api/nft-markers/enhance-contrast", tags=["nft-markers"])
async def enhance_image_contrast(
    image_path: str,
    factor: float = 1.5,
    username: str = Depends(require_admin)
) -> Dict[str, str]:
    """
    Enhance image contrast for better feature detection.
    """
    from nft_marker_generator import NFTMarkerGenerator
    
    nft_generator = NFTMarkerGenerator(STORAGE_ROOT)
    
    try:
        enhanced_path = nft_generator.enhance_contrast(
            image_path=image_path,
            factor=factor
        )
        
        return {
            "original_path": image_path,
            "enhanced_path": str(enhanced_path),
            "factor": str(factor)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enhance contrast: {str(e)}"
        )


@app.post("/api/nft-markers/clear-cache", tags=["nft-markers"])
async def clear_nft_cache(
    clear_all: bool = False,
    username: str = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Clear NFT analysis cache.
    """
    from nft_marker_generator import NFTMarkerGenerator
    
    nft_generator = NFTMarkerGenerator(STORAGE_ROOT)
    
    if not nft_generator.cache:
        return {"message": "Cache is not enabled", "cleared": 0}
    
    if clear_all:
        cleared = nft_generator.cache.clear_all()
    else:
        cleared = nft_generator.cache.clear_expired()
    
    return {
        "message": f"Cleared {cleared} cache entries",
        "cleared": cleared,
        "clear_all": clear_all
    }


# Add time import if not already present
import time


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)