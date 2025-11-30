"""
Video Animation Scheduler for Vertex AR.
Manages automatic activation and deactivation of video animations based on schedule.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from app.config import settings
from app.alerting import alert_manager
from app.database import Database
from logging_setup import get_logger

logger = get_logger(__name__)


class VideoAnimationScheduler:
    """Manages video animation scheduling and rotation."""
    
    def __init__(self):
        self.enabled = settings.VIDEO_SCHEDULER_ENABLED
        self.check_interval = settings.VIDEO_SCHEDULER_CHECK_INTERVAL
        self.rotation_interval = settings.VIDEO_SCHEDULER_ROTATION_INTERVAL
        self.notifications_enabled = settings.VIDEO_SCHEDULER_NOTIFICATIONS_ENABLED
        
    def get_database(self) -> Database:
        """Get database instance."""
        from app.main import get_current_app
        app = get_current_app()
        if not hasattr(app.state, 'database'):
            from pathlib import Path
            BASE_DIR = app.state.config["BASE_DIR"]
            DB_PATH = BASE_DIR / "app_data.db"
            from app.database import Database, ensure_default_admin_user
            app.state.database = Database(DB_PATH)
            ensure_default_admin_user(app.state.database)
        return app.state.database
    
    async def check_due_activations(self) -> int:
        """Check and activate videos that are due for activation."""
        try:
            database = self.get_database()
            due_videos = database.get_videos_due_for_activation()
            
            activated_count = 0
            for video in due_videos:
                success = database.activate_video_with_history(
                    video["id"],
                    reason="schedule_activation",
                    changed_by="system"
                )
                if success:
                    activated_count += 1
                    logger.info(f"Activated video {video['id']} for portrait {video['portrait_id']}")
                    
                    # Send notification
                    await self.send_activation_notification(video)
                else:
                    logger.error(f"Failed to activate video {video['id']}")
            
            if activated_count > 0:
                logger.info(f"Activated {activated_count} videos due for activation")
            
            return activated_count
            
        except Exception as e:
            logger.error(f"Error checking due activations: {e}")
            return 0
    
    async def check_due_deactivations(self) -> int:
        """Check and deactivate videos that are due for deactivation."""
        try:
            database = self.get_database()
            due_videos = database.get_videos_due_for_deactivation()
            
            deactivated_count = 0
            for video in due_videos:
                success = database.deactivate_video_with_history(
                    video["id"],
                    reason="schedule_deactivation",
                    changed_by="system"
                )
                if success:
                    deactivated_count += 1
                    logger.info(f"Deactivated video {video['id']} for portrait {video['portrait_id']}")
                    
                    # Send notification
                    await self.send_deactivation_notification(video)
                    
                    # Check if this portrait needs rotation
                    await self.handle_video_rotation(video["portrait_id"])
                else:
                    logger.error(f"Failed to deactivate video {video['id']}")
            
            if deactivated_count > 0:
                logger.info(f"Deactivated {deactivated_count} videos due for deactivation")
            
            return deactivated_count
            
        except Exception as e:
            logger.error(f"Error checking due deactivations: {e}")
            return 0
    
    async def handle_video_rotation(self, portrait_id: str) -> bool:
        """Handle video rotation for a portrait after deactivation."""
        try:
            database = self.get_database()
            
            # Get portrait to check if it has rotation settings
            # For now, we'll check if there are any videos with rotation_type set
            cursor = database._execute(
                "SELECT DISTINCT rotation_type FROM videos WHERE portrait_id = ? AND rotation_type != 'none'",
                (portrait_id,)
            )
            rotation_types = [row["rotation_type"] for row in cursor.fetchall()]
            
            if not rotation_types:
                return False
            
            # Try each rotation type
            for rotation_type in rotation_types:
                videos = database.get_videos_for_rotation(portrait_id, rotation_type)
                
                if videos and len(videos) > 1:
                    # Activate the next video in rotation
                    if rotation_type == "sequential":
                        # Find the next video that should be activated
                        current_time = datetime.utcnow()
                        for video in videos:
                            if video.get("start_datetime"):
                                start_time = datetime.fromisoformat(video["start_datetime"].replace('Z', '+00:00'))
                                if start_time <= current_time:
                                    # This video should be active now
                                    success = database.activate_video_with_history(
                                        video["id"],
                                        reason=f"sequential_rotation",
                                        changed_by="system"
                                    )
                                    if success:
                                        logger.info(f"Rotated to next video {video['id']} for portrait {portrait_id}")
                                        await self.send_rotation_notification(video, "sequential")
                                        return True
                    
                    elif rotation_type == "cyclic":
                        # For cyclic rotation, activate the first inactive video
                        for video in videos:
                            if not video.get("is_active", False):
                                success = database.activate_video_with_history(
                                    video["id"],
                                    reason="cyclic_rotation",
                                    changed_by="system"
                                )
                                if success:
                                    logger.info(f"Cyclic rotation activated video {video['id']} for portrait {portrait_id}")
                                    await self.send_rotation_notification(video, "cyclic")
                                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling video rotation for portrait {portrait_id}: {e}")
            return False
    
    async def archive_expired_videos(self) -> int:
        """Archive videos whose end time has passed."""
        try:
            database = self.get_database()
            archived_count = database.archive_expired_videos()
            
            if archived_count > 0:
                logger.info(f"Archived {archived_count} expired videos")
                
                # Send notification about archiving
                await self.send_archive_notification(archived_count)
            
            return archived_count
            
        except Exception as e:
            logger.error(f"Error archiving expired videos: {e}")
            return 0
    
    async def send_activation_notification(self, video: Dict[str, Any]) -> None:
        """Send notification about video activation."""
        if not self.notifications_enabled:
            return
            
        try:
            message = (
                f"🎬 **Video Activated**\n\n"
                f"Video ID: {video['id']}\n"
                f"Portrait ID: {video['portrait_id']}\n"
                f"Start Time: {video.get('start_datetime', 'N/A')}\n"
                f"End Time: {video.get('end_datetime', 'No end time')}\n"
                f"Rotation Type: {video.get('rotation_type', 'none')}"
            )
            
            # Send via Telegram
            if settings.TELEGRAM_BOT_TOKEN:
                await alert_manager.send_telegram_alert(message)
            
            # Send via Email (checks DB config internally)
            try:
                subject = f"Vertex AR Video Activated - {video['id']}"
                await alert_manager.send_email_alert(subject, message)
            except Exception as email_error:
                logger.debug(f"Email notification not sent: {email_error}")
                
        except Exception as e:
            logger.error(f"Error sending activation notification: {e}")
    
    async def send_deactivation_notification(self, video: Dict[str, Any]) -> None:
        """Send notification about video deactivation."""
        if not self.notifications_enabled:
            return
            
        try:
            message = (
                f"⏹️ **Video Deactivated**\n\n"
                f"Video ID: {video['id']}\n"
                f"Portrait ID: {video['portrait_id']}\n"
                f"End Time: {video.get('end_datetime', 'N/A')}\n"
                f"Reason: Schedule deactivation"
            )
            
            # Send via Telegram
            if settings.TELEGRAM_BOT_TOKEN:
                await alert_manager.send_telegram_alert(message)
            
            # Send via Email (checks DB config internally)
            try:
                subject = f"Vertex AR Video Deactivated - {video['id']}"
                await alert_manager.send_email_alert(subject, message)
            except Exception as email_error:
                logger.debug(f"Email notification not sent: {email_error}")
                
        except Exception as e:
            logger.error(f"Error sending deactivation notification: {e}")
    
    async def send_rotation_notification(self, video: Dict[str, Any], rotation_type: str) -> None:
        """Send notification about video rotation."""
        if not self.notifications_enabled:
            return
            
        try:
            message = (
                f"🔄 **Video Rotated**\n\n"
                f"Video ID: {video['id']}\n"
                f"Portrait ID: {video['portrait_id']}\n"
                f"Rotation Type: {rotation_type}\n"
                f"Activated at: {datetime.utcnow().isoformat()}"
            )
            
            # Send via Telegram
            if settings.TELEGRAM_BOT_TOKEN:
                await alert_manager.send_telegram_alert(message)
            
            # Send via Email (checks DB config internally)
            try:
                subject = f"Vertex AR Video Rotated - {video['id']}"
                await alert_manager.send_email_alert(subject, message)
            except Exception as email_error:
                logger.debug(f"Email notification not sent: {email_error}")
                
        except Exception as e:
            logger.error(f"Error sending rotation notification: {e}")
    
    async def send_archive_notification(self, archived_count: int) -> None:
        """Send notification about video archiving."""
        if not self.notifications_enabled:
            return
            
        try:
            message = (
                f"📦 **Videos Archived**\n\n"
                f"Number of videos archived: {archived_count}\n"
                f"Time: {datetime.utcnow().isoformat()}\n\n"
                f"Videos were automatically archived due to expired schedule."
            )
            
            # Send via Telegram
            if settings.TELEGRAM_BOT_TOKEN:
                await alert_manager.send_telegram_alert(message)
            
            # Send via Email (checks DB config internally)
            try:
                subject = f"Vertex AR Videos Archived - {archived_count} videos"
                await alert_manager.send_email_alert(subject, message)
            except Exception as email_error:
                logger.debug(f"Email notification not sent: {email_error}")
                
        except Exception as e:
            logger.error(f"Error sending archive notification: {e}")
    
    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status and statistics."""
        try:
            database = self.get_database()
            summary = database.get_scheduled_videos_summary()
            
            return {
                "scheduler_enabled": self.enabled,
                "check_interval_seconds": self.check_interval,
                "rotation_interval_seconds": self.rotation_interval,
                "last_check": datetime.utcnow().isoformat(),
                "video_summary": summary
            }
            
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            return {
                "scheduler_enabled": self.enabled,
                "error": str(e)
            }
    
    async def start_video_animation_scheduler(self):
        """Start the background task for video animation scheduling."""
        if not self.enabled:
            logger.info("Video animation scheduler disabled")
            return
        
        logger.info(f"Starting video animation scheduler - checking every {self.check_interval} seconds")
        
        while True:
            try:
                # Check for due activations
                await self.check_due_activations()
                
                # Check for due deactivations
                await self.check_due_deactivations()
                
                # Archive expired videos (run less frequently)
                if datetime.utcnow().minute % 10 == 0:  # Every 10 minutes
                    await self.archive_expired_videos()
                
                # Sleep until next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in video animation scheduler: {e}")
                await asyncio.sleep(self.check_interval)


# Global scheduler instance
video_animation_scheduler = VideoAnimationScheduler()