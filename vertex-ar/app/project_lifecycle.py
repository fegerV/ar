"""
Project Lifecycle Scheduler for Vertex AR.
Manages automatic status transitions and notifications based on subscription deadlines.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from app.config import settings
from app.alerting import alert_manager
from app.database import Database
from logging_setup import get_logger

logger = get_logger(__name__)


class ProjectLifecycleScheduler:
    """Manages project and portrait lifecycle scheduling and notifications."""
    
    def __init__(self):
        self.enabled = settings.LIFECYCLE_SCHEDULER_ENABLED
        self.check_interval = settings.LIFECYCLE_CHECK_INTERVAL_SECONDS
        self.notifications_enabled = settings.LIFECYCLE_NOTIFICATIONS_ENABLED
        
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
    
    def calculate_lifecycle_status(self, subscription_end: datetime) -> str:
        """
        Calculate lifecycle status based on subscription end date.
        
        Returns:
            - 'active': > 7 days remaining
            - 'expiring': <= 7 days remaining
            - 'archived': past expiry date
        """
        now = datetime.utcnow()
        
        if subscription_end < now:
            return 'archived'
        
        days_remaining = (subscription_end - now).total_seconds() / 86400
        
        if days_remaining <= 7:
            return 'expiring'
        
        return 'active'
    
    def should_send_7day_notification(self, portrait: Dict[str, Any], subscription_end: datetime) -> bool:
        """Check if 7-day notification should be sent."""
        if not portrait.get('subscription_end'):
            return False
        
        # Check if already sent
        if portrait.get('notification_7days_sent'):
            return False
        
        now = datetime.utcnow()
        days_remaining = (subscription_end - now).total_seconds() / 86400
        
        # Send when there are 7 days or less remaining (but not expired yet)
        return 0 < days_remaining <= 7
    
    def should_send_24hour_notification(self, portrait: Dict[str, Any], subscription_end: datetime) -> bool:
        """Check if 24-hour notification should be sent."""
        if not portrait.get('subscription_end'):
            return False
        
        # Check if already sent
        if portrait.get('notification_24hours_sent'):
            return False
        
        now = datetime.utcnow()
        hours_remaining = (subscription_end - now).total_seconds() / 3600
        
        # Send when there are 24 hours or less remaining (but not expired yet)
        return 0 < hours_remaining <= 24
    
    def should_send_expired_notification(self, portrait: Dict[str, Any], subscription_end: datetime) -> bool:
        """Check if post-expiry notification should be sent."""
        if not portrait.get('subscription_end'):
            return False
        
        # Check if already sent
        if portrait.get('notification_expired_sent'):
            return False
        
        now = datetime.utcnow()
        
        # Send when expired
        return subscription_end < now
    
    async def check_and_update_lifecycle_statuses(self) -> int:
        """Check and update lifecycle statuses for all portraits with subscription_end."""
        try:
            database = self.get_database()
            portraits = database.get_portraits_for_lifecycle_check()
            
            updated_count = 0
            for portrait in portraits:
                try:
                    subscription_end_str = portrait.get('subscription_end')
                    if not subscription_end_str:
                        continue
                    
                    # Parse subscription_end datetime
                    subscription_end = datetime.fromisoformat(subscription_end_str.replace('Z', '+00:00'))
                    if subscription_end.tzinfo:
                        subscription_end = subscription_end.replace(tzinfo=None)
                    
                    # Calculate new status
                    new_status = self.calculate_lifecycle_status(subscription_end)
                    current_status = portrait.get('lifecycle_status', 'active')
                    
                    # Update status if changed
                    if new_status != current_status:
                        success = database.update_portrait_lifecycle_status(portrait['id'], new_status)
                        if success:
                            updated_count += 1
                            logger.info(
                                f"Updated lifecycle status for portrait {portrait['id']}: "
                                f"{current_status} -> {new_status}"
                            )
                            
                            # Send notifications based on status change
                            await self.handle_status_change_notifications(portrait, new_status)
                    
                    # Check for time-based notifications (even if status hasn't changed)
                    await self.check_time_based_notifications(portrait, subscription_end)
                    
                except Exception as e:
                    logger.error(f"Error processing portrait {portrait.get('id')}: {e}")
                    continue
            
            if updated_count > 0:
                logger.info(f"Updated {updated_count} portrait lifecycle statuses")
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Error checking lifecycle statuses: {e}")
            return 0
    
    async def handle_status_change_notifications(self, portrait: Dict[str, Any], new_status: str) -> None:
        """Handle notifications when status changes."""
        try:
            # Send notification when transitioning to archived
            if new_status == 'archived':
                await self.send_expired_notification(portrait)
        except Exception as e:
            logger.error(f"Error handling status change notifications for portrait {portrait.get('id')}: {e}")
    
    async def check_time_based_notifications(self, portrait: Dict[str, Any], subscription_end: datetime) -> None:
        """Check and send time-based notifications (7 days, 24 hours)."""
        try:
            # Check 7-day notification
            if self.should_send_7day_notification(portrait, subscription_end):
                await self.send_7day_notification(portrait, subscription_end)
            
            # Check 24-hour notification
            if self.should_send_24hour_notification(portrait, subscription_end):
                await self.send_24hour_notification(portrait, subscription_end)
        except Exception as e:
            logger.error(f"Error checking time-based notifications for portrait {portrait.get('id')}: {e}")
    
    async def send_7day_notification(self, portrait: Dict[str, Any], subscription_end: datetime) -> None:
        """Send 7-day warning notification."""
        if not self.notifications_enabled:
            return
        
        try:
            database = self.get_database()
            
            # Get client info
            client = database.get_client(portrait['client_id'])
            if not client:
                logger.warning(f"Client not found for portrait {portrait['id']}")
                return
            
            # Calculate days remaining
            days_remaining = (subscription_end - datetime.utcnow()).total_seconds() / 86400
            
            # Prepare messages
            subject_ru = "Подписка истекает через 7 дней"
            subject_en = "Subscription expires in 7 days"
            
            message_ru = f"""
