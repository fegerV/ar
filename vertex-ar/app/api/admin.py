"""
Admin panel endpoints for Vertex AR API.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.auth import require_admin
from app.database import Database
from app.main import get_current_app
from app.models import ARContentResponse
from app.rate_limiter import create_rate_limit_dependency
from app.auth import _verify_password
from logging_setup import get_logger
from utils import format_bytes, get_disk_usage, get_storage_usage

logger = get_logger(__name__)
router = APIRouter()


def get_database() -> Database:
    """Get database instance."""
    from app.main import get_current_app
    app = get_current_app()
    if not hasattr(app.state, 'database'):
        from pathlib import Path
        BASE_DIR = app.state.config["BASE_DIR"]
        DB_PATH = BASE_DIR / "app_data.db"
        from app.database import Database, ensure_default_admin_user
        app.state.database = Database(DB_PATH)
        ensure_default_admin_user(app.state.database)
    return app.state.database


def get_templates() -> Jinja2Templates:
    """Get Jinja2 templates instance."""
    from app.main import get_current_app
    app = get_current_app()
    if not hasattr(app.state, 'templates'):
        BASE_DIR = app.state.config["BASE_DIR"]
        app.state.templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    return app.state.templates


def _redirect_to_login(error: str = "unauthorized") -> RedirectResponse:
    """Redirect user to admin login page with optional error flag."""
    response = RedirectResponse(
        url=f"/admin?error={error}",
        status_code=status.HTTP_302_FOUND,
    )
    response.delete_cookie("authToken")
    return response


def _validate_admin_session(request: Request) -> Optional[str]:
    """Validate admin session cookie and return username when valid."""
    auth_token = request.cookies.get("authToken")
    if not auth_token:
        return None
    try:
        app = get_current_app()
        tokens = app.state.tokens
        username = tokens.verify_token(auth_token)
        if not username:
            return None
        database = get_database()
        user = database.get_user(username)
        if not user or not user.get("is_admin", False):
            return None
        return username
    except Exception as exc:
        logger.error("Failed to validate admin session", exc_info=exc)
        return None


@router.get("/", response_class=HTMLResponse)
async def admin_panel(request: Request) -> HTMLResponse:
    """Serve admin panel or login page."""
    templates = get_templates()
    username = _validate_admin_session(request)
    if not username:
        if request.cookies.get("authToken"):
            return _redirect_to_login("unauthorized")
        error = request.query_params.get("error")
        return templates.TemplateResponse("login.html", {"request": request, "error": error})
    
    context = {"request": request, "username": username}
    return templates.TemplateResponse("admin_dashboard.html", context)


@router.get("/orders", response_class=HTMLResponse)
async def admin_orders_panel(request: Request) -> HTMLResponse:
    """Serve admin panel for orders management (unified view)."""
    username = _validate_admin_session(request)
    if not username:
        return _redirect_to_login("unauthorized")
    
    templates = get_templates()
    context = {"request": request, "username": username}
    return templates.TemplateResponse("admin_dashboard.html", context)


@router.get("/order/{portrait_id}", response_class=HTMLResponse)
async def admin_order_detail(request: Request, portrait_id: str) -> HTMLResponse:
    """Serve order detail page."""
    username = _validate_admin_session(request)
    if not username:
        return _redirect_to_login("unauthorized")
    
    templates = get_templates()
    database = get_database()
    
    # Get portrait information
    portrait = database.get_portrait(portrait_id)
    if not portrait:
        return RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)
    
    # Load image preview if available
    image_preview_data = None
    image_preview_path = portrait.get("image_preview_path")
    if image_preview_path:
        try:
            from pathlib import Path
            import base64
            preview_path = Path(image_preview_path)
            if preview_path.exists():
                with open(preview_path, "rb") as f:
                    image_preview_data = base64.b64encode(f.read()).decode()
        except Exception as e:
            logger.warning(f"Failed to load portrait preview: {e}")
    
    portrait["image_preview_data"] = image_preview_data
    
    # Get client information
    client = database.get_client(portrait["client_id"])
    
    # Get videos for this portrait
    videos = database.get_videos_by_portrait(portrait_id)
    
    # Enhance portrait with client info for template
    portrait["client_name"] = client["name"] if client else "N/A"
    portrait["client_phone"] = client["phone"] if client else "N/A"
    
    # Generate order number (simplified - in production you'd have a proper order number system)
    order_number = f"{hash(portrait_id) % 1000000:06d}"
    
    # Generate full URL
    from app.main import get_current_app
    app = get_current_app()
    base_url = app.state.config["BASE_URL"]
    full_url = f"{base_url}/portrait/{portrait['permanent_link']}"
    
    context = {
        "request": request,
        "username": username,
        "order_number": order_number,
        "portrait": portrait,
        "client": client,
        "videos": videos,
        "full_url": full_url,
        "image_analysis": {}  # Will be loaded via AJAX
    }
    return templates.TemplateResponse("admin_order_detail.html", context)


@router.post("/login")
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
) -> RedirectResponse:
    """Handle admin login from HTML form."""
    database = get_database()
    
    try:
        user = database.get_user(username)
        if user is None or not _verify_password(password, user["hashed_password"]):
            logger.warning(f"Admin login failed for user: {username}")
            return RedirectResponse(
                url="/admin?error=invalid_credentials",
                status_code=status.HTTP_302_FOUND
            )
        
        if not user.get("is_admin"):
            logger.warning(f"Non-admin login attempt by user: {username}")
            return RedirectResponse(
                url="/admin?error=invalid_credentials",
                status_code=status.HTTP_302_FOUND
            )
        
        app = get_current_app()
        tokens = app.state.tokens
        token = tokens.issue_token(username)

        database.update_last_login(username)

        logger.info(f"Admin login successful for user: {username}")
        
        response = RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="authToken",
            value=token,
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="lax",
            max_age=86400,
            path="/",
        )
        return response
    except Exception as e:
        logger.error(f"Error during admin login: {e}")
        return RedirectResponse(
            url="/admin?error=invalid_credentials",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/upload", response_model=ARContentResponse, dependencies=[Depends(create_rate_limit_dependency("10/minute"))])
async def upload_ar_content_admin(
    request: Request,
    image: UploadFile = File(...),
    video: UploadFile = File(...),
    username: str = Depends(require_admin)
) -> ARContentResponse:
    """
    Upload image and video to create AR content via admin panel.
    Supports both Authorization header and cookie-based authentication.
    """
    from app.api.ar import upload_ar_content
    return await upload_ar_content(request, image, video, username)


@router.get("/system-info")
async def get_system_info(_: str = Depends(require_admin)) -> Dict[str, Any]:
    """Return disk and storage usage information for admin dashboard."""
    app = get_current_app()
    storage_root = app.state.config["STORAGE_ROOT"]
    disk_usage = get_disk_usage(str(storage_root))
    storage_usage = get_storage_usage(str(storage_root))
    return {
        "disk_info": {
            "total": format_bytes(disk_usage["total"]),
            "used": format_bytes(disk_usage["used"]),
            "free": format_bytes(disk_usage["free"]),
            "used_percent": disk_usage["used_percent"],
            "free_percent": disk_usage["free_percent"],
        },
        "storage_info": {
            "total_size": storage_usage["formatted_size"],
            "file_count": storage_usage["file_count"],
            "path": str(storage_root),
        },
    }


@router.get("/content-stats")
async def get_content_stats(_: str = Depends(require_admin)) -> List[Dict[str, Any]]:
    """Return aggregated AR content statistics for the admin dashboard."""
    database = get_database()
    records = database.list_ar_content()
    stats: List[Dict[str, Any]] = []
    for record in records:
        stats.append({
            "id": record["id"],
            "views": record.get("view_count", 0),
            "clicks": record.get("click_count", 0),
            "created_at": record.get("created_at"),
            "ar_url": record.get("ar_url"),
        })
    stats.sort(key=lambda item: item["views"], reverse=True)
    return stats
