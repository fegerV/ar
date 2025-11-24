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

        # Normalize the backup path to handle potential URL encoding issues
        # Remove control characters that might be included in URL-encoded paths
        clean_backup_path = request.backup_path.strip().replace('\u000b', '').replace('\u0008', '').replace('\n', '').replace('\r', '').replace('\t', '')
        backup_path = Path(clean_backup_path)

        # Handle potential path traversal security issues and normalize path
        backup_path = backup_path.resolve()
        backup_dir = Path(manager.backup_dir).resolve()

        # Verify that the backup file is within the allowed backup directory
        # Check if backup_path is a subpath of backup_dir using relative_to for security
        try:
            backup_path.relative_to(backup_dir)
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied: backup must be within backup directory")

        if not backup_path.exists():
            raise HTTPException(status_code=404, detail=f"Backup file not found: {str(backup_path)}")

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

        # Normalize the backup path
        clean_backup_path = request.backup_path.strip().replace('\u000b', '').replace('\u0008', '').replace('\n', '').replace('\r', '').replace('\t', '')
        backup_path = Path(clean_backup_path)

        # Handle potential path traversal security issues
        backup_path = backup_path.resolve()
        backup_dir = Path(manager.backup_dir).resolve()

        # Verify that the backup file is within the allowed backup directory
        try:
            backup_path.relative_to(backup_dir)
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
            # Normalize the path to handle potential URL encoding issues
            # Remove control characters that might be included in URL-encoded paths
            clean_path_str = path_str.strip().replace('\u000b', '').replace('\u0008', '').replace('\n', '').replace('\r', '').replace('\t', '')
            backup_file = Path(clean_path_str)

            # Resolve the path to handle any relative components and normalize it
            backup_file = backup_file.resolve()

            # Ensure the backup is within the allowed backup directory (security check)
            try:
                backup_file.relative_to(backup_dir)
            except ValueError:
                raise HTTPException(status_code=403, detail="Access denied: backup must be within backup directory")

            # Validate backup path exists
            if not backup_file.exists():
                logger.warning("Backup file not found", backup_path=str(backup_file))
                missing_files.append(str(backup_file))
                continue

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