Уважаемый(ая) {client['name']},

Ваша подписка на портрет истекает через {int(days_remaining)} дней.

Портрет ID: {portrait['id']}
Дата окончания: {subscription_end.strftime('%d.%m.%Y %H:%M')}

Пожалуйста, свяжитесь с нами для продления подписки.

С уважением,
Команда Vertex AR
"""
            
            message_en = f"""
Dear {client['name']},

Your portrait subscription expires in {int(days_remaining)} days.

Portrait ID: {portrait['id']}
Expiration date: {subscription_end.strftime('%Y-%m-%d %H:%M')}

Please contact us to renew your subscription.

Best regards,
Vertex AR Team
"""
            
            # Send via Telegram (admin notification)
            telegram_message = f"""
⚠️ **Подписка истекает через 7 дней / Subscription expires in 7 days**

Клиент / Client: {client['name']}
Телефон / Phone: {client['phone']}
Портрет ID / Portrait ID: {portrait['id']}
Дата окончания / Expiration: {subscription_end.strftime('%d.%m.%Y %H:%M')}
Осталось дней / Days remaining: {int(days_remaining)}
"""
            
            await alert_manager.send_telegram_alert(telegram_message)
            
            # Send email to client if email exists
            client_email = client.get('email')
            if client_email:
                await self.send_client_email(client_email, subject_ru, message_ru)
            
            # Record notification sent
            database.record_lifecycle_notification(portrait['id'], '7days')
            logger.info(f"Sent 7-day notification for portrait {portrait['id']}")
            
        except Exception as e:
            logger.error(f"Error sending 7-day notification for portrait {portrait.get('id')}: {e}")
    
    async def send_24hour_notification(self, portrait: Dict[str, Any], subscription_end: datetime) -> None:
        """Send 24-hour warning notification."""
        if not self.notifications_enabled:
            return
        
        try:
            database = self.get_database()
            
            # Get client info
            client = database.get_client(portrait['client_id'])
            if not client:
                logger.warning(f"Client not found for portrait {portrait['id']}")
                return
            
            # Calculate hours remaining
            hours_remaining = (subscription_end - datetime.utcnow()).total_seconds() / 3600
            
            # Prepare messages
            subject_ru = "Подписка истекает через 24 часа"
            subject_en = "Subscription expires in 24 hours"
            
            message_ru = f"""
Уважаемый(ая) {client['name']},

Ваша подписка на портрет истекает через {int(hours_remaining)} часов!

