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
database = None


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
    global database
    from app.database import Database, ensure_default_admin_user, ensure_default_company
    database = Database(settings.DB_PATH)
    app.state.database = database
    ensure_default_admin_user(app.state.database)
    ensure_default_company(app.state.database)
    
    # Initialize async email service
    from app.services import init_email_service
    from app.notification_config import get_notification_config
    notification_config = get_notification_config()
    app.state.email_service = init_email_service(notification_config, database)
    logger.info("Async email service initialized")
    
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
    from app.api import auth, ar, admin, clients, companies, projects, folders, portraits, videos, health, users, notifications as notifications_api, notifications_management, notification_settings, orders, backups, monitoring, mobile, remote_storage, storage_config, storage_management, yandex_disk, email_templates
    
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(users.router, prefix="/users", tags=["users"])
    app.include_router(ar.router, prefix="/ar", tags=["ar"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])
    app.include_router(companies.router, tags=["companies"])
    app.include_router(projects.router, tags=["projects"])
    app.include_router(folders.router, tags=["folders"])
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
    app.include_router(email_templates.router, tags=["email_templates"])
    app.include_router(health.router, tags=["health"])
    app.include_router(notifications_api.router)
    app.include_router(notifications_management.router)
    app.include_router(notification_settings.router)
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
        
        # Determine portrait status based on video availability and status
        portrait_status = "active"
        video_url = None
        
        if not active_video:
            # No active video - treat as archived
            portrait_status = "archived"
        else:
            # Check video status field (if it exists)
            video_status = active_video.get("status", "active")
            if video_status == "archived":
                portrait_status = "archived"
            elif video_status == "inactive":
                portrait_status = "archived"
            else:
                # Video is active - prepare URL
                storage_manager = app.state.storage_manager
                video_url = storage_manager.get_public_url(active_video['video_path'], "videos")
                portrait_status = "active"
        
        # Prepare portrait data for AR viewer
        portrait_data = {
            "id": portrait["id"],
            "permanent_link": portrait["permanent_link"],
            "video_url": video_url,
            "view_count": portrait["view_count"],
            "status": portrait_status
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
    
    # Start video animation scheduler
    if settings.VIDEO_SCHEDULER_ENABLED:
        from app.video_animation_scheduler import video_animation_scheduler
        
        @app.on_event("startup")
        async def start_video_scheduler():
            """Start video animation scheduler."""
            import asyncio
            
            # Start video animation scheduler
            asyncio.create_task(video_animation_scheduler.start_video_animation_scheduler())
            logger.info("Video animation scheduler started")
    
    # Start lifecycle scheduler
    if settings.LIFECYCLE_SCHEDULER_ENABLED:
        from app.project_lifecycle import project_lifecycle_scheduler
        
        @app.on_event("startup")
        async def start_lifecycle_scheduler():
            """Start lifecycle scheduler."""
            import asyncio
            
            # Start lifecycle scheduler
            asyncio.create_task(project_lifecycle_scheduler.start_lifecycle_scheduler())
            logger.info("Lifecycle scheduler started")
    
    # Start persistent email queue with worker pool
    @app.on_event("startup")
    async def start_persistent_email_queue():
        """Start persistent email queue with worker pool."""
        try:
            import asyncio
            from app.email_service import email_service
            from app.services import email_queue as eq_module
            from app.config import settings
            
            # Get worker count from settings (default: 3)
            worker_count = getattr(settings, "EMAIL_QUEUE_WORKERS", 3)
            
            # Initialize persistent email queue
            eq_module.email_queue = eq_module.EmailQueue(
                email_service=email_service,
                database=database,
                worker_count=worker_count,
            )
            app.state.email_queue = eq_module.email_queue
            
            # Start workers
            await eq_module.email_queue.start_workers()
            logger.info(f"Persistent email queue started with {worker_count} workers")
            
        except Exception as e:
            logger.error("Failed to start persistent email queue", error=str(e), exc_info=e)
    
    # Start in-memory email queue processor (fallback/urgent emails)
    @app.on_event("startup")
    async def start_email_queue_processor():
        """Start in-memory email queue processor for urgent/fallback emails."""
        try:
            import asyncio
            from app.email_service import email_service
            
            async def email_queue_loop():
                """Process in-memory email queue periodically."""
                while True:
                    try:
                        await email_service.process_queue()
                    except Exception as e:
                        logger.error("Error processing in-memory email queue", error=str(e), exc_info=e)
                    
                    # Process every 30 seconds
                    await asyncio.sleep(30)
            
            asyncio.create_task(email_queue_loop())
            logger.info("In-memory email queue processor started (for urgent/fallback emails)")
            
        except Exception as e:
            logger.error("Failed to start in-memory email queue processor", error=str(e), exc_info=e)
    
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
    async def stop_persistent_email_queue():
        """Stop persistent email queue workers."""
        try:
            if hasattr(app.state, "email_queue"):
                await app.state.email_queue.stop_workers()
                logger.info("Persistent email queue stopped")
        except Exception as e:
            logger.error("Failed to stop persistent email queue", error=str(e), exc_info=e)
    
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