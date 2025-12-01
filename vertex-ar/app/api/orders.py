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
from app.services.folder_service import FolderService
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
    content_type: str | None = None,
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
    
    # Validate content_type against company's configured list
    if content_type:
        company_content_types = company.get('content_types', '')
        if company_content_types:
            allowed_types = [ct.strip() for ct in company_content_types.split(',')]
            if content_type not in allowed_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Content type '{content_type}' is not allowed for this company. Allowed: {', '.join(allowed_types)}"
                )
    else:
        content_type = "portraits"  # Default content type

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
    
    # Determine if we should use Yandex Disk storage
    yandex_disk_folder_id = company.get('yandex_disk_folder_id')
    storage_type = company.get('storage_type', 'local')
    use_yandex_storage = storage_type == 'yandex_disk' and yandex_disk_folder_id
    use_local_storage = storage_type in ('local', 'local_disk')
    
    # Initialize folder service for local storage
    folder_service = FolderService(storage_root) if use_local_storage else None
    
    # Create temp directory for NFT marker generation (always local)
    temp_dir = storage_root / "temp" / "orders" / portrait_id
    temp_dir.mkdir(parents=True, exist_ok=True)

    image.file.seek(0)
    video.file.seek(0)

    try:
        image_content = await image.read()
        video_content = await video.read()

        # Write files to temp directory first
        temp_image_path = temp_dir / f"{portrait_id}.jpg"
        with open(temp_image_path, "wb") as image_file:
            image_file.write(image_content)

        temp_video_path = temp_dir / f"{video_id}.mp4"
        with open(temp_video_path, "wb") as video_file:
            video_file.write(video_content)
        
        # Initialize paths (will be updated based on storage type)
        image_path = temp_image_path
        video_path = temp_video_path

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
                image_preview_path = temp_dir / f"{portrait_id}_preview.jpg"
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
                video_preview_path = temp_dir / f"{video_id}_preview.jpg"
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

        # Generate NFT markers using temp files
        nft_generator = NFTMarkerGenerator(storage_root)
        marker_config = NFTMarkerConfig(
            feature_density="high",
            levels=3,
            max_image_size=8192,
            max_image_area=50_000_000,
        )
        marker_result = nft_generator.generate_marker(str(temp_image_path), portrait_id, marker_config)

        permanent_link = f"portrait_{portrait_id}"
        portrait_url = f"{base_url}/portrait/{permanent_link}"

        qr_image = qrcode.make(portrait_url)
        qr_buffer = BytesIO()
        qr_image.save(qr_buffer, format="PNG")
        qr_code_base64 = base64.b64encode(qr_buffer.getvalue()).decode()
        
        # Upload to Yandex Disk if configured
        if use_yandex_storage:
            try:
                from storage_manager import get_storage_manager
                from app.storage_yandex import YandexDiskStorageAdapter
                
                storage_manager = get_storage_manager(storage_root)
                
                # Get the company-specific adapter
                adapter = storage_manager.get_company_adapter(company_id, content_type)
                
                # Ensure it's a Yandex Disk adapter
                if isinstance(adapter, YandexDiskStorageAdapter):
                    # Create folder structure on Yandex Disk
                    order_id = portrait_id
                    structure_result = adapter.ensure_order_structure(
                        yandex_disk_folder_id,
                        content_type,
                        order_id
                    )
                    
                    logger.info(
                        "Created order structure on Yandex Disk",
                        folder_id=yandex_disk_folder_id,
                        content_type=content_type,
                        order_id=order_id,
                        results=structure_result
                    )
                    
                    # Upload image to Yandex Disk
                    yandex_image_path = f"{yandex_disk_folder_id}/{content_type}/{order_id}/Image/{portrait_id}.jpg"
                    await adapter.save_file(image_content, yandex_image_path)
                    image_path = Path(yandex_image_path)  # Store logical path
                    logger.info("Uploaded image to Yandex Disk", path=yandex_image_path)
                    
                    # Upload video to Yandex Disk
                    yandex_video_path = f"{yandex_disk_folder_id}/{content_type}/{order_id}/Image/{video_id}.mp4"
                    await adapter.save_file(video_content, yandex_video_path)
                    video_path = Path(yandex_video_path)  # Store logical path
                    logger.info("Uploaded video to Yandex Disk", path=yandex_video_path)
                    
                    # Upload previews if they exist
                    if image_preview_path:
                        with open(image_preview_path, "rb") as f:
                            preview_data = f.read()
                        yandex_preview_path = f"{yandex_disk_folder_id}/{content_type}/{order_id}/Image/{portrait_id}_preview.jpg"
                        await adapter.save_file(preview_data, yandex_preview_path)
                        image_preview_path = Path(yandex_preview_path)
                        logger.info("Uploaded image preview to Yandex Disk", path=yandex_preview_path)
                    
                    if video_preview_path:
                        with open(video_preview_path, "rb") as f:
                            preview_data = f.read()
                        yandex_video_preview_path = f"{yandex_disk_folder_id}/{content_type}/{order_id}/Image/{video_id}_preview.jpg"
                        await adapter.save_file(preview_data, yandex_video_preview_path)
                        video_preview_path = Path(yandex_video_preview_path)
                        logger.info("Uploaded video preview to Yandex Disk", path=yandex_video_preview_path)
                    
                    # Upload QR code
                    qr_bytes = qr_buffer.getvalue()
                    yandex_qr_path = f"{yandex_disk_folder_id}/{content_type}/{order_id}/QR/{portrait_id}_qr.png"
                    await adapter.save_file(qr_bytes, yandex_qr_path)
                    logger.info("Uploaded QR code to Yandex Disk", path=yandex_qr_path)
                    
                    # Upload NFT markers
                    for marker_file, subdir in [
                        (marker_result.fset_path, "nft_markers"),
                        (marker_result.fset3_path, "nft_markers"),
                        (marker_result.iset_path, "nft_markers")
                    ]:
                        if marker_file and Path(marker_file).exists():
                            with open(marker_file, "rb") as f:
                                marker_data = f.read()
                            marker_filename = Path(marker_file).name
                            yandex_marker_path = f"{yandex_disk_folder_id}/{content_type}/{order_id}/{subdir}/{marker_filename}"
                            await adapter.save_file(marker_data, yandex_marker_path)
                            logger.info("Uploaded NFT marker to Yandex Disk", path=yandex_marker_path)
                    
                    logger.info(
                        "Successfully uploaded all order artifacts to Yandex Disk",
                        order_id=order_id,
                        company_id=company_id
                    )
                else:
                    logger.warning(
                        "Company configured for Yandex Disk but adapter is not YandexDiskStorageAdapter",
                        company_id=company_id,
                        adapter_type=type(adapter).__name__
                    )
                    use_yandex_storage = False
                    
            except Exception as yandex_exc:
                logger.error(
                    "Failed to upload to Yandex Disk, falling back to local storage",
                    error=str(yandex_exc),
                    company_id=company_id,
                    exc_info=yandex_exc
                )
                # Fall back to local storage
                use_yandex_storage = False
                use_local_storage = True
                folder_service = FolderService(storage_root)
        
        # Handle local storage if configured or fallback from Yandex
        if use_local_storage and folder_service:
            try:
                # Create folder structure using folder service
                order_id = portrait_id
                structure_result = folder_service.ensure_order_structure(
                    company,
                    content_type,
                    order_id
                )
                
                logger.info(
                    "Created order structure on local storage",
                    company_id=company_id,
                    content_type=content_type,
                    order_id=order_id,
                    results=structure_result
                )
                
                # Move image to Image subfolder
                final_image_path = folder_service.build_order_path(
                    company, content_type, order_id, "Image"
                ) / f"{portrait_id}.jpg"
                folder_service.move_file(temp_image_path, final_image_path)
                image_path = Path(folder_service.build_relative_path(
                    company, content_type, order_id, f"{portrait_id}.jpg", "Image"
                ))
                logger.info("Moved image to local storage", path=str(image_path))
                
                # Move video to Image subfolder
                final_video_path = folder_service.build_order_path(
                    company, content_type, order_id, "Image"
                ) / f"{video_id}.mp4"
                folder_service.move_file(temp_video_path, final_video_path)
                video_path = Path(folder_service.build_relative_path(
                    company, content_type, order_id, f"{video_id}.mp4", "Image"
                ))
                logger.info("Moved video to local storage", path=str(video_path))
                
                # Move image preview if exists
                if image_preview_path and image_preview_path.exists():
                    final_image_preview_path = folder_service.build_order_path(
                        company, content_type, order_id, "Image"
                    ) / f"{portrait_id}_preview.jpg"
                    folder_service.move_file(image_preview_path, final_image_preview_path)
                    image_preview_path = Path(folder_service.build_relative_path(
                        company, content_type, order_id, f"{portrait_id}_preview.jpg", "Image"
                    ))
                    logger.info("Moved image preview to local storage", path=str(image_preview_path))
                
                # Move video preview if exists
                if video_preview_path and video_preview_path.exists():
                    final_video_preview_path = folder_service.build_order_path(
                        company, content_type, order_id, "Image"
                    ) / f"{video_id}_preview.jpg"
                    folder_service.move_file(video_preview_path, final_video_preview_path)
                    video_preview_path = Path(folder_service.build_relative_path(
                        company, content_type, order_id, f"{video_id}_preview.jpg", "Image"
                    ))
                    logger.info("Moved video preview to local storage", path=str(video_preview_path))
                
                # Save QR code to QR subfolder
                qr_bytes = qr_buffer.getvalue()
                qr_filename = f"{portrait_id}_qr.png"
                qr_path = folder_service.build_order_path(
                    company, content_type, order_id, "QR"
                ) / qr_filename
                with open(qr_path, "wb") as qr_file:
                    qr_file.write(qr_bytes)
                logger.info("Saved QR code to local storage", path=str(qr_path))
                
                # Move NFT markers to nft_markers subfolder
                for marker_file in [marker_result.fset_path, marker_result.fset3_path, marker_result.iset_path]:
                    if marker_file and Path(marker_file).exists():
                        marker_filename = Path(marker_file).name
                        final_marker_path = folder_service.build_order_path(
                            company, content_type, order_id, "nft_markers"
                        ) / marker_filename
                        folder_service.move_file(Path(marker_file), final_marker_path)
                        
                        # Update marker_result with new paths (relative)
                        relative_marker_path = folder_service.build_relative_path(
                            company, content_type, order_id, marker_filename, "nft_markers"
                        )
                        if marker_file == marker_result.fset_path:
                            marker_result.fset_path = relative_marker_path
                        elif marker_file == marker_result.fset3_path:
                            marker_result.fset3_path = relative_marker_path
                        elif marker_file == marker_result.iset_path:
                            marker_result.iset_path = relative_marker_path
                        
                        logger.info("Moved NFT marker to local storage", path=relative_marker_path)
                
                # Clean up temp directory
                folder_service.cleanup_temp_directory(temp_dir)
                
                logger.info(
                    "Successfully organized all order artifacts in local storage",
                    order_id=order_id,
                    company_id=company_id
                )
                
            except (PermissionError, OSError) as storage_exc:
                logger.error(
                    "Failed to organize files in local storage folder structure",
                    error=str(storage_exc),
                    company_id=company_id,
                    order_id=portrait_id,
                    exc_info=storage_exc
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Storage error: {str(storage_exc)}"
                )

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
        # Clean up temp directory on error
        shutil.rmtree(temp_dir, ignore_errors=True)
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
    content_type: str = Form(None),
    username: str = Depends(require_admin),
) -> OrderResponse:
    """Create a new order with client, portrait, and primary video."""
    return await _create_order_workflow(
        phone, name, image, video, username, description, 
        endpoint="orders", company_id=company_id, subscription_end=subscription_end, 
        email=email, content_type=content_type
    )


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
    content_type: str = Form(None),
    username: str = Depends(require_admin),
) -> OrderResponse:
    """Legacy compatibility endpoint for /api/orders/create."""
    return await _create_order_workflow(
        phone, name, image, video, username, description, 
        endpoint="api/orders", company_id=company_id, subscription_end=subscription_end, 
        email=email, content_type=content_type
    )
