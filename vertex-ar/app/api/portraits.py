"""
Portrait management endpoints for Vertex AR API.
"""
import base64
import math
import shutil
import uuid
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

import qrcode
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query, status

from app.api.auth import get_current_user, require_admin
from app.cache import CacheManager
from app.config import settings
from app.database import Database
from app.models import ClientResponse, PortraitResponse, VideoResponse
from app.main import get_current_app
from nft_marker_generator import NFTMarkerConfig, NFTMarkerGenerator
from utils import format_bytes
from logging_setup import get_logger

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


def get_cache() -> Optional[CacheManager]:
    """Get cache manager instance."""
    try:
        app = get_current_app()
        return getattr(app.state, 'cache_manager', None)
    except Exception:
        return None


async def invalidate_portrait_cache() -> None:
    """Invalidate portrait listing cache when data changes."""
    cache = get_cache()
    if cache:
        await cache.invalidate_all()
        logger.info("Portrait cache invalidated")


def _portrait_to_response(portrait: Dict[str, Any]) -> PortraitResponse:
    """Convert database record to API response."""
    return PortraitResponse(
        id=portrait["id"],
        client_id=portrait["client_id"],
        folder_id=portrait.get("folder_id"),
        permanent_link=portrait["permanent_link"],
        qr_code_base64=portrait.get("qr_code"),
        image_path=portrait["image_path"],
        view_count=portrait["view_count"],
        created_at=portrait["created_at"],
        subscription_end=portrait.get("subscription_end"),
        lifecycle_status=portrait.get("lifecycle_status", "active"),
        last_status_change=portrait.get("last_status_change"),
    )


def _video_to_response(video: Dict[str, Any]) -> VideoResponse:
    """Convert video record to API response."""
    return VideoResponse(
        id=video["id"],
        portrait_id=video["portrait_id"],
        video_path=video["video_path"],
        is_active=bool(video["is_active"]),
        created_at=video["created_at"],
    )


@router.post("/", response_model=PortraitResponse, status_code=status.HTTP_201_CREATED)
async def create_portrait(
    client_id: str,
    image: UploadFile = File(...),
    folder_id: Optional[str] = Form(None),
    username: str = Depends(get_current_user)
) -> PortraitResponse:
    """Create a new portrait for a client."""
    database = get_database()
    
    # Invalidate cache after creation
    await invalidate_portrait_cache()
    
    # Check if client exists
    client = database.get_client(client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Check if folder exists (if provided)
    if folder_id:
        folder = database.get_folder(folder_id)
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found"
            )
    
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file")
    
    # Generate UUID and paths
    portrait_id = str(uuid.uuid4())
    permanent_link = f"portrait_{portrait_id}"
    
    app = get_current_app()
    storage_manager = app.state.storage_manager
    storage_root = app.state.config["STORAGE_ROOT"]
    base_url = app.state.config["BASE_URL"]
    
    # Get company ID for client-specific storage
    company_id = client.get('company_id')
    
    # Generate paths for storage
    portrait_image_path = f"portraits/{client_id}/{portrait_id}.jpg"
    portrait_preview_path = f"portraits/{client_id}/{portrait_id}_preview.webp"
    
    # Save image using company-specific storage manager
    image.file.seek(0)
    image_content = await image.read()
    
    # Use company-specific storage adapter if available
    if company_id:
        storage_adapter = storage_manager.get_adapter_for_content(company_id, "portraits")
    else:
        storage_adapter = storage_manager.get_adapter("portraits")
    
    await storage_adapter.save_file(image_content, portrait_image_path)
    
    # Generate image preview with improved quality and WebP support
    from preview_generator import PreviewGenerator
    image_preview_path_saved = None
    
    try:
        image_preview = PreviewGenerator.generate_image_preview(image_content, size=(300, 300), format='webp')
        if image_preview:
            await storage_adapter.save_file(image_preview, portrait_preview_path)
            image_preview_path_saved = portrait_preview_path
            from logging_setup import get_logger
            logger = get_logger(__name__)
            logger.info(f"Portrait preview created: {portrait_preview_path}")
    except Exception as e:
        from logging_setup import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error generating portrait preview: {e}")
    
    # Generate QR code
    portrait_url = f"{base_url}/portrait/{permanent_link}"
    qr_img = qrcode.make(portrait_url)
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode()
    
    # Generate NFT markers with increased image size limits
    from nft_marker_generator import NFTMarkerConfig, NFTMarkerGenerator
    nft_generator = NFTMarkerGenerator(storage_root)
    config = NFTMarkerConfig(
        feature_density="high", 
        levels=3,
        max_image_size=8192,  # Increased from 4096 to support larger images
        max_image_area=50_000_000  # Increased from 16_777_216 to support larger images
    )
    
    # Get image for NFT generation (save temporarily if needed)
    temp_image_path = None
    try:
        if storage_manager.get_storage_type("portraits") == "local":
            temp_image_path = storage_root / portrait_image_path
        else:
            # Save temporarily for NFT generation
            temp_image_path = storage_root / f"temp_{portrait_id}.jpg"
            with open(temp_image_path, "wb") as f:
                f.write(image_content)
        
        marker_result = nft_generator.generate_marker(str(temp_image_path), portrait_id, config)
    finally:
        # Clean up temp file
        if temp_image_path and temp_image_path.name.startswith("temp_") and temp_image_path.exists():
            temp_image_path.unlink()
    
    # Create portrait in database
    db_portrait = database.create_portrait(
        portrait_id=portrait_id,
        client_id=client_id,
        image_path=portrait_image_path,
        marker_fset=marker_result.fset_path,
        marker_fset3=marker_result.fset3_path,
        marker_iset=marker_result.iset_path,
        permanent_link=permanent_link,
        qr_code=qr_base64,
        image_preview_path=image_preview_path_saved,
        folder_id=folder_id,
    )
    
    # Ensure QR code is included in response payload
    db_portrait["qr_code"] = qr_base64
    
    # Get public URLs using company-specific storage manager
    if db_portrait.get("image_path"):
        db_portrait["image_url"] = storage_adapter.get_public_url(db_portrait["image_path"])
    if db_portrait.get("image_preview_path"):
        db_portrait["preview_url"] = storage_adapter.get_public_url(db_portrait["image_preview_path"])
    
    return _portrait_to_response(db_portrait)


