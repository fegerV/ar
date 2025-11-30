"""
Notification settings API endpoints for Vertex AR.
Manages centralized email and Telegram notification settings.
"""
import uuid
import asyncio
from typing import Any, Dict, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.auth import require_admin
from app.database import Database
from app.encryption import encryption_manager
from app.main import get_current_app
from app.models import (
    NotificationSettingsUpdate,
    NotificationSettingsResponse,
    NotificationTestRequest,
    NotificationTestResponse,
    NotificationHistoryItem,
    PaginatedNotificationHistoryResponse,
    MessageResponse,
)
from logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/notification-settings", tags=["notification-settings"])


def _mask_sensitive_data(value: Optional[str]) -> Optional[str]:
    """Mask sensitive data for display."""
    if not value or len(value) < 8:
        return "****" if value else None
    return value[:4] + "****" + value[-4:]


def _prepare_settings_response(settings: Dict[str, Any]) -> NotificationSettingsResponse:
    """Prepare notification settings for API response."""
    # Mask sensitive fields
    settings['smtp_password_masked'] = _mask_sensitive_data(
        settings.get('smtp_password_encrypted')
    ) if settings.get('smtp_password_encrypted') else None
    settings['telegram_bot_token_masked'] = _mask_sensitive_data(
        settings.get('telegram_bot_token_encrypted')
    ) if settings.get('telegram_bot_token_encrypted') else None
    
    # Convert boolean integers to actual booleans
    bool_fields = [
        'smtp_use_tls', 'smtp_use_ssl', 'event_log_errors', 'event_db_issues',
        'event_disk_space', 'event_resource_monitoring', 'event_backup_success',
        'event_info_notifications', 'is_active'
    ]
    for field in bool_fields:
        if field in settings and settings[field] is not None:
            settings[field] = bool(settings[field])
    
    # Remove encrypted fields from response
    settings.pop('smtp_password_encrypted', None)
    settings.pop('telegram_bot_token_encrypted', None)
    
    return NotificationSettingsResponse(**settings)


