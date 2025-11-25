"""
Notification integrations module for Vertex AR.
Handles webhooks, external integrations, and advanced notification routing.
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
import aiohttp
from enum import Enum

from app.config import settings
from logging_setup import get_logger

logger = get_logger(__name__)


class WebhookStatus(Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRY = "retry"


class WebhookEvent:
    """Represents a webhook event."""
    def __init__(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        retries: int = 3
    ):
        self.url = url
        self.payload = payload
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout
        self.retries = retries
        self.attempts = 0
        self.status = WebhookStatus.PENDING
        self.last_error = None
        self.created_at = datetime.utcnow()
        self.delivered_at = None


class NotificationIntegrator:
    """Manages notification integrations and webhooks."""
    
    def __init__(self):
        self.enabled = settings.ALERTING_ENABLED
        self.webhook_queue: List[WebhookEvent] = []
        self.integration_handlers: Dict[str, Callable] = {}
        self.webhook_timeout = 30
        self.max_retries = 3
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default integration handlers."""
        self.integration_handlers["telegram"] = self._handle_telegram
        self.integration_handlers["email"] = self._handle_email
        self.integration_handlers["webhook"] = self._handle_webhook
    
    async def send_webhook(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """Send webhook notification."""
        try:
            event = WebhookEvent(url, payload, headers)
            self.webhook_queue.append(event)
            
            # Try to deliver immediately
            return await self._deliver_webhook(event)
            
        except Exception as e:
            logger.error(f"Error sending webhook: {e}")
            return False
    
    async def _deliver_webhook(self, event: WebhookEvent) -> bool:
        """Deliver webhook event with retry logic."""
        try:
            event.attempts += 1
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    event.url,
                    json=event.payload,
                    headers=event.headers,
                    timeout=aiohttp.ClientTimeout(total=event.timeout)
                ) as response:
                    if 200 <= response.status < 300:
                        event.status = WebhookStatus.DELIVERED
                        event.delivered_at = datetime.utcnow()
                        logger.info(f"Webhook delivered to {event.url}")
                        return True
                    else:
                        error_text = await response.text()
                        event.last_error = f"HTTP {response.status}: {error_text}"
                        logger.warning(f"Webhook failed: {event.last_error}")
                        
                        if event.attempts < event.retries:
                            event.status = WebhookStatus.RETRY
                            await asyncio.sleep(2 ** event.attempts)  # Exponential backoff
                            return await self._deliver_webhook(event)
                        else:
                            event.status = WebhookStatus.FAILED
                            return False
                            
        except asyncio.TimeoutError:
            event.last_error = "Timeout"
            logger.warning(f"Webhook timeout for {event.url}")
        except Exception as e:
            event.last_error = str(e)
            logger.error(f"Webhook delivery error: {e}")
        
        if event.attempts < event.retries:
            event.status = WebhookStatus.RETRY
            await asyncio.sleep(2 ** event.attempts)
            return await self._deliver_webhook(event)
        else:
            event.status = WebhookStatus.FAILED
            return False
    
    async def process_webhook_queue(self) -> Dict[str, int]:
        """Process pending webhook queue."""
        stats = {"pending": 0, "delivered": 0, "failed": 0}
        
        for event in self.webhook_queue[:]:  # Copy to avoid modification during iteration
            if event.status == WebhookStatus.PENDING or event.status == WebhookStatus.RETRY:
                stats["pending"] += 1
                success = await self._deliver_webhook(event)
                if success:
                    stats["delivered"] += 1
                elif event.status == WebhookStatus.FAILED:
                    stats["failed"] += 1
        
        # Clean up old events
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self.webhook_queue = [
            event for event in self.webhook_queue
            if event.created_at > cutoff or event.status == WebhookStatus.PENDING
        ]
        
        return stats
    
    async def route_notification(
        self,
        notification_data: Dict[str, Any],
        integrations: List[str],
        priority: str = "medium"
    ) -> Dict[str, bool]:
        """Route notification through multiple integrations."""
        results = {}
        
        for integration in integrations:
            if integration in self.integration_handlers:
                try:
                    handler = self.integration_handlers[integration]
                    success = await handler(notification_data, priority)
                    results[integration] = success
                except Exception as e:
                    logger.error(f"Error in {integration} integration: {e}")
                    results[integration] = False
            else:
                logger.warning(f"Unknown integration: {integration}")
                results[integration] = False
        
        return results
    
    async def _handle_telegram(self, notification_data: Dict[str, Any], priority: str) -> bool:
        """Handle Telegram integration."""
        try:
            from app.alerting import alert_manager
            return await alert_manager.send_telegram_alert(
                self._format_message(notification_data, priority)
            )
        except Exception as e:
            logger.error(f"Telegram integration error: {e}")
            return False
    
    async def _handle_email(self, notification_data: Dict[str, Any], priority: str) -> bool:
        """Handle email integration."""
        try:
            from app.alerting import alert_manager
            subject = f"[{priority.upper()}] {notification_data.get('title', 'Notification')}"
            message = self._format_message(notification_data, priority)
            return await alert_manager.send_email_alert(subject, message)
        except Exception as e:
            logger.error(f"Email integration error: {e}")
            return False
    
    async def _handle_webhook(self, notification_data: Dict[str, Any], priority: str) -> bool:
        """Handle generic webhook integration."""
        # This would need webhook URLs from configuration
        webhook_urls = getattr(settings, 'WEBHOOK_URLS', [])
        
        if not webhook_urls:
            return True  # No webhooks configured
        
        success_count = 0
        for url in webhook_urls:
            if await self.send_webhook(url, notification_data):
                success_count += 1
        
        return success_count > 0
    
    def _format_message(self, notification_data: Dict[str, Any], priority: str) -> str:
        """Format notification message for external services."""
        priority_emoji = {
            "critical": "🔴",
            "high": "🟠", 
            "medium": "🟡",
            "low": "🟢",
            "ignore": "⚪"
        }
        
        emoji = priority_emoji.get(priority, "📢")
        
        message = f"{emoji} **{priority.upper()}**\n\n"
        message += f"**{notification_data.get('title', 'Notification')}**\n\n"
        message += f"{notification_data.get('message', '')}\n"
        
        if notification_data.get('source'):
            message += f"\n*Source: {notification_data['source']}*"
        
        if notification_data.get('service_name'):
            message += f" | *Service: {notification_data['service_name']}*"
        
        message += f"\n\n*Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*"
        
        return message
    
    def register_integration_handler(self, name: str, handler: Callable):
        """Register custom integration handler."""
        self.integration_handlers[name] = handler
        logger.info(f"Registered integration handler: {name}")
    
    def get_webhook_stats(self) -> Dict[str, Any]:
        """Get webhook delivery statistics."""
        stats = {
            "total_events": len(self.webhook_queue),
            "by_status": {},
            "recent_deliveries": 0,
            "recent_failures": 0
        }
        
        # Count by status
        for event in self.webhook_queue:
            status = event.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # Count recent events (last hour)
            if event.created_at > datetime.utcnow() - timedelta(hours=1):
                if event.status == WebhookStatus.DELIVERED:
                    stats["recent_deliveries"] += 1
                elif event.status == WebhookStatus.FAILED:
                    stats["recent_failures"] += 1
        
        return stats


