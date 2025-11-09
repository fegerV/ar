"""
AR content endpoints for Vertex AR API.
"""
import base64
import shutil
import uuid
from io import BytesIO
from pathlib import Path
from typing import Dict

import qrcode
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.api.auth import get_current_user, require_admin
from app.database import Database
from app.models import ARContentResponse
from app.main import get_current_app
from app.rate_limiter import create_rate_limit_dependency
from logging_setup import get_logger

router = APIRouter()
logger = get_logger(__name__)


def get_database() -> Database:
    """Get database instance."""
    app = get_current_app()
    return app.state.database


@router.post("/upload", response_model=ARContentResponse, dependencies=[Depends(create_rate_limit_dependency("10/minute"))])
async def upload_ar_content(
    request: Request,
    image: UploadFile = File(...),
    video: UploadFile = File(...),
    username: str = Depends(require_admin)
) -> ARContentResponse:
    """
    Upload image and video to create AR content.
    Only admins can upload.
    """
    app = get_current_app()
    base_url = app.state.config["BASE_URL"]
    storage_root = app.state.config["STORAGE_ROOT"]
    
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file")
    
    if not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid video file")
    
    # Generate UUID for files
    content_id = str(uuid.uuid4())
    
    # Create storage directories
    user_storage = storage_root / "ar_content" / username
    user_storage.mkdir(parents=True, exist_ok=True)
    content_dir = user_storage / content_id
    content_dir.mkdir(parents=True, exist_ok=True)
    
    # Read file contents for preview generation
    image.file.seek(0)
    image_content = await image.read()
    video.file.seek(0)
    video_content = await video.read()
    
    # Save image
    image_path = content_dir / f"{content_id}.jpg"
    with open(image_path, "wb") as f:
        f.write(image_content)
    
    # Save video
    video_path = content_dir / f"{content_id}.mp4"
    with open(video_path, "wb") as f:
        f.write(video_content)
    
    # Generate previews
    from preview_generator import PreviewGenerator
    
    image_preview_path = None
    video_preview_path = None
    
    try:
        # Generate image preview
        image_preview = PreviewGenerator.generate_image_preview(image_content)
        if image_preview:
            image_preview_path = content_dir / f"{content_id}_preview.jpg"
            with open(image_preview_path, "wb") as f:
                f.write(image_preview)
            logger.info(f"Image preview created: {image_preview_path}")
    except Exception as e:
        logger.error(f"Error generating image preview: {e}")
    
    try:
        # Generate video preview
        video_preview = PreviewGenerator.generate_video_preview(video_content)
        if video_preview:
            video_preview_path = content_dir / f"{content_id}_video_preview.jpg"
            with open(video_preview_path, "wb") as f:
                f.write(video_preview)
            logger.info(f"Video preview created: {video_preview_path}")
    except Exception as e:
        logger.error(f"Error generating video preview: {e}")
    
    # Generate QR code
    ar_url = f"{base_url}/ar/{content_id}"
    qr_img = qrcode.make(ar_url)
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode()
    
    # Generate NFT markers
    from nft_marker_generator import NFTMarkerConfig, NFTMarkerGenerator
    nft_generator = NFTMarkerGenerator(storage_root)
    config = NFTMarkerConfig(feature_density="high", levels=3)
    marker_result = nft_generator.generate_marker(str(image_path), content_id, config)
    
    # Create database record
    database = get_database()
    db_record = database.create_ar_content(
        content_id=content_id,
        username=username,
        image_path=str(image_path),
        video_path=str(video_path),
        image_preview_path=str(image_preview_path) if image_preview_path else None,
        video_preview_path=str(video_preview_path) if video_preview_path else None,
        marker_fset=marker_result.fset_path,
        marker_fset3=marker_result.fset3_path,
        marker_iset=marker_result.iset_path,
        ar_url=ar_url,
        qr_code=qr_base64,
    )
    
    return ARContentResponse(
        id=content_id,
        ar_url=ar_url,
        qr_code_base64=qr_base64,
        image_path=str(image_path),
        video_path=str(video_path),
        created_at=db_record["created_at"],
    )


@router.get("/list")
async def list_ar_content(username: str = Depends(get_current_user)) -> list:
    """List all AR content (admins see all, users see their own)."""
    database = get_database()
    user = database.get_user(username)
    if user and user.get("is_admin"):
        return database.list_ar_content()
    return database.list_ar_content(username)


@router.post("/{content_id}/click")
async def track_content_click(content_id: str) -> Dict[str, str]:
    """Track click interactions for AR content."""
    database = get_database()
    record = database.get_ar_content(content_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AR content not found")
    database.increment_click_count(content_id)
    logger.info("AR content click tracked", extra={"content_id": content_id})
    return {"status": "success", "content_id": content_id}


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ar_content(content_id: str, _: str = Depends(require_admin)) -> None:
    """Delete AR content and associated files."""
    database = get_database()
    record = database.get_ar_content(content_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AR content not found")

    image_path = record.get("image_path")
    content_dir = Path(image_path).parent if image_path else None

    if content_dir and content_dir.exists():
        try:
            shutil.rmtree(content_dir)
        except OSError as exc:
            logger.error(
                "Failed to remove AR content directory",
                extra={"content_id": content_id, "path": str(content_dir)},
                exc_info=exc,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove stored content files",
            )

    if not database.delete_ar_content(content_id):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete AR content from database",
        )

    logger.info("AR content deleted", extra={"content_id": content_id})