@router.get("/")
async def list_portraits(
    client_id: Optional[str] = Query(None),
    folder_id: Optional[str] = Query(None),
    company_id: Optional[str] = Query(None),
    lifecycle_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(None, ge=1, le=settings.CACHE_PAGE_SIZE_MAX, description="Items per page"),
    include_preview: bool = Query(False, description="Include base64-encoded preview data"),
    username: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get paginated list of portraits with optional filters.
    
    Returns:
        {
            "items": [...],
            "total": 100,
            "page": 1,
            "page_size": 50,
            "total_pages": 2
        }
    """
    database = get_database()
    cache = get_cache()
    
    # Use default page size if not specified
    if page_size is None:
        page_size = settings.CACHE_PAGE_SIZE_DEFAULT
    
    # Generate cache key
    cache_key_parts = (
        "portraits",
        "list",
        client_id or "all",
        folder_id or "all",
        company_id or "all",
        lifecycle_status or "all",
        page,
        page_size,
        include_preview,
    )
    
    # Try to get from cache
    cached_result = None
    if cache and not include_preview:  # Don't cache preview data (too large)
        cached_result = await cache.get(*cache_key_parts)
        if cached_result:
            logger.debug("Cache hit for portrait list", page=page, page_size=page_size)
            return cached_result
    
    # Fetch from database
    portraits = database.list_portraits_paginated(
        page=page,
        page_size=page_size,
        client_id=client_id,
        folder_id=folder_id,
        company_id=company_id,
        lifecycle_status=lifecycle_status,
    )
    
    total = database.count_portraits(
        client_id=client_id,
        folder_id=folder_id,
        company_id=company_id,
        lifecycle_status=lifecycle_status,
    )
    
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    
    # Convert to response format
    items = []
    if not include_preview:
        items = [_portrait_to_response(portrait).dict() for portrait in portraits]
    else:
        # Include preview data
        from pathlib import Path
        
        for portrait in portraits:
            portrait_dict = _portrait_to_response(portrait).dict()
            
            # Add preview data if available
            preview_data = None
            image_preview_path = portrait.get("image_preview_path")
            if image_preview_path:
                try:
                    preview_path = Path(image_preview_path)
                    if preview_path.exists():
                        with open(preview_path, "rb") as f:
                            preview_content = base64.b64encode(f.read()).decode()
                            # Determine format from file extension
                            if image_preview_path.endswith('.webp'):
                                preview_data = f"data:image/webp;base64,{preview_content}"
                            else:
                                preview_data = f"data:image/jpeg;base64,{preview_content}"
                except Exception as e:
                    logger.warning(f"Failed to load preview for portrait {portrait['id']}: {e}")
            
            portrait_dict['image_preview_data'] = preview_data
            items.append(portrait_dict)
    
    result = {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }
    
    # Cache result (only if not including previews)
    if cache and not include_preview:
        await cache.set(result, *cache_key_parts, ttl=settings.CACHE_TTL)
        logger.debug("Cached portrait list", page=page, page_size=page_size)
    
    return result


@router.get("/list", response_model=List[PortraitResponse])
async def list_portraits_legacy(
    client_id: Optional[str] = None,
    _: str = Depends(require_admin)
) -> List[PortraitResponse]:
    """Legacy endpoint: list portraits via query parameter (admin only)."""
    database = get_database()
    portraits = database.list_portraits(client_id)
    return [_portrait_to_response(portrait) for portrait in portraits]


@router.get("/admin/list-with-preview")
async def list_portraits_with_preview(
    company_id: Optional[str] = Query(None),
    lifecycle_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(None, ge=1, le=settings.CACHE_PAGE_SIZE_MAX, description="Items per page"),
    _: str = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get paginated portraits with preview images and video info for admin dashboard.
    
    This is the preview-heavy endpoint used by the admin dashboard.
    Supports pagination and caching to reduce database/storage load.
    """
    database = get_database()
    cache = get_cache()
    
    # Use default page size if not specified
    if page_size is None:
        page_size = settings.CACHE_PAGE_SIZE_DEFAULT
    
    # Generate cache key
    cache_key_parts = (
        "portraits",
        "admin_preview",
        company_id or "all",
        lifecycle_status or "all",
        page,
        page_size,
    )
    
    # Try to get from cache
    cached_result = None
    if cache:
        cached_result = await cache.get(*cache_key_parts)
        if cached_result:
            logger.debug("Cache hit for admin portrait preview list", page=page, page_size=page_size)
            return cached_result
    
    # Fetch paginated portraits from database
    portraits = database.list_portraits_paginated(
        page=page,
        page_size=page_size,
        company_id=company_id,
        lifecycle_status=lifecycle_status,
    )
    
    total = database.count_portraits(
        company_id=company_id,
        lifecycle_status=lifecycle_status,
    )
    
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    
    logger.info(
        f"Loading page {page}/{total_pages} ({len(portraits)} portraits) with previews",
        company_id=company_id or "all",
        total=total
    )
    
    result = []
    for portrait in portraits:
        try:
            preview_data = None
            image_preview_path = portrait.get("image_preview_path")
            logger.info(f"Portrait {portrait['id']}: image_preview_path={image_preview_path}")
            if image_preview_path:
                try:
                    from pathlib import Path
                    preview_path = Path(image_preview_path)
                    if preview_path.exists():
                        with open(preview_path, "rb") as f:
                            preview_data = base64.b64encode(f.read()).decode()
                            logger.info(f"Successfully loaded image preview for portrait {portrait['id']}, size={len(preview_data)}")
                    else:
                        logger.warning(f"Preview path does not exist for portrait {portrait['id']}: {preview_path}")
                except Exception as e:
                    logger.warning(f"Failed to read preview for portrait {portrait['id']}: {e}")
            
            # Get client information
            client = database.get_client(portrait["client_id"])
            
            videos = database.list_videos(portrait["id"])
            
            videos_with_previews = []
            active_video_description = "Нет активного видео"
            
            for v in videos:
                video_preview_data = None
                video_preview_path = v.get("video_preview_path")
                logger.info(f"Video {v['id']}: video_preview_path={video_preview_path}")
                if video_preview_path:
                    try:
                        from pathlib import Path
                        preview_path = Path(video_preview_path)
                        if preview_path.exists():
                            with open(preview_path, "rb") as f:
                                video_preview_data = base64.b64encode(f.read()).decode()
                                logger.info(f"Successfully loaded video preview for video {v['id']}, size={len(video_preview_data)}")
                        else:
                            logger.warning(f"Video preview path does not exist for video {v['id']}: {preview_path}")
                    except Exception as e:
                        logger.warning(f"Failed to read video preview for video {v['id']}: {e}")
                
                # Check if this is the active video
                if v.get("is_active"):
                    active_video_description = v.get("description", "Активное видео без описания")
                
                videos_with_previews.append({
                    "id": v["id"],
                    "is_active": bool(v["is_active"]),
                    "created_at": v.get("created_at"),
                    "preview": f"data:image/webp;base64,{video_preview_data}" if video_preview_data and video_preview_path and video_preview_path.endswith('.webp') else f"data:image/jpeg;base64,{video_preview_data}" if video_preview_data else ""
                })
            
            result.append({
                "id": portrait["id"],
                "client_id": portrait["client_id"],
                "permanent_link": portrait["permanent_link"],
                "view_count": portrait.get("view_count", 0),
                "created_at": portrait.get("created_at"),
                "preview": preview_data or "",
                "videos": videos_with_previews,
                "client_name": client["name"] if client else "N/A",
                "client_phone": client["phone"] if client else "N/A",
                "active_video_description": active_video_description,
                "image_preview_data": f"data:image/webp;base64,{preview_data}" if preview_data and image_preview_path and image_preview_path.endswith('.webp') else f"data:image/jpeg;base64,{preview_data}" if preview_data else "",
                "qr_code_base64": f"data:image/png;base64,{portrait.get('qr_code', '')}" if portrait.get('qr_code') else ""
            })
        except Exception as e:
            logger.error(f"Error processing portrait {portrait.get('id')}: {e}")
            continue
    
    response_data = {
        "portraits": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }
    
    # Cache the result
    if cache:
        await cache.set(response_data, *cache_key_parts, ttl=settings.CACHE_TTL)
        logger.debug("Cached admin portrait preview list", page=page, page_size=page_size)
    
    logger.info(f"Returning page {page}/{total_pages} with {len(result)} portraits with previews")
    return response_data


@router.get("/{portrait_id}/analyze", response_model=Dict[str, Any])
async def analyze_portrait_image(
    portrait_id: str,
    _: str = Depends(require_admin)
) -> Dict[str, Any]:
    """Analyze portrait image for quality metrics."""
    from logging_setup import get_logger
    logger = get_logger(__name__)
    
    database = get_database()
    portrait = database.get_portrait(portrait_id)
    
    if not portrait:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portrait not found"
        )
    
    try:
        from nft_marker_generator import analyze_image
        image_path = portrait["image_path"]
        analysis = analyze_image(image_path)
        
        logger.info(f"Image analysis completed for portrait {portrait_id}")
        return analysis
        
    except Exception as e:
        logger.error(f"Failed to analyze image for portrait {portrait_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze image"
        )


