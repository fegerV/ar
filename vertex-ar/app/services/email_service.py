"""
Async Email Service for Vertex AR.

Provides reliable email delivery with:
- aiosmtplib for async SMTP operations
- Template rendering support
- Exponential backoff retries
- Structured logging
- Notification history integration
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib
from jinja2 import Template

from app.config import settings
from app.database import Database
from app.notification_config import NotificationConfig
from logging_setup import get_logger

logger = get_logger(__name__)


class EmailService:
    """
    Async email service with template support, retries, and notification history.
    """
    
    def __init__(self, notification_config: NotificationConfig, db: Database):
        """
        Initialize the email service.
        
        Args:
            notification_config: Notification configuration instance
            db: Database instance for templates and history
        """
        self.notification_config = notification_config
        self.db = db
        self.enabled = False
        
        # Check if SMTP is configured
        try:
            smtp_config = self.notification_config.get_smtp_config(actor="email_service_init")
            self.enabled = smtp_config is not None
        except Exception as e:
            logger.warning(f"Could not check SMTP config: {e}")
        
        logger.info(f"AsyncEmailService initialized (enabled: {self.enabled})")
    
    def _get_retry_delays(self) -> List[float]:
        """
        Get retry delay schedule from settings.
        
        Returns:
            List of delay values in seconds
        """
        if hasattr(settings, 'EMAIL_RETRY_DELAYS') and settings.EMAIL_RETRY_DELAYS:
            return settings.EMAIL_RETRY_DELAYS
        # Default exponential backoff: 1, 2, 4, 8, 16 seconds
        return [1, 2, 4, 8, 16]
    
    def _get_max_retry_attempts(self) -> int:
        """
        Get maximum retry attempts from settings.
        
        Returns:
            Maximum number of retry attempts
        """
        if hasattr(settings, 'EMAIL_RETRY_MAX_ATTEMPTS') and settings.EMAIL_RETRY_MAX_ATTEMPTS:
            return settings.EMAIL_RETRY_MAX_ATTEMPTS
        # Default: length of delay schedule
        return len(self._get_retry_delays())
    
    async def send_email(
        self,
        to_addresses: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        from_address: Optional[str] = None,
    ) -> bool:
        """
        Send an email with retry logic.
        
        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            from_address: Optional sender address (uses config default if not provided)
        
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("Email service disabled, cannot send email", subject=subject)
            return False
        
        if not to_addresses:
            logger.error("No recipient addresses provided", subject=subject)
            return False
        
        # Get SMTP config
        try:
            smtp_config = self.notification_config.get_smtp_config(actor="email_service")
            if not smtp_config:
                logger.error("SMTP configuration not available", subject=subject)
                return False
        except Exception as e:
            logger.error("Failed to get SMTP config", error=str(e), subject=subject)
            return False
        
        # Use provided from_address or config default
        sender = from_address or smtp_config.get('from_email') or settings.EMAIL_FROM
        
        # Build message
        msg = self._build_message(
            to_addresses=to_addresses,
            subject=subject,
            body=body,
            html_body=html_body,
            from_address=sender,
        )
        
        # Send with retry logic
        return await self._send_with_retry(
            msg=msg,
            smtp_config=smtp_config,
            to_addresses=to_addresses,
            subject=subject,
            body=body[:200],  # Truncate for logging
        )
    
    async def send_template_email(
        self,
        to_addresses: List[str],
        template_type: str,
        variables: Dict[str, Any],
        from_address: Optional[str] = None,
    ) -> bool:
        """
        Send an email using a database template.
        
        Args:
            to_addresses: List of recipient email addresses
            template_type: Template type identifier (e.g., 'subscription_end')
            variables: Variables to render in the template
            from_address: Optional sender address
        
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("Email service disabled, cannot send template email", template_type=template_type)
            return False
        
        # Get template from database
        try:
            template_data = self.db.get_active_template_by_type(template_type)
            if not template_data:
                logger.error("Email template not found", template_type=template_type)
                return False
        except Exception as e:
            logger.error("Failed to load email template", template_type=template_type, error=str(e))
            return False
        
        # Render template
        try:
            subject = self._render_template(template_data['subject'], variables)
            html_body = self._render_template(template_data['html_content'], variables)
            # Generate plain text from HTML (simple approach)
            body = self._html_to_text(html_body)
        except Exception as e:
            logger.error("Failed to render email template", template_type=template_type, error=str(e))
            return False
        
        # Send the email
        return await self.send_email(
            to_addresses=to_addresses,
            subject=subject,
            body=body,
            html_body=html_body,
            from_address=from_address,
        )
    
    async def send_bulk_email(
        self,
        recipients: List[Dict[str, str]],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        from_address: Optional[str] = None,
        max_concurrent: int = 5,
    ) -> Dict[str, int]:
        """
        Send emails to multiple recipients concurrently.
        
        Args:
            recipients: List of dicts with 'email' key (and optionally 'name')
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            from_address: Optional sender address
            max_concurrent: Maximum concurrent sends
        
        Returns:
            Dict with counts: {'sent': N, 'failed': M, 'total': X}
        """
        if not self.enabled:
            logger.warning("Email service disabled, cannot send bulk email")
            return {'sent': 0, 'failed': len(recipients), 'total': len(recipients)}
        
        if not recipients:
            logger.warning("No recipients provided for bulk email")
            return {'sent': 0, 'failed': 0, 'total': 0}
        
        sent = 0
        failed = 0
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def send_one(recipient: Dict[str, str]) -> bool:
            async with semaphore:
                email = recipient.get('email')
                if not email:
                    logger.warning("Recipient missing email address", recipient=recipient)
                    return False
                
                # Optionally customize subject/body with recipient name
                recipient_subject = subject
                recipient_body = body
                recipient_html = html_body
                
                if 'name' in recipient:
                    # Simple variable substitution
                    recipient_subject = subject.replace('{{name}}', recipient['name'])
                    recipient_body = body.replace('{{name}}', recipient['name'])
                    if html_body:
                        recipient_html = html_body.replace('{{name}}', recipient['name'])
                
                return await self.send_email(
                    to_addresses=[email],
                    subject=recipient_subject,
                    body=recipient_body,
                    html_body=recipient_html,
                    from_address=from_address,
                )
        
        # Send all emails concurrently
        tasks = [send_one(recipient) for recipient in recipients]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count results
        for result in results:
            if isinstance(result, Exception):
                logger.error("Bulk email send exception", error=str(result))
                failed += 1
            elif result:
                sent += 1
            else:
                failed += 1
        
        logger.info(
            "Bulk email completed",
            sent=sent,
            failed=failed,
            total=len(recipients),
        )
        
        return {'sent': sent, 'failed': failed, 'total': len(recipients)}
    
    def _build_message(
        self,
        to_addresses: List[str],
        subject: str,
        body: str,
        html_body: Optional[str],
        from_address: str,
    ) -> MIMEMultipart:
        """
        Build a MIME message.
        
        Args:
            to_addresses: Recipient addresses
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            from_address: Sender address
        
        Returns:
            MIME multipart message
        """
        msg = MIMEMultipart('alternative')
        msg['From'] = from_address
        msg['To'] = ", ".join(to_addresses)
        msg['Subject'] = subject
        msg['Date'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
        
        # Attach plain text
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Attach HTML if provided
        if html_body:
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        return msg
    
    async def _send_with_retry(
        self,
        msg: MIMEMultipart,
        smtp_config: Dict[str, Any],
        to_addresses: List[str],
        subject: str,
        body: str,
    ) -> bool:
        """
        Send email with exponential backoff retry logic.
        
        Args:
            msg: MIME message to send
            smtp_config: SMTP configuration
            to_addresses: Recipient addresses
            subject: Subject (for logging)
            body: Body excerpt (for logging)
        
        Returns:
            True if sent successfully, False otherwise
        """
        retry_delays = self._get_retry_delays()
        max_attempts = self._get_max_retry_attempts()
        
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                # Attempt to send
                await self._send_smtp(msg, smtp_config)
                
                # Success! Log to notification history
                await self._log_notification_history(
                    recipient=", ".join(to_addresses),
                    subject=subject,
                    message=body,
                    status='sent',
                    error_message=None,
                )
                
                logger.info(
                    "Email sent successfully",
                    to=to_addresses,
                    subject=subject,
                    attempt=attempt + 1,
                )
                
                return True
                
            except Exception as e:
                last_error = str(e)
                error_type = type(e).__name__
                
                logger.warning(
                    "Email send attempt failed",
                    to=to_addresses,
                    subject=subject,
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                    error_type=error_type,
                    error=last_error,
                )
                
                # If not the last attempt, wait before retrying
                if attempt < max_attempts - 1:
                    delay = retry_delays[attempt] if attempt < len(retry_delays) else retry_delays[-1]
                    logger.debug(
                        "Retrying email send after delay",
                        delay=delay,
                        next_attempt=attempt + 2,
                    )
                    await asyncio.sleep(delay)
        
        # All attempts failed - log to notification history
        await self._log_notification_history(
            recipient=", ".join(to_addresses),
            subject=subject,
            message=body,
            status='failed',
            error_message=last_error,
        )
        
        logger.error(
            "Email send failed after all retry attempts",
            to=to_addresses,
            subject=subject,
            attempts=max_attempts,
            error=last_error,
        )
        
        return False
    
    async def _send_smtp(self, msg: MIMEMultipart, smtp_config: Dict[str, Any]) -> None:
        """
        Send email via SMTP using aiosmtplib.
        
        Args:
            msg: MIME message to send
            smtp_config: SMTP configuration
        
        Raises:
            Exception on send failure
        """
        host = smtp_config['host']
        port = smtp_config['port']
        username = smtp_config['username']
        password = smtp_config['password']
        use_tls = smtp_config.get('use_tls', True)
        use_ssl = smtp_config.get('use_ssl', False)
        
        # Determine connection type
        if use_ssl:
            # Direct SSL connection
            smtp = aiosmtplib.SMTP(
                hostname=host,
                port=port,
                use_tls=True,
                timeout=30,
            )
        else:
            # Standard connection with optional STARTTLS
            smtp = aiosmtplib.SMTP(
                hostname=host,
                port=port,
                use_tls=False,
                timeout=30,
            )
        
        try:
            # Connect
            await smtp.connect()
            
            # Upgrade to TLS if needed
            if use_tls and not use_ssl:
                await smtp.starttls()
            
            # Authenticate
            if username and password:
                await smtp.login(username, password)
            
            # Send message
            await smtp.send_message(msg)
            
        finally:
            # Always close connection
            try:
                await smtp.quit()
            except Exception as e:
                logger.debug("Error closing SMTP connection", error=str(e))
    
    async def _log_notification_history(
        self,
        recipient: str,
        subject: str,
        message: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log email send attempt to notification history.
        
        Args:
            recipient: Recipient address(es)
            subject: Email subject
            message: Email body excerpt
            status: 'sent' or 'failed'
            error_message: Optional error message if failed
        """
        try:
            history_id = str(uuid.uuid4())
            self.db.add_notification_history(
                history_id=history_id,
                notification_type='email',
                recipient=recipient,
                subject=subject,
                message=message,
                status=status,
                error_message=error_message,
            )
        except Exception as e:
            logger.error("Failed to log notification history", error=str(e))
    
    @staticmethod
    def _render_template(template_str: str, variables: Dict[str, Any]) -> str:
        """
        Render a Jinja2 template string with variables.
        
        Args:
            template_str: Template string
            variables: Variables to render
        
        Returns:
            Rendered template
        """
        template = Template(template_str)
        return template.render(**variables)
    
    @staticmethod
    def _html_to_text(html: str) -> str:
        """
        Convert HTML to plain text (simple approach).
        
        Args:
            html: HTML string
        
        Returns:
            Plain text string
        """
        # Simple HTML to text conversion
        # Remove HTML tags
        import re
        text = re.sub('<[^<]+?>', '', html)
        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text


# Global instance (will be initialized in main.py)
_email_service: Optional[EmailService] = None


def init_email_service(notification_config: NotificationConfig, db: Database) -> EmailService:
    """
    Initialize the global email service instance.
    
    Args:
        notification_config: Notification configuration
        db: Database instance
    
    Returns:
        EmailService instance
    """
    global _email_service
    _email_service = EmailService(notification_config, db)
    logger.info("Global async email service initialized")
    return _email_service


def get_email_service() -> Optional[EmailService]:
    """
    Get the global email service instance.
    
    Returns:
        EmailService instance or None if not initialized
    """
    return _email_service