Портрет ID: {portrait['id']}
Дата окончания: {subscription_end.strftime('%d.%m.%Y %H:%M')}

Это последнее напоминание. Пожалуйста, срочно свяжитесь с нами для продления подписки.

С уважением,
Команда Vertex AR
"""
            
            message_en = f"""
Dear {client['name']},

Your portrait subscription expires in {int(hours_remaining)} hours!

Portrait ID: {portrait['id']}
Expiration date: {subscription_end.strftime('%Y-%m-%d %H:%M')}

This is your final reminder. Please contact us urgently to renew your subscription.

Best regards,
Vertex AR Team
"""
            
            # Send via Telegram (admin notification)
            telegram_message = f"""
🚨 **Подписка истекает через 24 часа / Subscription expires in 24 hours**

Клиент / Client: {client['name']}
Телефон / Phone: {client['phone']}
Портрет ID / Portrait ID: {portrait['id']}
Дата окончания / Expiration: {subscription_end.strftime('%d.%m.%Y %H:%M')}
Осталось часов / Hours remaining: {int(hours_remaining)}
"""
            
            await alert_manager.send_telegram_alert(telegram_message)
            
            # Send email to client if email exists
            client_email = client.get('email')
            if client_email:
                await self.send_client_email(client_email, subject_ru, message_ru)
            
            # Record notification sent
            database.record_lifecycle_notification(portrait['id'], '24hours')
            logger.info(f"Sent 24-hour notification for portrait {portrait['id']}")
            
        except Exception as e:
            logger.error(f"Error sending 24-hour notification for portrait {portrait.get('id')}: {e}")
    
    async def send_expired_notification(self, portrait: Dict[str, Any]) -> None:
        """Send post-expiry notification."""
        if not self.notifications_enabled:
            return
        
        try:
            database = self.get_database()
            
            # Check if already sent
            if portrait.get('notification_expired_sent'):
                return
            
            # Get client info
            client = database.get_client(portrait['client_id'])
            if not client:
                logger.warning(f"Client not found for portrait {portrait['id']}")
                return
            
            subscription_end_str = portrait.get('subscription_end')
            if subscription_end_str:
                subscription_end = datetime.fromisoformat(subscription_end_str.replace('Z', '+00:00'))
                if subscription_end.tzinfo:
                    subscription_end = subscription_end.replace(tzinfo=None)
            else:
                subscription_end = datetime.utcnow()
            
            # Prepare messages
            subject_ru = "Подписка истекла"
            subject_en = "Subscription expired"
            
            message_ru = f"""
Уважаемый(ая) {client['name']},

Ваша подписка на портрет истекла.

Портрет ID: {portrait['id']}
Дата окончания: {subscription_end.strftime('%d.%m.%Y %H:%M')}

Портрет был переведен в архив. Для восстановления доступа, пожалуйста, свяжитесь с нами для продления подписки.

С уважением,
Команда Vertex AR
"""
            
            message_en = f"""
Dear {client['name']},

Your portrait subscription has expired.

Portrait ID: {portrait['id']}
Expiration date: {subscription_end.strftime('%Y-%m-%d %H:%M')}

The portrait has been archived. To restore access, please contact us to renew your subscription.

Best regards,
Vertex AR Team
"""
            
            # Send via Telegram (admin notification)
            telegram_message = f"""
⚫️ **Подписка истекла / Subscription expired**

