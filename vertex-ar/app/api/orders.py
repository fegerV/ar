"""Orders API endpoints for Vertex AR admin workflows."""

from __future__ import annotations

import base64
import math
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


legacy_router = APIRouter()


def _validate_upload(file: UploadFile, expected_prefix: str, error_detail: str) -> None:
    logger.info(f"File content_type: {file.content_type}, expected_prefix: {expected_prefix}")
    # Allow both expected MIME types and octet-stream for video files (common issue)
    if expected_prefix == "video/" and file.content_type == "application/octet-stream":
        logger.warning(f"Accepting octet-stream as video file for {file.filename}")
        return
    if not file.content_type or not file.content_type.startswith(expected_prefix):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail)


async def _create_order_workflow(
    phone: str,
    name: str,
    image: UploadFile,
    video: UploadFile,
    username: str,
    description: str | None = None,
    endpoint: str = "orders",
    company_id: str = "vertex-ar-default",
    subscription_end: str | None = None,
    email: str | None = None,
) -> OrderResponse:
    """Shared implementation for creating an order."""
    _validate_upload(image, "image/", "Invalid image file")
    _validate_upload(video, "video/", "Invalid video file")

    app = get_current_app()
    database = get_database()
    storage_root: Path = app.state.config["STORAGE_ROOT"]  # type: ignore[index]
    base_url: str = app.state.config["BASE_URL"]  # type: ignore[index]

    # Normalize and validate company
    company_id = company_id or "vertex-ar-default"
    company = database.get_company(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID '{company_id}' not found"
        )

    client = database.get_client_by_phone(phone, company_id)
    if not client:
        client_id = str(uuid.uuid4())
        client = database.create_client(client_id, phone, name, company_id, email)
        logger.info(
            "Created new client for order",
            extra={"client_id": client_id, "admin": username, "endpoint": endpoint, "company_id": company_id, "email": email},
        )
    elif client.get("name") != name or (email and client.get("email") != email):
        # Update client name and/or email if they differ
        database.update_client(client["id"], name=name if client.get("name") != name else None, email=email if email and client.get("email") != email else None)
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

        video_file_size_mb: int | None = None
        try:
            video_size_bytes = video_path.stat().st_size
            if video_size_bytes:
                video_file_size_mb = max(1, math.ceil(video_size_bytes / (1024 * 1024)))
        except OSError:
            video_file_size_mb = None

        image_preview_path: Path | None = None
        video_preview_path: Path | None = None

        try:
            image_preview = PreviewGenerator.generate_image_preview(image_content)
            if image_preview:
                image_preview_path = portrait_dir / f"{portrait_id}_preview.jpg"
                with open(image_preview_path, "wb") as preview_file:
                    preview_file.write(image_preview)
                logger.info(
                    "Portrait preview created successfully",
                    extra={"portrait_id": portrait_id, "preview_path": str(image_preview_path), "size": len(image_preview)},
                )
            else:
                logger.warning(
                    "Image preview generation returned None",
                    extra={"portrait_id": portrait_id},
                )
        except Exception as exc:  # pragma: no cover - preview generation best-effort
            logger.warning(
                "Failed to generate portrait preview",
                extra={"portrait_id": portrait_id, "admin": username, "endpoint": endpoint},
                exc_info=exc,
            )

        try:
            video_preview = PreviewGenerator.generate_video_preview(video_content)
            if video_preview:
                video_preview_path = portrait_dir / f"{video_id}_preview.jpg"
                with open(video_preview_path, "wb") as preview_file:
                    preview_file.write(video_preview)
                logger.info(
                    "Video preview created successfully",
                    extra={"video_id": video_id, "preview_path": str(video_preview_path), "size": len(video_preview)},
                )
            else:
                logger.warning(
                    "Video preview generation returned None",
                    extra={"video_id": video_id},
                )
        except Exception as exc:  # pragma: no cover - preview generation best-effort
            logger.warning(
                "Failed to generate video preview",
                extra={"portrait_id": portrait_id, "admin": username, "endpoint": endpoint},
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
            subscription_end=subscription_end,
        )

        video_record = database.create_video(
            video_id=video_id,
            portrait_id=portrait_id,
            video_path=str(video_path),
            is_active=True,
            video_preview_path=str(video_preview_path) if video_preview_path else None,
            description=description,
            file_size_mb=video_file_size_mb,
        )

        logger.info(
            "Order created successfully",
            extra={
                "portrait_id": portrait_id,
                "client_id": client["id"],
                "admin": username,
                "endpoint": endpoint,
            },
        )

        return OrderResponse(
            client=ClientResponse(
                id=client["id"],
                phone=client["phone"],
                name=client["name"],
                email=client.get("email"),
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
                subscription_end=portrait_record.get("subscription_end"),
                lifecycle_status=portrait_record.get("lifecycle_status", "active"),
                last_status_change=portrait_record.get("last_status_change"),
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
            extra={"admin": username, "client_phone": phone, "endpoint": endpoint},
            exc_info=exc,
        )
        shutil.rmtree(portrait_dir, ignore_errors=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create order")


@router.post("/create", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    phone: str = Form(...),
    name: str = Form(...),
    image: UploadFile = File(...),
    video: UploadFile = File(...),
    description: str = Form(None),
    company_id: str = Form("vertex-ar-default"),
    subscription_end: str = Form(None),
    email: str = Form(None),
    username: str = Depends(require_admin),
) -> OrderResponse:
    """Create a new order with client, portrait, and primary video."""
    return await _create_order_workflow(phone, name, image, video, username, description, endpoint="orders", company_id=company_id, subscription_end=subscription_end, email=email)


@legacy_router.post(
    "/create",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_order_legacy(
    phone: str = Form(...),
    name: str = Form(...),
    image: UploadFile = File(...),
    video: UploadFile = File(...),
    description: str = Form(None),
    company_id: str = Form("vertex-ar-default"),
    subscription_end: str = Form(None),
    email: str = Form(None),
    username: str = Depends(require_admin),
) -> OrderResponse:
    """Legacy compatibility endpoint for /api/orders/create."""
    return await _create_order_workflow(phone, name, image, video, username, description, endpoint="api/orders", company_id=company_id, subscription_end=subscription_end, email=email)