@router.post("/{portrait_id}/regenerate-marker")
async def regenerate_portrait_marker(
    portrait_id: str,
    _: str = Depends(require_admin),
) -> Dict[str, Any]:
    """Regenerate NFT marker files for a portrait and remove outdated ones."""
    from logging_setup import get_logger

    logger = get_logger(__name__)
    database = get_database()

    portrait = database.get_portrait(portrait_id)
    if not portrait:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portrait not found",
        )

    image_path_value = portrait.get("image_path")
    if not image_path_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Portrait image path is missing")

    image_path = Path(image_path_value)
    if not image_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portrait image file not found")

    app = get_current_app()
    storage_root: Path = app.state.config["STORAGE_ROOT"]
    marker_name = portrait_id
    marker_dir = storage_root / "nft_markers" / marker_name

    backup_dir: Optional[Path] = None
    if marker_dir.exists():
        backup_suffix = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        backup_dir = marker_dir.parent / f"{marker_name}_backup_{backup_suffix}"
        try:
            shutil.move(str(marker_dir), str(backup_dir))
        except Exception as exc:
            logger.error("Failed to backup existing marker directory %s: %s", marker_dir, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to backup existing marker files",
            ) from exc

    nft_generator = NFTMarkerGenerator(storage_root)
    marker_config = NFTMarkerConfig(
        feature_density="high",
        levels=3,
        max_image_size=8192,
        max_image_area=50_000_000,
    )

    try:
        marker_result = nft_generator.generate_marker(image_path, marker_name, marker_config)
        database.update_portrait_marker_paths(
            portrait_id=portrait_id,
            marker_fset=marker_result.fset_path,
            marker_fset3=marker_result.fset3_path,
            marker_iset=marker_result.iset_path,
        )
    except Exception as exc:
        logger.error("Failed to regenerate NFT markers for portrait %s: %s", portrait_id, exc)
        if marker_dir.exists():
            shutil.rmtree(marker_dir, ignore_errors=True)
        if backup_dir and backup_dir.exists():
            try:
                shutil.move(str(backup_dir), str(marker_dir))
            except Exception as restore_exc:
                logger.error("Failed to restore marker backup for portrait %s: %s", portrait_id, restore_exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate NFT markers",
        ) from exc
    else:
        if backup_dir and backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)

    def format_size_response(bytes_value: Optional[int]) -> str:
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

    marker_files = [
        ("fset", marker_result.fset_path, ".fset"),
        ("fset3", marker_result.fset3_path, ".fset3"),
        ("iset", marker_result.iset_path, ".iset"),
    ]

    total_size = 0
    marker_updated_ts: Optional[float] = None
    marker_files_payload: List[Dict[str, Any]] = []

    for file_type, path_value, extension in marker_files:
        path_obj = Path(path_value)
        size_bytes = None
        modified_ts = None
        try:
            if path_obj.exists():
                stat_result = path_obj.stat()
                size_bytes = stat_result.st_size
                modified_ts = stat_result.st_mtime
        except OSError as exc:
            logger.warning("Failed to stat regenerated marker file %s: %s", path_obj, exc)
        if size_bytes:
            total_size += size_bytes
        if modified_ts:
            marker_updated_ts = max(marker_updated_ts or modified_ts, modified_ts)
        marker_files_payload.append({
            "type": file_type,
            "path": path_value,
            "size_bytes": size_bytes,
            "size_display": format_size_response(size_bytes),
            "download_name": f"{portrait_id}{extension}",
        })

    updated_at_iso: Optional[str] = None
    updated_at_display = None
    if marker_updated_ts:
        updated_dt = datetime.fromtimestamp(marker_updated_ts)
        updated_at_iso = updated_dt.isoformat()
        updated_at_display = updated_dt.strftime("%d.%m.%Y %H:%M:%S")

    response_payload: Dict[str, Any] = {
        "message": "NFT маркеры успешно перегенерированы",
        "marker_size_bytes": total_size,
        "marker_size_display": format_size_response(total_size),
        "marker_size_mb": round(total_size / (1024 * 1024), 2) if total_size else None,
        "updated_at": updated_at_iso,
        "updated_at_display": updated_at_display,
        "files": marker_files_payload,
        "has_files": any(item.get("size_bytes") for item in marker_files_payload),
    }

    return response_payload


