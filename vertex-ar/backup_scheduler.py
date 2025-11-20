"""
Automated backup scheduler for Vertex AR.
Uses APScheduler to run periodic backups.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backup_manager import create_backup_manager
from logging_setup import get_logger

logger = get_logger(__name__)


class BackupScheduler:
    """Handles automated scheduled backups."""
    
    def __init__(
        self,
        backup_manager=None,
        database_schedule: Optional[str] = None,
        storage_schedule: Optional[str] = None,
        full_schedule: Optional[str] = None,
        rotation_schedule: Optional[str] = None,
    ):
        """
        Initialize backup scheduler.
        
        Args:
            backup_manager: BackupManager instance (created if None)
            database_schedule: Cron expression for database backups (default: daily at 2 AM)
            storage_schedule: Cron expression for storage backups (default: weekly Sunday at 3 AM)
            full_schedule: Cron expression for full backups (default: weekly Sunday at 3 AM)
            rotation_schedule: Cron expression for rotation (default: daily at 4 AM)
        """
        self.backup_manager = backup_manager or create_backup_manager()
        self.scheduler = BackgroundScheduler()
        
        # Default schedules from environment or defaults
        self.database_schedule = database_schedule or os.getenv("BACKUP_DATABASE_SCHEDULE", "0 2 * * *")
        self.storage_schedule = storage_schedule or os.getenv("BACKUP_STORAGE_SCHEDULE", "0 3 * * 0")
        self.full_schedule = full_schedule or os.getenv("BACKUP_FULL_SCHEDULE", "0 3 * * 0")
        self.rotation_schedule = rotation_schedule or os.getenv("BACKUP_ROTATION_SCHEDULE", "0 4 * * *")
        
        # Enable/disable schedules
        self.enable_database = os.getenv("BACKUP_DATABASE_ENABLED", "true").lower() == "true"
        self.enable_storage = os.getenv("BACKUP_STORAGE_ENABLED", "false").lower() == "true"
        self.enable_full = os.getenv("BACKUP_FULL_ENABLED", "true").lower() == "true"
        self.enable_rotation = os.getenv("BACKUP_ROTATION_ENABLED", "true").lower() == "true"
        
        self._setup_jobs()
    
    def _setup_jobs(self):
        """Setup scheduled backup jobs."""
        try:
            # Database backup job
            if self.enable_database:
                self.scheduler.add_job(
                    self._run_database_backup,
                    CronTrigger.from_crontab(self.database_schedule),
                    id="database_backup",
                    name="Database Backup",
                    replace_existing=True,
                    misfire_grace_time=300  # 5 minutes grace period
                )
                logger.info("Scheduled database backup", schedule=self.database_schedule)
            
            # Storage backup job
            if self.enable_storage:
                self.scheduler.add_job(
                    self._run_storage_backup,
                    CronTrigger.from_crontab(self.storage_schedule),
                    id="storage_backup",
                    name="Storage Backup",
                    replace_existing=True,
                    misfire_grace_time=300
                )
                logger.info("Scheduled storage backup", schedule=self.storage_schedule)
            
            # Full backup job
            if self.enable_full:
                self.scheduler.add_job(
                    self._run_full_backup,
                    CronTrigger.from_crontab(self.full_schedule),
                    id="full_backup",
                    name="Full Backup",
                    replace_existing=True,
                    misfire_grace_time=300
                )
                logger.info("Scheduled full backup", schedule=self.full_schedule)
            
            # Rotation job
            if self.enable_rotation:
                self.scheduler.add_job(
                    self._run_rotation,
                    CronTrigger.from_crontab(self.rotation_schedule),
                    id="backup_rotation",
                    name="Backup Rotation",
                    replace_existing=True,
                    misfire_grace_time=300
                )
                logger.info("Scheduled backup rotation", schedule=self.rotation_schedule)
        
        except Exception as e:
            logger.error("Failed to setup backup jobs", error=str(e), exc_info=e)
            raise
    
    def _run_database_backup(self):
        """Run database backup job."""
        try:
            logger.info("Starting scheduled database backup")
            result = self.backup_manager.backup_database()
            
            if result.get("success"):
                logger.info(
                    "Scheduled database backup completed",
                    backup_path=result.get("backup_path"),
                    size_mb=round(result.get("metadata", {}).get("file_size", 0) / (1024 * 1024), 2)
                )
            else:
                logger.error("Scheduled database backup failed", error=result.get("error"))
        
        except Exception as e:
            logger.error("Exception during scheduled database backup", error=str(e), exc_info=e)
    
    def _run_storage_backup(self):
        """Run storage backup job."""
        try:
            logger.info("Starting scheduled storage backup")
            result = self.backup_manager.backup_storage()
            
            if result.get("success"):
                logger.info(
                    "Scheduled storage backup completed",
                    backup_path=result.get("backup_path"),
                    size_mb=round(result.get("metadata", {}).get("file_size", 0) / (1024 * 1024), 2),
                    file_count=result.get("metadata", {}).get("file_count", 0)
                )
            else:
                logger.error("Scheduled storage backup failed", error=result.get("error"))
        
        except Exception as e:
            logger.error("Exception during scheduled storage backup", error=str(e), exc_info=e)
    
    def _run_full_backup(self):
        """Run full backup job."""
        try:
            logger.info("Starting scheduled full backup")
            result = self.backup_manager.create_full_backup()
            
            if result.get("success"):
                db_meta = result.get("database", {})
                st_meta = result.get("storage", {})
                total_size = db_meta.get("file_size", 0) + st_meta.get("file_size", 0)
                
                logger.info(
                    "Scheduled full backup completed",
                    timestamp=result.get("timestamp"),
                    size_mb=round(total_size / (1024 * 1024), 2)
                )
            else:
                logger.error("Scheduled full backup failed")
        
        except Exception as e:
            logger.error("Exception during scheduled full backup", error=str(e), exc_info=e)
    
    def _run_rotation(self):
        """Run backup rotation job."""
        try:
            logger.info("Starting scheduled backup rotation")
            removed = self.backup_manager.rotate_backups()
            
            total_removed = sum(removed.values())
            if total_removed > 0:
                logger.info("Scheduled backup rotation completed", removed=removed, total=total_removed)
            else:
                logger.info("Scheduled backup rotation: no old backups to remove")
        
        except Exception as e:
            logger.error("Exception during scheduled backup rotation", error=str(e), exc_info=e)
    
    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Backup scheduler started")
            self.print_schedule()
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Backup scheduler stopped")
    
    def print_schedule(self):
        """Print current schedule."""
        jobs = self.scheduler.get_jobs()
        if jobs:
            logger.info(f"Active backup jobs: {len(jobs)}")
            for job in jobs:
                next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "N/A"
                logger.info(f"  - {job.name} (ID: {job.id}): next run at {next_run}")
        else:
            logger.info("No active backup jobs scheduled")
    
    def get_next_run_times(self):
        """Get next run times for all jobs."""
        jobs = self.scheduler.get_jobs()
        return {
            job.id: {
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            }
            for job in jobs
        }
    
    def trigger_backup(self, backup_type: str):
        """
        Manually trigger a backup job.
        
        Args:
            backup_type: Type of backup (database, storage, full, rotation)
        """
        try:
            if backup_type == "database":
                self._run_database_backup()
            elif backup_type == "storage":
                self._run_storage_backup()
            elif backup_type == "full":
                self._run_full_backup()
            elif backup_type == "rotation":
                self._run_rotation()
            else:
                logger.error("Invalid backup type", backup_type=backup_type)
                return False
            
            return True
        
        except Exception as e:
            logger.error("Failed to trigger backup", backup_type=backup_type, error=str(e), exc_info=e)
            return False


# Global scheduler instance
_scheduler_instance: Optional[BackupScheduler] = None


def get_backup_scheduler() -> BackupScheduler:
    """Get or create the global backup scheduler instance."""
    global _scheduler_instance
    
    if _scheduler_instance is None:
        _scheduler_instance = BackupScheduler()
    
    return _scheduler_instance


def start_backup_scheduler():
    """Start the global backup scheduler."""
    scheduler = get_backup_scheduler()
    scheduler.start()
    return scheduler


def stop_backup_scheduler():
    """Stop the global backup scheduler."""
    global _scheduler_instance
    
    if _scheduler_instance is not None:
        _scheduler_instance.stop()
        _scheduler_instance = None


if __name__ == "__main__":
    # Run as standalone service
    import signal
    import sys
    
    def signal_handler(sig, frame):
        """Handle shutdown signals."""
        logger.info("Received shutdown signal, stopping scheduler...")
        stop_backup_scheduler()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting backup scheduler service...")
    scheduler = start_backup_scheduler()
    
    # Keep the process running
    try:
        while True:
            import time
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        stop_backup_scheduler()
