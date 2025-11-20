"""
Mobile API endpoints for React Native application.
Provides optimized data structures for mobile AR viewing.
"""
import base64
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.database import Database
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


# Request/Response models for mobile API

class DeviceInfo(BaseModel):
    """Device information for analytics."""
    platform: str = Field(..., description="ios or android")
    os_version: str = Field(..., description="Operating system version")
    app_version: str = Field(..., description="Mobile app version")
    model: Optional[str] = Field(None, description="Device model")


class ARInfo(BaseModel):
    """AR scanning information."""
    scan_time_ms: Optional[int] = Field(None, description="Time to detect marker in milliseconds")
    fps_average: Optional[float] = Field(None, description="Average FPS during session")
    marker_lost_count: Optional[int] = Field(None, description="Number of times marker was lost")


class PortraitViewRequest(BaseModel):
    """Request for tracking portrait view."""
    timestamp: str = Field(..., description="ISO8601 timestamp")
    duration_seconds: int = Field(..., ge=0, description="View duration in seconds")
    device_info: DeviceInfo
    ar_info: Optional[ARInfo] = None
    session_id: Optional[str] = Field(None, description="Unique session identifier")


class ImageInfo(BaseModel):
    """Image information."""
    url: str
    preview_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class MarkersInfo(BaseModel):
    """NFT markers information."""
    fset: str
    fset3: str
    iset: str


class VideoInfo(BaseModel):
    """Video information."""
    id: str
    url: str
    preview_url: Optional[str] = None
    description: Optional[str] = None
    file_size_mb: Optional[float] = None
    duration_seconds: Optional[int] = None


class ClientInfo(BaseModel):
    """Client information."""
    id: str
    name: str
    phone: str


class MobilePortraitResponse(BaseModel):
    """Portrait response optimized for mobile."""
    id: str
    permanent_link: str
    client: ClientInfo
    image: ImageInfo
    markers: MarkersInfo
    active_video: Optional[VideoInfo] = None
    qr_code: Optional[str] = None
    view_count: int
    created_at: str


class PortraitsListResponse(BaseModel):
    """Paginated list of portraits."""
    portraits: List[MobilePortraitResponse]
    total: int
    page: int
    page_size: int


class ViewResponse(BaseModel):
    """Response for view tracking."""
    success: bool
    view_count: int


class CompanyInfo(BaseModel):
    """Company information."""
    id: str
    name: str
    portraits_count: int
    created_at: str


class MarkerStatusFile(BaseModel):
    """Marker file status."""
    size: int
    updated_at: str


class MarkerStatusResponse(BaseModel):
    """Marker availability status."""
    available: bool
    files: Dict[str, MarkerStatusFile]
    total_size_mb: float


def _build_portrait_response(
    portrait: Dict[str, Any],
    client: Dict[str, Any],
    active_video: Optional[Dict[str, Any]],
    base_url: str,
    storage_root: Path
) -> MobilePortraitResponse:
    """Build mobile portrait response from database records."""
    
    # Build image URLs
    image_rel_path = Path(portrait["image_path"]).relative_to(storage_root)
    image_url = f"{base_url}/storage/{image_rel_path}"
    
    image_preview_url = None
    if portrait.get("image_preview_path"):
        preview_rel_path = Path(portrait["image_preview_path"]).relative_to(storage_root)
        image_preview_url = f"{base_url}/storage/{preview_rel_path}"
    
    # Build marker URLs
    portrait_id = portrait["id"]
    markers = MarkersInfo(
        fset=f"{base_url}/nft-markers/{portrait_id}/{portrait_id}.fset",
        fset3=f"{base_url}/nft-markers/{portrait_id}/{portrait_id}.fset3",
        iset=f"{base_url}/nft-markers/{portrait_id}/{portrait_id}.iset"
    )
    
    # Build video info if available
    video_info = None
    if active_video:
        video_rel_path = Path(active_video["video_path"]).relative_to(storage_root)
        video_url = f"{base_url}/storage/{video_rel_path}"
        
        video_preview_url = None
        if active_video.get("video_preview_path"):
            video_preview_rel = Path(active_video["video_preview_path"]).relative_to(storage_root)
            video_preview_url = f"{base_url}/storage/{video_preview_rel}"
        
        video_info = VideoInfo(
            id=active_video["id"],
            url=video_url,
            preview_url=video_preview_url,
            description=active_video.get("description"),
            file_size_mb=active_video.get("file_size_mb")
        )
    
    # Build client info
    client_info = ClientInfo(
        id=client["id"],
        name=client["name"],
        phone=client["phone"]
    )
    
    # QR code
    qr_code = None
    if portrait.get("qr_code"):
        qr_code = f"data:image/png;base64,{portrait['qr_code']}"
    
    return MobilePortraitResponse(
        id=portrait["id"],
        permanent_link=portrait["permanent_link"],
        client=client_info,
        image=ImageInfo(
            url=image_url,
            preview_url=image_preview_url
        ),
        markers=markers,
        active_video=video_info,
        qr_code=qr_code,
        view_count=portrait.get("view_count", 0),
        created_at=portrait["created_at"]
    )


