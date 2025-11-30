"""
Notification configuration loader.
Loads notification settings from database and provides them to the notification system.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from app.database import Database
from app.config import settings
from app.encryption import encryption_manager
from logging_setup import get_logger

logger = get_logger(__name__)


def _sanitize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize config dict for logging by masking sensitive values.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Sanitized copy with masked secrets
    """
    if not config:
        return {}
    
    sanitized = config.copy()
    sensitive_keys = ['password', 'token', 'secret', 'key']
    
    for key in sanitized:
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            if sanitized[key]:
                sanitized[key] = "***REDACTED***"
    
    return sanitized


class NotificationConfig:
    """Manages notification configuration from database."""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self._cached_settings = None
    
    def get_settings(self) -> Optional[Dict[str, Any]]:
        """Get notification settings from database."""
        try:
            db = Database(self.db_path)
            settings_data = db.get_notification_settings()
            
            if settings_data and settings_data.get('is_active'):
                # Decrypt sensitive fields
                if settings_data.get('smtp_password_encrypted'):
                    try:
                        settings_data['smtp_password'] = encryption_manager.decrypt(
                            settings_data['smtp_password_encrypted']
                        )
                    except Exception as e:
                        logger.error(f"Failed to decrypt SMTP password: {e}")
                        settings_data['smtp_password'] = None
                
                if settings_data.get('telegram_bot_token_encrypted'):
                    try:
                        settings_data['telegram_bot_token'] = encryption_manager.decrypt(
                            settings_data['telegram_bot_token_encrypted']
                        )
                    except Exception as e:
                        logger.error(f"Failed to decrypt Telegram bot token: {e}")
                        settings_data['telegram_bot_token'] = None
                
                self._cached_settings = settings_data
                return settings_data
            
            # Return None if no settings or not active
            return None
            
        except Exception as e:
            logger.error(f"Error loading notification settings from database: {e}")
            return None
    
    def get_smtp_config(self, actor: str = "system") -> Optional[Dict[str, Any]]:
        """
        Get SMTP configuration with security logging and guardrails.
        
        Args:
            actor: Identifier of the actor requesting config (for audit trail)
            
        Returns:
            SMTP configuration dict or None if not properly configured
        """
        # Log access attempt with timestamp
        logger.info(
            "SMTP config accessed",
            actor=actor,
            timestamp=datetime.utcnow().isoformat(),
        )
        
        settings_data = self.get_settings()
        if not settings_data:
            logger.warning(
                "SMTP config unavailable: no notification settings in database",
                actor=actor,
            )
            return None
        
        # SECURITY GUARDRAIL: Require encrypted database entries
        if not settings_data.get('smtp_password_encrypted'):
            logger.error(
                "SMTP config rejected: missing encrypted password in database",
                actor=actor,
                has_host=bool(settings_data.get('smtp_host')),
                has_username=bool(settings_data.get('smtp_username')),
            )
            return None
        
        if not settings_data.get('smtp_host') or not settings_data.get('smtp_username'):
            logger.warning(
                "SMTP config incomplete",
                actor=actor,
                has_host=bool(settings_data.get('smtp_host')),
                has_username=bool(settings_data.get('smtp_username')),
            )
            return None
        
        config = {
            'host': settings_data['smtp_host'],
            'port': settings_data.get('smtp_port', 587),
            'username': settings_data['smtp_username'],
            'password': settings_data.get('smtp_password'),
            'from_email': settings_data.get('smtp_from_email') or settings_data['smtp_username'],
            'use_tls': bool(settings_data.get('smtp_use_tls', 1)),
            'use_ssl': bool(settings_data.get('smtp_use_ssl', 0)),
        }
        
        # Log successful retrieval with sanitized config
        logger.info(
            "SMTP config retrieved successfully",
            actor=actor,
            config=_sanitize_config(config),
        )
        
        return config
    
    def get_telegram_config(self) -> Optional[Dict[str, Any]]:
        """Get Telegram configuration."""
        settings_data = self.get_settings()
        if not settings_data:
            return None
        
        if not settings_data.get('telegram_bot_token') or not settings_data.get('telegram_chat_ids'):
            return None
        
        # Parse chat IDs
        chat_ids = [cid.strip() for cid in settings_data['telegram_chat_ids'].split(',') if cid.strip()]
        
        return {
            'bot_token': settings_data['telegram_bot_token'],
            'chat_ids': chat_ids,
        }
    
    def get_event_settings(self) -> Dict[str, bool]:
        """Get event notification settings."""
        settings_data = self.get_settings()
        if not settings_data:
            # Return defaults
            return {
                'log_errors': True,
                'db_issues': True,
                'disk_space': True,
                'resource_monitoring': True,
                'backup_success': True,
                'info_notifications': True,
            }
        
        return {
            'log_errors': bool(settings_data.get('event_log_errors', 1)),
            'db_issues': bool(settings_data.get('event_db_issues', 1)),
            'disk_space': bool(settings_data.get('event_disk_space', 1)),
            'resource_monitoring': bool(settings_data.get('event_resource_monitoring', 1)),
            'backup_success': bool(settings_data.get('event_backup_success', 1)),
            'info_notifications': bool(settings_data.get('event_info_notifications', 1)),
        }
    
    def get_thresholds(self) -> Dict[str, int]:
        """Get monitoring thresholds."""
        settings_data = self.get_settings()
        if not settings_data:
            # Return defaults from environment or hardcoded
            return {
                'cpu': int(settings.CPU_THRESHOLD),
                'memory': int(settings.MEMORY_THRESHOLD),
                'disk': int(settings.DISK_THRESHOLD),
            }
        
        return {
            'cpu': settings_data.get('cpu_threshold_percent', 80),
            'memory': settings_data.get('memory_threshold_percent', 85),
            'disk': settings_data.get('disk_threshold_percent', 90),
        }
    
    def should_send_notification(self, event_type: str) -> bool:
        """Check if notifications should be sent for a given event type."""
        event_settings = self.get_event_settings()
        return event_settings.get(event_type, True)


# Global notification config instance
_notification_config = None


def get_notification_config(db_path=None) -> NotificationConfig:
    """Get or create the global notification config instance."""
    global _notification_config
    if _notification_config is None:
        if db_path is None:
            db_path = settings.DB_PATH
        _notification_config = NotificationConfig(db_path)
    return _notification_config
