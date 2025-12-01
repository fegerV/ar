"""
Remote storage management API endpoints.
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from app.api.auth import require_admin
from app.models import CompanyBackupConfig, CompanyBackupConfigResponse
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


@router.get("/providers")
async def list_providers(_admin=Depends(require_admin)) -> Dict[str, Any]:
    """
    List all configured remote storage providers.
    
    Returns a list of provider names that are configured and ready to use.
    Requires admin authentication.
    """
    try:
        storage_manager = get_remote_storage_manager()
        providers = storage_manager.list_providers()
        
        # Get connection status for each provider
        provider_details = []
        for provider_name in providers:
            storage = storage_manager.get_storage(provider_name)
            is_connected = False
            if storage:
                try:
                    is_connected = storage.test_connection()
                except Exception:
                    pass
            
            provider_details.append({
                "name": provider_name,
                "connected": is_connected
            })
        
        return {
            "success": True,
            "providers": provider_details,
            "count": len(provider_details)
        }
    except Exception as e:
        logger.error("Failed to list providers", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to list providers: {str(e)}")


@router.post("/companies/{company_id}/backup-config")
async def set_company_backup_config(
    company_id: str,
    config: CompanyBackupConfig,
    request: Request,
    _admin=Depends(require_admin)
) -> CompanyBackupConfigResponse:
    """
    Set remote backup configuration for a specific company.
    
    This assigns a backup provider and remote path to a company,
    enabling automatic remote backups for that company's data.
    
    Requires admin authentication.
    """
    try:
        database = request.app.state.database
        
        # Verify company exists
        company = database.get_company(company_id)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found")
        
        # If a provider is specified, verify it exists
        if config.backup_provider:
            storage_manager = get_remote_storage_manager()
            storage = storage_manager.get_storage(config.backup_provider)
            if not storage:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Provider '{config.backup_provider}' is not configured"
                )
            
            # Test connection
            try:
                if not storage.test_connection():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Provider '{config.backup_provider}' connection test failed"
                    )
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Provider '{config.backup_provider}' is not accessible: {str(e)}"
                )
        
        # Update database
        success = database.set_company_backup_config(
            company_id,
            config.backup_provider,
            config.backup_remote_path
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update backup configuration")
        
        logger.info(
            "Updated company backup config",
            company_id=company_id,
            provider=config.backup_provider,
            remote_path=config.backup_remote_path,
            admin=_admin
        )
        
        return CompanyBackupConfigResponse(
            company_id=company_id,
            company_name=company["name"],
            backup_provider=config.backup_provider,
            backup_remote_path=config.backup_remote_path
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to set company backup config", error=str(e), company_id=company_id, exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to set backup config: {str(e)}")


@router.get("/companies/{company_id}/backup-config")
async def get_company_backup_config(
    company_id: str,
    request: Request,
    _admin=Depends(require_admin)
) -> CompanyBackupConfigResponse:
    """
    Get remote backup configuration for a specific company.
    
    Returns the assigned backup provider and remote path.
    Requires admin authentication.
    """
    try:
        database = request.app.state.database
        
        # Get company
        company = database.get_company(company_id)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found")
        
        return CompanyBackupConfigResponse(
            company_id=company_id,
            company_name=company["name"],
            backup_provider=company.get("backup_provider"),
            backup_remote_path=company.get("backup_remote_path")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get company backup config", error=str(e), company_id=company_id, exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to get backup config: {str(e)}")


@router.get("/companies/backup-configs")
async def list_companies_backup_configs(
    request: Request,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    List backup configurations for all companies.
    
    Returns a list of all companies with their backup settings.
    Requires admin authentication.
    """
    try:
        database = request.app.state.database
        companies = database.list_companies()
        
        configs = [
            CompanyBackupConfigResponse(
                company_id=company["id"],
                company_name=company["name"],
                backup_provider=company.get("backup_provider"),
                backup_remote_path=company.get("backup_remote_path")
            )
            for company in companies
        ]
        
        return {
            "success": True,
            "companies": [config.model_dump() for config in configs],
            "count": len(configs)
        }
        
    except Exception as e:
        logger.error("Failed to list company backup configs", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to list backup configs: {str(e)}")


@router.post("/companies/{company_id}/sync-backup")
async def sync_company_backup(
    company_id: str,
    backup_path: str,
    request: Request,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Sync a specific backup file to the company's configured remote storage.
    
    The company must have a backup provider configured.
    Requires admin authentication.
    """
    try:
        database = request.app.state.database
        
        # Get company backup config
        company = database.get_company(company_id)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found")
        
        backup_provider = company.get("backup_provider")
        backup_remote_path = company.get("backup_remote_path", "vertex-ar-backups")
        
        if not backup_provider:
            raise HTTPException(
                status_code=400,
                detail=f"Company '{company['name']}' does not have a backup provider configured"
            )
        
        # Get storage and backup managers
        storage_manager = get_remote_storage_manager()
        storage = storage_manager.get_storage(backup_provider)
        
        if not storage:
            raise HTTPException(
                status_code=400,
                detail=f"Backup provider '{backup_provider}' is not configured"
            )
        
        backup_manager = create_backup_manager()
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            raise HTTPException(status_code=404, detail=f"Backup file not found: {backup_path}")
        
        logger.info(
            "Syncing company backup",
            company_id=company_id,
            company_name=company["name"],
            backup_path=backup_path,
            provider=backup_provider,
            remote_path=backup_remote_path,
            admin=_admin
        )
        
        # Sync to remote
        result = backup_manager.sync_to_remote(backup_file, storage, backup_remote_path)
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Sync failed"))
        
        return {
            "success": True,
            "message": f"Backup synced to {backup_provider}",
            "company_id": company_id,
            "company_name": company["name"],
            "provider": backup_provider,
            "remote_path": result.get("remote_path"),
            "size_mb": round(result.get("size", 0) / (1024 * 1024), 2)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to sync company backup", error=str(e), company_id=company_id, exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to sync backup: {str(e)}")


@router.post("/companies/{company_id}/download-backup")
async def download_company_backup(
    company_id: str,
    remote_filename: str,
    request: Request,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Download a backup from the company's configured remote storage.
    
    The company must have a backup provider configured.
    Requires admin authentication.
    """
    try:
        database = request.app.state.database
        
        # Get company backup config
        company = database.get_company(company_id)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found")
        
        backup_provider = company.get("backup_provider")
        backup_remote_path = company.get("backup_remote_path", "vertex-ar-backups")
        
        if not backup_provider:
            raise HTTPException(
                status_code=400,
                detail=f"Company '{company['name']}' does not have a backup provider configured"
            )
        
        # Get storage and backup managers
        storage_manager = get_remote_storage_manager()
        storage = storage_manager.get_storage(backup_provider)
        
        if not storage:
            raise HTTPException(
                status_code=400,
                detail=f"Backup provider '{backup_provider}' is not configured"
            )
        
        backup_manager = create_backup_manager()
        
        logger.info(
            "Downloading company backup",
            company_id=company_id,
            company_name=company["name"],
            remote_filename=remote_filename,
            provider=backup_provider,
            remote_path=backup_remote_path,
            admin=_admin
        )
        
        # Download from remote
        result = backup_manager.restore_from_remote(storage, remote_filename, backup_remote_path)
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Download failed"))
        
        return {
            "success": True,
            "message": result.get("message"),
            "company_id": company_id,
            "company_name": company["name"],
            "provider": backup_provider,
            "local_path": result.get("local_path"),
            "backup_type": result.get("backup_type")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to download company backup", error=str(e), company_id=company_id, exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to download backup: {str(e)}")