@router.get("", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    _admin: str = Depends(require_admin)
) -> NotificationSettingsResponse:
    """
    Get current notification settings.
    Requires admin authentication.
    """
    try:
        app = get_current_app()
        db = Database(app.state.config["DB_PATH"])
        
        settings = db.get_notification_settings()
        
        if not settings:
            # Return default settings if none exist
            default_settings = {
                'id': 'default',
                'smtp_host': None,
                'smtp_port': 587,
                'smtp_username': None,
                'smtp_password_encrypted': None,
                'smtp_from_email': None,
                'smtp_use_tls': 1,
                'smtp_use_ssl': 0,
                'telegram_bot_token_encrypted': None,
                'telegram_chat_ids': None,
                'event_log_errors': 1,
                'event_db_issues': 1,
                'event_disk_space': 1,
                'event_resource_monitoring': 1,
                'event_backup_success': 1,
                'event_info_notifications': 1,
                'disk_threshold_percent': 90,
                'cpu_threshold_percent': 80,
                'memory_threshold_percent': 85,
                'is_active': 1,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            return _prepare_settings_response(default_settings)
        
        return _prepare_settings_response(settings)
        
    except Exception as e:
        logger.error(f"Error getting notification settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get notification settings"
        )


@router.put("", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    settings_update: NotificationSettingsUpdate,
    _admin: str = Depends(require_admin)
) -> NotificationSettingsResponse:
    """
    Update notification settings.
    Requires admin authentication.
    """
    try:
        app = get_current_app()
        db = Database(app.state.config["DB_PATH"])
        
        # Prepare update data
        update_data = {}
        
        # Handle SMTP settings
        if settings_update.smtp_host is not None:
            update_data['smtp_host'] = settings_update.smtp_host
        if settings_update.smtp_port is not None:
            update_data['smtp_port'] = settings_update.smtp_port
        if settings_update.smtp_username is not None:
            update_data['smtp_username'] = settings_update.smtp_username
        if settings_update.smtp_password is not None and settings_update.smtp_password:
            # Encrypt password before storing
            update_data['smtp_password_encrypted'] = encryption_manager.encrypt(
                settings_update.smtp_password
            )
        if settings_update.smtp_from_email is not None:
            update_data['smtp_from_email'] = settings_update.smtp_from_email
        if settings_update.smtp_use_tls is not None:
            update_data['smtp_use_tls'] = 1 if settings_update.smtp_use_tls else 0
        if settings_update.smtp_use_ssl is not None:
            update_data['smtp_use_ssl'] = 1 if settings_update.smtp_use_ssl else 0
        
        # Handle Telegram settings
        if settings_update.telegram_bot_token is not None and settings_update.telegram_bot_token:
            # Encrypt token before storing
            update_data['telegram_bot_token_encrypted'] = encryption_manager.encrypt(
                settings_update.telegram_bot_token
            )
        if settings_update.telegram_chat_ids is not None:
            update_data['telegram_chat_ids'] = settings_update.telegram_chat_ids
        
        # Handle event settings
        if settings_update.event_log_errors is not None:
            update_data['event_log_errors'] = 1 if settings_update.event_log_errors else 0
        if settings_update.event_db_issues is not None:
            update_data['event_db_issues'] = 1 if settings_update.event_db_issues else 0
        if settings_update.event_disk_space is not None:
            update_data['event_disk_space'] = 1 if settings_update.event_disk_space else 0
        if settings_update.event_resource_monitoring is not None:
            update_data['event_resource_monitoring'] = 1 if settings_update.event_resource_monitoring else 0
        if settings_update.event_backup_success is not None:
            update_data['event_backup_success'] = 1 if settings_update.event_backup_success else 0
        if settings_update.event_info_notifications is not None:
            update_data['event_info_notifications'] = 1 if settings_update.event_info_notifications else 0
        
        # Handle threshold settings
        if settings_update.disk_threshold_percent is not None:
            update_data['disk_threshold_percent'] = settings_update.disk_threshold_percent
        if settings_update.cpu_threshold_percent is not None:
            update_data['cpu_threshold_percent'] = settings_update.cpu_threshold_percent
        if settings_update.memory_threshold_percent is not None:
            update_data['memory_threshold_percent'] = settings_update.memory_threshold_percent
        
        # Handle active flag
        if settings_update.is_active is not None:
            update_data['is_active'] = 1 if settings_update.is_active else 0
        
        # Save settings
        settings_id = str(uuid.uuid4())
        saved_settings = db.save_notification_settings(settings_id, **update_data)
        
        logger.info("Notification settings updated successfully")
        return _prepare_settings_response(saved_settings)
        
    except Exception as e:
        logger.error(f"Error updating notification settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update notification settings: {str(e)}"
        )


@router.post("/test", response_model=NotificationTestResponse)
async def test_notification_settings(
    test_request: NotificationTestRequest,
    _admin: str = Depends(require_admin)
) -> NotificationTestResponse:
    """
    Test notification settings by sending test messages.
    Requires admin authentication.
    """
    try:
        app = get_current_app()
        db = Database(app.state.config["DB_PATH"])
        
        settings = db.get_notification_settings()
        if not settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No notification settings found. Please configure settings first."
            )
        
        results = {}
        overall_success = True
        
        # Test email if requested
        if test_request.test_type in ['email', 'both']:
            email_result = await _test_email_notification(settings)
            results['email'] = email_result
            overall_success = overall_success and email_result['success']
        
        # Test Telegram if requested
        if test_request.test_type in ['telegram', 'both']:
            telegram_result = await _test_telegram_notification(settings)
            results['telegram'] = telegram_result
            overall_success = overall_success and telegram_result['success']
        
        message = "All tests passed successfully" if overall_success else "Some tests failed"
        
        return NotificationTestResponse(
            success=overall_success,
            results=results,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing notification settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test notification settings: {str(e)}"
        )


