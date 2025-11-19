"""
Backup management API endpoints.
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from app.api.auth import require_admin
from backup_manager import create_backup_manager
from logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/backups", tags=["backups"])


class BackupCreateRequest(BaseModel):
    """Request model for creating a backup."""
    type: str = "full"  # full, database, or storage
    

class BackupRestoreRequest(BaseModel):
    """Request model for restoring from backup."""
    backup_path: str
    verify_checksum: bool = True


class BackupInfo(BaseModel):
    """Backup information model."""
    timestamp: str
    type: str
    created_at: str
    file_size: Optional[int] = None
    backup_path: Optional[str] = None
    checksum: Optional[str] = None
    file_count: Optional[int] = None


class BackupStats(BaseModel):
    """Backup statistics model."""
    database_backups: int
    storage_backups: int
    full_backups: int
    total_backups: int
    database_size_mb: float
    storage_size_mb: float
    total_size_mb: float
    backup_dir: str
    latest_backup: Optional[BackupInfo] = None


def format_backup_info(metadata: Dict[str, Any]) -> BackupInfo:
    """Format backup metadata as BackupInfo model."""
    backup_type = metadata.get("type", "unknown")
    
    # For full backups, combine database and storage info
    if backup_type == "full":
        db_meta = metadata.get("database", {})
        st_meta = metadata.get("storage", {})
        file_size = db_meta.get("file_size", 0) + st_meta.get("file_size", 0)
        file_count = st_meta.get("file_count", 0)
        backup_path = None
    else:
        file_size = metadata.get("file_size")
        file_count = metadata.get("file_count")
        backup_path = metadata.get("backup_path")
    
    return BackupInfo(
        timestamp=metadata.get("timestamp", ""),
        type=backup_type,
        created_at=metadata.get("created_at", ""),
        file_size=file_size,
        backup_path=backup_path,
        checksum=metadata.get("checksum"),
        file_count=file_count
    )


@router.post("/create")
async def create_backup(
    request: BackupCreateRequest,
    background_tasks: BackgroundTasks,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Create a new backup.
    
    Requires admin authentication.
    """
    try:
        manager = create_backup_manager()
        
        logger.info("Creating backup", backup_type=request.type, admin=_admin)
        
        if request.type == "database":
            result = manager.backup_database()
        elif request.type == "storage":
            result = manager.backup_storage()
        elif request.type == "full":
            result = manager.create_full_backup()
        else:
            raise HTTPException(status_code=400, detail=f"Invalid backup type: {request.type}")
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Backup failed"))
        
        # Rotate old backups in background
        background_tasks.add_task(manager.rotate_backups)
        
        return {
            "success": True,
            "message": "Backup created successfully",
            "backup": format_backup_info(result.get("metadata", result))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create backup", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to create backup: {str(e)}")


@router.get("/list")
async def list_backups(
    backup_type: str = "all",
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    List all available backups.
    
    Requires admin authentication.
    """
    try:
        manager = create_backup_manager()
        
        backups = manager.list_backups(backup_type)
        
        return {
            "success": True,
            "backups": [format_backup_info(b) for b in backups],
            "count": len(backups)
        }
        
    except Exception as e:
        logger.error("Failed to list backups", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")


@router.get("/stats")
async def get_backup_stats(_admin=Depends(require_admin)) -> BackupStats:
    """
    Get backup statistics.
    
    Requires admin authentication.
    """
    try:
        manager = create_backup_manager()
        
        stats = manager.get_backup_stats()
        
        # Format latest backup
        latest_backup = None
        if stats.get("latest_backup"):
            latest_backup = format_backup_info(stats["latest_backup"])
        
        return BackupStats(
            database_backups=stats["database_backups"],
            storage_backups=stats["storage_backups"],
            full_backups=stats["full_backups"],
            total_backups=stats["total_backups"],
            database_size_mb=stats["database_size_mb"],
            storage_size_mb=stats["storage_size_mb"],
            total_size_mb=stats["total_size_mb"],
            backup_dir=stats["backup_dir"],
            latest_backup=latest_backup
        )
        
    except Exception as e:
        logger.error("Failed to get backup stats", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to get backup stats: {str(e)}")


@router.post("/restore")
async def restore_backup(
    request: BackupRestoreRequest,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Restore from a backup.
    
    ⚠️ WARNING: This will overwrite current data!
    
    Requires admin authentication.
    """
    try:
        manager = create_backup_manager()
        
        backup_path = Path(request.backup_path)
        
        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="Backup file not found")
        
        logger.warning(
            "Restoring from backup",
            backup_path=str(backup_path),
            admin=_admin
        )
        
        # Detect backup type
        if "db_backup" in backup_path.name or backup_path.suffix == ".db":
            success = manager.restore_database(backup_path, verify_checksum=request.verify_checksum)
            backup_type = "database"
        elif "storage_backup" in backup_path.name:
            success = manager.restore_storage(backup_path, verify_checksum=request.verify_checksum)
            backup_type = "storage"
        else:
            raise HTTPException(status_code=400, detail="Cannot determine backup type from filename")
        
        if not success:
            raise HTTPException(status_code=500, detail="Restore failed")
        
        logger.info(
            "Backup restored successfully",
            backup_type=backup_type,
            backup_path=str(backup_path)
        )
        
        return {
            "success": True,
            "message": f"{backup_type.capitalize()} restored successfully",
            "backup_type": backup_type,
            "backup_path": str(backup_path)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to restore backup", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to restore backup: {str(e)}")


@router.post("/rotate")
async def rotate_backups(
    max_backups: int = 7,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Rotate (remove old) backups.
    
    Requires admin authentication.
    """
    try:
        manager = create_backup_manager(max_backups=max_backups)
        
        logger.info("Rotating backups", max_backups=max_backups, admin=_admin)
        
        removed = manager.rotate_backups()
        
        return {
            "success": True,
            "message": "Backup rotation completed",
            "removed": removed,
            "total_removed": sum(removed.values())
        }
        
    except Exception as e:
        logger.error("Failed to rotate backups", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to rotate backups: {str(e)}")
