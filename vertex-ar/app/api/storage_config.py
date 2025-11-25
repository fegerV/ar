"""
Storage configuration API endpoints.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.api.auth import require_admin
from storage_config import get_storage_config
from storage_manager import get_storage_manager
from logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/storage-config", tags=["storage_config"])


class StorageTypeConfig(BaseModel):
    """Storage type configuration model."""
    storage_type: str  # local, minio, yandex_disk
    yandex_disk: Optional[Dict[str, Any]] = None


class BackupSettingsModel(BaseModel):
    """Backup settings model."""
    auto_split_backups: bool = True
    max_backup_size_mb: int = 500
    chunk_size_mb: int = 100
    compression: str = "gz"


class YandexDiskConfig(BaseModel):
    """Yandex Disk configuration model."""
    oauth_token: str
    enabled: bool = True


class MinioConfig(BaseModel):
    """MinIO configuration model."""
    enabled: bool = True
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str


@router.get("/config")
async def get_storage_config_api(_admin=Depends(require_admin)) -> Dict[str, Any]:
    """
    Get current storage configuration.
    
    Requires admin authentication.
    """
    try:
        config = get_storage_config()
        storage_manager = get_storage_manager()
        
        # Get storage info
        storage_info = storage_manager.get_storage_info()
        
        return {
            "success": True,
            "config": config.get_all_config(),
            "storage_info": storage_info,
            "yandex_enabled": config.is_yandex_enabled()
        }
        
    except Exception as e:
        logger.error("Failed to get storage config", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")


@router.post("/content-type/{content_type}")
async def update_content_type_storage(
    content_type: str,
    config: StorageTypeConfig,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Update storage configuration for a content type.
    
    Args:
        content_type: Content type (portraits, videos, previews, nft_markers)
        config: Storage configuration
    
    Requires admin authentication.
    """
    if content_type not in ["portraits", "videos", "previews", "nft_markers"]:
        raise HTTPException(status_code=400, detail=f"Invalid content type: {content_type}")
    
    try:
        storage_config = get_storage_config()
        
        # Set storage type
        storage_config.set_storage_type(content_type, config.storage_type)
        
        # Set Yandex Disk config if provided
        if config.yandex_disk:
            storage_config.set_yandex_config(
                content_type,
                config.yandex_disk.get("enabled", False),
                config.yandex_disk.get("base_path")
            )
        
        # Reinitialize storage manager
        storage_manager = get_storage_manager()
        storage_manager.reinitialize_adapters()
        
        logger.info(
            "Storage configuration updated",
            content_type=content_type,
            storage_type=config.storage_type,
            admin=_admin
        )
        
        return {
            "success": True,
            "message": f"Storage configuration for {content_type} updated successfully",
            "content_type": content_type,
            "storage_type": config.storage_type
        }
        
    except Exception as e:
        logger.error("Failed to update storage config", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")


@router.post("/backup-settings")
async def update_backup_settings(
    settings: BackupSettingsModel,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Update backup settings.
    
    Requires admin authentication.
    """
    try:
        config = get_storage_config()
        config.set_backup_settings(settings.dict())
        
        logger.info("Backup settings updated", admin=_admin)
        
        return {
            "success": True,
            "message": "Backup settings updated successfully",
            "settings": config.get_backup_settings()
        }
        
    except Exception as e:
        logger.error("Failed to update backup settings", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to update backup settings: {str(e)}")


@router.post("/yandex-disk")
async def update_yandex_disk_config(
    config: YandexDiskConfig,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Update Yandex Disk configuration.
    
    Requires admin authentication.
    """
    try:
        storage_config = get_storage_config()
        storage_config.set_yandex_token(config.oauth_token)
        
        # Reinitialize storage manager
        storage_manager = get_storage_manager()
        storage_manager.reinitialize_adapters()
        
        logger.info("Yandex Disk configuration updated", admin=_admin)
        
        return {
            "success": True,
            "message": "Yandex Disk configuration updated successfully",
            "enabled": config.enabled
        }
        
    except Exception as e:
        logger.error("Failed to update Yandex Disk config", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to update Yandex Disk config: {str(e)}")


@router.post("/minio")
async def update_minio_config(
    config: MinioConfig,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Update MinIO configuration.
    
    Requires admin authentication.
    """
    try:
        storage_config = get_storage_config()
        storage_config.set_minio_config(config.dict())
        
        # Reinitialize storage manager
        storage_manager = get_storage_manager()
        storage_manager.reinitialize_adapters()
        
        logger.info("MinIO configuration updated", admin=_admin)
        
        return {
            "success": True,
            "message": "MinIO configuration updated successfully",
            "enabled": config.enabled
        }
        
    except Exception as e:
        logger.error("Failed to update MinIO config", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to update MinIO config: {str(e)}")


@router.get("/test-connection/{storage_type}")
async def test_storage_connection(
    storage_type: str,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Test connection to storage type.
    
    Args:
        storage_type: Storage type to test (local, minio, yandex_disk)
    
    Requires admin authentication.
    """
    try:
        if storage_type == "yandex_disk":
            config = get_storage_config()
            if not config.is_yandex_enabled():
                return {
                    "success": False,
                    "storage_type": storage_type,
                    "error": "Yandex Disk not configured"
                }
            
            from app.storage_yandex import YandexDiskStorageAdapter
            adapter = YandexDiskStorageAdapter(config.get_yandex_token())
            is_connected = adapter.test_connection()
            
            # Get storage info
            info = adapter.get_storage_info() if is_connected else None
            
            return {
                "success": True,
                "storage_type": storage_type,
                "connected": is_connected,
                "info": info
            }
        
        elif storage_type == "minio":
            config = get_storage_config()
            minio_config = config.get_minio_config()
            
            if not minio_config.get("enabled"):
                return {
                    "success": False,
                    "storage_type": storage_type,
                    "error": "MinIO not configured"
                }
            
            from app.storage_minio import MinioStorageAdapter
            adapter = MinioStorageAdapter(
                endpoint=minio_config.get("endpoint", ""),
                access_key=minio_config.get("access_key", ""),
                secret_key=minio_config.get("secret_key", ""),
                bucket=minio_config.get("bucket", "")
            )
            
            # Test connection by listing buckets
            try:
                buckets = adapter.client.list_buckets()
                is_connected = True
            except Exception as e:
                is_connected = False
                logger.error("MinIO connection test failed", error=str(e))
            
            return {
                "success": True,
                "storage_type": storage_type,
                "connected": is_connected
            }
        
        elif storage_type == "local":
            # Local storage is always available
            storage_root = Path("storage")
            storage_root.mkdir(parents=True, exist_ok=True)
            
            return {
                "success": True,
                "storage_type": storage_type,
                "connected": True,
                "path": str(storage_root.absolute())
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown storage type: {storage_type}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to test storage connection", error=str(e), storage_type=storage_type, exc_info=e)
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")


@router.get("/storage-info/{storage_type}")
async def get_storage_type_info(
    storage_type: str,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get storage information for a specific storage type.
    
    Requires admin authentication.
    """
    try:
        if storage_type == "yandex_disk":
            config = get_storage_config()
            if not config.is_yandex_enabled():
                raise HTTPException(status_code=400, detail="Yandex Disk not configured")
            
            from app.storage_yandex import YandexDiskStorageAdapter
            adapter = YandexDiskStorageAdapter(config.get_yandex_token())
            info = adapter.get_storage_info()
            
            return {
                "success": True,
                "storage_type": storage_type,
                "info": info
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"Storage info not available for: {storage_type}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get storage info", error=str(e), storage_type=storage_type, exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to get storage info: {str(e)}")