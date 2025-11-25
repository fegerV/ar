"""
Backup management system for Vertex AR.
Handles database and file backups with rotation and restoration.
Supports remote storage sync (Yandex Disk, Google Drive).
"""
import json
import shutil
import sqlite3
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib
import os

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
    
    def _split_large_file(self, file_path: Path, max_size_mb: int = 100) -> List[Path]:
        """
        Split a large file into smaller chunks.
        
        Args:
            file_path: Path to the large file
            max_size_mb: Maximum size of each chunk in MB
            
        Returns:
            List of paths to the split files
        """
        if not file_path.exists():
            return []
        
        file_size = file_path.stat().st_size
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size <= max_size_bytes:
            return [file_path]
        
        split_files = []
        base_name = file_path.stem
        extension = file_path.suffix
        parent_dir = file_path.parent
        
        chunk_num = 1
        bytes_read = 0
        
        try:
            with open(file_path, 'rb') as input_file:
                while bytes_read < file_size:
                    chunk_path = parent_dir / f"{base_name}.part{chunk_num:03d}{extension}"
                    split_files.append(chunk_path)
                    
                    with open(chunk_path, 'wb') as chunk_file:
                        chunk_bytes_written = 0
                        while chunk_bytes_written < max_size_bytes and bytes_read < file_size:
                            chunk_size = min(8192, max_size_bytes - chunk_bytes_written, file_size - bytes_read)
                            data = input_file.read(chunk_size)
                            chunk_file.write(data)
                            chunk_bytes_written += len(data)
                            bytes_read += len(data)
                    
                    chunk_num += 1
            
            logger.info(
                "File split into chunks",
                original_file=str(file_path),
                original_size_mb=round(file_size / (1024 * 1024), 2),
                chunks_count=len(split_files),
                chunk_size_mb=max_size_mb
            )
            
            return split_files
            
        except Exception as e:
            logger.error("Failed to split file", error=str(e), file=str(file_path))
            # Clean up partial chunks
            for chunk_file in split_files:
                if chunk_file.exists():
                    chunk_file.unlink()
            return []
    
    def _merge_split_files(self, split_files: List[Path], output_path: Path) -> bool:
        """
        Merge split files back into a single file.
        
        Args:
            split_files: List of split file paths (in order)
            output_path: Path for the merged output file
            
        Returns:
            True if merge was successful
        """
        if not split_files:
            return False
        
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as output_file:
                for split_file in split_files:
                    if not split_file.exists():
                        logger.error("Split file missing", file=str(split_file))
                        return False
                    
                    with open(split_file, 'rb') as input_file:
                        shutil.copyfileobj(input_file, output_file)
            
            logger.info(
                "Files merged successfully",
                output_file=str(output_path),
                chunks_count=len(split_files)
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to merge files", error=str(e), output=str(output_path))
            return False
    
    def _get_backup_settings(self) -> Dict[str, Any]:
        """
        Get backup settings from configuration file.
        
        Returns:
            Dictionary with backup settings
        """
        try:
            config_file = Path("app_data/backup_settings.json")
            if config_file.exists():
                with open(config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error("Failed to load backup settings", error=str(e))
        
        # Default settings
        return {
            "compression": "gz",
            "max_backups": 7,
            "auto_split_backups": True,
            "max_backup_size_mb": 500
        }
    
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
        
        # Get backup settings
        settings = self._get_backup_settings()
        compression = settings.get("compression", self.compression)
        auto_split = settings.get("auto_split_backups", True)
        max_size_mb = settings.get("max_backup_size_mb", 500)
        
        timestamp = timestamp or self._get_timestamp()
        archive_ext = f".tar.{compression}" if compression else ".tar"
        backup_filename = f"storage_backup_{timestamp}{archive_ext}"
        backup_path = self.storage_backup_dir / backup_filename
        
        try:
            # Create compressed tar archive
            compression_mode = f"w:{compression}" if compression else "w"
            
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
                "compression": compression,
                "created_at": datetime.now().isoformat(),
                "split_files": []
            }
            
            # Split large file if needed
            split_files = []
            if auto_split and file_size > max_size_mb * 1024 * 1024:
                split_files = self._split_large_file(backup_path, max_size_mb)
                if split_files and len(split_files) > 1:
                    # Remove original large file
                    backup_path.unlink()
                    # Update backup path to first split file
                    backup_path = split_files[0]
                    # Add split files info to metadata
                    metadata["split_files"] = [str(f) for f in split_files]
                    metadata["split"] = True
                    metadata["chunk_size_mb"] = max_size_mb
            
            # Save metadata file (for main backup file or first chunk)
            metadata_path = backup_path.with_suffix(".json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(
                "Storage backup created",
                backup_path=str(backup_path),
                size_mb=round(file_size / (1024 * 1024), 2),
                file_count=file_count,
                chunks=len(split_files) if split_files else 1
            )
            
            return {
                "success": True,
                "backup_path": str(backup_path),
                "metadata": metadata,
                "split_files": split_files
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
    
    def verify_backup(self, backup_path: Path) -> Dict[str, Any]:
        """
        Verify backup integrity without restoring.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            Dictionary with verification results
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            return {"success": False, "error": "Backup file not found", "valid": False}
        
        try:
            # Load metadata
            metadata_path = backup_path.with_suffix(".json")
            if not metadata_path.exists():
                return {
                    "success": False,
                    "error": "Metadata file not found",
                    "valid": False
                }
            
            with open(metadata_path) as f:
                metadata = json.load(f)
            
            # Verify checksum
            current_checksum = self._calculate_checksum(backup_path)
            checksum_valid = current_checksum == metadata.get("checksum")
            
            if not checksum_valid:
                logger.error("Backup checksum mismatch", backup_path=str(backup_path))
                return {
                    "success": False,
                    "error": "Checksum mismatch - backup may be corrupted",
                    "valid": False,
                    "expected_checksum": metadata.get("checksum"),
                    "actual_checksum": current_checksum
                }
            
            # For tar files, verify structure
            if backup_path.suffix in [".tar", ".tgz"] or ".tar." in backup_path.name:
                try:
                    with tarfile.open(backup_path, "r:*") as tar:
                        members = tar.getmembers()
                        file_count = len(members)
                except Exception as e:
                    logger.error("Archive verification failed", error=str(e))
                    return {
                        "success": False,
                        "error": f"Archive corrupted: {str(e)}",
                        "valid": False
                    }
            
            logger.info("Backup verification successful", backup_path=str(backup_path))
            return {
                "success": True,
                "valid": True,
                "message": "Backup is valid and intact",
                "file_size": backup_path.stat().st_size,
                "checksum": current_checksum,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error("Failed to verify backup", error=str(e), exc_info=e)
            return {"success": False, "error": str(e), "valid": False}
    
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
    
    def sync_to_remote(self, backup_path: Path, remote_storage, remote_dir: str = "vertex-ar-backups") -> Dict[str, Any]:
        """
        Sync a backup to remote storage.
        
        Args:
            backup_path: Path to local backup file
            remote_storage: RemoteStorage instance
            remote_dir: Remote directory path
            
        Returns:
            Dictionary with sync result
        """
        if not backup_path.exists():
            return {"success": False, "error": "Backup file not found"}
        
        try:
            # Check if this is a split backup
            metadata_path = backup_path.with_suffix(".json")
            split_files = []
            
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    split_files = metadata.get("split_files", [])
            
            # If split files exist, sync all of them
            if split_files:
                uploaded_files = []
                total_size = 0
                
                for split_file_path in split_files:
                    split_path = Path(split_file_path)
                    if not split_path.exists():
                        logger.error("Split file not found", file=str(split_path))
                        continue
                    
                    # Construct remote path for split file
                    remote_path = f"{remote_dir}/{split_path.name}"
                    
                    # Upload split file
                    result = remote_storage.upload_file(split_path, remote_path)
                    
                    if result.get("success"):
                        uploaded_files.append(split_path.name)
                        total_size += split_path.stat().st_size
                        logger.info(
                            "Split file synced to remote storage",
                            split_file=split_path.name,
                            remote_path=remote_path
                        )
                    else:
                        logger.error(
                            "Failed to sync split file",
                            split_file=split_path.name,
                            error=result.get("error")
                        )
                
                # Upload metadata file
                metadata_remote_path = f"{remote_dir}/{metadata_path.name}"
                remote_storage.upload_file(metadata_path, metadata_remote_path)
                
                if uploaded_files:
                    logger.info(
                        "Split backup synced to remote storage",
                        chunks_count=len(uploaded_files),
                        total_size_mb=round(total_size / (1024 * 1024), 2)
                    )
                    
                    return {
                        "success": True,
                        "remote_path": f"{remote_dir}/{Path(split_files[0]).name}",
                        "split_files": uploaded_files,
                        "chunks_count": len(uploaded_files),
                        "size": total_size
                    }
                else:
                    return {"success": False, "error": "No split files were uploaded"}
            
            # Single file backup (original logic)
            else:
                # Construct remote path
                remote_path = f"{remote_dir}/{backup_path.name}"
                
                # Upload backup file
                result = remote_storage.upload_file(backup_path, remote_path)
                
                if result.get("success"):
                    # Also upload metadata file if exists
                    metadata_path = backup_path.with_suffix(".json")
                    if metadata_path.exists():
                        metadata_remote_path = f"{remote_dir}/{metadata_path.name}"
                        remote_storage.upload_file(metadata_path, metadata_remote_path)
                    
                    logger.info(
                        "Backup synced to remote storage",
                        backup_file=backup_path.name,
                        remote_path=remote_path
                    )
                
                return result
            
        except Exception as e:
            logger.error("Failed to sync backup to remote", error=str(e))
            return {"success": False, "error": str(e)}
    
    def restore_from_remote(
        self, 
        remote_storage, 
        remote_filename: str, 
        remote_dir: str = "vertex-ar-backups"
    ) -> Dict[str, Any]:
        """
        Restore a backup from remote storage.
        
        Args:
            remote_storage: RemoteStorage instance
            remote_filename: Name of backup file in remote storage
            remote_dir: Remote directory path
            
        Returns:
            Dictionary with restore result
        """
        try:
            # Determine backup type from filename
            if "db_backup" in remote_filename:
                local_dir = self.db_backup_dir
                backup_type = "database"
            elif "storage_backup" in remote_filename:
                local_dir = self.storage_backup_dir
                backup_type = "storage"
            else:
                return {"success": False, "error": "Cannot determine backup type"}
            
            # Download backup file
            local_path = local_dir / remote_filename
            remote_path = f"{remote_dir}/{remote_filename}"
            
            result = remote_storage.download_file(remote_path, local_path)
            
            if not result.get("success"):
                return result
            
            # Download metadata file
            metadata_filename = Path(remote_filename).with_suffix(".json").name
            metadata_local_path = local_path.with_suffix(".json")
            metadata_remote_path = f"{remote_dir}/{metadata_filename}"
            
            remote_storage.download_file(metadata_remote_path, metadata_local_path)
            
            logger.info(
                "Backup downloaded from remote storage",
                backup_file=remote_filename,
                local_path=str(local_path)
            )
            
            return {
                "success": True,
                "backup_type": backup_type,
                "local_path": str(local_path),
                "message": f"Backup downloaded. Use restore endpoint to apply it."
            }
            
        except Exception as e:
            logger.error("Failed to restore from remote", error=str(e))
            return {"success": False, "error": str(e)}


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
