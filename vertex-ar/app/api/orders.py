"""Orders API endpoints for Vertex AR admin workflows."""

from __future__ import annotations

import base64
import shutil
import uuid
from io import BytesIO
from pathlib import Path

import qrcode
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.auth import require_admin
from app.database import Database
from app.main import get_current_app
from app.models import ClientResponse, OrderResponse, PortraitResponse, VideoResponse
from logging_setup import get_logger
from nft_marker_generator import NFTMarkerConfig, NFTMarkerGenerator
from preview_generator import PreviewGenerator

logger = get_logger(__name__)
router = APIRouter()


def get_database() -> Database:
    """Return shared database instance."""
    app = get_current_app()
    return app.state.database  # type: ignore[attr-defined]



@router.post("/create", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    phone: str = Form(...),
    name: str = Form(...),
    image: UploadFile = File(...),
    video: UploadFile = File(...),
    username: str = Depends(require_admin),
) -> OrderResponse:
    """Create a new order with client, portrait, and primary video."""
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file")

    if not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid video file")

    app = get_current_app()
    database = get_database()
    storage_root: Path = app.state.config["STORAGE_ROOT"]  # type: ignore[index]
    base_url: str = app.state.config["BASE_URL"]  # type: ignore[index]

    client = database.get_client_by_phone(phone)
    if not client:
        client_id = str(uuid.uuid4())
        client = database.create_client(client_id, phone, name)
        logger.info("Created new client for order", extra={"client_id": client_id, "admin": username})
    elif client.get("name") != name:
        database.update_client(client["id"], name=name)
        client = database.get_client(client["id"])  # refresh with updated values

    portrait_id = str(uuid.uuid4())
    video_id = str(uuid.uuid4())
    portrait_dir = storage_root / "portraits" / client["id"] / portrait_id
    portrait_dir.mkdir(parents=True, exist_ok=True)

    image.file.seek(0)
    video.file.seek(0)

    try:
        image_content = await image.read()
        video_content = await video.read()

        image_path = portrait_dir / f"{portrait_id}.jpg"
        with open(image_path, "wb") as image_file:
            image_file.write(image_content)

        video_path = portrait_dir / f"{video_id}.mp4"
        with open(video_path, "wb") as video_file:
            video_file.write(video_content)

        image_preview_path: Path | None = None
        video_preview_path: Path | None = None

        try:
            image_preview = PreviewGenerator.generate_image_preview(image_content)
            if image_preview:
                image_preview_path = portrait_dir / f"{portrait_id}_preview.jpg"
                with open(image_preview_path, "wb") as preview_file:
                    preview_file.write(image_preview)
        except Exception as exc:  # pragma: no cover - preview generation best-effort
            logger.warning(
                "Failed to generate portrait preview",
                extra={"portrait_id": portrait_id, "admin": username},
                exc_info=exc,
            )

        try:
            video_preview = PreviewGenerator.generate_video_preview(video_content)
            if video_preview:
                video_preview_path = portrait_dir / f"{video_id}_preview.jpg"
                with open(video_preview_path, "wb") as preview_file:
                    preview_file.write(video_preview)
        except Exception as exc:  # pragma: no cover - preview generation best-effort
            logger.warning(
                "Failed to generate video preview",
                extra={"portrait_id": portrait_id, "admin": username},
                exc_info=exc,
            )

        nft_generator = NFTMarkerGenerator(storage_root)
        marker_config = NFTMarkerConfig(
            feature_density="high",
            levels=3,
            max_image_size=8192,
            max_image_area=50_000_000,
        )
        marker_result = nft_generator.generate_marker(str(image_path), portrait_id, marker_config)

        permanent_link = f"portrait_{portrait_id}"
        portrait_url = f"{base_url}/portrait/{permanent_link}"

        qr_image = qrcode.make(portrait_url)
        qr_buffer = BytesIO()
        qr_image.save(qr_buffer, format="PNG")
        qr_code_base64 = base64.b64encode(qr_buffer.getvalue()).decode()

        portrait_record = database.create_portrait(
            portrait_id=portrait_id,
            client_id=client["id"],
            image_path=str(image_path),
            marker_fset=marker_result.fset_path,
            marker_fset3=marker_result.fset3_path,
            marker_iset=marker_result.iset_path,
            permanent_link=permanent_link,
            qr_code=qr_code_base64,
            image_preview_path=str(image_preview_path) if image_preview_path else None,
        )

        video_record = database.create_video(
            video_id=video_id,
            portrait_id=portrait_id,
            video_path=str(video_path),
            is_active=True,
            video_preview_path=str(video_preview_path) if video_preview_path else None,
        )

        logger.info(
            "Order created successfully",
            extra={
                "portrait_id": portrait_id,
                "client_id": client["id"],
                "admin": username,
            },
        )

        return OrderResponse(
            client=ClientResponse(
                id=client["id"],
                phone=client["phone"],
                name=client["name"],
                created_at=client["created_at"],
            ),
            portrait=PortraitResponse(
                id=portrait_record["id"],
                client_id=portrait_record["client_id"],
                permanent_link=portrait_record["permanent_link"],
                qr_code_base64=qr_code_base64,
                image_path=portrait_record["image_path"],
                view_count=portrait_record["view_count"],
                created_at=portrait_record["created_at"],
            ),
            video=VideoResponse(
                id=video_record["id"],
                portrait_id=video_record["portrait_id"],
                video_path=video_record["video_path"],
                is_active=bool(video_record["is_active"]),
                created_at=video_record["created_at"],
            ),
        )
    except Exception as exc:
        logger.error(
            "Failed to create order",
            extra={"admin": username, "client_phone": phone},
            exc_info=exc,
        )
        shutil.rmtree(portrait_dir, ignore_errors=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create order")
