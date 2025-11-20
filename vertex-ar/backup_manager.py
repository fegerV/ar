"""
Backup management system for Vertex AR.
Handles database and file backups with rotation and restoration.
"""
import json
import shutil
import sqlite3
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

from logging_setup import get_logger

logger = get_logger(__name__)


class BackupManager:
    """Manages backups for database and storage files."""
    
    def __init__(
        self,
        backup_dir: Path,
        db_path: Path,
        storage_path: Path,
        max_backups: int = 7,
        compression: str = "gz"
    ):
        """
        Initialize backup manager.
        
        Args:
            backup_dir: Directory to store backups
            db_path: Path to SQLite database file
            storage_path: Path to storage directory
            max_backups: Maximum number of backups to keep
            compression: Compression type for tar archives (gz, bz2, xz, or empty for no compression)
        """
        self.backup_dir = Path(backup_dir)
        self.db_path = Path(db_path)
        self.storage_path = Path(storage_path)
        self.max_backups = max_backups
        self.compression = compression
        
        # Create backup directory if it doesn't exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Subdirectories for different backup types
        self.db_backup_dir = self.backup_dir / "database"
        self.storage_backup_dir = self.backup_dir / "storage"
        self.full_backup_dir = self.backup_dir / "full"
        
        for dir_path in [self.db_backup_dir, self.storage_backup_dir, self.full_backup_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for backup naming."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def backup_database(self, timestamp: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a backup of the SQLite database.
        
        Args:
            timestamp: Custom timestamp for backup (optional)
            
        Returns:
            Dictionary with backup information
        """
        if not self.db_path.exists():
            logger.warning("Database file not found", db_path=str(self.db_path))
            return {"success": False, "error": "Database file not found"}
        
        timestamp = timestamp or self._get_timestamp()
        backup_filename = f"db_backup_{timestamp}.db"
        backup_path = self.db_backup_dir / backup_filename
        
        try:
            # Use SQLite's backup API for safe backup
            source_conn = sqlite3.connect(str(self.db_path))
            backup_conn = sqlite3.connect(str(backup_path))
            
            with backup_conn:
                source_conn.backup(backup_conn)
            
            source_conn.close()
            backup_conn.close()
            
            # Calculate checksum
            checksum = self._calculate_checksum(backup_path)
            
            # Get file size
            file_size = backup_path.stat().st_size
            
            # Create metadata file
            metadata = {
                "timestamp": timestamp,
                "type": "database",
                "original_path": str(self.db_path),
                "backup_path": str(backup_path),
                "file_size": file_size,
                "checksum": checksum,
                "created_at": datetime.now().isoformat()
            }
            
            metadata_path = backup_path.with_suffix(".json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(
                "Database backup created",
                backup_path=str(backup_path),
                size_mb=round(file_size / (1024 * 1024), 2)
            )
            
            return {
                "success": True,
                "backup_path": str(backup_path),
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error("Failed to backup database", error=str(e), exc_info=e)
            return {"success": False, "error": str(e)}
    
    def backup_storage(self, timestamp: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a compressed backup of the storage directory.
        
        Args:
            timestamp: Custom timestamp for backup (optional)
            
        Returns:
            Dictionary with backup information
        """
        if not self.storage_path.exists():
            logger.warning("Storage directory not found", storage_path=str(self.storage_path))
            return {"success": False, "error": "Storage directory not found"}
        
        timestamp = timestamp or self._get_timestamp()
        archive_ext = f".tar.{self.compression}" if self.compression else ".tar"
        backup_filename = f"storage_backup_{timestamp}{archive_ext}"
        backup_path = self.storage_backup_dir / backup_filename
        
        try:
            # Create compressed tar archive
            compression_mode = f"w:{self.compression}" if self.compression else "w"
            
            with tarfile.open(backup_path, compression_mode) as tar:
                tar.add(self.storage_path, arcname="storage")
            
            # Calculate checksum
            checksum = self._calculate_checksum(backup_path)
            
            # Get file size
            file_size = backup_path.stat().st_size
            
            # Count files
            file_count = sum(1 for _ in self.storage_path.rglob("*") if _.is_file())
            
            # Create metadata file
            metadata = {
                "timestamp": timestamp,
                "type": "storage",
                "original_path": str(self.storage_path),
                "backup_path": str(backup_path),
                "file_size": file_size,
                "file_count": file_count,
                "checksum": checksum,
                "compression": self.compression,
                "created_at": datetime.now().isoformat()
            }
            
            metadata_path = backup_path.with_suffix(".json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(
                "Storage backup created",
                backup_path=str(backup_path),
                size_mb=round(file_size / (1024 * 1024), 2),
                file_count=file_count
            )
            
            return {
                "success": True,
                "backup_path": str(backup_path),
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error("Failed to backup storage", error=str(e), exc_info=e)
            return {"success": False, "error": str(e)}
    
    def create_full_backup(self) -> Dict[str, Any]:
        """
        Create a full backup (database + storage).
        
        Returns:
            Dictionary with backup information
        """
        timestamp = self._get_timestamp()
        
        logger.info("Starting full backup", timestamp=timestamp)
        
        # Backup database
        db_result = self.backup_database(timestamp)
        
        # Backup storage
        storage_result = self.backup_storage(timestamp)
        
        # Create combined metadata
        metadata = {
            "timestamp": timestamp,
            "type": "full",
            "database": db_result.get("metadata") if db_result.get("success") else None,
            "storage": storage_result.get("metadata") if storage_result.get("success") else None,
            "created_at": datetime.now().isoformat(),
            "success": db_result.get("success") and storage_result.get("success"),
            "db_success": db_result.get("success", False),
            "storage_success": storage_result.get("success", False),
            "errors": []
        }
        
        # Add error messages if components failed
        if not db_result.get("success"):
            metadata["errors"].append(f"Database backup failed: {db_result.get('error', 'Unknown error')}")
            logger.error("Database backup failed in full backup", timestamp=timestamp, error=db_result.get("error"))
        
        if not storage_result.get("success"):
            metadata["errors"].append(f"Storage backup failed: {storage_result.get('error', 'Unknown error')}")
            logger.error("Storage backup failed in full backup", timestamp=timestamp, error=storage_result.get("error"))
        
        # Save full backup metadata only if at least one component succeeded
        if db_result.get("success") or storage_result.get("success"):
            metadata_path = self.full_backup_dir / f"full_backup_{timestamp}.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
        
        if metadata["success"]:
            logger.info("Full backup completed successfully", timestamp=timestamp)
        else:
            logger.error("Full backup completed with errors", timestamp=timestamp, errors=metadata["errors"])
        
        return metadata
    
    def list_backups(self, backup_type: str = "all") -> List[Dict[str, Any]]:
        """
        List available backups.
        
        Args:
            backup_type: Type of backups to list (database, storage, full, or all)
            
        Returns:
            List of backup metadata dictionaries
        """
        backups = []
        
        if backup_type in ["database", "all"]:
            for metadata_file in self.db_backup_dir.glob("*.json"):
                try:
                    with open(metadata_file) as f:
                        backups.append(json.load(f))
                except Exception as e:
                    logger.error("Failed to read backup metadata", file=str(metadata_file), error=str(e))
        
        if backup_type in ["storage", "all"]:
            for metadata_file in self.storage_backup_dir.glob("*.json"):
                try:
                    with open(metadata_file) as f:
                        backups.append(json.load(f))
                except Exception as e:
                    logger.error("Failed to read backup metadata", file=str(metadata_file), error=str(e))
        
        if backup_type in ["full", "all"]:
            for metadata_file in self.full_backup_dir.glob("*.json"):
                try:
                    with open(metadata_file) as f:
                        backups.append(json.load(f))
                except Exception as e:
                    logger.error("Failed to read backup metadata", file=str(metadata_file), error=str(e))
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return backups
    
    def rotate_backups(self) -> Dict[str, int]:
        """
        Remove old backups, keeping only the most recent ones.
        
        Returns:
            Dictionary with counts of removed backups by type
        """
        removed = {"database": 0, "storage": 0, "full": 0}
        
        # Rotate database backups
        db_backups = sorted(
            self.db_backup_dir.glob("db_backup_*.db"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        for backup_file in db_backups[self.max_backups:]:
            try:
                backup_file.unlink()
                # Remove metadata file too
                metadata_file = backup_file.with_suffix(".json")
                if metadata_file.exists():
                    metadata_file.unlink()
                removed["database"] += 1
                logger.info("Removed old database backup", file=backup_file.name)
            except Exception as e:
                logger.error("Failed to remove old backup", file=str(backup_file), error=str(e))
        
        # Rotate storage backups
        storage_backups = sorted(
            [f for f in self.storage_backup_dir.glob("storage_backup_*") if not f.suffix == ".json"],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        for backup_file in storage_backups[self.max_backups:]:
            try:
                backup_file.unlink()
                # Remove metadata file too
                metadata_file = backup_file.with_suffix(".json")
                if metadata_file.exists():
                    metadata_file.unlink()
                removed["storage"] += 1
                logger.info("Removed old storage backup", file=backup_file.name)
            except Exception as e:
                logger.error("Failed to remove old backup", file=str(backup_file), error=str(e))
        
        # Rotate full backup metadata
        full_backups = sorted(
            self.full_backup_dir.glob("full_backup_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        for metadata_file in full_backups[self.max_backups:]:
            try:
                metadata_file.unlink()
                removed["full"] += 1
                logger.info("Removed old full backup metadata", file=metadata_file.name)
            except Exception as e:
                logger.error("Failed to remove old backup metadata", file=str(metadata_file), error=str(e))
        
        if sum(removed.values()) > 0:
            logger.info("Backup rotation completed", removed=removed)
        
        return removed
    
    def restore_database(self, backup_path: Path, verify_checksum: bool = True) -> bool:
        """
        Restore database from backup.
        
        Args:
            backup_path: Path to backup file
            verify_checksum: Whether to verify checksum before restoring
            
        Returns:
            True if restore was successful
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            logger.error("Backup file not found", backup_path=str(backup_path))
            return False
        
        try:
            # Load metadata
            metadata_path = backup_path.with_suffix(".json")
            if metadata_path.exists() and verify_checksum:
                with open(metadata_path) as f:
                    metadata = json.load(f)
                
                # Verify checksum
                current_checksum = self._calculate_checksum(backup_path)
                if current_checksum != metadata.get("checksum"):
                    logger.error("Backup checksum mismatch", backup_path=str(backup_path))
                    return False
            
            # Create backup of current database
            if self.db_path.exists():
                backup_current = self.db_path.with_suffix(f".db.before_restore_{self._get_timestamp()}")
                shutil.copy2(self.db_path, backup_current)
                logger.info("Current database backed up", backup_path=str(backup_current))
            
            # Restore database
            shutil.copy2(backup_path, self.db_path)
            
            logger.info("Database restored successfully", backup_path=str(backup_path))
            return True
            
        except Exception as e:
            logger.error("Failed to restore database", error=str(e), exc_info=e)
            return False
    
    def restore_storage(self, backup_path: Path, verify_checksum: bool = True) -> bool:
        """
        Restore storage from backup.
        
        Args:
            backup_path: Path to backup archive
            verify_checksum: Whether to verify checksum before restoring
            
        Returns:
            True if restore was successful
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            logger.error("Backup file not found", backup_path=str(backup_path))
            return False
        
        try:
            # Load metadata
            metadata_path = backup_path.with_suffix(".json")
            if metadata_path.exists() and verify_checksum:
                with open(metadata_path) as f:
                    metadata = json.load(f)
                
                # Verify checksum
                current_checksum = self._calculate_checksum(backup_path)
                if current_checksum != metadata.get("checksum"):
                    logger.error("Backup checksum mismatch", backup_path=str(backup_path))
                    return False
            
            # Create backup of current storage
            if self.storage_path.exists():
                backup_current = self.storage_path.parent / f"storage_before_restore_{self._get_timestamp()}"
                shutil.copytree(self.storage_path, backup_current)
                logger.info("Current storage backed up", backup_path=str(backup_current))
            
            # Remove current storage
            if self.storage_path.exists():
                shutil.rmtree(self.storage_path)
            
            # Extract backup
            with tarfile.open(backup_path, "r:*") as tar:
                # Extract to parent directory (archive contains 'storage' folder)
                tar.extractall(self.storage_path.parent)
            
            logger.info("Storage restored successfully", backup_path=str(backup_path))
            return True
            
        except Exception as e:
            logger.error("Failed to restore storage", error=str(e), exc_info=e)
            return False
    
    def get_backup_stats(self) -> Dict[str, Any]:
        """
        Get statistics about backups.
        
        Returns:
            Dictionary with backup statistics
        """
        db_backups = list(self.db_backup_dir.glob("db_backup_*.db"))
        storage_backups = [f for f in self.storage_backup_dir.glob("storage_backup_*") if not f.suffix == ".json"]
        full_backups = list(self.full_backup_dir.glob("full_backup_*.json"))
        
        db_size = sum(f.stat().st_size for f in db_backups)
        storage_size = sum(f.stat().st_size for f in storage_backups)
        
        latest_backup = None
        all_backups = self.list_backups("full")
        if all_backups:
            latest_backup = all_backups[0]
        
        return {
            "database_backups": len(db_backups),
            "storage_backups": len(storage_backups),
            "full_backups": len(full_backups),
            "total_backups": len(db_backups) + len(storage_backups) + len(full_backups),
            "database_size_mb": round(db_size / (1024 * 1024), 2),
            "storage_size_mb": round(storage_size / (1024 * 1024), 2),
            "total_size_mb": round((db_size + storage_size) / (1024 * 1024), 2),
            "latest_backup": latest_backup,
            "backup_dir": str(self.backup_dir)
        }


def create_backup_manager(
    backup_dir: Optional[Path] = None,
    db_path: Optional[Path] = None,
    storage_path: Optional[Path] = None,
    max_backups: int = 7
) -> BackupManager:
    """
    Factory function to create BackupManager with default paths.
    
    Args:
        backup_dir: Directory for backups (default: BASE_DIR/backups)
        db_path: Database path (default: from config)
        storage_path: Storage path (default: from config)
        max_backups: Maximum backups to keep
        
    Returns:
        BackupManager instance
    """
    from app.config import settings
    
    if backup_dir is None:
        backup_dir = settings.BASE_DIR / "backups"
    
    if db_path is None:
        db_path = settings.DB_PATH
    
    if storage_path is None:
        storage_path = settings.STORAGE_ROOT
    
    return BackupManager(
        backup_dir=backup_dir,
        db_path=db_path,
        storage_path=storage_path,
        max_backups=max_backups
    )
