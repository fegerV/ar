"""
Email Service with Queue and Prometheus Monitoring for Vertex AR.
Provides reliable email delivery with retry logic, metrics, and failure alerting.
"""
import asyncio
import smtplib
import time
from collections import deque
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from typing import Dict, List, Optional, Any, Deque
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

from app.config import settings
from logging_setup import get_logger

logger = get_logger(__name__)


class EmailStatus(Enum):
    """Email delivery status."""
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    RETRY = "retry"


class EmailMessage:
    """Represents an email message in the queue."""
    
    def __init__(
        self,
        to_addresses: List[str],
        subject: str,
        body: str,
        from_address: Optional[str] = None,
        html_body: Optional[str] = None,
        priority: int = 5,
    ):
        self.id = f"{time.time()}_{hash(subject)}"
        self.to_addresses = to_addresses
        self.subject = subject
        self.body = body
        self.html_body = html_body
        self.from_address = from_address or settings.EMAIL_FROM
        self.priority = priority  # 1-10, lower = higher priority
        
        self.status = EmailStatus.PENDING
        self.attempts = 0
        self.max_attempts = 3
        self.last_error: Optional[str] = None
        self.created_at = datetime.utcnow()
        self.sent_at: Optional[datetime] = None
        self.next_retry_at: Optional[datetime] = None
    
    def __lt__(self, other):
        """Compare for priority queue (lower priority number = higher priority)."""
        return self.priority < other.priority


