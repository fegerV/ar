"""
Admin panel endpoints for Vertex AR API.
"""
import csv
import io
import json
import os
import platform
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.api.auth import require_admin
from app.database import Database
from app.main import get_current_app
from app.models import ARContentResponse
from app.rate_limiter import create_rate_limit_dependency
from app.utils import verify_password as _verify_password
from logging_setup import get_logger
from nft_marker_generator import analyze_image
from utils import format_bytes, get_disk_usage, get_storage_usage

logger = get_logger(__name__)


def _format_duration(seconds: float) -> str:
    seconds_int = int(seconds)
    days, remainder = divmod(seconds_int, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    parts: List[str] = []
    if days:
        parts.append(f"{days}д")
    if hours or days:
        parts.append(f"{hours}ч")
    if minutes or hours or days:
        parts.append(f"{minutes}м")
    parts.append(f"{secs}с")
    return " ".join(parts)


def _get_uptime_seconds() -> Optional[float]:
    try:
        with open("/proc/uptime", "r", encoding="utf-8") as uptime_file:
            return float(uptime_file.readline().split()[0])
    except (FileNotFoundError, ValueError, IndexError):
        return None


def _get_memory_info() -> Optional[Dict[str, float]]:
    try:
        info: Dict[str, int] = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as meminfo:
            for line in meminfo:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    info[key] = int(parts[1])
        total = info.get("MemTotal")
        available = info.get("MemAvailable") or info.get("MemFree")
        if not total or not available:
            return None
        used = total - available
        return {
            "total": float(total) * 1024,
            "used": float(used) * 1024,
            "percent": (used / total) * 100,
        }
    except (FileNotFoundError, ValueError):
        return None


def _get_cpu_percent() -> float:
    try:
        load_avg = os.getloadavg()[0]
        cores = os.cpu_count() or 1
        return max(0.0, min(100.0, (load_avg / cores) * 100))
    except (AttributeError, OSError):
        return 0.0


def _build_public_url(path: Optional[str]) -> str:
    if not path:
        return ""
    path_str = str(path)
    if path_str.startswith(("http://", "https://", "data:")):
        return path_str
    app = get_current_app()
    base_url = app.state.config["BASE_URL"]
    storage_root = Path(app.state.config["STORAGE_ROOT"])
    try:
        path_obj = Path(path_str)
        if path_obj.is_absolute():
            relative_path = path_obj.relative_to(storage_root)
        else:
            relative_path = path_obj
        return f"{base_url}/storage/{relative_path.as_posix().lstrip('/')}"
    except Exception:
        return f"{base_url}/{path_str.lstrip('/')}"


def _serialize_records(records: List[Dict[str, Any]], total_count: int) -> List[Dict[str, Any]]:
    serialized: List[Dict[str, Any]] = []
    total = max(total_count, len(records)) or 1
    base_url = get_current_app().state.config["BASE_URL"]
    for idx, record in enumerate(records):
        order_position = total - idx
        image_source = record.get("image_preview_path") or record.get("image_path")
        video_preview = record.get("video_preview_path")
        serialized.append({
            "id": record.get("portrait_id"),
            "order_number": f"{max(order_position, 1):06d}",
            "client_id": record.get("client_id"),
            "client_name": record.get("client_name"),
            "client_phone": record.get("client_phone"),
            "company_id": record.get("company_id"),
            "portrait_path": _build_public_url(image_source),
            "active_video_id": record.get("video_id"),
            "active_video_url": _build_public_url(record.get("video_path")),
            "active_video_preview": _build_public_url(video_preview),
            "video_description": record.get("video_description"),
            "views": record.get("view_count", 0),
            "created_at": record.get("created_at"),
            "permanent_link": record.get("permanent_link"),
            "permanent_url": f"{base_url}/portrait/{record.get('permanent_link')}",
            "qr_code": f"data:image/png;base64,{record.get('qr_code')}" if record.get("qr_code") else None,
        })
    return serialized


def _ensure_company_exists(database: Database, company_id: Optional[str]) -> None:
    if company_id:
        company = database.get_company(company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Компания не найдена")


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


@router.get("/clients", response_class=HTMLResponse)
async def admin_clients_panel(request: Request) -> HTMLResponse:
    """Serve admin panel for clients management."""
    username = _validate_admin_session(request)
    if not username:
        return _redirect_to_login("unauthorized")

    templates = get_templates()
    context = {"request": request, "username": username}
    return templates.TemplateResponse("admin_clients.html", context)


@router.get("/backups", response_class=HTMLResponse)
async def admin_backups_panel(request: Request) -> HTMLResponse:
    """Serve admin panel for backup management."""
    username = _validate_admin_session(request)
    if not username:
        return _redirect_to_login("unauthorized")

    templates = get_templates()
    context = {"request": request, "username": username}
    return templates.TemplateResponse("admin_backups.html", context)


@router.get("/notifications", response_class=HTMLResponse)
async def admin_notifications_panel(request: Request) -> HTMLResponse:
    """Serve notification center page."""
    username = _validate_admin_session(request)
    if not username:
        return _redirect_to_login("unauthorized")

    templates = get_templates()
    context = {"request": request, "username": username}
    return templates.TemplateResponse("admin_notifications.html", context)


@router.get("/settings", response_class=HTMLResponse)
async def admin_settings_panel(request: Request) -> HTMLResponse:
    """Serve admin settings page."""
    username = _validate_admin_session(request)
    if not username:
        return _redirect_to_login("unauthorized")

    templates = get_templates()
    context = {"request": request, "username": username}
    return templates.TemplateResponse("admin_settings.html", context)


@router.post("/settings/backup")
async def admin_backup_settings(
    request: Request,
    settings_data: Dict[str, Any],
    _: str = Depends(require_admin)
) -> Dict[str, Any]:
    """Save backup settings."""
    try:
        # Save settings to a configuration file or database
        # For now, we'll store them in a JSON config file
        from pathlib import Path
        import json
        
        config_dir = Path("app_data")
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "backup_settings.json"
        
        # Load existing settings
        existing_settings = {}
        if config_file.exists():
            with open(config_file, 'r') as f:
                existing_settings = json.load(f)
        
        # Update with new settings
        existing_settings.update(settings_data)
        
        # Save updated settings
        with open(config_file, 'w') as f:
            json.dump(existing_settings, f, indent=2)
        
        logger.info(f"Backup settings updated by admin: {_}")
        
        return {"success": True, "message": "Backup settings saved successfully"}
        
    except Exception as e:
        logger.error(f"Failed to save backup settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")


@router.get("/settings/backup")
async def admin_get_backup_settings(
    request: Request,
    _: str = Depends(require_admin)
) -> Dict[str, Any]:
    """Get current backup settings."""
    try:
        from pathlib import Path
        import json
        
        config_file = Path("app_data/backup_settings.json")
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                settings = json.load(f)
        else:
            # Default settings
            settings = {
                "compression": "gz",
                "max_backups": 7,
                "auto_split_backups": True
            }
        
        return {"success": True, "settings": settings}
        
    except Exception as e:
        logger.error(f"Failed to get backup settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get settings: {str(e)}")


@router.get("/order/{portrait_id}", response_class=HTMLResponse)
async def admin_order_detail(request: Request, portrait_id: str) -> HTMLResponse:
    """Serve order detail page."""
    username = _validate_admin_session(request)
    if not username:
        return _redirect_to_login("unauthorized")

    templates = get_templates()
    database = get_database()
    app = get_current_app()
    base_url = app.state.config["BASE_URL"]
    storage_root = Path(app.state.config["STORAGE_ROOT"])

    def format_size(bytes_value: Optional[int]) -> str:
        if not bytes_value or bytes_value <= 0:
            return "Неизвестно"
        human_readable = format_bytes(bytes_value)
        replacements = {
            " B": " Б",
            " KB": " КБ",
            " MB": " МБ",
            " GB": " ГБ",
            " TB": " ТБ",
            " PB": " ПБ",
        }
        for eng, ru in replacements.items():
            human_readable = human_readable.replace(eng, ru)
        return human_readable

    def get_file_stats(path_value: Optional[str]) -> tuple[Optional[int], Optional[float]]:
        if not path_value:
            return None, None
        candidates = []
        path_obj = Path(path_value)
        candidates.append(path_obj)
        if not path_obj.is_absolute():
            candidates.append(storage_root / path_obj)
        else:
            try:
                relative = path_obj.relative_to(storage_root)
                candidates.append(storage_root / relative)
            except ValueError:
                pass
        for candidate in candidates:
            try:
                if candidate.exists():
                    stat_result = candidate.stat()
                    return stat_result.st_size, stat_result.st_mtime
            except OSError as exc:
                logger.warning("Failed to stat file %s: %s", candidate, exc)
        return None, None

    def get_criteria_text(contrast_value: Any) -> str:
        try:
            contrast_float = float(contrast_value)
        except (TypeError, ValueError):
            return "N/A"
        if contrast_float < 30:
            return "Контраст < 30 → плохое"
        if contrast_float < 60:
            return "30 ≤ Контраст < 60 → удовлетворительное"
        if contrast_float < 90:
            return "60 ≤ Контраст < 90 → хорошее"
        return "Контраст ≥ 90 → отличное"

    def build_public_url(path: Optional[str]) -> str:
        if not path:
            return ""
        path_str = str(path)
        if path_str.startswith(("http://", "https://", "data:")):
            return path_str
        if path_str.startswith("/storage/"):
            return f"{base_url}{path_str}"
        if path_str.startswith("storage/"):
            return f"{base_url}/{path_str}"
        storage_segment = "/storage/"
        if storage_segment in path_str:
            return f"{base_url}{path_str[path_str.index(storage_segment):]}"
        path_obj = Path(path_str)
        try:
            if path_obj.is_absolute():
                relative_path = path_obj.relative_to(storage_root)
            else:
                relative_path = path_obj
            return f"{base_url}/storage/{relative_path.as_posix().lstrip('/')}"
        except ValueError:
            cleaned = path_str.lstrip("/")
            return f"{base_url}/storage/{cleaned}"
        except Exception as exc:
            logger.warning(f"Failed to build public URL for path {path_str}: {exc}")
            cleaned = path_str.lstrip("/")
            return f"{base_url}/storage/{cleaned}"

    # Get portrait information
    portrait = database.get_portrait(portrait_id)
    if not portrait:
        return RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)

    # Load image preview if available
    image_preview_data = None
    image_preview_path = portrait.get("image_preview_path")
    if image_preview_path:
        try:
            import base64
            preview_path = Path(image_preview_path)
            if preview_path.exists():
                with open(preview_path, "rb") as f:
                    image_preview_data = base64.b64encode(f.read()).decode()
        except Exception as e:
            logger.warning(f"Failed to load portrait preview: {e}")

    portrait["image_preview_data"] = image_preview_data
    portrait_preview_url = f"data:image/jpeg;base64,{image_preview_data}" if image_preview_data else None

    # Get client information
    client = database.get_client(portrait["client_id"])

    # Get videos for this portrait
    videos = database.get_videos_by_portrait(portrait_id)
    for video in videos:
        video_path_value = video.get("video_path")
        video["public_url"] = build_public_url(video_path_value)
        size_bytes, _ = get_file_stats(video_path_value)
        if size_bytes is None and video.get("file_size_mb"):
            try:
                size_bytes = int(video["file_size_mb"]) * 1024 * 1024
            except (TypeError, ValueError):
                size_bytes = None
        video["file_size_bytes"] = size_bytes
        video["file_size_display"] = format_size(size_bytes)
        if size_bytes is not None:
            video["file_size_mb_precise"] = round(size_bytes / (1024 * 1024), 2)
        else:
            video["file_size_mb_precise"] = None

    # Enhance portrait with client info for template
    portrait["client_name"] = client["name"] if client else "N/A"
    portrait["client_phone"] = client["phone"] if client else "N/A"

    # Preload image analysis data for initial render
    image_analysis_data: Dict[str, Any] = {}
    try:
        analysis = analyze_image(portrait["image_path"])
        if isinstance(analysis, dict):
            image_analysis_data.update({
                "width": analysis.get("width"),
                "height": analysis.get("height"),
                "brightness": analysis.get("brightness"),
                "contrast": analysis.get("contrast"),
                "quality": analysis.get("quality"),
                "valid": analysis.get("valid", True),
            })
            if analysis.get("message"):
                image_analysis_data["message"] = analysis.get("message")
            recommendation_value = analysis.get("recommendation") or analysis.get("recommendations")
            if recommendation_value:
                image_analysis_data["recommendation"] = recommendation_value
                image_analysis_data["recommendations"] = recommendation_value
            image_analysis_data["criteria"] = get_criteria_text(analysis.get("contrast"))
    except Exception as exc:
        logger.warning("Failed to preload image analysis for portrait %s: %s", portrait_id, exc)
    if "recommendations" not in image_analysis_data and image_analysis_data.get("recommendation"):
        image_analysis_data["recommendations"] = image_analysis_data["recommendation"]

    # Prepare marker file information
    marker_files_specs = [
        ("fset", portrait.get("marker_fset"), ".fset"),
        ("fset3", portrait.get("marker_fset3"), ".fset3"),
        ("iset", portrait.get("marker_iset"), ".iset"),
    ]
    marker_files: List[Dict[str, Any]] = []
    marker_total_size = 0
    marker_updated_ts: Optional[float] = None

    for type_name, path_value, extension in marker_files_specs:
        size_bytes, mtime = get_file_stats(path_value)
        if size_bytes:
            marker_total_size += size_bytes
        if mtime:
            marker_updated_ts = max(marker_updated_ts or mtime, mtime)
        marker_files.append({
            "type": type_name,
            "label": extension,
            "url": build_public_url(path_value),
            "size_bytes": size_bytes,
            "size_display": format_size(size_bytes),
            "exists": bool(size_bytes),
            "download_name": f"{portrait_id}{extension}",
        })

    marker_updated_at_iso: Optional[str] = None
    marker_updated_at_display = "—"
    if marker_updated_ts:
        updated_dt = datetime.fromtimestamp(marker_updated_ts)
        marker_updated_at_iso = updated_dt.isoformat()
        marker_updated_at_display = updated_dt.strftime("%d.%m.%Y %H:%M:%S")

    marker_info = {
        "files": marker_files,
        "total_size_bytes": marker_total_size,
        "total_size_display": format_size(marker_total_size),
        "updated_at": marker_updated_at_iso,
        "updated_at_display": marker_updated_at_display,
        "has_files": any(file_info["exists"] for file_info in marker_files),
    }
    if marker_total_size:
        marker_info["total_size_mb"] = round(marker_total_size / (1024 * 1024), 2)

    # Generate order number based on portrait position in the list (consistent with Content Records)
    all_portraits = database.list_portraits()
    portrait_index = next((i for i, p in enumerate(all_portraits) if p.get("id") == portrait_id), -1)
    order_position: Optional[int] = None
    if portrait_index >= 0:
        order_position = len(all_portraits) - portrait_index
        order_number = f"{order_position:06d}"
    else:
        # Fallback if portrait not found in list
        order_number = f"{hash(portrait_id) % 1000000:06d}"

    # Generate full URL
    full_url = f"{base_url}/portrait/{portrait['permanent_link']}"

    # Generate portrait image URL
    portrait_image_url = build_public_url(portrait['image_path'])
    portrait_preview_download_url = build_public_url(image_preview_path)

    context = {
        "request": request,
        "username": username,
        "order_number": order_number,
        "order_position": order_position,
        "portrait": portrait,
        "client": client,
        "videos": videos,
        "full_url": full_url,
        "portrait_image_url": portrait_image_url,
        "portrait_preview_url": portrait_preview_url,
        "portrait_preview_download_url": portrait_preview_download_url,
        "portrait_preview_filename": f"{portrait_id}_preview.jpg",
        "image_analysis": image_analysis_data,
        "marker_info": marker_info,
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
    client_name: str = Form(None),
    client_phone: str = Form(None),
    client_notes: str = Form(None),
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
    """Return extended system metrics for the admin dashboard."""
    app = get_current_app()
    storage_root = app.state.config["STORAGE_ROOT"]
    disk_usage = get_disk_usage(str(storage_root))
    storage_usage = get_storage_usage(str(storage_root))
    uptime_seconds = _get_uptime_seconds()
    memory_info = _get_memory_info()
    cpu_percent = _get_cpu_percent()
    return {
        "version": app.state.config["VERSION"],
        "uptime": _format_duration(uptime_seconds) if uptime_seconds else "N/A",
        "uptime_seconds": uptime_seconds,
        "memory_usage": (
            f"{format_bytes(memory_info['used'])} / {format_bytes(memory_info['total'])}"
            if memory_info else "N/A"
        ),
        "memory_percent": round(memory_info["percent"], 2) if memory_info else None,
        "disk_usage": f"{format_bytes(disk_usage['used'])} / {format_bytes(disk_usage['total'])}",
        "disk_percent": disk_usage["used_percent"],
        "cpu_usage": f"{cpu_percent:.1f}%",
        "cpu_percent": cpu_percent,
        "cpu_cores": os.cpu_count() or 1,
        "hostname": platform.node(),
        "platform": platform.platform(),
        "storage_info": {
            "total_size": storage_usage["formatted_size"],
            "file_count": storage_usage["file_count"],
            "path": str(storage_root),
            "used_percent": disk_usage["used_percent"],
            "free_percent": disk_usage["free_percent"],
        },
    }


@router.get("/stats")
async def get_dashboard_stats(
    company_id: Optional[str] = None,
    _: str = Depends(require_admin)
) -> Dict[str, Any]:
    """Return aggregated statistics for the dashboard."""
    database = get_database()
    _ensure_company_exists(database, company_id)
    total_portraits = database.count_portraits(company_id=company_id)
    storage_root = get_current_app().state.config["STORAGE_ROOT"]
    disk_usage = get_disk_usage(str(storage_root))
    storage_usage = get_storage_usage(str(storage_root))
    storage_percent = 0.0
    if disk_usage["total"]:
        storage_percent = min(100.0, round((storage_usage["total_size"] / disk_usage["total"]) * 100, 2))
    return {
        "company_id": company_id,
        "total_clients": database.count_clients(company_id=company_id),
        "total_portraits": total_portraits,
        "total_videos": database.count_videos(company_id=company_id),
        "total_orders": total_portraits,
        "active_portraits": database.count_active_portraits(company_id=company_id),
        "total_views": database.sum_portrait_views(company_id=company_id),
        "storage_used": storage_usage["formatted_size"],
        "storage_available": format_bytes(disk_usage["free"]),
        "storage_usage_percent": storage_percent,
    }


@router.get("/records")
async def list_dashboard_records(
    company_id: Optional[str] = None,
    limit: int = 250,
    _: str = Depends(require_admin)
) -> Dict[str, Any]:
    """Return portrait records for the dashboard table."""
    database = get_database()
    _ensure_company_exists(database, company_id)
    safe_limit = max(10, min(limit, 1000))
    records_raw = database.get_admin_records(company_id=company_id, limit=safe_limit)
    total_portraits = database.count_portraits(company_id=company_id)
    return {
        "records": _serialize_records(records_raw, total_portraits),
        "total": total_portraits,
    }


@router.get("/search")
async def search_dashboard_records(
    q: str = "",
    company_id: Optional[str] = None,
    limit: int = 100,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    min_views: Optional[int] = None,
    max_views: Optional[int] = None,
    _: str = Depends(require_admin)
) -> Dict[str, Any]:
    """Search and filter records by various criteria."""
    database = get_database()
    _ensure_company_exists(database, company_id)
    safe_limit = max(10, min(limit, 500))

    if not q.strip() and not any([date_from, date_to, min_views is not None, max_views is not None]):
        records_raw = database.get_admin_records(company_id=company_id, limit=safe_limit)
    else:
        search_query = q.strip() if q.strip() else None
        records_raw = database.get_admin_records(company_id=company_id, limit=safe_limit, search=search_query)

    filtered_records = []
    for record in records_raw:
        if date_from or date_to:
            created_at = record.get("created_at")
            if created_at:
                try:
                    from datetime import datetime
                    if isinstance(created_at, str):
                        record_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        record_date = created_at

                    if date_from:
                        filter_date_from = datetime.fromisoformat(date_from)
                        if record_date < filter_date_from:
                            continue

                    if date_to:
                        filter_date_to = datetime.fromisoformat(date_to)
                        if record_date > filter_date_to:
                            continue
                except (ValueError, AttributeError):
                    pass

        if min_views is not None or max_views is not None:
            views = record.get("view_count", 0) or 0
            if min_views is not None and views < min_views:
                continue
            if max_views is not None and views > max_views:
                continue

        filtered_records.append(record)

    total_portraits = database.count_portraits(company_id=company_id)
    return {
        "results": _serialize_records(filtered_records, total_portraits),
        "total_filtered": len(filtered_records),
        "total": total_portraits
    }


@router.delete("/records/{portrait_id}")
async def delete_dashboard_record(
    portrait_id: str,
    _: str = Depends(require_admin)
) -> Dict[str, str]:
    """Remove portrait along with associated files for dashboard actions."""
    database = get_database()
    portrait = database.get_portrait(portrait_id)
    if not portrait:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
    app = get_current_app()
    storage_root = Path(app.state.config["STORAGE_ROOT"])
    client_id = portrait.get("client_id")
    if not client_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Для записи не найден клиент")
    portrait_storage = storage_root / "portraits" / client_id / portrait_id
    try:
        if portrait_storage.exists():
            shutil.rmtree(portrait_storage)
    except OSError as exc:
        logger.warning("Failed to remove portrait storage %s: %s", portrait_storage, exc)
    marker_paths = [portrait.get("marker_fset"), portrait.get("marker_fset3"), portrait.get("marker_iset")]
    for marker_path in marker_paths:
        if not marker_path:
            continue
        try:
            marker_obj = Path(marker_path)
            if not marker_obj.is_absolute():
                marker_obj = storage_root / marker_obj
            if marker_obj.exists():
                marker_obj.unlink()
        except OSError as exc:
            logger.warning("Failed to remove marker file %s: %s", marker_path, exc)
    if not database.delete_portrait(portrait_id):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Не удалось удалить запись")
    return {"message": "Запись удалена"}


@router.get("/logout")
async def admin_logout(request: Request) -> RedirectResponse:
    """Handle admin logout and redirect to login page."""
    response = RedirectResponse(
        url="/admin",
        status_code=status.HTTP_302_FOUND,
    )
    response.delete_cookie("authToken")
    return response


@router.post("/export")
async def export_data(
    request: Request,
    _: str = Depends(require_admin)
) -> StreamingResponse:
    """Export admin data as CSV."""
    try:
        data = await request.json()
        export_format = data.get("format", "csv")
        include = data.get("include", ["clients", "portraits", "orders"])
        company_id = data.get("company_id")

        database = get_database()

        if export_format == "csv":
            return await _export_to_csv(database, include, company_id)
        elif export_format == "json":
            return await _export_to_json(database, include, company_id)
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")
    except Exception as e:
        logger.error(f"Export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


async def _export_to_csv(
    database: Database,
    include: List[str],
    company_id: Optional[str]
) -> StreamingResponse:
    """Export data to CSV format."""
    output = io.StringIO()

    try:
        if "clients" in include:
            clients = database.list_clients(company_id=company_id) if company_id else database.list_clients()
            if clients:
                writer = csv.DictWriter(
                    output,
                    fieldnames=["id", "name", "phone", "email", "company_id", "created_at"]
                )
                writer.writeheader()
                for client in clients:
                    writer.writerow({
                        "id": str(client.get("id", "")),
                        "name": str(client.get("name", "")),
                        "phone": str(client.get("phone", "")),
                        "email": str(client.get("email", "")),
                        "company_id": str(client.get("company_id", "")),
                        "created_at": str(client.get("created_at", "")),
                    })

        if "orders" in include or "portraits" in include:
            if company_id:
                clients = database.list_clients(company_id=company_id)
                client_ids = [client["id"] for client in clients]
                records = []
                for client_id in client_ids:
                    records.extend(database.list_ar_content(client_id))
            else:
                records = database.list_ar_content()

            if records:
                writer = csv.DictWriter(
                    output,
                    fieldnames=[
                        "portrait_id", "client_id", "client_name", "client_phone",
                        "view_count", "created_at", "company_id"
                    ]
                )
                writer.writeheader()
                for record in records:
                    writer.writerow({
                        "portrait_id": str(record.get("id", "")),
                        "client_id": str(record.get("client_id", "")),
                        "client_name": str(record.get("client_name", "")),
                        "client_phone": str(record.get("client_phone", "")),
                        "view_count": str(record.get("view_count", 0)),
                        "created_at": str(record.get("created_at", "")),
                        "company_id": str(record.get("company_id", "")),
                    })

        output.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=export_{timestamp}.csv"}
        )
    except Exception as e:
        logger.error(f"Error exporting to CSV: {e}", exc_info=True)
        raise


async def _export_to_json(
    database: Database,
    include: List[str],
    company_id: Optional[str]
) -> StreamingResponse:
    """Export data to JSON format."""
    export_data = {}

    if "clients" in include:
        clients = database.list_clients(company_id=company_id) if company_id else database.list_clients()
        export_data["clients"] = clients

    if "orders" in include or "portraits" in include:
        if company_id:
            clients = database.list_clients(company_id=company_id)
            client_ids = [client["id"] for client in clients]
            records = []
            for client_id in client_ids:
                records.extend(database.list_ar_content(client_id))
        else:
            records = database.list_ar_content()
        export_data["records"] = records

    output = io.BytesIO()
    json_data = json.dumps(export_data, ensure_ascii=False, indent=2, default=str)
    output.write(json_data.encode())
    output.seek(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=export_{timestamp}.json"}
    )


@router.get("/content-stats")
async def get_content_stats(
    company_id: Optional[str] = None,
    _: str = Depends(require_admin)
) -> List[Dict[str, Any]]:
    """Return aggregated AR content statistics for the admin dashboard."""
    database = get_database()

    # Get portraits for the specified company
    if company_id:
        clients = database.list_clients(company_id=company_id)
        client_ids = [client["id"] for client in clients]
        records = []
        for client_id in client_ids:
            client_records = database.list_ar_content(client_id)
            records.extend(client_records)
    else:
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


@router.get("/admin/storage", response_class=HTMLResponse)
async def admin_storage_page(request: Request):
    """Admin storage management page."""
    from app.main import get_current_app
    app = get_current_app()
    templates = app.state.templates
    
    # Verify admin user
    auth_token = request.cookies.get("authToken")
    if not auth_token:
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        tokens = app.state.tokens
        username = tokens.verify_token(auth_token)
        if not username:
            return RedirectResponse(url="/admin/login", status_code=302)
        
        database = app.state.database
        user = database.get_user(username)
        if not user or not user.get("is_admin", False):
            return RedirectResponse(url="/admin/login", status_code=302)
        
        return templates.TemplateResponse("admin_storage.html", {"request": request})
    
    except Exception as exc:
        logger.error(f"Error rendering admin storage page: {exc}")
        return RedirectResponse(url="/admin/login", status_code=302)
