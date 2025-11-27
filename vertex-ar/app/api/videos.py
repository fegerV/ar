"""
Video management endpoints for Vertex AR API.
"""
import base64
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.api.auth import get_current_user, require_admin
from app.database import Database
from app.models import (
    VideoResponse, 
    VideoScheduleUpdate, 
    VideoScheduleHistory, 
    VideoRotationRequest
)
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
    app = get_current_app()
    storage_manager = app.state.storage_manager
    
    response = VideoResponse(
        id=video["id"],
        portrait_id=video["portrait_id"],
        video_path=video["video_path"],
        is_active=bool(video["is_active"]),
        created_at=video["created_at"],
        file_size_mb=video.get("file_size_mb"),
        # New scheduling fields
        start_datetime=video.get("start_datetime"),
        end_datetime=video.get("end_datetime"),
        rotation_type=video.get("rotation_type"),
        status=video.get("status"),
    )
    
    # Add public URLs
    if video.get("video_path"):
        response.video_url = storage_manager.get_public_url(video["video_path"], "videos")
    if video.get("video_preview_path"):
        response.preview_url = storage_manager.get_public_url(video["video_preview_path"], "previews")
    
    return response


@router.get("/", response_model=List[VideoResponse])
async def list_all_videos(
    company_id: str = Query(None, description="Filter by company ID"),
    status: str = Query(None, description="Filter by status (active, inactive, archived)"),
    rotation_type: str = Query(None, description="Filter by rotation type (none, sequential, cyclic)"),
    username: str = Depends(require_admin)
) -> List[VideoResponse]:
    """
    Get list of all videos with scheduling information (admin only).
    
    This endpoint returns all videos with their scheduling metadata and supports
    filtering by company, status, and rotation type.
    """
    database = get_database()
    
    videos = database.list_videos_for_schedule(
        company_id=company_id,
        status=status,
        rotation_type=rotation_type,
    )
    
    return [_video_to_response(video) for video in videos]


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
    storage_manager = app.state.storage_manager
    storage_root = app.state.config["STORAGE_ROOT"]
    
    # Generate paths for storage
    portrait = database.get_portrait(portrait_id)
    client_id = portrait["client_id"]
    video_path = f"portraits/{client_id}/{portrait_id}/{video_id}.mp4"
    video_preview_path = f"portraits/{client_id}/{portrait_id}/{video_id}_preview.webp"
    
    # Read and save video
    video.file.seek(0)
    video_content = await video.read()
    
    # Calculate file size in MB
    file_size_bytes = len(video_content)
    file_size_mb = int(file_size_bytes / (1024 * 1024))  # Convert to MB and round down to integer
    
    logger.info(f"Video file size: {file_size_bytes} bytes = {file_size_mb} MB")
    
    # Save video using storage manager
    await storage_manager.save_file(video_content, video_path, "videos")
    
    # Generate video preview with improved quality and WebP support
    from preview_generator import PreviewGenerator
    video_preview_path_saved = None
    
    try:
        video_preview = PreviewGenerator.generate_video_preview(video_content, size=(300, 300), format='webp')
        if video_preview and len(video_preview) > 0:
            await storage_manager.save_file(video_preview, video_preview_path, "previews")
            video_preview_path_saved = video_preview_path
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
        video_path=video_path,
        is_active=is_active,
        video_preview_path=video_preview_path_saved,
        description=description,
        file_size_mb=file_size_mb,
    )
    
    logger.info(f"Database returned video: {db_video}")
    
    # Get public URLs using storage manager
    if db_video.get("video_path"):
        db_video["video_url"] = storage_manager.get_public_url(db_video["video_path"], "videos")
    if db_video.get("video_preview_path"):
        db_video["preview_url"] = storage_manager.get_public_url(db_video["video_preview_path"], "previews")
    
    return VideoResponse(
        id=db_video["id"],
        portrait_id=db_video["portrait_id"],
        video_path=db_video["video_path"],
        video_url=db_video.get("video_url"),
        preview_url=db_video.get("preview_url"),
        is_active=bool(db_video["is_active"]),
        created_at=db_video["created_at"],
        file_size_mb=db_video.get("file_size_mb"),
        # New scheduling fields
        start_datetime=db_video.get("start_datetime"),
        end_datetime=db_video.get("end_datetime"),
        rotation_type=db_video.get("rotation_type"),
        status=db_video.get("status"),
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
            # New scheduling fields
            start_datetime=video.get("start_datetime"),
            end_datetime=video.get("end_datetime"),
            rotation_type=video.get("rotation_type"),
            status=video.get("status"),
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
        # New scheduling fields
        start_datetime=video.get("start_datetime"),
        end_datetime=video.get("end_datetime"),
        rotation_type=video.get("rotation_type"),
        status=video.get("status"),
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
        # New scheduling fields
        start_datetime=updated_video.get("start_datetime"),
        end_datetime=updated_video.get("end_datetime"),
        rotation_type=updated_video.get("rotation_type"),
        status=updated_video.get("status"),
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
        # New scheduling fields
        start_datetime=video.get("start_datetime"),
        end_datetime=video.get("end_datetime"),
        rotation_type=video.get("rotation_type"),
        status=video.get("status"),
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


# Video scheduling endpoints
@router.put("/{video_id}/schedule", response_model=VideoResponse)
async def update_video_schedule(
    video_id: str,
    schedule_data: VideoScheduleUpdate,
    username: str = Depends(require_admin)
) -> VideoResponse:
    """Update video scheduling settings (admin only)."""
    database = get_database()
    
    # Check if video exists
    video = database.get_video(video_id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Update schedule
    success = database.update_video_schedule(
        video_id=video_id,
        start_datetime=schedule_data.start_datetime,
        end_datetime=schedule_data.end_datetime,
        rotation_type=schedule_data.rotation_type,
        status=schedule_data.status,
        changed_by=username
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update video schedule"
        )
    
    logger.info(f"Video {video_id} schedule updated by {username}")
    
    # Return updated video
    updated_video = database.get_video(video_id)
    return _video_to_response(updated_video)


@router.get("/{video_id}/schedule/history", response_model=List[VideoScheduleHistory])
async def get_video_schedule_history(
    video_id: str,
    username: str = Depends(require_admin)
) -> List[VideoScheduleHistory]:
    """Get schedule change history for a video (admin only)."""
    database = get_database()
    
    # Check if video exists
    video = database.get_video(video_id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    history = database.get_video_schedule_history(video_id)
    return [
        VideoScheduleHistory(
            id=record["id"],
            video_id=record["video_id"],
            old_status=record.get("old_status"),
            new_status=record["new_status"],
            change_reason=record["change_reason"],
            changed_at=record["changed_at"],
            changed_by=record.get("changed_by")
        )
        for record in history
    ]


@router.post("/rotation/trigger", response_model=Dict[str, Any])
async def trigger_video_rotation(
    rotation_request: VideoRotationRequest,
    username: str = Depends(require_admin)
) -> Dict[str, Any]:
    """Manually trigger video rotation for a portrait (admin only)."""
    database = get_database()
    
    # Check if portrait exists
    portrait = database.get_portrait(rotation_request.portrait_id)
    if not portrait:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portrait not found"
        )
    
    # Get videos for rotation
    videos = database.get_videos_for_rotation(
        rotation_request.portrait_id, 
        rotation_request.rotation_type
    )
    
    if not videos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No videos available for {rotation_request.rotation_type} rotation"
        )
    
    # Activate the first video in rotation
    success = database.activate_video_with_history(
        videos[0]["id"],
        reason=f"manual_{rotation_request.rotation_type}_rotation",
        changed_by=username
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger video rotation"
        )
    
    logger.info(f"Manual {rotation_request.rotation_type} rotation triggered by {username}")
    
    return {
        "message": f"Video rotation triggered successfully",
        "rotation_type": rotation_request.rotation_type,
        "portrait_id": rotation_request.portrait_id,
        "activated_video_id": videos[0]["id"]
    }


@router.get("/scheduler/status", response_model=Dict[str, Any])
async def get_scheduler_status(
    username: str = Depends(require_admin)
) -> Dict[str, Any]:
    """Get video animation scheduler status (admin only)."""
    from app.video_animation_scheduler import video_animation_scheduler
    
    status = await video_animation_scheduler.get_scheduler_status()
    return status


@router.post("/scheduler/archive-expired", response_model=Dict[str, Any])
async def trigger_archive_expired(
    username: str = Depends(require_admin)
) -> Dict[str, Any]:
    """Manually trigger archiving of expired videos (admin only)."""
    from app.video_animation_scheduler import video_animation_scheduler
    
    archived_count = await video_animation_scheduler.archive_expired_videos()
    
    logger.info(f"Manual archive of expired videos triggered by {username}")
    
    return {
        "message": "Expired videos archived successfully",
        "archived_count": archived_count
    }