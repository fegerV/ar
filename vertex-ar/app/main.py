"""
Main application factory for Vertex AR.
Creates and configures the FastAPI application.
"""
import os
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

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
    
    # Load environment variables
    BASE_DIR = Path(__file__).resolve().parent.parent
    VERSION_FILE = BASE_DIR / "VERSION"
    
    try:
        VERSION = VERSION_FILE.read_text().strip()
    except FileNotFoundError:
        VERSION = "1.0.0"
    
    # Configuration
    BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
    SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
    AUTH_MAX_ATTEMPTS = int(os.getenv("AUTH_MAX_ATTEMPTS", "5"))
    AUTH_LOCKOUT_MINUTES = int(os.getenv("AUTH_LOCKOUT_MINUTES", "15"))
    RUNNING_TESTS = os.getenv("RUNNING_TESTS") == "1" or "PYTEST_CURRENT_TEST" in os.environ
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true" and not RUNNING_TESTS
    GLOBAL_RATE_LIMIT = os.getenv("GLOBAL_RATE_LIMIT", "100/minute")
    AUTH_RATE_LIMIT = os.getenv("AUTH_RATE_LIMIT", "5/minute")
    UPLOAD_RATE_LIMIT = os.getenv("UPLOAD_RATE_LIMIT", "10/minute")
    
    # Initialize Sentry
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            environment=os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development")),
        )
        logger.info("Sentry initialized", environment=os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development")))
    
    # Initialize rate limiter
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
    
    # Create FastAPI app
    app = FastAPI(
        title="Vertex AR - Simplified",
        version=VERSION,
        description="A lightweight AR backend for creating augmented reality experiences from image + video pairs",
        dependencies=[Depends(global_rate_limit_dependency)],
    )
    
    # Configure rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    
    # Configure Prometheus metrics
    Instrumentator().instrument(app).expose(app)
    
    # Configure CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
    logger.info("CORS configured", origins=CORS_ORIGINS)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    
    # Mount static files
    STATIC_ROOT = BASE_DIR / "static"
    STATIC_ROOT.mkdir(parents=True, exist_ok=True)
    STORAGE_ROOT = BASE_DIR / "storage"
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    
    app.mount("/static", StaticFiles(directory=str(STATIC_ROOT)), name="static")
    app.mount("/storage", StaticFiles(directory=str(STORAGE_ROOT)), name="storage")
    
    # Store configuration in app state
    app.state.config = {
        "BASE_DIR": BASE_DIR,
        "STATIC_ROOT": STATIC_ROOT,
        "STORAGE_ROOT": STORAGE_ROOT,
        "BASE_URL": BASE_URL,
        "VERSION": VERSION,
        "SESSION_TIMEOUT_MINUTES": SESSION_TIMEOUT_MINUTES,
        "AUTH_MAX_ATTEMPTS": AUTH_MAX_ATTEMPTS,
        "AUTH_LOCKOUT_MINUTES": AUTH_LOCKOUT_MINUTES,
        "GLOBAL_RATE_LIMIT": GLOBAL_RATE_LIMIT,
        "AUTH_RATE_LIMIT": AUTH_RATE_LIMIT,
        "UPLOAD_RATE_LIMIT": UPLOAD_RATE_LIMIT,
    }
    
    # Store rate limiter in app state
    app.state.limiter = limiter
    
    # Register API routes
    from app.api import auth, ar, admin, clients, portraits, videos, health
    
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(ar.router, prefix="/ar", tags=["ar"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])
    app.include_router(clients.router, prefix="/clients", tags=["clients"])
    app.include_router(portraits.router, prefix="/portraits", tags=["portraits"])
    app.include_router(videos.router, prefix="/videos", tags=["videos"])
    app.include_router(health.router, tags=["health"])
    
    # Root endpoint
    @app.get("/")
    def read_root():
        return {"Hello": "Vertex AR (Simplified)"}
    
    # Store global app instance
    _app_instance = app
    
    return app