@router.get("/portraits", response_model=PortraitsListResponse)
async def list_portraits_mobile(
    company_id: Optional[str] = Query(None, description="Filter by company ID"),
    client_id: Optional[str] = Query(None, description="Filter by client ID"),
    include_inactive: bool = Query(False, description="Include portraits without active video"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    username: Optional[str] = Depends(get_current_user)
) -> PortraitsListResponse:
    """
    Get list of portraits optimized for mobile application.
    
    Returns portraits with all necessary URLs and metadata for AR viewing.
    Optionally filtered by company or client.
    """
    database = get_database()
    from app.main import get_current_app
    app = get_current_app()
    base_url = app.state.config["BASE_URL"]
    storage_root = app.state.config["STORAGE_ROOT"]
    
    logger.info(
        "mobile_portraits_list_request",
        company_id=company_id,
        client_id=client_id,
        include_inactive=include_inactive,
        page=page,
        page_size=page_size,
        username=username
    )
    
    # Get portraits based on filters
    all_portraits = []
    
    if client_id:
        # Filter by specific client
        all_portraits = database.list_portraits(client_id=client_id)
    elif company_id:
        # Filter by company - get all clients first
        clients = database.list_clients(company_id=company_id)
        for client in clients:
            portraits = database.list_portraits(client_id=client["id"])
            all_portraits.extend(portraits)
    else:
        # Get all portraits
        all_portraits = database.list_portraits()
    
    # Filter out portraits without active video if needed
    portraits_with_data = []
    for portrait in all_portraits:
        client = database.get_client(portrait["client_id"])
        if not client:
            continue
        
        active_video = database.get_active_video(portrait["id"])
        
        if not include_inactive and not active_video:
            continue
        
        try:
            portrait_response = _build_portrait_response(
                portrait, client, active_video, base_url, storage_root
            )
            portraits_with_data.append(portrait_response)
        except Exception as e:
            logger.error(f"Error building portrait response for {portrait['id']}: {e}")
            continue
    
    # Apply pagination
    total = len(portraits_with_data)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_portraits = portraits_with_data[start_idx:end_idx]
    
    logger.info(
        "mobile_portraits_list_response",
        total=total,
        returned=len(paginated_portraits),
        page=page,
        page_size=page_size
    )
    
    return PortraitsListResponse(
        portraits=paginated_portraits,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/portraits/{permanent_link}", response_model=MobilePortraitResponse)
async def get_portrait_by_link_mobile(permanent_link: str) -> MobilePortraitResponse:
    """
    Get specific portrait by permanent link (public endpoint).
    
    This endpoint is public and doesn't require authentication.
    Used for direct access via QR codes.
    """
    database = get_database()
    from app.main import get_current_app
    app = get_current_app()
    base_url = app.state.config["BASE_URL"]
    storage_root = app.state.config["STORAGE_ROOT"]
    
    logger.info("mobile_portrait_fetch_by_link", permanent_link=permanent_link)
    
    portrait = database.get_portrait_by_link(permanent_link)
    if not portrait:
        logger.warning("mobile_portrait_not_found", permanent_link=permanent_link)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portrait not found"
        )
    
    client = database.get_client(portrait["client_id"])
    if not client:
        logger.error("mobile_portrait_client_not_found", portrait_id=portrait["id"])
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    active_video = database.get_active_video(portrait["id"])
    if not active_video:
        logger.warning("mobile_portrait_no_active_video", portrait_id=portrait["id"])
    
    try:
        return _build_portrait_response(portrait, client, active_video, base_url, storage_root)
    except Exception as e:
        logger.error(f"Error building portrait response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to build portrait data"
        )


@router.post("/portraits/{portrait_id}/view", response_model=ViewResponse)
async def track_portrait_view(
    portrait_id: str,
    view_data: PortraitViewRequest
) -> ViewResponse:
    """
    Track portrait view from mobile app (public endpoint).
    
    Records view statistics and device/AR information for analytics.
    """
    database = get_database()
    
    logger.info(
        "mobile_portrait_view_tracked",
        portrait_id=portrait_id,
        duration_seconds=view_data.duration_seconds,
        platform=view_data.device_info.platform,
        session_id=view_data.session_id
    )
    
    # Check if portrait exists
    portrait = database.get_portrait(portrait_id)
    if not portrait:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portrait not found"
        )
    
    # Increment view count
    try:
        database.increment_portrait_views(portrait_id)
        updated_portrait = database.get_portrait(portrait_id)
        new_view_count = updated_portrait["view_count"]
        
        logger.info(
            "mobile_portrait_view_count_updated",
            portrait_id=portrait_id,
            new_count=new_view_count
        )
        
        return ViewResponse(
            success=True,
            view_count=new_view_count
        )
    except Exception as e:
        logger.error(f"Failed to increment view count for portrait {portrait_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to track view"
        )


