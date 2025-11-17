"""
Video management endpoints for Vertex AR API.
"""
import base64
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.auth import get_current_user, require_admin
from app.database import Database
from app.models import VideoResponse
from app.main import get_current_app
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


def _video_to_response(video: Dict[str, Any]) -> VideoResponse:
    """Convert raw database record to API response."""
    return VideoResponse(
        id=video["id"],
        portrait_id=video["portrait_id"],
        video_path=video["video_path"],
        is_active=bool(video["is_active"]),
        created_at=video["created_at"],
        file_size_mb=video.get("file_size_mb"),
    )


@router.post("/", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def create_video(
    portrait_id: str = Form(...),
    video: UploadFile = File(...),
    is_active: bool = Form(False),
    description: str = Form(None),
    username: str = Depends(get_current_user)
) -> VideoResponse:
    """Create a new video for a portrait."""
    database = get_database()
    
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
    
    # Calculate file size in MB
    file_size_bytes = len(video_content)
    file_size_mb = int(file_size_bytes / (1024 * 1024))  # Convert to MB and round down to integer
    
    logger.info(f"Video file size: {file_size_bytes} bytes = {file_size_mb} MB")
    
    with open(video_path, "wb") as f:
        f.write(video_content)
    
    # Generate video preview with improved quality and WebP support
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
    
    # Create video in database
    logger.info(f"Creating video with file_size_mb: {file_size_mb}")
    db_video = database.create_video(
        video_id=video_id,
        portrait_id=portrait_id,
        video_path=str(video_path),
        is_active=is_active,
        video_preview_path=str(video_preview_path) if video_preview_path else None,
        description=description,
        file_size_mb=file_size_mb,
    )
    
    logger.info(f"Database returned video: {db_video}")
    
    return VideoResponse(
        id=db_video["id"],
        portrait_id=db_video["portrait_id"],
        video_path=db_video["video_path"],
        is_active=bool(db_video["is_active"]),
        created_at=db_video["created_at"],
        file_size_mb=db_video.get("file_size_mb"),
    )


@router.get("/portrait/{portrait_id}", response_model=List[VideoResponse])
async def list_videos(
    portrait_id: str,
    username: str = Depends(get_current_user)
) -> List[VideoResponse]:
    """Get list of videos for a portrait."""
    database = get_database()
    
    # Check if portrait exists
    portrait = database.get_portrait(portrait_id)
    if not portrait:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portrait not found"
        )
    
    videos = database.list_videos(portrait_id)
    
    return [
        VideoResponse(
            id=video["id"],
            portrait_id=video["portrait_id"],
            video_path=video["video_path"],
            is_active=bool(video["is_active"]),
            created_at=video["created_at"],
            file_size_mb=video.get("file_size_mb"),
        )
        for video in videos
    ]


@router.get("/active/{portrait_id}", response_model=VideoResponse)
async def get_active_video(
    portrait_id: str,
    username: str = Depends(get_current_user)
) -> VideoResponse:
    """Get active video for a portrait."""
    database = get_database()
    
    # Check if portrait exists
    portrait = database.get_portrait(portrait_id)
    if not portrait:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portrait not found"
        )
    
    video = database.get_active_video(portrait_id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active video found for this portrait"
        )
    
    return VideoResponse(
        id=video["id"],
        portrait_id=video["portrait_id"],
        video_path=video["video_path"],
        is_active=bool(video["is_active"]),
        created_at=video["created_at"],
        file_size_mb=video.get("file_size_mb"),
    )


