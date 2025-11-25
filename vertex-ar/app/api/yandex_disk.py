"""
Yandex Disk file access API endpoints.
"""
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from urllib.parse import unquote

from app.storage_yandex import YandexDiskStorageAdapter
from storage_config import get_storage_config
from logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/yandex-disk", tags=["yandex_disk"])


@router.get("/file/{encoded_path:path}")
async def get_yandex_disk_file(encoded_path: str) -> Response:
    """
    Get file from Yandex Disk by encoded path.
    
    This endpoint serves as a proxy for Yandex Disk files.
    """
    try:
        # Decode the path
        file_path = unquote(encoded_path)
        
        # Get Yandex Disk configuration
        config = get_storage_config()
        if not config.is_yandex_enabled():
            raise HTTPException(status_code=404, detail="Yandex Disk not configured")
        
        # Create adapter
        adapter = YandexDiskStorageAdapter(config.get_yandex_token())
        
        # Get file data
        file_data = await adapter.get_file(file_path)
        
        # Determine content type
        content_type = "application/octet-stream"
        if file_path.lower().endswith(('.jpg', '.jpeg')):
            content_type = "image/jpeg"
        elif file_path.lower().endswith('.png'):
            content_type = "image/png"
        elif file_path.lower().endswith('.webp'):
            content_type = "image/webp"
        elif file_path.lower().endswith('.mp4'):
            content_type = "video/mp4"
        elif file_path.lower().endswith('.webm'):
            content_type = "video/webm"
        
        return Response(
            content=file_data,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to serve Yandex Disk file",
            error=str(e),
            file_path=file_path if 'file_path' in locals() else encoded_path
        )
        raise HTTPException(status_code=404, detail="File not found")


@router.get("/download/{encoded_path:path}")
async def download_yandex_disk_file(encoded_path: str) -> Response:
    """
    Download file from Yandex Disk by encoded path.
    
    This endpoint provides direct download for Yandex Disk files.
    """
    try:
        # Decode the path
        file_path = unquote(encoded_path)
        
        # Get Yandex Disk configuration
        config = get_storage_config()
        if not config.is_yandex_enabled():
            raise HTTPException(status_code=404, detail="Yandex Disk not configured")
        
        # Create adapter
        adapter = YandexDiskStorageAdapter(config.get_yandex_token())
        
        # Get direct download URL
        download_url = adapter.get_download_url(file_path)
        
        # Get file data
        file_data = await adapter.get_file(file_path)
        
        # Extract filename from path
        filename = Path(file_path).name
        
        return Response(
            content=file_data,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"",
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to download Yandex Disk file",
            error=str(e),
            file_path=file_path if 'file_path' in locals() else encoded_path
        )
        raise HTTPException(status_code=404, detail="File not found")