@router.post("/{portrait_id}/videos", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def add_video_to_portrait(
    portrait_id: str,
    video: UploadFile = File(...),
    description: str = Form(None),
    username: str = Depends(require_admin)
) -> VideoResponse:
    """Add a new video to an existing portrait (admin only)."""
    from logging_setup import get_logger
    logger = get_logger(__name__)
    
    database = get_database()
    
    # Invalidate cache after video creation
    await invalidate_portrait_cache()
    
    # Check if portrait exists
    portrait = database.get_portrait(portrait_id)
    if not portrait:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portrait not found"
        )
    
    if not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid video file")
    
    # Generate UUID and paths
    video_id = str(uuid.uuid4())
    
    app = get_current_app()
    storage_root = app.state.config["STORAGE_ROOT"]
    
    # Create storage directories
    client_id = portrait["client_id"]
    portrait_storage = storage_root / "portraits" / client_id / portrait_id
    portrait_storage.mkdir(parents=True, exist_ok=True)
    
    # Read and save video
    video.file.seek(0)
    video_content = await video.read()
    video_path = portrait_storage / f"{video_id}.mp4"
    
    with open(video_path, "wb") as f:
        f.write(video_content)
    
    video_file_size_mb: int | None = None
    try:
        video_size_bytes = video_path.stat().st_size
        if video_size_bytes:
            video_file_size_mb = max(1, math.ceil(video_size_bytes / (1024 * 1024)))
    except OSError:
        video_file_size_mb = None
    
    # Generate video preview
    from preview_generator import PreviewGenerator
    video_preview_path = None
    
    try:
        video_preview = PreviewGenerator.generate_video_preview(video_content, size=(300, 300), format='webp')
        if video_preview and len(video_preview) > 0:
            video_preview_path = portrait_storage / f"{video_id}_preview.webp"
            with open(video_preview_path, "wb") as f:
                f.write(video_preview)
            logger.info(f"Video preview created: {video_preview_path}, size: {len(video_preview)} bytes")
        else:
            logger.warning(f"Failed to generate video preview for video {video_id}")
    except Exception as e:
        logger.error(f"Error generating video preview: {e}")
    
    # Create video in database (not active by default)
    db_video = database.create_video(
        video_id=video_id,
        portrait_id=portrait_id,
        video_path=str(video_path),
        is_active=False,  # New videos are not active by default
        video_preview_path=str(video_preview_path) if video_preview_path else None,
        description=description,
        file_size_mb=video_file_size_mb,
    )
    
    logger.info(f"Video added to portrait {portrait_id}: {video_id}")
    
    return _video_to_response(db_video)