Клиент / Client: {client['name']}
Телефон / Phone: {client['phone']}
Портрет ID / Portrait ID: {portrait['id']}
Дата окончания / Expiration: {subscription_end.strftime('%d.%m.%Y %H:%M')}
Статус / Status: Archived
"""
            
            await alert_manager.send_telegram_alert(telegram_message)
            
            # Send email to client if email exists
            client_email = client.get('email')
            if client_email:
                await self.send_client_email(client_email, subject_ru, message_ru)
            
            # Record notification sent
            database.record_lifecycle_notification(portrait['id'], 'expired')
            logger.info(f"Sent expiry notification for portrait {portrait['id']}")
            
        except Exception as e:
            logger.error(f"Error sending expiry notification for portrait {portrait.get('id')}: {e}")
    
    async def send_client_email(self, recipient: str, subject: str, message: str) -> bool:
        """Send transactional email to client."""
        try:
            # Use the existing email alert system with custom recipient
            from app.notification_config import get_notification_config
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            notification_config = get_notification_config()
            smtp_config = notification_config.get_smtp_config(actor="lifecycle_scheduler")
            
            if not smtp_config:
                logger.warning("SMTP configuration not available in database")
                return False
            
            smtp_host = smtp_config['host']
            smtp_port = smtp_config['port']
            smtp_username = smtp_config['username']
            smtp_password = smtp_config['password']
            from_email = smtp_config['from_email']
            use_tls = smtp_config['use_tls']
            use_ssl = smtp_config['use_ssl']
            
            if not smtp_username or not smtp_password:
                logger.warning("Email credentials incomplete")
                return False
            
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = recipient
            msg['Subject'] = subject
            
            body = MIMEText(message, 'plain', 'utf-8')
            msg.attach(body)
            
            # Send email in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._send_email_sync,
                smtp_host,
                smtp_port,
                smtp_username,
                smtp_password,
                use_tls,
                use_ssl,
                msg
            )
            
            logger.info(f"Client email sent to {recipient}")
            
            # Log to notification history
            try:
                import uuid
                db = self.get_database()
                db.add_notification_history(
                    history_id=str(uuid.uuid4()),
                    notification_type='email',
                    recipient=recipient,
                    subject=subject,
                    message=message,
                    status='sent'
                )
            except Exception as log_error:
                logger.error(f"Failed to log notification history: {log_error}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending client email to {recipient}: {e}")
            
            # Log failure to notification history
            try:
                import uuid
                db = self.get_database()
                db.add_notification_history(
                    history_id=str(uuid.uuid4()),
                    notification_type='email',
                    recipient=recipient,
                    subject=subject,
                    message=message,
                    status='failed',
                    error_message=str(e)
                )
            except Exception as log_error:
                logger.error(f"Failed to log notification history: {log_error}")
            
            return False
    
    def _send_email_sync(self, host: str, port: int, username: str, password: str,
                         use_tls: bool, use_ssl: bool, msg: Any) -> None:
        """Synchronous email sending for thread pool execution."""
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port)
        else:
            server = smtplib.SMTP(host, port)
            if use_tls:
                server.starttls()
        
        server.login(username, password)
        server.send_message(msg)
        server.quit()
    
    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status and statistics."""
        try:
            database = self.get_database()
            
            # Get status counts
            status_counts = database.count_portraits_by_status()
            
            # Get portraits needing attention
            portraits = database.get_portraits_for_lifecycle_check()
            
            now = datetime.utcnow()
            expiring_soon = []
            expired = []
            
            for portrait in portraits:
                subscription_end_str = portrait.get('subscription_end')
                if subscription_end_str:
                    subscription_end = datetime.fromisoformat(subscription_end_str.replace('Z', '+00:00'))
                    if subscription_end.tzinfo:
                        subscription_end = subscription_end.replace(tzinfo=None)
                    
                    if subscription_end < now:
                        expired.append(portrait['id'])
                    elif (subscription_end - now).total_seconds() / 86400 <= 7:
                        expiring_soon.append(portrait['id'])
            
            return {
                "scheduler_enabled": self.enabled,
                "notifications_enabled": self.notifications_enabled,
                "check_interval_seconds": self.check_interval,
                "last_check": datetime.utcnow().isoformat(),
                "status_counts": status_counts,
                "expiring_soon_count": len(expiring_soon),
                "expired_count": len(expired)
            }
            
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            return {
                "scheduler_enabled": self.enabled,
                "notifications_enabled": self.notifications_enabled,
                "error": str(e)
            }
    
    async def start_lifecycle_scheduler(self):
        """Start the background task for lifecycle scheduling."""
        if not self.enabled:
            logger.info("Lifecycle scheduler disabled")
            return
        
        logger.info(f"Starting lifecycle scheduler - checking every {self.check_interval} seconds")
        
        while True:
            try:
                # Check and update lifecycle statuses
                await self.check_and_update_lifecycle_statuses()
                
                # Sleep until next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in lifecycle scheduler: {e}")
                await asyncio.sleep(self.check_interval)


# Global scheduler instance
project_lifecycle_scheduler = ProjectLifecycleScheduler()
