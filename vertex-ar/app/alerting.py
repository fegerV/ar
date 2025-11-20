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
        
        # Store in database notifications
        try:
            from notifications import send_notification
            send_notification(
                title=f"Alert: {subject}",
                message=message,
                notification_type="error" if severity == "high" else "warning"
            )
        except Exception as e:
            logger.error(f"Failed to store alert in database: {e}")
        
        return success
    
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
