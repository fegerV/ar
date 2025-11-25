"""
Main application factory for Vertex AR.
Creates and configures the FastAPI application.
"""
import sentry_sdk
from pathlib import Path
import fastapi
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.rate_limiter import create_rate_limit_dependency, rate_limit_dependency
from app.middleware import RequestLoggingMiddleware, ErrorLoggingMiddleware, ValidationErrorLoggingMiddleware
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
    
    # Add logging middleware
    logger.info("Logging middleware configured")
    app.add_middleware(ValidationErrorLoggingMiddleware)
    app.add_middleware(ErrorLoggingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    
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
    
    # Mount NFT markers directory (for AR.js to access marker files)
    nft_markers_path = settings.STORAGE_ROOT / "nft_markers"
    nft_markers_path.mkdir(parents=True, exist_ok=True)
    app.mount("/nft-markers", StaticFiles(directory=str(nft_markers_path)), name="nft-markers")
    
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
    from app.database import Database, ensure_default_admin_user, ensure_default_company
    app.state.database = Database(settings.DB_PATH)
    ensure_default_admin_user(app.state.database)
    ensure_default_company(app.state.database)
    
    # Initialize auth components
    from app.auth import AuthSecurityManager, TokenManager
    app.state.auth_security = AuthSecurityManager(
        max_attempts=settings.AUTH_MAX_ATTEMPTS,
        lockout_minutes=settings.AUTH_LOCKOUT_MINUTES
    )
    app.state.tokens = TokenManager(
        session_timeout_minutes=settings.SESSION_TIMEOUT_MINUTES
    )
    
    # Initialize storage manager
    from storage_manager import get_storage_manager
    app.state.storage_manager = get_storage_manager(settings.STORAGE_ROOT)
    
    # Keep backward compatibility - set default storage adapter
    app.state.storage = app.state.storage_manager.get_adapter("portraits")
    
    # Initialize templates
    app.state.templates = Jinja2Templates(directory=str(settings.BASE_DIR / "templates"))
    
    # Register API routes
    from app.api import auth, ar, admin, clients, companies, portraits, videos, health, users, notifications as notifications_api, notifications_management, orders, backups, monitoring, mobile, remote_storage, storage_config, storage_management, yandex_disk
    
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(users.router, prefix="/users", tags=["users"])
    app.include_router(ar.router, prefix="/ar", tags=["ar"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])
    app.include_router(companies.router, tags=["companies"])
    app.include_router(clients.router, prefix="/clients", tags=["clients"])
    app.include_router(portraits.router, prefix="/portraits", tags=["portraits"])
    app.include_router(videos.router, prefix="/videos", tags=["videos"])
    app.include_router(orders.router, prefix="/orders", tags=["orders"])
    app.include_router(orders.legacy_router, prefix="/api/orders", tags=["orders"])
    app.include_router(backups.router, tags=["backups"])
    app.include_router(remote_storage.router, tags=["remote_storage"])
    app.include_router(storage_config.router, tags=["storage_config"])
    app.include_router(storage_management.router, tags=["storage_management"])
    app.include_router(yandex_disk.router, tags=["yandex_disk"])
    app.include_router(health.router, tags=["health"])
    app.include_router(notifications_api.router)
    app.include_router(notifications_management.router)
    app.include_router(monitoring.router, prefix="/admin")
    app.include_router(mobile.router, prefix="/api/mobile", tags=["mobile"])
    
    # Enhanced Prometheus metrics endpoint
    @app.get("/metrics")
    async def prometheus_metrics():
        """Serve comprehensive Prometheus metrics."""
        from app.prometheus_metrics import prometheus_exporter
        from fastapi.responses import Response
        
        metrics_data = prometheus_exporter.get_metrics()
        return Response(
            content=metrics_data,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    
    # Favicon endpoint
    @app.get("/favicon.ico")
    async def favicon():
        """Serve favicon.ico file."""
        favicon_path = settings.STATIC_ROOT / "favicon.ico"
        if favicon_path.exists():
            return FileResponse(str(favicon_path))
        # Return empty response if favicon doesn't exist
        return fastapi.Response(status_code=204)
    
    # Root endpoint
    @app.get("/")
    def read_root():
        return {"Hello": "Vertex AR (Simplified)", "version": settings.VERSION}
    
    # Public portrait viewer endpoint
    @app.get("/portrait/{permanent_link}", response_class=fastapi.responses.HTMLResponse)
    async def view_portrait(request: Request, permanent_link: str):
        """Public endpoint to view AR portrait by permanent link."""
        database = app.state.database
        portrait = database.get_portrait_by_link(permanent_link)
        
        if not portrait:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail="Portrait not found"
            )
        
        # Increment view count
        database.increment_portrait_views(portrait["id"])
        
        # Get active video for this portrait
        active_video = database.get_active_video(portrait["id"])
        if not active_video:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail="No active video found for this portrait"
            )
        
        # Prepare video URL using storage manager
        base_url = app.state.config["BASE_URL"]
        storage_manager = app.state.storage_manager
        
        # Get video URL from storage manager
        video_url = storage_manager.get_public_url(active_video['video_path'], "videos")
        
        # Prepare portrait data for AR viewer
        portrait_data = {
            "id": portrait["id"],
            "permanent_link": portrait["permanent_link"],
            "video_url": video_url,
            "view_count": portrait["view_count"]
        }
        
        templates = app.state.templates
        return templates.TemplateResponse("ar_page.html", {"request": request, "record": portrait_data})
    
    # Start background monitoring tasks
    if settings.ALERTING_ENABLED:
        from app.monitoring import system_monitor
        from app.weekly_reports import weekly_report_generator
        
        @app.on_event("startup")
        async def start_monitoring_tasks():
            """Start background monitoring and reporting tasks."""
            import asyncio
            
            # Start system monitoring
            asyncio.create_task(system_monitor.start_monitoring())
            logger.info("System monitoring task started")
            
            # Start weekly report scheduler
            asyncio.create_task(weekly_report_generator.start_weekly_report_scheduler())
            logger.info("Weekly report scheduler started")
    
    # Start notification center services
    @app.on_event("startup")
    async def start_notification_services():
        """Start notification center background services."""
        try:
            import asyncio
            from notification_integrations import notification_scheduler
            from notification_sync import notification_sync_manager
            
            # Start notification scheduler
            asyncio.create_task(notification_scheduler.start())
            logger.info("Notification scheduler started")
            
            # Start notification sync manager
            asyncio.create_task(notification_sync_manager.start())
            logger.info("Notification sync manager started")
            
        except Exception as e:
            logger.error("Failed to start notification services", error=str(e), exc_info=e)
    
    @app.on_event("shutdown")
    async def stop_notification_services():
        """Stop notification center background services."""
        try:
            from notification_integrations import notification_scheduler
            from notification_sync import notification_sync_manager
            
            notification_scheduler.stop()
            notification_sync_manager.stop()
            logger.info("Notification services stopped")
            
        except Exception as e:
            logger.error("Failed to stop notification services", error=str(e), exc_info=e)
    
    # Start automated backup scheduler
    @app.on_event("startup")
    async def start_backup_scheduler():
        """Start automated backup scheduler."""
        try:
            from backup_scheduler import start_backup_scheduler as init_backup_scheduler
            scheduler = init_backup_scheduler()
            app.state.backup_scheduler = scheduler
            logger.info("Automated backup scheduler started")
        except Exception as e:
            logger.error("Failed to start backup scheduler", error=str(e), exc_info=e)
    
    @app.on_event("shutdown")
    async def stop_backup_scheduler():
        """Stop automated backup scheduler."""
        try:
            if hasattr(app.state, "backup_scheduler"):
                app.state.backup_scheduler.stop()
                logger.info("Automated backup scheduler stopped")
        except Exception as e:
            logger.error("Failed to stop backup scheduler", error=str(e), exc_info=e)
    
    # Store global app instance
    _app_instance = app
    
    return app


# Create app instance for uvicorn
app = create_app()