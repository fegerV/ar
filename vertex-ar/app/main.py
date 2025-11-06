"""
Main application factory for Vertex AR.
Creates and configures the FastAPI application.
"""
import sentry_sdk
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.rate_limiter import create_rate_limit_dependency, rate_limit_dependency
from logging_setup import get_logger

logger = get_logger(__name__)

# Global app instance for access in modules
_app_instance = None


def get_current_app() -> FastAPI:
    """Get the current FastAPI app instance."""
    global _app_instance
    if _app_instance is None:
        raise RuntimeError("App not initialized. Call create_app() first.")
    return _app_instance


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    global _app_instance
    
    # Initialize Sentry
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            environment=settings.SENTRY_ENVIRONMENT,
        )
        logger.info("Sentry initialized", environment=settings.SENTRY_ENVIRONMENT)
    
    # Create FastAPI app
    app = FastAPI(
        title="Vertex AR - Simplified",
        version=settings.VERSION,
        description="A lightweight AR backend for creating augmented reality experiences from image + video pairs",
        dependencies=[Depends(create_rate_limit_dependency(settings.GLOBAL_RATE_LIMIT))],
    )
    
    # Configure Prometheus metrics
    Instrumentator().instrument(app).expose(app)
    
    # Configure CORS
    logger.info("CORS configured", origins=settings.CORS_ORIGINS)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    
    # Mount static files
    app.mount("/static", StaticFiles(directory=str(settings.STATIC_ROOT)), name="static")
    app.mount("/storage", StaticFiles(directory=str(settings.STORAGE_ROOT)), name="storage")
    
    # Store configuration in app state
    app.state.config = {
        "BASE_DIR": settings.BASE_DIR,
        "STATIC_ROOT": settings.STATIC_ROOT,
        "STORAGE_ROOT": settings.STORAGE_ROOT,
        "BASE_URL": settings.BASE_URL,
        "VERSION": settings.VERSION,
        "SESSION_TIMEOUT_MINUTES": settings.SESSION_TIMEOUT_MINUTES,
        "AUTH_MAX_ATTEMPTS": settings.AUTH_MAX_ATTEMPTS,
        "AUTH_LOCKOUT_MINUTES": settings.AUTH_LOCKOUT_MINUTES,
        "GLOBAL_RATE_LIMIT": settings.GLOBAL_RATE_LIMIT,
        "AUTH_RATE_LIMIT": settings.AUTH_RATE_LIMIT,
        "UPLOAD_RATE_LIMIT": settings.UPLOAD_RATE_LIMIT,
        "STORAGE_TYPE": settings.STORAGE_TYPE,
        "TELEGRAM_BOT_TOKEN": settings.TELEGRAM_BOT_TOKEN,
        "TELEGRAM_CHAT_ID": settings.TELEGRAM_CHAT_ID,
        "MAX_FILE_SIZE": settings.MAX_FILE_SIZE,
        "ALLOWED_IMAGE_TYPES": settings.ALLOWED_IMAGE_TYPES,
        "ALLOWED_VIDEO_TYPES": settings.ALLOWED_VIDEO_TYPES,
    }
    
    # Initialize database
    from app.database import Database
    app.state.database = Database(settings.DB_PATH)
    
    # Initialize auth components
    from app.auth import AuthSecurityManager, TokenManager
    app.state.auth_security = AuthSecurityManager(
        max_attempts=settings.AUTH_MAX_ATTEMPTS,
        lockout_minutes=settings.AUTH_LOCKOUT_MINUTES
    )
    app.state.tokens = TokenManager(
        session_timeout_minutes=settings.SESSION_TIMEOUT_MINUTES
    )
    
    # Initialize storage adapter
    from app.storage import StorageAdapter
    if settings.STORAGE_TYPE == "minio":
        from app.storage_minio import MinioStorageAdapter
        app.state.storage = MinioStorageAdapter(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            bucket=settings.MINIO_BUCKET
        )
    else:
        from app.storage_local import LocalStorageAdapter
        app.state.storage = LocalStorageAdapter(settings.STORAGE_ROOT)
    
    # Register API routes
    from app.api import auth, ar, admin, clients, portraits, videos, health, users
    
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(users.router, prefix="/users", tags=["users"])
    app.include_router(ar.router, prefix="/ar", tags=["ar"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])
    app.include_router(clients.router, prefix="/clients", tags=["clients"])
    app.include_router(portraits.router, prefix="/portraits", tags=["portraits"])
    app.include_router(videos.router, prefix="/videos", tags=["videos"])
    app.include_router(health.router, tags=["health"])
    
    # Root endpoint
    @app.get("/")
    def read_root():
        return {"Hello": "Vertex AR (Simplified)", "version": settings.VERSION}
    
    # Store global app instance
    _app_instance = app
    
    return app