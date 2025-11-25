"""
Alerting system for Vertex AR - handles emergency notifications via email and Telegram.
"""
import asyncio
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            logger.warning("Telegram credentials not configured")
            return False
            
        try:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "text": f"🚨 **VERTEX AR ALERT** 🚨\n\n{message}",
                "parse_mode": "Markdown"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as response:
                    if response.status == 200:
                        logger.info("Telegram alert sent successfully")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to send Telegram alert: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
            return False
    
    async def send_email_alert(self, subject: str, message: str) -> bool:
        """Send alert via email."""
        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD or not settings.ADMIN_EMAILS:
            logger.warning("Email credentials not configured")
            return False
            
        try:
            msg = MIMEMultipart()
            msg['From'] = settings.EMAIL_FROM
            msg['To'] = ", ".join(settings.ADMIN_EMAILS)
            msg['Subject'] = f"[VERTEX AR ALERT] {subject}"
            
            body = MIMEText(f"""
Vertex AR Emergency Alert

{message}

---
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
Server: {settings.BASE_URL}
            """, 'plain')
            
            msg.attach(body)
            
            # Send email in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_email_sync, msg)
            
            logger.info(f"Email alert sent to {len(settings.ADMIN_EMAILS)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
            return False
    
    def _send_email_sync(self, msg: MIMEMultipart) -> None:
        """Synchronous email sending for thread pool execution."""
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
    
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
        
        # Send email alert
        if settings.SMTP_USERNAME and settings.ADMIN_EMAILS:
            email_success = await self.send_email_alert(subject, formatted_message)
            success = success and email_success
        
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
            
        # Test Email
        if settings.SMTP_USERNAME and settings.ADMIN_EMAILS:
            results["email"] = await self.send_email_alert(
                "Test Alert", 
                "This is a test message from Vertex AR alert system"
            )
        else:
            results["email"] = False
        
        logger.info(f"Alert system test results: {results}")
        return results


# Global alert manager instance
alert_manager = AlertManager()
