"""
Backup management API endpoints.
"""
import re
import shutil
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


def resolve_backup_path(path_str: str, manager) -> Optional[Path]:
    """
    Resolve a backup path that may be from a different platform.
    Handles Windows paths on Linux and vice versa.
    
    Args:
        path_str: The path string from the backup metadata
        manager: BackupManager instance
        
    Returns:
        Resolved Path object or None if not found
    """
    clean_path_str = path_str.strip().replace('\u000b', '').replace('\u0008', '').replace('\n', '').replace('\r', '').replace('\t', '')
    
    # Check if this is a Windows path (has drive letter with colon, backslashes, or mixed separators)
    is_windows_path = (
        re.match(r'^[A-Za-z]:[/\\]', clean_path_str) is not None or 
        '\\' in clean_path_str
    )
    
    if is_windows_path:
        # Extract filename from Windows path
        filename = clean_path_str.replace('\\', '/').split('/')[-1]
        
        # Determine backup type from filename and construct local path
        if filename.startswith('db_backup_'):
            return manager.db_backup_dir / filename
        elif filename.startswith('storage_backup_'):
            return manager.storage_backup_dir / filename
        else:
            # Try to find the file in all backup directories
            for search_dir in [manager.db_backup_dir, manager.storage_backup_dir]:
                potential_path = search_dir / filename
                if potential_path.exists():
                    return potential_path
            return None
    else:
        # Handle Unix-style path
        backup_file = Path(clean_path_str)
        backup_dir = Path(manager.backup_dir).resolve()
        
        # Try to resolve the path
        try:
            backup_file = backup_file.resolve()
            backup_file.relative_to(backup_dir)
            return backup_file
        except ValueError:
            # If relative path fails, try with original backup path
            try:
                original_path = Path(clean_path_str)
                if not original_path.is_absolute():
                    # If it's a relative path, join it with backup_dir
                    backup_file = (backup_dir / original_path).resolve()
                    backup_file.relative_to(backup_dir)
                    return backup_file
            except (ValueError, RuntimeError):
                pass
        
        return None


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
        # Return paths as comma-separated string for full backups
        # Include only available paths
        paths = []
        db_path = db_meta.get("backup_path")
        st_path = st_meta.get("backup_path")
        if db_path:
            paths.append(db_path)
        if st_path:
            paths.append(st_path)
        backup_path = ",".join(paths) if paths else None
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
        backup_dir = Path(manager.backup_dir).resolve()

        # Resolve backup path using cross-platform helper
        backup_path = resolve_backup_path(request.backup_path, manager)
        
        if backup_path is None:
            raise HTTPException(status_code=404, detail=f"Backup file not found: {request.backup_path}")
        
        if not backup_path.exists():
            raise HTTPException(status_code=404, detail=f"Backup file not found: {str(backup_path)}")
        
        # Security check: Ensure the backup is within the allowed backup directory
        try:
            backup_path.resolve().relative_to(backup_dir)
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied: backup must be within backup directory")

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


