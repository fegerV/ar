"""
Remote storage management API endpoints.
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.api.auth import require_admin
from backup_manager import create_backup_manager
from remote_storage import get_remote_storage_manager
from logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/remote-storage", tags=["remote_storage"])


class RemoteStorageConfig(BaseModel):
    """Remote storage configuration model."""
    yandex_disk: Optional[Dict[str, Any]] = None
    google_drive: Optional[Dict[str, Any]] = None


class SyncToRemoteRequest(BaseModel):
    """Request model for syncing backup to remote storage."""
    backup_path: str
    provider: str  # yandex_disk or google_drive
    remote_dir: str = "vertex-ar-backups"


class RestoreFromRemoteRequest(BaseModel):
    """Request model for restoring backup from remote storage."""
    remote_filename: str
    provider: str
    remote_dir: str = "vertex-ar-backups"


class RemoteFileInfo(BaseModel):
    """Remote file information model."""
    name: str
    size: int
    created: Optional[str] = None
    modified: Optional[str] = None
    provider: str


@router.post("/config")
async def update_config(
    config: RemoteStorageConfig,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Update remote storage configuration.
    
    Requires admin authentication.
    """
    try:
        manager = get_remote_storage_manager()
        
        # Prepare configuration
        config_dict = {}
        
        if config.yandex_disk:
            config_dict["yandex_disk"] = config.yandex_disk
        
        if config.google_drive:
            config_dict["google_drive"] = config.google_drive
        
        # Save configuration
        manager.save_config(config_dict)
        
        logger.info("Remote storage config updated", admin=_admin)
        
        return {
            "success": True,
            "message": "Configuration updated successfully",
            "providers": manager.list_providers()
        }
        
    except Exception as e:
        logger.error("Failed to update remote storage config", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")


@router.get("/config")
async def get_config(_admin=Depends(require_admin)) -> Dict[str, Any]:
    """
    Get current remote storage configuration (without sensitive data).
    
    Requires admin authentication.
    """
    try:
        manager = get_remote_storage_manager()
        
        return {
            "success": True,
            "providers": manager.list_providers(),
            "has_yandex_disk": "yandex_disk" in manager.list_providers(),
            "has_google_drive": "google_drive" in manager.list_providers()
        }
        
    except Exception as e:
        logger.error("Failed to get remote storage config", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")


@router.get("/test-connection/{provider}")
async def test_connection(
    provider: str,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Test connection to remote storage provider.
    
    Requires admin authentication.
    """
    try:
        manager = get_remote_storage_manager()
        storage = manager.get_storage(provider)
        
        if not storage:
            raise HTTPException(status_code=404, detail=f"Provider '{provider}' not configured")
        
        is_connected = storage.test_connection()
        
        return {
            "success": True,
            "provider": provider,
            "connected": is_connected
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to test connection", error=str(e), provider=provider, exc_info=e)
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")


@router.get("/storage-info/{provider}")
async def get_storage_info(
    provider: str,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get storage quota and usage information.
    
    Requires admin authentication.
    """
    try:
        manager = get_remote_storage_manager()
        storage = manager.get_storage(provider)
        
        if not storage:
            raise HTTPException(status_code=404, detail=f"Provider '{provider}' not configured")
        
        info = storage.get_storage_info()
        
        if not info.get("success"):
            raise HTTPException(status_code=500, detail=info.get("error", "Failed to get storage info"))
        
        # Convert to GB for readability
        return {
            "success": True,
            "provider": provider,
            "total_gb": round(info["total_space"] / (1024**3), 2),
            "used_gb": round(info["used_space"] / (1024**3), 2),
            "available_gb": round(info["available_space"] / (1024**3), 2),
            "trash_gb": round(info.get("trash_size", 0) / (1024**3), 2)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get storage info", error=str(e), provider=provider, exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to get storage info: {str(e)}")


@router.post("/sync")
async def sync_to_remote(
    request: SyncToRemoteRequest,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Sync a local backup to remote storage.
    
    Requires admin authentication.
    """
    try:
        backup_manager = create_backup_manager()
        storage_manager = get_remote_storage_manager()
        
        storage = storage_manager.get_storage(request.provider)
        if not storage:
            raise HTTPException(status_code=404, detail=f"Provider '{request.provider}' not configured")
        
        backup_path = Path(request.backup_path)
        
        logger.info(
            "Syncing backup to remote storage",
            backup_path=str(backup_path),
            provider=request.provider,
            admin=_admin
        )
        
        result = backup_manager.sync_to_remote(backup_path, storage, request.remote_dir)
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Sync failed"))
        
        return {
            "success": True,
            "message": f"Backup synced to {request.provider}",
            "provider": request.provider,
            "remote_path": result.get("remote_path"),
            "size_mb": round(result.get("size", 0) / (1024 * 1024), 2)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to sync to remote", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to sync: {str(e)}")


@router.post("/download")
async def download_from_remote(
    request: RestoreFromRemoteRequest,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Download a backup from remote storage.
    
    This downloads the backup but does not restore it.
    Use the restore endpoint after downloading.
    
    Requires admin authentication.
    """
    try:
        backup_manager = create_backup_manager()
        storage_manager = get_remote_storage_manager()
        
        storage = storage_manager.get_storage(request.provider)
        if not storage:
            raise HTTPException(status_code=404, detail=f"Provider '{request.provider}' not configured")
        
        logger.info(
            "Downloading backup from remote storage",
            filename=request.remote_filename,
            provider=request.provider,
            admin=_admin
        )
        
        result = backup_manager.restore_from_remote(
            storage,
            request.remote_filename,
            request.remote_dir
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Download failed"))
        
        return {
            "success": True,
            "message": result.get("message"),
            "provider": request.provider,
            "local_path": result.get("local_path"),
            "backup_type": result.get("backup_type")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to download from remote", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to download: {str(e)}")


@router.get("/list/{provider}")
async def list_remote_files(
    provider: str,
    remote_dir: str = "vertex-ar-backups",
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    List backup files in remote storage.
    
    Requires admin authentication.
    """
    try:
        storage_manager = get_remote_storage_manager()
        storage = storage_manager.get_storage(provider)
        
        if not storage:
            raise HTTPException(status_code=404, detail=f"Provider '{provider}' not configured")
        
        files = storage.list_files(remote_dir)
        
        # Filter only backup files
        backup_files = [
            RemoteFileInfo(
                name=f["name"],
                size=f["size"],
                created=f.get("created"),
                modified=f.get("modified"),
                provider=provider
            )
            for f in files
            if "backup" in f["name"] and not f["name"].endswith(".json")
        ]
        
        return {
            "success": True,
            "provider": provider,
            "files": [f.dict() for f in backup_files],
            "count": len(backup_files)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list remote files", error=str(e), provider=provider, exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.delete("/delete/{provider}")
async def delete_remote_file(
    provider: str,
    remote_path: str,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Delete a backup file from remote storage.
    
    Requires admin authentication.
    """
    try:
        storage_manager = get_remote_storage_manager()
        storage = storage_manager.get_storage(provider)
        
        if not storage:
            raise HTTPException(status_code=404, detail=f"Provider '{provider}' not configured")
        
        logger.warning(
            "Deleting file from remote storage",
            remote_path=remote_path,
            provider=provider,
            admin=_admin
        )
        
        result = storage.delete_file(remote_path)
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Delete failed"))
        
        return {
            "success": True,
            "message": f"File deleted from {provider}",
            "provider": provider,
            "remote_path": remote_path
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete remote file", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")


@router.post("/sync-all/{provider}")
async def sync_all_to_remote(
    provider: str,
    remote_dir: str = "vertex-ar-backups",
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Sync all local backups to remote storage.
    
    Requires admin authentication.
    """
    try:
        backup_manager = create_backup_manager()
        storage_manager = get_remote_storage_manager()
        
        storage = storage_manager.get_storage(provider)
        if not storage:
            raise HTTPException(status_code=404, detail=f"Provider '{provider}' not configured")
        
        logger.info("Syncing all backups to remote storage", provider=provider, admin=_admin)
        
        # Get all backups
        backups = backup_manager.list_backups("all")
        
        synced = []
        failed = []
        
        for backup in backups:
            backup_path = backup.get("backup_path")
            if not backup_path:
                continue
            
            # For full backups, sync both database and storage
            if backup.get("type") == "full":
                db_path = backup.get("database", {}).get("backup_path")
                st_path = backup.get("storage", {}).get("backup_path")
                
                for path_str in [db_path, st_path]:
                    if path_str:
                        path = Path(path_str)
                        result = backup_manager.sync_to_remote(path, storage, remote_dir)
                        if result.get("success"):
                            synced.append(path.name)
                        else:
                            failed.append(path.name)
            else:
                path = Path(backup_path)
                result = backup_manager.sync_to_remote(path, storage, remote_dir)
                if result.get("success"):
                    synced.append(path.name)
                else:
                    failed.append(path.name)
        
        return {
            "success": True,
            "message": f"Synced {len(synced)} backups to {provider}",
            "provider": provider,
            "synced": synced,
            "failed": failed,
            "synced_count": len(synced),
            "failed_count": len(failed)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to sync all backups", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to sync all: {str(e)}")