@router.delete("/{portrait_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portrait(
    portrait_id: str,
    username: str = Depends(require_admin)
):
    """Delete a portrait and all its associated data."""
    from logging_setup import get_logger
    import shutil
    logger = get_logger(__name__)
    
    database = get_database()
    
    # Invalidate cache after deletion
    await invalidate_portrait_cache()
    
    # Check if portrait exists
    portrait = database.get_portrait(portrait_id)
    if not portrait:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portrait not found"
        )
    
    try:
        # Get all videos for this portrait
        videos = database.list_videos(portrait_id)
        
        # Delete portrait from database (this should cascade delete videos)
        deleted = database.delete_portrait(portrait_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete portrait"
            )
        
        # Delete files from storage
        app = get_current_app()
        storage_root = app.state.config["STORAGE_ROOT"]
        client_id = portrait["client_id"]
        portrait_storage = storage_root / "portraits" / client_id / portrait_id
        
        if portrait_storage.exists():
            shutil.rmtree(portrait_storage)
            logger.info(f"Deleted portrait storage: {portrait_storage}")
        
        # Delete NFT markers
        marker_paths = [
            portrait.get("marker_fset"),
            portrait.get("marker_fset3"),
            portrait.get("marker_iset")
        ]
        
        for marker_path in marker_paths:
            if marker_path:
                marker_file = storage_root / marker_path
                if marker_file.exists():
                    marker_file.unlink()
                    logger.info(f"Deleted marker file: {marker_file}")
        
        logger.info(f"Portrait {portrait_id} deleted successfully by {username}")
        
    except Exception as e:
        logger.error(f"Failed to delete portrait {portrait_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete portrait"
        )