class NotificationScheduler:
    """Handles scheduled notification tasks."""
    
    def __init__(self, integrator: NotificationIntegrator):
        self.integrator = integrator
        self.scheduled_tasks: List[Dict[str, Any]] = []
        self.running = False
    
    async def start(self):
        """Start the scheduler."""
        self.running = True
        logger.info("Notification scheduler started")
        
        while self.running:
            try:
                # Process webhook queue
                await self.integrator.process_webhook_queue()
                
                # Process scheduled tasks
                await self._process_scheduled_tasks()
                
                # Sleep for 30 seconds
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        logger.info("Notification scheduler stopped")
    
    async def _process_scheduled_tasks(self):
        """Process scheduled notification tasks."""
        now = datetime.utcnow()
        
        for task in self.scheduled_tasks[:]:
            if task.get('next_run') and now >= task['next_run']:
                try:
                    await self._execute_scheduled_task(task)
                    
                    # Update next run time
                    if task.get('interval_minutes'):
                        task['next_run'] = now + timedelta(minutes=task['interval_minutes'])
                    else:
                        self.scheduled_tasks.remove(task)
                        
                except Exception as e:
                    logger.error(f"Error executing scheduled task: {e}")
    
    async def _execute_scheduled_task(self, task: Dict[str, Any]):
        """Execute a scheduled notification task."""
        notification_data = task['notification_data']
        integrations = task['integrations']
        priority = task.get('priority', 'medium')
        
        results = await self.integrator.route_notification(
            notification_data, integrations, priority
        )
        
        logger.info(f"Scheduled task executed: {results}")
    
    def schedule_notification(
        self,
        notification_data: Dict[str, Any],
        integrations: List[str],
        priority: str = "medium",
        run_at: Optional[datetime] = None,
        interval_minutes: Optional[int] = None
    ):
        """Schedule a notification task."""
        task = {
            'notification_data': notification_data,
            'integrations': integrations,
            'priority': priority,
            'next_run': run_at or datetime.utcnow(),
            'interval_minutes': interval_minutes,
            'created_at': datetime.utcnow()
        }
        
        self.scheduled_tasks.append(task)
        logger.info(f"Scheduled notification task: {task}")


# Global instances
notification_integrator = NotificationIntegrator()
notification_scheduler = NotificationScheduler(notification_integrator)