@router.get("/schedule")
async def get_backup_schedule(_admin=Depends(require_admin)) -> Dict[str, Any]:
    """
    Get automated backup schedule information.

    Requires admin authentication.
    """
    try:
        from backup_scheduler import get_backup_scheduler

        scheduler = get_backup_scheduler()
        next_runs = scheduler.get_next_run_times()

        return {
            "success": True,
            "scheduler_running": scheduler.scheduler.running,
            "jobs": next_runs,
            "schedules": {
                "database": scheduler.database_schedule if scheduler.enable_database else "disabled",
                "storage": scheduler.storage_schedule if scheduler.enable_storage else "disabled",
                "full": scheduler.full_schedule if scheduler.enable_full else "disabled",
                "rotation": scheduler.rotation_schedule if scheduler.enable_rotation else "disabled"
            }
        }
    except Exception as e:
        logger.error("Failed to get backup schedule", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to get backup schedule: {str(e)}")


@router.get("/can-delete")
async def can_delete_backup(
    backup_path: str,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Check if a backup can be deleted.
    
    Returns False if it's the last backup to prevent accidental data loss.
    
    Requires admin authentication.
    """
    try:
        manager = create_backup_manager()
        
        # Get all backups
        all_backups = manager.list_backups("all")
        
        # If only one backup exists, prevent deletion
        if len(all_backups) <= 1:
            return {
                "success": True,
                "can_delete": False,
                "reason": "Cannot delete the last backup"
            }
        
        return {
            "success": True,
            "can_delete": True,
            "total_backups": len(all_backups)
        }
    
    except Exception as e:
        logger.error("Failed to check if backup can be deleted", error=str(e), exc_info=e)
        return {
            "success": False,
            "can_delete": True,  # Default to allowing deletion if check fails
            "error": str(e)
        }


@router.post("/restore-test")
async def test_restore_backup(
    request: BackupRestoreRequest,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Test if a backup can be restored without actually restoring.
    
    Checks:
    - File exists and is readable
    - Metadata is valid
    - Archive structure is valid (for tar files)
    - We have enough disk space
    
    Requires admin authentication.
    """
    try:
        manager = create_backup_manager()
        backup_dir = Path(manager.backup_dir).resolve()
        
        # Resolve backup path using cross-platform helper
        backup_path = resolve_backup_path(request.backup_path, manager)
        
        if backup_path is None:
            raise HTTPException(status_code=404, detail=f"Backup file not found")
        
        if not backup_path.exists():
            raise HTTPException(status_code=404, detail=f"Backup file not found")
        
        # Security check: Ensure the backup is within the allowed backup directory
        try:
            backup_path.resolve().relative_to(backup_dir)
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied: backup must be within backup directory")
        
        logger.info("Testing restore for backup", backup_path=str(backup_path), admin=_admin)
        
        # First verify backup integrity
        verify_result = manager.verify_backup(backup_path)
        if not verify_result.get("valid"):
            return {
                "success": False,
                "can_restore": False,
                "error": f"Backup is corrupted: {verify_result.get('error')}",
                "tests": {
                    "file_exists": False,
                    "checksum_valid": False,
                    "archive_readable": False
                }
            }
        
        # Check disk space
        disk_usage = shutil.disk_usage(manager.backup_dir)
        file_size = backup_path.stat().st_size
        
        # We need at least 2x the backup file size to restore safely
        required_space = file_size * 2
        available_space = disk_usage.free
        
        return {
            "success": True,
            "can_restore": available_space >= required_space,
            "tests": {
                "file_exists": True,
                "checksum_valid": True,
                "archive_readable": True,
                "disk_space_available": available_space >= required_space
            },
            "details": {
                "backup_size_mb": round(file_size / (1024 * 1024), 2),
                "required_space_mb": round(required_space / (1024 * 1024), 2),
                "available_space_mb": round(available_space / (1024 * 1024), 2)
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to test restore", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to test restore: {str(e)}")


@router.post("/verify")
async def verify_backup(
    request: BackupRestoreRequest,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Verify backup integrity without restoring.

    Checks:
    - File exists
    - Metadata exists
    - Checksum is valid
    - For tar files: archive structure is valid

    Requires admin authentication.
    """
    try:
        manager = create_backup_manager()
        backup_dir = Path(manager.backup_dir).resolve()

        # Resolve backup path using cross-platform helper
        backup_path = resolve_backup_path(request.backup_path, manager)
        
        if backup_path is None:
            raise HTTPException(status_code=404, detail=f"Backup file not found: {request.backup_path}")
        
        # Security check: Ensure the backup is within the allowed backup directory
        try:
            backup_path.resolve().relative_to(backup_dir)
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied: backup must be within backup directory")

        logger.info("Verifying backup", backup_path=str(backup_path), admin=_admin)

        result = manager.verify_backup(backup_path)

        if result.get("success"):
            return {
                "success": True,
                "valid": result.get("valid"),
                "message": result.get("message"),
                "file_size": result.get("file_size"),
                "checksum": result.get("checksum")
            }
        else:
            return {
                "success": False,
                "valid": False,
                "error": result.get("error"),
                "details": result
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to verify backup", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to verify backup: {str(e)}")


@router.delete("/delete")
async def delete_backup(
    backup_path: str,
    _admin=Depends(require_admin)
) -> Dict[str, Any]:
    """
    Delete a specific backup file.
    For full backups, backup_path can be comma-separated paths.

    Requires admin authentication.
    """
    try:
        manager = create_backup_manager()
        backup_dir = Path(manager.backup_dir).resolve()

        # Handle empty backup path
        if not backup_path or not backup_path.strip():
            raise HTTPException(status_code=400, detail="Backup path is required")

        # Handle multiple paths (for full backups)
        paths = [p.strip() for p in backup_path.split(",") if p.strip()]
        deleted_files = []
        missing_files = []

        for path_str in paths:
            # Resolve backup path using cross-platform helper
            backup_file = resolve_backup_path(path_str, manager)
            
            if backup_file is None:
                logger.warning("Backup file not found or invalid path", original_path=path_str)
                missing_files.append(path_str)
                continue
            
            # Validate backup path exists
            if not backup_file.exists():
                logger.warning("Backup file not found", backup_path=str(backup_file))
                missing_files.append(str(backup_file))
                continue
            
            # Security check: Ensure the backup is within the allowed backup directory
            try:
                backup_file.resolve().relative_to(backup_dir)
            except ValueError:
                logger.error("Security violation: backup path outside backup directory", 
                           backup_path=str(backup_file), backup_dir=str(backup_dir))
                raise HTTPException(status_code=403, detail="Access denied: backup must be within backup directory")

            logger.info("Deleting backup file", backup_path=str(backup_file), admin=_admin)

            # Delete the backup file
            backup_file.unlink()

            # Delete associated metadata file if exists
            metadata_file = backup_file.with_suffix(".json")
            if metadata_file.exists() and metadata_file != backup_file:
                metadata_file.unlink()
                logger.info("Deleted metadata file", metadata_path=str(metadata_file))

            deleted_files.append(str(backup_file))

        if not deleted_files and not missing_files:
            raise HTTPException(status_code=404, detail="Backup file not found")
        elif not deleted_files and missing_files:
            # All files were missing
            if len(missing_files) == 1:
                raise HTTPException(status_code=404, detail=f"Backup file not found: {missing_files[0]}")
            else:
                raise HTTPException(status_code=404, detail=f"Backup files not found: {', '.join(missing_files)}")
        elif missing_files:
            # Some files were deleted, some were missing
            logger.warning("Some backup files were not found", missing_files=missing_files, deleted_files=deleted_files)

        return {
            "success": True,
            "message": f"Deleted {len(deleted_files)} backup file(s)" + (f" ({len(missing_files)} not found)" if missing_files else ""),
            "deleted_files": deleted_files,
            "missing_files": missing_files if missing_files else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete backup", error=str(e), exc_info=e)
        raise HTTPException(status_code=500, detail=f"Failed to delete backup: {str(e)}")

