"""
Notification synchronization and cleanup module for Vertex AR.
Handles automated cleanup, synchronization tasks, and maintenance.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from app.config import settings
from logging_setup import get_logger
from notifications import (
    get_db,
    cleanup_expired_notifications,
    get_notifications,
    NotificationFilter,
    NotificationPriority,
    NotificationStatus,
    bulk_update_notifications_status
)

logger = get_logger(__name__)


class NotificationSyncManager:
    """Manages notification synchronization and cleanup tasks."""
    
    def __init__(self):
        self.running = False
        self.sync_interval = getattr(settings, 'NOTIFICATION_SYNC_INTERVAL', 300)  # 5 minutes default
        self.cleanup_interval = getattr(settings, 'NOTIFICATION_CLEANUP_INTERVAL', 3600)  # 1 hour default
        self.retention_days = getattr(settings, 'NOTIFICATION_RETENTION_DAYS', 30)
        self.auto_archive_hours = getattr(settings, 'NOTIFICATION_AUTO_ARCHIVE_HOURS', 24)
        
        # Statistics
        self.last_sync = None
        self.last_cleanup = None
        self.sync_stats = {}
        self.cleanup_stats = {}
    
    async def start(self):
        """Start the sync manager."""
        self.running = True
        logger.info("Notification sync manager started")
        
        while self.running:
            try:
                await self._perform_sync_cycle()
                await asyncio.sleep(self.sync_interval)
                
            except Exception as e:
                logger.error(f"Sync manager error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def stop(self):
        """Stop the sync manager."""
        self.running = False
        logger.info("Notification sync manager stopped")
    
    async def _perform_sync_cycle(self):
        """Perform a complete sync cycle."""
        now = datetime.utcnow()
        
        # Perform cleanup if needed
        if not self.last_cleanup or (now - self.last_cleanup).seconds >= self.cleanup_interval:
            await self._perform_cleanup()
            self.last_cleanup = now
        
        # Perform regular sync
        await self._perform_regular_sync()
        self.last_sync = now
        
        # Log statistics
        if self.sync_stats or self.cleanup_stats:
            logger.info(f"Sync cycle completed. Sync: {self.sync_stats}, Cleanup: {self.cleanup_stats}")
    
    async def _perform_regular_sync(self):
        """Perform regular synchronization tasks."""
        try:
            db = next(get_db())
            
            # Auto-archive old notifications
            await self._auto_archive_notifications(db)
            
            # Update statistics
            self.sync_stats = await self._get_sync_statistics(db)
            
            db.close()
            
        except Exception as e:
            logger.error(f"Regular sync error: {e}")
            self.sync_stats = {"error": str(e)}
    
    async def _perform_cleanup(self):
        """Perform cleanup tasks."""
        try:
            db = next(get_db())
            
            # Cleanup expired notifications
            cleanup_expired_notifications(db)
            
            # Cleanup old notifications based on retention policy
            await self._cleanup_old_notifications(db)
            
            # Update statistics
            self.cleanup_stats = await self._get_cleanup_statistics(db)
            
            db.close()
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            self.cleanup_stats = {"error": str(e)}
    
    async def _auto_archive_notifications(self, db: Session):
        """Automatically archive old notifications."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=self.auto_archive_hours)
            
            # Find notifications that should be archived
            filters = NotificationFilter(
                status=NotificationStatus.READ,
                date_to=cutoff_time
            )
            
            notifications_to_archive = get_notifications(db, filters, limit=10000)
            
            if notifications_to_archive:
                notification_ids = [n.id for n in notifications_to_archive]
                archived_count = bulk_update_notifications_status(
                    db, notification_ids, NotificationStatus.ARCHIVED
                )
                
                logger.info(f"Auto-archived {archived_count} old notifications")
                
        except Exception as e:
            logger.error(f"Auto-archive error: {e}")
    
    async def _cleanup_old_notifications(self, db: Session):
        """Clean up very old notifications based on retention policy."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
            
            # Find very old notifications to delete
            filters = NotificationFilter(date_to=cutoff_date)
            
            old_notifications = get_notifications(db, filters, limit=5000)
            
            if old_notifications:
                # Delete old notifications (excluding critical ones)
                critical_count = 0
                deleted_count = 0
                
                for notification in old_notifications:
                    if notification.priority == NotificationPriority.CRITICAL:
                        critical_count += 1
                        continue
                    
                    db.delete(notification)
                    deleted_count += 1
                
                if deleted_count > 0:
                    db.commit()
                    logger.info(f"Cleaned up {deleted_count} old notifications (kept {critical_count} critical)")
                
        except Exception as e:
            logger.error(f"Old notifications cleanup error: {e}")
            db.rollback()
    
    async def _get_sync_statistics(self, db: Session) -> Dict[str, Any]:
        """Get synchronization statistics."""
        try:
            from notifications import get_notification_statistics
            
            stats = get_notification_statistics(db)
            
            # Add additional sync-specific stats
            now = datetime.utcnow()
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(days=1)
            
            # Recent notifications
            recent_filters = NotificationFilter(date_from=hour_ago)
            recent_notifications = get_notifications(db, recent_filters, limit=1000)
            
            # Unprocessed notifications
            unprocessed_filters = NotificationFilter(status=NotificationStatus.NEW)
            unprocessed_notifications = get_notifications(db, unprocessed_filters, limit=1000)
            
            return {
                "total_notifications": stats.get('total_count', 0),
                "recent_hour": len(recent_notifications),
                "unprocessed": len(unprocessed_notifications),
                "by_priority": stats.get('by_priority', {}),
                "by_status": stats.get('by_status', {}),
                "last_sync": now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting sync statistics: {e}")
            return {"error": str(e)}
    
    async def _get_cleanup_statistics(self) -> Dict[str, Any]:
        """Get cleanup statistics."""
        try:
            return {
                "last_cleanup": datetime.utcnow().isoformat(),
                "retention_days": self.retention_days,
                "auto_archive_hours": self.auto_archive_hours
            }
        except Exception as e:
            logger.error(f"Error getting cleanup statistics: {e}")
            return {"error": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """Get current sync manager status."""
        return {
            "running": self.running,
            "sync_interval": self.sync_interval,
            "cleanup_interval": self.cleanup_interval,
            "retention_days": self.retention_days,
            "auto_archive_hours": self.auto_archive_hours,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "last_cleanup": self.last_cleanup.isoformat() if self.last_cleanup else None,
            "sync_stats": self.sync_stats,
            "cleanup_stats": self.cleanup_stats
        }


class NotificationAggregator:
    """Aggregates and deduplicates notifications."""
    
    def __init__(self):
        self.aggregation_rules = {}
        self.deduplication_window = getattr(settings, 'NOTIFICATION_DEDUP_WINDOW', 300)  # 5 minutes
    
    def add_aggregation_rule(
        self,
        name: str,
        pattern: str,
        max_count: int = 10,
        time_window: int = 3600
    ):
        """Add an aggregation rule."""
        rule = {
            'name': name,
            'pattern': pattern,
            'max_count': max_count,
            'time_window': time_window,
            'created_at': datetime.utcnow()
        }
        self.aggregation_rules[name] = rule
        logger.info(f"Added aggregation rule: {name}")
    
    def should_aggregate(
        self,
        notification_data: Dict[str, Any],
        existing_notifications: List[Any]
    ) -> Optional[str]:
        """Check if notification should be aggregated."""
        title = notification_data.get('title', '')
        message = notification_data.get('message', '')
        
        for rule_name, rule in self.aggregation_rules.items():
            pattern = rule['pattern']
            
            # Simple pattern matching (can be enhanced with regex)
            if pattern.lower() in title.lower() or pattern.lower() in message.lower():
                # Check time window
                now = datetime.utcnow()
                cutoff = now - timedelta(seconds=rule['time_window'])
                
                # Count recent similar notifications
                recent_similar = [
                    n for n in existing_notifications
                    if (n.created_at and n.created_at > cutoff and
                        pattern.lower() in n.title.lower() or 
                        pattern.lower() in n.message.lower())
                ]
                
                if len(recent_similar) < rule['max_count']:
                    return rule_name
        
        return None
    
    def generate_aggregated_notification(
        self,
        base_notification: Dict[str, Any],
        similar_notifications: List[Any],
        rule_name: str
    ) -> Dict[str, Any]:
        """Generate an aggregated notification."""
        rule = self.aggregation_rules[rule_name]
        
        aggregated = base_notification.copy()
        aggregated['title'] = f"[{rule['name'].upper()}] {base_notification['title']}"
        aggregated['message'] = f"{base_notification['message']}\n\n*Aggregated {len(similar_notifications) + 1} similar events*"
        
        # Add event data about aggregation
        event_data = base_notification.get('event_data', {})
        event_data.update({
            'aggregated': True,
            'aggregation_rule': rule_name,
            'aggregated_count': len(similar_notifications) + 1,
            'aggregated_at': datetime.utcnow().isoformat()
        })
        aggregated['event_data'] = event_data
        
        return aggregated
    
    def get_aggregation_stats(self) -> Dict[str, Any]:
        """Get aggregation statistics."""
        return {
            "rules_count": len(self.aggregation_rules),
            "deduplication_window": self.deduplication_window,
            "rules": {name: {
                'pattern': rule['pattern'],
                'max_count': rule['max_count'],
                'time_window': rule['time_window']
            } for name, rule in self.aggregation_rules.items()}
        }


# Global instances
notification_sync_manager = NotificationSyncManager()
notification_aggregator = NotificationAggregator()

# Add default aggregation rules
notification_aggregator.add_aggregation_rule(
    "high_cpu", "high cpu usage", max_count=5, time_window=1800
)
notification_aggregator.add_aggregation_rule(
    "disk_space", "disk space", max_count=3, time_window=3600
)
notification_aggregator.add_aggregation_rule(
    "database_error", "database error", max_count=10, time_window=600
)