"""
Alerting system for Vertex AR - handles emergency notifications via email and Telegram.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import aiohttp

from app.config import settings
from logging_setup import get_logger

logger = get_logger(__name__)


class AlertManager:
    """Manages emergency alerts and notifications."""
    
    def __init__(self):
        self.enabled = settings.ALERTING_ENABLED
        self.last_alerts: Dict[str, datetime] = {}
        self.alert_cooldown = 300  # 5 minutes cooldown between same alert type
        
    async def send_telegram_alert(self, message: str) -> bool:
        """Send alert via Telegram bot."""
        # Try to get settings from database first
        from app.notification_config import get_notification_config
        notification_config = get_notification_config()
        telegram_config = notification_config.get_telegram_config()
        
        if telegram_config:
            bot_token = telegram_config['bot_token']
            chat_ids = telegram_config['chat_ids']
        else:
            # Fallback to environment variables
            bot_token = settings.TELEGRAM_BOT_TOKEN
            chat_ids = [settings.TELEGRAM_CHAT_ID] if settings.TELEGRAM_CHAT_ID else []
        
        if not bot_token or not chat_ids:
            logger.warning("Telegram credentials not configured")
            return False
            
        try:
            success_count = 0
            for chat_id in chat_ids:
                try:
                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    payload = {
                        "chat_id": chat_id,
                        "text": f"🚨 **VERTEX AR ALERT** 🚨\n\n{message}",
                        "parse_mode": "Markdown"
                    }
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, json=payload, timeout=10) as response:
                            if response.status == 200:
                                logger.info(f"Telegram alert sent successfully to {chat_id}")
                                success_count += 1
                                
                                # Log to notification history
                                try:
                                    from app.database import Database
                                    import uuid
                                    db = Database(settings.DB_PATH)
                                    db.add_notification_history(
                                        history_id=str(uuid.uuid4()),
                                        notification_type='telegram',
                                        recipient=str(chat_id),
                                        message=message,
                                        status='sent'
                                    )
                                except Exception as log_error:
                                    logger.error(f"Failed to log notification history: {log_error}")
                            else:
                                error_text = await response.text()
                                logger.error(f"Failed to send Telegram alert to {chat_id}: {response.status} - {error_text}")
                                
                                # Log failure to notification history
                                try:
                                    from app.database import Database
                                    import uuid
                                    db = Database(settings.DB_PATH)
                                    db.add_notification_history(
                                        history_id=str(uuid.uuid4()),
                                        notification_type='telegram',
                                        recipient=str(chat_id),
                                        message=message,
                                        status='failed',
                                        error_message=f"HTTP {response.status}: {error_text}"
                                    )
                                except Exception as log_error:
                                    logger.error(f"Failed to log notification history: {log_error}")
                except Exception as e:
                    logger.error(f"Error sending Telegram alert to {chat_id}: {e}")
                    
                    # Log failure to notification history
                    try:
                        from app.database import Database
                        import uuid
                        db = Database(settings.DB_PATH)
                        db.add_notification_history(
                            history_id=str(uuid.uuid4()),
                            notification_type='telegram',
                            recipient=str(chat_id),
                            message=message,
                            status='failed',
                            error_message=str(e)
                        )
                    except Exception as log_error:
                        logger.error(f"Failed to log notification history: {log_error}")
            
            return success_count > 0
                        
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
            return False
    
    async def send_email_alert(self, subject: str, message: str) -> bool:
        """Send alert via email using EmailService."""
        try:
            # Get email service
            from app.email_service import email_service
            
            # Get SMTP config to determine recipient and check if configured
            from app.notification_config import get_notification_config
            notification_config = get_notification_config()
            smtp_config = notification_config.get_smtp_config(actor="alerting")
            
            if not smtp_config:
                logger.warning("SMTP configuration not available in database")
                return False
            
            from_email = smtp_config['from_email']
            
            # Send to admin emails if configured, otherwise to from_email
            admin_emails = settings.ADMIN_EMAILS if settings.ADMIN_EMAILS else [from_email]
            
            if not admin_emails:
                logger.warning("No admin email addresses configured")
                return False
            
            # Prepare email body
            body = f"""
Vertex AR Emergency Alert

{message}