@router.get("/{portrait_id}", response_model=PortraitResponse)
async def get_portrait(
    portrait_id: str,
    username: str = Depends(get_current_user)
) -> PortraitResponse:
    """Get portrait by ID."""
    database = get_database()
    portrait = database.get_portrait(portrait_id)
    
    if not portrait:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portrait not found"
        )
    
    return _portrait_to_response(portrait)


@router.get("/link/{permanent_link}", response_model=PortraitResponse)
async def get_portrait_by_link(permanent_link: str) -> PortraitResponse:
    """Get portrait by permanent link (public endpoint)."""
    database = get_database()
    portrait = database.get_portrait_by_link(permanent_link)
    
    if not portrait:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portrait not found"
        )
    
    # Increment view count
    database.increment_portrait_views(portrait["id"])
    portrait["view_count"] = portrait.get("view_count", 0) + 1
    
    return _portrait_to_response(portrait)


@router.get("/{portrait_id}/details", response_model=Dict[str, Any])
async def get_portrait_details(
    portrait_id: str,
    _: str = Depends(require_admin)
) -> Dict[str, Any]:
    """Return portrait details along with client and videos."""
    database = get_database()
    portrait = database.get_portrait(portrait_id)
    if not portrait:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portrait not found")
    client = database.get_client(portrait["client_id"])
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    videos = database.list_videos(portrait_id)
    portrait_response = _portrait_to_response(portrait)
    client_response = ClientResponse(
        id=client["id"],
        phone=client["phone"],
        name=client["name"],
        created_at=client["created_at"],
    )
    videos_response = [_video_to_response(video) for video in videos]
    
    return {
        "portrait": portrait_response.model_dump(),
        "client": client_response.model_dump(),
        "videos": [video.model_dump() for video in videos_response],
    }


@router.delete("/{portrait_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portrait(
    portrait_id: str,
    username: str = Depends(get_current_user)
):
    """Delete portrait."""
    database = get_database()
    
    # Check if portrait exists
    existing_portrait = database.get_portrait(portrait_id)
    if not existing_portrait:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portrait not found"
        )
    
    # Delete portrait
    deleted = database.delete_portrait(portrait_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete portrait"
        )