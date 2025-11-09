"""
Portrait management endpoints for Vertex AR API.
"""
import base64
import uuid
from io import BytesIO
from typing import List

import qrcode
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.auth import get_current_user
from app.database import Database
from app.models import PortraitResponse
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
    
    # Generate NFT markers
    from nft_marker_generator import NFTMarkerConfig, NFTMarkerGenerator
    nft_generator = NFTMarkerGenerator(storage_root)
    config = NFTMarkerConfig(feature_density="high", levels=3)
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
    
    return PortraitResponse(
        id=db_portrait["id"],
        client_id=db_portrait["client_id"],
        permanent_link=db_portrait["permanent_link"],
        qr_code_base64=qr_base64,
        image_path=db_portrait["image_path"],
        view_count=db_portrait["view_count"],
        created_at=db_portrait["created_at"]
    )


@router.get("/", response_model=List[PortraitResponse])
async def list_portraits(
    client_id: str = None,
    username: str = Depends(get_current_user)
) -> List[PortraitResponse]:
    """Get list of portraits (optionally filtered by client)."""
    database = get_database()
    portraits = database.list_portraits(client_id)
    
    return [
        PortraitResponse(
            id=portrait["id"],
            client_id=portrait["client_id"],
            permanent_link=portrait["permanent_link"],
            qr_code_base64=portrait.get("qr_code"),
            image_path=portrait["image_path"],
            view_count=portrait["view_count"],
            created_at=portrait["created_at"]
        )
        for portrait in portraits
    ]


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
    
    return PortraitResponse(
        id=portrait["id"],
        client_id=portrait["client_id"],
        permanent_link=portrait["permanent_link"],
        qr_code_base64=portrait.get("qr_code"),
        image_path=portrait["image_path"],
        view_count=portrait["view_count"],
        created_at=portrait["created_at"]
    )


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
    
    return PortraitResponse(
        id=portrait["id"],
        client_id=portrait["client_id"],
        permanent_link=portrait["permanent_link"],
        qr_code_base64=portrait.get("qr_code"),
        image_path=portrait["image_path"],
        view_count=portrait["view_count"] + 1,  # Incremented view
        created_at=portrait["created_at"]
    )


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