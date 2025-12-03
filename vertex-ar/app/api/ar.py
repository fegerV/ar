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
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Import auth functions directly to avoid circular imports
# from app.api.auth import get_current_user, require_admin
from app.database import Database
from app.models import ARContentResponse
# Remove direct import from main to avoid circular import
# from app.main import get_current_app
from app.rate_limiter import create_rate_limit_dependency
from logging_setup import get_logger

router = APIRouter()
logger = get_logger(__name__)


def get_database() -> Database:
    """Get database instance."""
    # Import here to avoid circular import
    from app.main import get_current_app
    app = get_current_app()
    return app.state.database


def get_templates() -> Jinja2Templates:
    """Get Jinja2 templates instance."""
    # Import here to avoid circular import
    from app.main import get_current_app
    app = get_current_app()
    if not hasattr(app.state, 'templates'):
        BASE_DIR = app.state.config["BASE_DIR"]
        app.state.templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    return app.state.templates


async def get_current_user(
    request: Request,
    # Import security here to avoid circular import
    credentials=None
):
    """Get current authenticated user - simplified version to avoid circular import."""
    # Import here to avoid circular import
    from app.main import get_current_app
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
    from fastapi import HTTPException, status

    if credentials is None:
        security = HTTPBearer(auto_error=False)
        # Try to get credentials from request
        auth_header = request.headers.get("Authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        if not token:
            token = request.cookies.get("authToken")
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    else:
        token = credentials.credentials if credentials else None
        if not token:
            token = request.cookies.get("authToken")
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    # Get token manager
    app = get_current_app()
    tokens = app.state.tokens
    username = tokens.verify_token(token)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or invalid")

    database = app.state.database
    user = database.get_user(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is deactivated")

    return user


async def require_admin(request: Request) -> str:
    """Require admin role for endpoint access. Returns username.

    Can authenticate via:
    1. Authorization Bearer token header
    2. authToken cookie
    """
    # Import here to avoid circular import
    from app.main import get_current_app
    from fastapi import HTTPException, status

    app = get_current_app()
    tokens = app.state.tokens
    database = app.state.database

    token = None

    # Try to get token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]

    # If no header token, try cookie
    if not token:
        token = request.cookies.get("authToken")

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    username = tokens.verify_token(token)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or invalid")

    user = database.get_user(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if not user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return username


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
            image_preview_path = content_dir / f"{content_id}_preview.webp"
            with open(image_preview_path, "wb") as f:
                f.write(image_preview)
            logger.info(f"Image preview created: {image_preview_path}")
    except Exception as e:
        logger.error(f"Error generating image preview: {e}")

    try:
        # Generate video preview
        video_preview = PreviewGenerator.generate_video_preview(video_content)
        if video_preview:
            video_preview_path = content_dir / f"{content_id}_video_preview.webp"
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

    # Generate NFT markers with increased image size limits
    from nft_marker_generator import NFTMarkerConfig, NFTMarkerGenerator
    nft_generator = NFTMarkerGenerator(storage_root)
    config = NFTMarkerConfig(
        feature_density="high",
        levels=3,
        max_image_size=8192,  # Increased from 4096 to support larger images
        max_image_area=50_000_000  # Increased from 16_777_216 to support larger images
    )
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


@router.get("/{content_id}", response_class=HTMLResponse)
async def view_ar_content(request: Request, content_id: str) -> HTMLResponse:
    """View AR content page (public access)."""
    database = get_database()
    record = database.get_ar_content(content_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AR content not found")

    # Increment view count
    database.increment_view_count(content_id)
    logger.info("AR content viewed", extra={"content_id": content_id})

    # Prepare video URL
    app = get_current_app()
    base_url = app.state.config["BASE_URL"]
    video_url = f"{base_url}/storage/{Path(record['video_path']).relative_to(app.state.config['STORAGE_ROOT'])}"

    # Prepare record data for template
    record_data = {
        "id": record["id"],
        "video_url": video_url,
    }

    templates = get_templates()
    return templates.TemplateResponse("ar_page.html", {"request": request, "record": record_data})


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