class EmailQueue:
    """
    Email queue with priority handling and retry logic.
    """
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.pending: Deque[EmailMessage] = deque()
        self.failed: List[EmailMessage] = []
        self.sent_count = 0
        self.failed_count = 0
        self._lock = asyncio.Lock()
    
    async def enqueue(self, message: EmailMessage) -> bool:
        """Add message to queue."""
        async with self._lock:
            if len(self.pending) >= self.max_size:
                logger.warning(f"Email queue full (max: {self.max_size}), rejecting message")
                return False
            
            # Insert in priority order
            inserted = False
            for i, msg in enumerate(self.pending):
                if message.priority < msg.priority:
                    self.pending.insert(i, message)
                    inserted = True
                    break
            
            if not inserted:
                self.pending.append(message)
            
            logger.debug(f"Email queued: {message.id} (priority: {message.priority})")
            return True
    
    async def dequeue(self) -> Optional[EmailMessage]:
        """Get next message from queue."""
        async with self._lock:
            # Check for retry-ready messages in failed list
            now = datetime.utcnow()
            for msg in self.failed[:]:
                if msg.next_retry_at and msg.next_retry_at <= now:
                    self.failed.remove(msg)
                    msg.status = EmailStatus.RETRY
                    return msg
            
            # Get next pending message
            if self.pending:
                return self.pending.popleft()
            
            return None
    
    async def mark_sent(self, message: EmailMessage):
        """Mark message as successfully sent."""
        async with self._lock:
            message.status = EmailStatus.SENT
            message.sent_at = datetime.utcnow()
            self.sent_count += 1
    
    async def mark_failed(self, message: EmailMessage, error: str, retry: bool = True):
        """Mark message as failed and optionally schedule retry."""
        async with self._lock:
            message.last_error = error
            message.attempts += 1
            
            if retry and message.attempts < message.max_attempts:
                # Exponential backoff: 2^attempts minutes
                retry_delay = timedelta(minutes=2 ** message.attempts)
                message.next_retry_at = datetime.utcnow() + retry_delay
                message.status = EmailStatus.FAILED
                
                # Add back to failed list for retry
                if message not in self.failed:
                    self.failed.append(message)
                
                logger.warning(
                    f"Email {message.id} failed (attempt {message.attempts}/{message.max_attempts}), "
                    f"will retry at {message.next_retry_at}"
                )
            else:
                message.status = EmailStatus.FAILED
                self.failed_count += 1
                
                # Keep in failed list but mark as permanently failed
                if message not in self.failed:
                    self.failed.append(message)
                
                logger.error(
                    f"Email {message.id} permanently failed after {message.attempts} attempts: {error}"
                )
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        async with self._lock:
            retry_count = sum(1 for msg in self.failed if msg.next_retry_at is not None)
            permanent_failed = sum(1 for msg in self.failed if msg.next_retry_at is None)
            
            return {
                "pending": len(self.pending),
                "retry_queue": retry_count,
                "permanent_failed": permanent_failed,
                "total_sent": self.sent_count,
                "total_failed": self.failed_count,
                "queue_depth": len(self.pending) + retry_count,
            }
    
    async def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent failed messages."""
        async with self._lock:
            recent_failed = sorted(
                self.failed,
                key=lambda m: m.created_at,
                reverse=True
            )[:limit]
            
            return [
                {
                    "id": msg.id,
                    "to": msg.to_addresses,
                    "subject": msg.subject,
                    "error": msg.last_error,
                    "attempts": msg.attempts,
                    "created_at": msg.created_at.isoformat(),
                    "next_retry": msg.next_retry_at.isoformat() if msg.next_retry_at else None,
                }
                for msg in recent_failed
            ]


class EmailService:
    """
    Email service with Prometheus metrics and failure rate monitoring.
    """
    
    # Class-level metric instances (will be created once)
    _metrics_initialized = False
    email_sent_total = None
    email_failed_total = None
    email_send_duration_seconds = None
    email_retry_attempts = None
    email_queue_depth = None
    email_pending_count = None
    email_failed_count = None
    
    @classmethod
    def _init_metrics(cls):
        """Initialize Prometheus metrics with custom registry."""
        if cls._metrics_initialized:
            return
        
        # Get the custom registry
        try:
            from app.prometheus_metrics import registry as custom_registry
        except ImportError:
            # Fallback to default registry if not available
            from prometheus_client import REGISTRY as custom_registry
        
        # Create metrics with custom registry
        cls.email_sent_total = Counter(
            'vertex_ar_email_sent_total',
            'Total number of emails successfully sent',
            ['priority'],
            registry=custom_registry
        )
        
        cls.email_failed_total = Counter(
            'vertex_ar_email_failed_total',
            'Total number of emails that failed to send',
            ['priority', 'error_type'],
            registry=custom_registry
        )
        
        cls.email_send_duration_seconds = Histogram(
            'vertex_ar_email_send_duration_seconds',
            'Email send duration in seconds',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
            registry=custom_registry
        )
        
        cls.email_retry_attempts = Counter(
            'vertex_ar_email_retry_attempts_total',
            'Total number of email retry attempts',
            ['attempt_number'],
            registry=custom_registry
        )
        
        cls.email_queue_depth = Gauge(
            'vertex_ar_email_queue_depth',
            'Current depth of email queue',
            registry=custom_registry
        )
        
        cls.email_pending_count = Gauge(
            'vertex_ar_email_pending_count',
            'Number of emails pending in queue',
            registry=custom_registry
        )
        
        cls.email_failed_count = Gauge(
            'vertex_ar_email_failed_count',
            'Number of emails in failed state',
            registry=custom_registry
        )
        
        cls._metrics_initialized = True
        logger.info("Email service Prometheus metrics initialized")
    
    def __init__(self):
        # Initialize metrics if not already done
        self._init_metrics()
        
        self.queue = EmailQueue()
        self.enabled = bool(settings.SMTP_USERNAME and settings.SMTP_PASSWORD)
        self.processing = False
        
        # Failure rate tracking (rolling window)
        self.send_history: Deque[Dict[str, Any]] = deque(maxlen=1000)
        self.last_alert_time: Optional[datetime] = None
        self.alert_cooldown = timedelta(hours=1)
        
        logger.info(f"EmailService initialized (enabled: {self.enabled})")
    
    async def send_email(
        self,
        to_addresses: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        priority: int = 5,
    ) -> bool:
        """
        Queue an email for sending.
        
        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            priority: Priority (1-10, lower = higher priority)
        
        Returns:
            True if successfully queued, False otherwise
        """
        if not self.enabled:
            logger.warning("Email service disabled, cannot send email")
            return False
        
        message = EmailMessage(
            to_addresses=to_addresses,
            subject=subject,
            body=body,
            html_body=html_body,
            priority=priority,
        )
        
        queued = await self.queue.enqueue(message)
        
        if queued:
            # Update queue depth metric
            stats = await self.queue.get_stats()
            self.email_queue_depth.set(stats["queue_depth"])
            self.email_pending_count.set(stats["pending"])
            
            logger.info(f"Email queued: {subject} to {len(to_addresses)} recipients")
        
        return queued
    
    async def _send_email_sync(self, message: EmailMessage) -> None:
        """
        Synchronously send an email via SMTP.
        
        Raises exception on failure.
        """
        # Get SMTP config from database or fallback to settings
        try:
            from app.notification_config import get_notification_config
            notification_config = get_notification_config()
            smtp_config = notification_config.get_smtp_config()
            
            if smtp_config:
                smtp_host = smtp_config['host']
                smtp_port = smtp_config['port']
                smtp_username = smtp_config['username']
                smtp_password = smtp_config['password']
                use_tls = smtp_config['use_tls']
                use_ssl = smtp_config['use_ssl']
            else:
                # Fallback to environment variables
                smtp_host = settings.SMTP_SERVER
                smtp_port = settings.SMTP_PORT
                smtp_username = settings.SMTP_USERNAME
                smtp_password = settings.SMTP_PASSWORD
                use_tls = True
                use_ssl = False
        except Exception as e:
            logger.warning(f"Could not get SMTP config from database: {e}, using settings")
            smtp_host = settings.SMTP_SERVER
            smtp_port = settings.SMTP_PORT
            smtp_username = settings.SMTP_USERNAME
            smtp_password = settings.SMTP_PASSWORD
            use_tls = True
            use_ssl = False
        
        # Build MIME message
        msg = MIMEMultipart('alternative')
        msg['From'] = message.from_address
        msg['To'] = ", ".join(message.to_addresses)
        msg['Subject'] = message.subject
        
        # Attach plain text
        msg.attach(MIMEText(message.body, 'plain'))
        
        # Attach HTML if provided
        if message.html_body:
            msg.attach(MIMEText(message.html_body, 'html'))
        
        # Send via SMTP
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._smtp_send,
            smtp_host,
            smtp_port,
            smtp_username,
            smtp_password,
            use_tls,
            use_ssl,
            msg,
        )
    
    def _smtp_send(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        use_tls: bool,
        use_ssl: bool,
        msg: MIMEMultipart,
    ) -> None:
        """Synchronous SMTP send (runs in executor)."""
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=30)
        else:
            server = smtplib.SMTP(host, port, timeout=30)
            if use_tls:
                server.starttls()
        
        server.login(username, password)
        server.send_message(msg)
        server.quit()
    
    async def process_queue(self) -> Dict[str, int]:
        """
        Process pending emails in the queue.
        
        Returns:
            Statistics about processed emails
        """
        if self.processing:
            logger.debug("Queue processing already in progress")
            return {"processed": 0, "sent": 0, "failed": 0}
        
        self.processing = True
        processed = 0
        sent = 0
        failed = 0
        
        try:
            # Process up to 10 messages per batch
            for _ in range(10):
                message = await self.queue.dequeue()
                if not message:
                    break
                
                processed += 1
                message.status = EmailStatus.SENDING
                
                # Track retry attempts
                if message.attempts > 0:
                    self.email_retry_attempts.labels(
                        attempt_number=str(message.attempts)
                    ).inc()
                
                # Send email with timing
                start_time = time.time()
                try:
                    await self._send_email_sync(message)
                    duration = time.time() - start_time
                    
                    # Record metrics
                    self.email_send_duration_seconds.observe(duration)
                    self.email_sent_total.labels(priority=str(message.priority)).inc()
                    
                    await self.queue.mark_sent(message)
                    sent += 1
                    
                    # Track in history
                    self.send_history.append({
                        "timestamp": datetime.utcnow(),
                        "success": True,
                        "duration": duration,
                    })
                    
                    logger.info(f"Email sent successfully: {message.id} (took {duration:.2f}s)")
                    
                except Exception as e:
                    duration = time.time() - start_time
                    error_type = type(e).__name__
                    error_message = str(e)
                    
                    # Record metrics
                    self.email_failed_total.labels(
                        priority=str(message.priority),
                        error_type=error_type
                    ).inc()
                    
                    await self.queue.mark_failed(message, error_message)
                    failed += 1
                    
                    # Track in history
                    self.send_history.append({
                        "timestamp": datetime.utcnow(),
                        "success": False,
                        "error": error_message,
                        "duration": duration,
                    })
                    
                    logger.error(f"Email send failed: {message.id} - {error_type}: {error_message}")
            
            # Update queue metrics
            stats = await self.queue.get_stats()
            self.email_queue_depth.set(stats["queue_depth"])
            self.email_pending_count.set(stats["pending"])
            self.email_failed_count.set(stats["permanent_failed"])
            
            # Check failure rate and alert if needed
            await self._check_failure_rate()
            
            logger.debug(f"Queue processed: {processed} emails ({sent} sent, {failed} failed)")
            
        finally:
            self.processing = False
        
        return {"processed": processed, "sent": sent, "failed": failed}
    
    async def _check_failure_rate(self) -> None:
        """Check failure rate over last hour and send alert if > 10%."""
        if not self.send_history:
            return
        
        # Calculate failure rate for last hour
        cutoff = datetime.utcnow() - timedelta(hours=1)
        recent = [h for h in self.send_history if h["timestamp"] > cutoff]
        
        if len(recent) < 10:  # Need at least 10 emails to calculate meaningful rate
            return
        
        failed = sum(1 for h in recent if not h["success"])
        failure_rate = failed / len(recent)
        
        # Alert if failure rate > 10% and not in cooldown
        if failure_rate > 0.10:
            now = datetime.utcnow()
            if self.last_alert_time is None or (now - self.last_alert_time) > self.alert_cooldown:
                self.last_alert_time = now
                
                # Send alert via alert_manager
                try:
                    from app.alerting import alert_manager
                    
                    await alert_manager.send_alert(
                        alert_type="email_failure_rate",
                        subject="High Email Failure Rate",
                        message=(
                            f"Email delivery failure rate is {failure_rate:.1%} over the last hour.\n"
                            f"Total attempts: {len(recent)}\n"
                            f"Failed: {failed}\n"
                            f"Threshold: 10%\n\n"
                            f"Check SMTP configuration and email service logs."
                        ),
                        severity="high"
                    )
                    
                    logger.warning(f"High email failure rate alert sent: {failure_rate:.1%}")
                    
                except Exception as e:
                    logger.error(f"Failed to send email failure rate alert: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive email service statistics."""
        queue_stats = await self.queue.get_stats()
        
        # Calculate recent failure rate
        cutoff = datetime.utcnow() - timedelta(hours=1)
        recent = [h for h in self.send_history if h["timestamp"] > cutoff]
        
        failure_rate = 0.0
        if recent:
            failed = sum(1 for h in recent if not h["success"])
            failure_rate = failed / len(recent)
        
        # Get recent errors
        recent_errors = await self.queue.get_recent_errors(limit=5)
        
        # Get last error
        last_error = None
        if recent_errors:
            last_error = recent_errors[0]
        
        # Calculate retry histogram
        retry_histogram = {}
        for msg in self.queue.failed:
            retry_histogram[msg.attempts] = retry_histogram.get(msg.attempts, 0) + 1
        
        return {
            "enabled": self.enabled,
            "processing": self.processing,
            "queue": queue_stats,
            "failure_rate_1h": round(failure_rate * 100, 2),  # Percentage
            "recent_attempts_1h": len(recent),
            "retry_histogram": retry_histogram,
            "last_error": last_error,
            "recent_errors": recent_errors,
        }
    
    async def get_prometheus_metrics_snapshot(self) -> Dict[str, Any]:
        """Get snapshot of Prometheus metrics for API response."""
        queue_stats = await self.queue.get_stats()
        
        return {
            "email_sent_total": self.queue.sent_count,
            "email_failed_total": self.queue.failed_count,
            "email_queue_depth": queue_stats["queue_depth"],
            "email_pending_count": queue_stats["pending"],
            "email_failed_count": queue_stats["permanent_failed"],
        }


# Global email service instance
email_service = EmailService()