@router.put("/{video_id}/active", response_model=VideoResponse)
async def set_active_video(
    video_id: str,
    username: str = Depends(get_current_user)
) -> VideoResponse:
    """Set video as active for its portrait."""
    database = get_database()
    
    # Check if video exists
    video = database.get_video(video_id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    portrait_id = video["portrait_id"]
    
    # Set as active
    updated = database.set_active_video(video_id, portrait_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set active video"
        )
    
    # Return updated video
    updated_video = database.get_video(video_id)
    return VideoResponse(
        id=updated_video["id"],
        portrait_id=updated_video["portrait_id"],
        video_path=updated_video["video_path"],
        is_active=bool(updated_video["is_active"]),
        created_at=updated_video["created_at"],
        file_size_mb=updated_video.get("file_size_mb"),
    )


@router.get("/{video_id}/preview")
async def get_video_preview(
    video_id: str,
    _: str = Depends(require_admin)
) -> Dict[str, Any]:
    """Get video preview as base64 data."""
    database = get_database()
    video = database.get_video(video_id)
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    video_preview_path = video.get("video_preview_path")
    if not video_preview_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video preview not found"
        )
    
    try:
        from pathlib import Path
        app = get_current_app()
        base_dir = app.state.config["BASE_DIR"]
        
        # Handle both relative and absolute preview paths
        if video_preview_path.startswith("storage/"):
            preview_path = base_dir / video_preview_path
        elif video_preview_path.startswith("/"):
            preview_path = Path(video_preview_path)
        else:
            # Relative path, assume it's relative to storage root
            storage_root = app.state.config["STORAGE_ROOT"]
            preview_path = storage_root / video_preview_path
        
        logger.info(f"Looking for video preview at: {preview_path}")
        
        if preview_path.exists():
            with open(preview_path, "rb") as f:
                preview_bytes = f.read()
                
                # Check if file is not empty
                if len(preview_bytes) == 0:
                    logger.error(f"Video preview file is empty: {preview_path}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Video preview file is empty"
                    )
                
                # Encode to base64
                preview_data = base64.b64encode(preview_bytes).decode('utf-8')
                
                # Verify the base64 data is valid
                if not preview_data:
                    logger.error(f"Failed to encode video preview to base64: {preview_path}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to encode video preview"
                    )
                
                logger.info(f"Successfully loaded preview for video {video_id}, size: {len(preview_bytes)} bytes")
                
                # Determine format from file extension
                if video_preview_path.endswith('.webp'):
                    return {"preview_data": f"data:image/webp;base64,{preview_data}"}
                else:
                    return {"preview_data": f"data:image/jpeg;base64,{preview_data}"}
        else:
            logger.error(f"Video preview file not found at {preview_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video preview file not found"
            )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to load video preview for video {video_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load video preview"
        )


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    username: str = Depends(get_current_user)
) -> VideoResponse:
    """Get video by ID."""
    database = get_database()
    video = database.get_video(video_id)
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    return VideoResponse(
        id=video["id"],
        portrait_id=video["portrait_id"],
        video_path=video["video_path"],
        is_active=bool(video["is_active"]),
        created_at=video["created_at"],
        file_size_mb=video.get("file_size_mb"),
    )


@router.post("/{video_id}/activate", response_model=VideoResponse)
async def activate_video_admin(
    video_id: str,
    username: str = Depends(require_admin)
) -> VideoResponse:
    """Activate video for its portrait (admin only)."""
    database = get_database()
    
    # Check if video exists
    video = database.get_video(video_id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    portrait_id = video["portrait_id"]
    
    # Set as active
    updated = database.set_active_video(video_id, portrait_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate video"
        )
    
    logger.info(f"Video {video_id} activated for portrait {portrait_id} by {username}")
    
    # Return updated video
    updated_video = database.get_video(video_id)
    return _video_to_response(updated_video)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video_admin(
    video_id: str,
    username: str = Depends(require_admin)
):
    """Delete video (admin only)."""
    import shutil
    logger = get_logger(__name__)
    
    database = get_database()
    
    # Check if video exists
    existing_video = database.get_video(video_id)
    if not existing_video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    try:
        # Delete video from database
        deleted = database.delete_video(video_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete video"
            )
        
        # Delete video file and preview
        app = get_current_app()
        storage_root = app.state.config["STORAGE_ROOT"]
        
        video_path = existing_video.get("video_path")
        if video_path:
            video_file = storage_root / video_path
            if video_file.exists():
                video_file.unlink()
                logger.info(f"Deleted video file: {video_file}")
        
        preview_path = existing_video.get("video_preview_path")
        if preview_path:
            preview_file = storage_root / preview_path
            if preview_file.exists():
                preview_file.unlink()
                logger.info(f"Deleted video preview: {preview_file}")
        
        logger.info(f"Video {video_id} deleted successfully by {username}")
        
    except Exception as e:
        logger.error(f"Failed to delete video {video_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete video"
        )