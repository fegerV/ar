"""
Portrait management endpoints for Vertex AR API.
"""
import base64
import uuid
from io import BytesIO
from typing import Any, Dict, List, Optional

import qrcode
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.auth import get_current_user, require_admin
from app.database import Database
from app.models import ClientResponse, PortraitResponse, VideoResponse
from app.main import get_current_app

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


def _portrait_to_response(portrait: Dict[str, Any]) -> PortraitResponse:
    """Convert database record to API response."""
    return PortraitResponse(
        id=portrait["id"],
        client_id=portrait["client_id"],
        permanent_link=portrait["permanent_link"],
        qr_code_base64=portrait.get("qr_code"),
        image_path=portrait["image_path"],
        view_count=portrait["view_count"],
        created_at=portrait["created_at"],
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
    username: str = Depends(get_current_user)
) -> PortraitResponse:
    """Create a new portrait for a client."""
    database = get_database()
    
    # Check if client exists
    client = database.get_client(client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file")
    
    # Generate UUID and paths
    portrait_id = str(uuid.uuid4())
    permanent_link = f"portrait_{portrait_id}"
    
    app = get_current_app()
    storage_root = app.state.config["STORAGE_ROOT"]
    base_url = app.state.config["BASE_URL"]
    
    # Create storage directories
    client_storage = storage_root / "portraits" / client_id
    client_storage.mkdir(parents=True, exist_ok=True)
    
    # Read and save image
    image.file.seek(0)
    image_content = await image.read()
    image_path = client_storage / f"{portrait_id}.jpg"
    
    with open(image_path, "wb") as f:
        f.write(image_content)
    
    # Generate image preview
    from preview_generator import PreviewGenerator
    image_preview_path = None
    
    try:
        image_preview = PreviewGenerator.generate_image_preview(image_content)
        if image_preview:
            image_preview_path = client_storage / f"{portrait_id}_preview.jpg"
            with open(image_preview_path, "wb") as f:
                f.write(image_preview)
            from logging_setup import get_logger
            logger = get_logger(__name__)
            logger.info(f"Portrait preview created: {image_preview_path}")
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
    marker_result = nft_generator.generate_marker(str(image_path), portrait_id, config)
    
    # Create portrait in database
    db_portrait = database.create_portrait(
        portrait_id=portrait_id,
        client_id=client_id,
        image_path=str(image_path),
        marker_fset=marker_result.fset_path,
        marker_fset3=marker_result.fset3_path,
        marker_iset=marker_result.iset_path,
        permanent_link=permanent_link,
        qr_code=qr_base64,
        image_preview_path=str(image_preview_path) if image_preview_path else None,
    )
    
    # Ensure QR code is included in response payload
    db_portrait["qr_code"] = qr_base64
    
    return _portrait_to_response(db_portrait)


@router.get("/", response_model=List[PortraitResponse])
async def list_portraits(
    client_id: Optional[str] = None,
    username: str = Depends(get_current_user)
) -> List[PortraitResponse]:
    """Get list of portraits (optionally filtered by client)."""
    database = get_database()
    portraits = database.list_portraits(client_id)
    
    return [_portrait_to_response(portrait) for portrait in portraits]


@router.get("/list", response_model=List[PortraitResponse])
async def list_portraits_legacy(
    client_id: Optional[str] = None,
    _: str = Depends(require_admin)
) -> List[PortraitResponse]:
    """Legacy endpoint: list portraits via query parameter (admin only)."""
    database = get_database()
    portraits = database.list_portraits(client_id)
    return [_portrait_to_response(portrait) for portrait in portraits]


@router.get("/admin/list-with-preview", response_model=List[Dict[str, Any]])
async def list_portraits_with_preview(
    _: str = Depends(require_admin)
) -> List[Dict[str, Any]]:
    """Get all portraits with preview images and video info for admin dashboard."""
    from logging_setup import get_logger
    logger = get_logger(__name__)
    
    database = get_database()
    portraits = database.list_portraits()
    
    result = []
    for portrait in portraits:
        try:
            preview_data = None
            image_preview_path = portrait.get("image_preview_path")
            if image_preview_path:
                try:
                    from pathlib import Path
                    preview_path = Path(image_preview_path)
                    if preview_path.exists():
                        with open(preview_path, "rb") as f:
                            import base64
                            preview_data = base64.b64encode(f.read()).decode()
                except Exception as e:
                    logger.warning(f"Failed to read preview for portrait {portrait['id']}: {e}")
            
            videos = database.list_videos(portrait["id"])
            
            result.append({
                "id": portrait["id"],
                "client_id": portrait["client_id"],
                "permanent_link": portrait["permanent_link"],
                "view_count": portrait.get("view_count", 0),
                "created_at": portrait.get("created_at"),
                "preview": preview_data or "",
                "videos": [
                    {
                        "id": v["id"],
                        "is_active": bool(v["is_active"]),
                        "created_at": v.get("created_at")
                    }
                    for v in videos
                ]
            })
        except Exception as e:
            logger.error(f"Error processing portrait {portrait.get('id')}: {e}")
            continue
    
    return result


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