@router.get("/companies", response_model=List[CompanyInfo])
async def list_companies_mobile(
    username: Optional[str] = Depends(get_current_user)
) -> List[CompanyInfo]:
    """
    Get list of companies with portrait counts.
    
    Used for company selection in mobile app.
    """
    database = get_database()
    
    logger.info("mobile_companies_list_request", username=username)
    
    companies = database.list_companies()
    
    result = []
    for company in companies:
        # Count portraits for this company
        clients = database.list_clients(company_id=company["id"])
        portraits_count = 0
        for client in clients:
            portraits = database.list_portraits(client_id=client["id"])
            portraits_count += len(portraits)
        
        result.append(CompanyInfo(
            id=company["id"],
            name=company["name"],
            portraits_count=portraits_count,
            created_at=company["created_at"]
        ))
    
    logger.info("mobile_companies_list_response", count=len(result))
    
    return result


@router.get("/portraits/{portrait_id}/marker-status", response_model=MarkerStatusResponse)
async def get_marker_status(
    portrait_id: str,
    username: Optional[str] = Depends(get_current_user)
) -> MarkerStatusResponse:
    """
    Check availability and status of NFT marker files.
    
    Returns file sizes and timestamps for cache management.
    """
    database = get_database()
    from app.main import get_current_app
    app = get_current_app()
    storage_root = app.state.config["STORAGE_ROOT"]
    
    logger.info("mobile_marker_status_check", portrait_id=portrait_id)
    
    portrait = database.get_portrait(portrait_id)
    if not portrait:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portrait not found"
        )
    
    marker_files = {
        "fset": portrait.get("marker_fset"),
        "fset3": portrait.get("marker_fset3"),
        "iset": portrait.get("marker_iset")
    }
    
    files_status = {}
    total_size = 0
    all_available = True
    
    for file_type, file_path in marker_files.items():
        if not file_path:
            all_available = False
            continue
        
        try:
            path = Path(file_path)
            if path.exists():
                stat = path.stat()
                files_status[file_type] = MarkerStatusFile(
                    size=stat.st_size,
                    updated_at=datetime.fromtimestamp(stat.st_mtime).isoformat()
                )
                total_size += stat.st_size
            else:
                all_available = False
        except Exception as e:
            logger.warning(f"Error checking marker file {file_path}: {e}")
            all_available = False
    
    total_size_mb = round(total_size / (1024 * 1024), 2)
    
    return MarkerStatusResponse(
        available=all_available and len(files_status) == 3,
        files=files_status,
        total_size_mb=total_size_mb
    )