async def _test_email_notification(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Test email notification settings using EmailService."""
    try:
        if not settings.get('smtp_host') or not settings.get('smtp_username'):
            return {
                'success': False,
                'message': 'Email settings not configured',
                'error': 'Missing SMTP host or username'
            }
        
        # Check if password is configured
        if not settings.get('smtp_password_encrypted'):
            return {
                'success': False,
                'message': 'Email password not configured',
                'error': 'Missing SMTP password'
            }
        
        # Get email service
        from app.email_service import email_service
        
        # Determine recipient
        recipient = settings.get('smtp_from_email') or settings['smtp_username']
        
        # Create test message
        subject = "[Vertex AR] Test Email Notification"
        body = (
            f"This is a test email from Vertex AR notification system.\n\n"
            f"Sent at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            f"If you received this email, your email notification settings are working correctly."
        )
        
        # Send email via EmailService (urgent=True for immediate test)
        success = await email_service.send_email(
            to_addresses=[recipient],
            subject=subject,
            body=body,
            priority=1,  # High priority for tests
            urgent=True  # Bypass persistent queue for immediate delivery
        )
        
        if success:
            return {
                'success': True,
                'message': f'Test email sent successfully to {recipient}',
                'recipient': recipient
            }
        else:
            return {
                'success': False,
                'message': 'Failed to send test email',
                'error': 'Email service returned failure'
            }
        
    except Exception as e:
        logger.error(f"Email test failed: {e}")
        return {
            'success': False,
            'message': 'Failed to send test email',
            'error': str(e)
        }


async def _test_telegram_notification(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Test Telegram notification settings."""
    import aiohttp
    
    try:
        if not settings.get('telegram_bot_token_encrypted'):
            return {
                'success': False,
                'message': 'Telegram bot token not configured',
                'error': 'Missing bot token'
            }
        
        if not settings.get('telegram_chat_ids'):
            return {
                'success': False,
                'message': 'Telegram chat IDs not configured',
                'error': 'Missing chat IDs'
            }
        
        # Decrypt bot token
        bot_token = encryption_manager.decrypt(settings['telegram_bot_token_encrypted'])
        
        # Get first chat ID
        chat_ids = [cid.strip() for cid in settings['telegram_chat_ids'].split(',')]
        chat_id = chat_ids[0] if chat_ids else None
        
        if not chat_id:
            return {
                'success': False,
                'message': 'No valid chat ID found',
                'error': 'Empty chat ID list'
            }
        
        # Send test message
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": (
                "🔔 **Test Notification from Vertex AR**\n\n"
                f"Sent at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                "If you received this message, your Telegram notification settings are working correctly."
            ),
            "parse_mode": "Markdown"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as response:
                if response.status == 200:
                    return {
                        'success': True,
                        'message': f'Test message sent successfully to chat {chat_id}',
                        'recipient': chat_id
                    }
                else:
                    error_text = await response.text()
                    return {
                        'success': False,
                        'message': 'Failed to send test message',
                        'error': f"HTTP {response.status}: {error_text}"
                    }
        
    except Exception as e:
        logger.error(f"Telegram test failed: {e}")
        return {
            'success': False,
            'message': 'Failed to send test Telegram message',
            'error': str(e)
        }


@router.get("/history", response_model=PaginatedNotificationHistoryResponse)
async def get_notification_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    notification_type: Optional[str] = Query(None, description="Filter by type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    _admin: str = Depends(require_admin)
) -> PaginatedNotificationHistoryResponse:
    """
    Get notification history with pagination and filters.
    Requires admin authentication.
    """
    try:
        app = get_current_app()
        db = Database(app.state.config["DB_PATH"])
        
        offset = (page - 1) * page_size
        
        history_items = db.list_notification_history(
            limit=page_size,
            offset=offset,
            notification_type=notification_type,
            status=status
        )
        
        total = db.count_notification_history(
            notification_type=notification_type,
            status=status
        )
        
        total_pages = (total + page_size - 1) // page_size
        
        items = [NotificationHistoryItem(**item) for item in history_items]
        
        return PaginatedNotificationHistoryResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Error getting notification history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get notification history"
        )


@router.delete("/history/cleanup", response_model=MessageResponse)
async def cleanup_notification_history(
    days: int = Query(30, ge=1, description="Delete records older than this many days"),
    _admin: str = Depends(require_admin)
) -> MessageResponse:
    """
    Clean up old notification history records.
    Requires admin authentication.
    """
    try:
        app = get_current_app()
        db = Database(app.state.config["DB_PATH"])
        
        deleted = db.cleanup_old_notification_history(days)
        
        return MessageResponse(
            message=f"Cleaned up {deleted} old notification history records"
        )
        
    except Exception as e:
        logger.error(f"Error cleaning up notification history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clean up notification history"
        )