---
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
Server: {settings.BASE_URL}
            """
            
            # Send email via EmailService (urgent=True for immediate delivery)
            success = await email_service.send_email(
                to_addresses=admin_emails,
                subject=f"[VERTEX AR ALERT] {subject}",
                body=body,
                priority=1,  # High priority for alerts
                urgent=True  # Bypass persistent queue for immediate delivery
            )
            
            if success:
                logger.info(f"Email alert sent to {len(admin_emails)} recipients")
            
            # Log to notification history
            for recipient in admin_emails:
                try:
                    from app.database import Database
                    import uuid
                    db = Database(settings.DB_PATH)
                    db.add_notification_history(
                        history_id=str(uuid.uuid4()),
                        notification_type='email',
                        recipient=recipient,
                        subject=subject,
                        message=message,
                        status='sent' if success else 'failed',
                        error_message=None if success else 'Email service returned failure'
                    )
                except Exception as log_error:
                    logger.error(f"Failed to log notification history: {log_error}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
            
            # Log failure to notification history
            try:
                # Get admin emails for history logging
                from app.notification_config import get_notification_config
                notification_config = get_notification_config()
                smtp_config = notification_config.get_smtp_config(actor="alerting")
                
                from_email = smtp_config.get('from_email') if smtp_config else None
                admin_emails = settings.ADMIN_EMAILS if settings.ADMIN_EMAILS else ([from_email] if from_email else [])
                
                for recipient in admin_emails:
                    try:
                        from app.database import Database
                        import uuid
                        db = Database(settings.DB_PATH)
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
            except Exception:
                pass  # Best effort logging
            
            return False
    
    def should_send_alert(self, alert_type: str) -> bool:
        """Check if alert should be sent (cooldown logic)."""
        now = datetime.utcnow()
        last_time = self.last_alerts.get(alert_type)
        
        if last_time and (now - last_time).seconds < self.alert_cooldown:
            return False
            
        self.last_alerts[alert_type] = now
        return True
    
    async def send_alert(self, alert_type: str, subject: str, message: str, severity: str = "high") -> bool:
        """Send alert via all configured channels."""
        if not self.enabled:
            logger.debug(f"Alerting disabled, skipping {alert_type} alert")
            return False
            
        if not self.should_send_alert(alert_type):
            logger.debug(f"Alert {alert_type} in cooldown period")
            return False
        
        severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(severity, "⚠️")
        formatted_message = f"{severity_emoji} **{severity.upper()}**\n\n{message}"
        
        success = True
        
        # Send Telegram alert
        if settings.TELEGRAM_BOT_TOKEN:
            telegram_success = await self.send_telegram_alert(formatted_message)
            success = success and telegram_success
        
        # Send email alert (checks DB config internally)
        try:
            email_success = await self.send_email_alert(subject, formatted_message)
            success = success and email_success
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            success = False
        
        # Store in database notifications with enhanced features
        try:
            from notifications import send_notification, NotificationPriority
            from notification_integrations import notification_integrator
            from notification_sync import notification_aggregator
            
            # Determine priority based on severity
            priority_map = {
                "high": NotificationPriority.HIGH,
                "medium": NotificationPriority.MEDIUM,
                "low": NotificationPriority.LOW
            }
            notification_priority = priority_map.get(severity, NotificationPriority.MEDIUM)
            
            # Create enhanced notification data
            notification_data = {
                "title": f"Alert: {subject}",
                "message": message,
                "notification_type": "error" if severity == "high" else "warning",
                "priority": notification_priority,
                "source": "alerting_system",
                "service_name": "vertex_ar",
                "event_data": {
                    "alert_type": alert_type,
                    "severity": severity,
                    "subject": subject,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            # Check if should aggregate
            existing_notifications = []
            try:
                from notifications import get_db, get_notifications
                db = next(get_db())
                existing_notifications = get_notifications(db, limit=100)
                db.close()
            except Exception as e:
                logger.warning(f"Could not fetch existing notifications for aggregation: {e}")
            
            # Check aggregation
            rule_name = notification_aggregator.should_aggregate(notification_data, existing_notifications)
            if rule_name:
                notification_data = notification_aggregator.generate_aggregated_notification(
                    notification_data, existing_notifications, rule_name
                )
            
            # Send to database
            send_notification(**notification_data)
            
            # Route through integrations based on priority
            if self.enabled:
                routes = self._get_routes_for_priority(notification_priority.value)
                if routes:
                    await notification_integrator.route_notification(
                        notification_data, routes, notification_priority.value
                    )
            
        except Exception as e:
            logger.error(f"Failed to store/route alert in enhanced notification system: {e}")
            
            # Fallback to original method
            try:
                from notifications import send_notification
                send_notification(
                    title=f"Alert: {subject}",
                    message=message,
                    notification_type="error" if severity == "high" else "warning"
                )
            except Exception as fallback_error:
                logger.error(f"Failed to store alert in database: {fallback_error}")
    
    def _get_routes_for_priority(self, priority: str) -> List[str]:
        """Get integration routes based on priority."""
        from app.config import settings
        
        route_map = {
            "critical": settings.CRITICAL_NOTIFICATION_ROUTES,
            "high": settings.HIGH_NOTIFICATION_ROUTES,
            "medium": settings.MEDIUM_NOTIFICATION_ROUTES,
            "low": settings.LOW_NOTIFICATION_ROUTES
        }
        
        routes = route_map.get(priority, [])
        
        # Filter based on enabled integrations
        filtered_routes = []
        for route in routes:
            route = route.strip()
            if route == "telegram" and settings.NOTIFICATION_TELEGRAM_ENABLED:
                filtered_routes.append(route)
            elif route == "email" and settings.NOTIFICATION_EMAIL_ENABLED:
                filtered_routes.append(route)
            elif route == "webhook" and settings.NOTIFICATION_WEBHOOK_ENABLED:
                filtered_routes.append(route)
        
        return filtered_routes
    
    async def test_alert_system(self) -> Dict[str, bool]:
        """Test all alert channels."""
        logger.info("Testing alert system...")
        
        results = {}
        
        # Test Telegram
        if settings.TELEGRAM_BOT_TOKEN:
            results["telegram"] = await self.send_telegram_alert("Test message from Vertex AR alert system")
        else:
            results["telegram"] = False
            
        # Test Email (checks DB config internally)
        try:
            results["email"] = await self.send_email_alert(
                "Test Alert", 
                "This is a test message from Vertex AR alert system"
            )
        except Exception as e:
            logger.warning(f"Email test failed: {e}")
            results["email"] = False
        
        logger.info(f"Alert system test results: {results}")
        return results


# Global alert manager instance
alert_manager = AlertManager()
