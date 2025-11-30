"""
Unit tests for async EmailService.

Tests email sending, template rendering, bulk operations, retry logic,
and notification history integration.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch, call
from datetime import datetime
from email.mime.multipart import MIMEMultipart

# Import the service under test
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent / "vertex-ar"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.services.email_service import EmailService


class TestEmailServiceInitialization:
    """Test EmailService initialization."""
    
    def test_init_with_smtp_configured(self):
        """Test initialization when SMTP is configured."""
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = {
            'host': 'smtp.example.com',
            'port': 587,
            'username': 'user',
            'password': 'pass',
        }
        
        mock_db = Mock()
        
        service = EmailService(mock_config, mock_db)
        
        assert service.enabled is True
        assert service.notification_config == mock_config
        assert service.db == mock_db
    
    def test_init_without_smtp_configured(self):
        """Test initialization when SMTP is not configured."""
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = None
        
        mock_db = Mock()
        
        service = EmailService(mock_config, mock_db)
        
        assert service.enabled is False
    
    def test_init_with_smtp_error(self):
        """Test initialization when SMTP config check fails."""
        mock_config = Mock()
        mock_config.get_smtp_config.side_effect = Exception("DB error")
        
        mock_db = Mock()
        
        service = EmailService(mock_config, mock_db)
        
        assert service.enabled is False


class TestEmailServiceRetryConfig:
    """Test retry configuration methods."""
    
    def test_default_retry_delays(self):
        """Test default retry delays."""
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = None
        mock_db = Mock()
        
        service = EmailService(mock_config, mock_db)
        delays = service._get_retry_delays()
        
        assert delays == [1, 2, 4, 8, 16]
    
    def test_custom_retry_delays_from_settings(self):
        """Test custom retry delays from settings."""
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = None
        mock_db = Mock()
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.EMAIL_RETRY_DELAYS = [0.5, 1.0, 2.0]
            
            service = EmailService(mock_config, mock_db)
            delays = service._get_retry_delays()
            
            assert delays == [0.5, 1.0, 2.0]
    
    def test_default_max_attempts(self):
        """Test default max attempts."""
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = None
        mock_db = Mock()
        
        service = EmailService(mock_config, mock_db)
        max_attempts = service._get_max_retry_attempts()
        
        assert max_attempts == 5  # Length of default delays
    
    def test_custom_max_attempts_from_settings(self):
        """Test custom max attempts from settings."""
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = None
        mock_db = Mock()
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.EMAIL_RETRY_MAX_ATTEMPTS = 3
            
            service = EmailService(mock_config, mock_db)
            max_attempts = service._get_max_retry_attempts()
            
            assert max_attempts == 3


@pytest.mark.asyncio
class TestEmailServiceSendEmail:
    """Test send_email method."""
    
    async def test_send_email_when_disabled(self):
        """Test sending email when service is disabled."""
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = None
        mock_db = Mock()
        
        service = EmailService(mock_config, mock_db)
        
        result = await service.send_email(
            to_addresses=['test@example.com'],
            subject='Test',
            body='Test body',
        )
        
        assert result is False
    
    async def test_send_email_no_recipients(self):
        """Test sending email with no recipients."""
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = {'host': 'smtp.example.com'}
        mock_db = Mock()
        
        service = EmailService(mock_config, mock_db)
        service.enabled = True
        
        result = await service.send_email(
            to_addresses=[],
            subject='Test',
            body='Test body',
        )
        
        assert result is False
    
    async def test_send_email_smtp_config_unavailable(self):
        """Test sending email when SMTP config becomes unavailable."""
        mock_config = Mock()
        mock_config.get_smtp_config.side_effect = [
            {'host': 'smtp.example.com'},  # Init check
            None,  # Send check
        ]
        mock_db = Mock()
        
        service = EmailService(mock_config, mock_db)
        
        result = await service.send_email(
            to_addresses=['test@example.com'],
            subject='Test',
            body='Test body',
        )
        
        assert result is False
    
    async def test_send_email_success(self):
        """Test successful email send."""
        smtp_config = {
            'host': 'smtp.example.com',
            'port': 587,
            'username': 'user',
            'password': 'pass',
            'from_email': 'sender@example.com',
            'use_tls': True,
            'use_ssl': False,
        }
        
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = smtp_config
        
        mock_db = Mock()
        mock_db.add_notification_history = Mock()
        
        service = EmailService(mock_config, mock_db)
        
        # Mock SMTP send
        with patch.object(service, '_send_smtp', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = None
            
            result = await service.send_email(
                to_addresses=['test@example.com'],
                subject='Test Subject',
                body='Test body',
                html_body='<p>Test body</p>',
            )
        
        assert result is True
        mock_send.assert_called_once()
        
        # Verify notification history was logged
        mock_db.add_notification_history.assert_called_once()
        call_args = mock_db.add_notification_history.call_args[1]
        assert call_args['notification_type'] == 'email'
        assert call_args['recipient'] == 'test@example.com'
        assert call_args['subject'] == 'Test Subject'
        assert call_args['status'] == 'sent'
        assert call_args['error_message'] is None
    
    async def test_send_email_retry_and_success(self):
        """Test email send with retries that eventually succeeds."""
        smtp_config = {
            'host': 'smtp.example.com',
            'port': 587,
            'username': 'user',
            'password': 'pass',
            'from_email': 'sender@example.com',
            'use_tls': True,
            'use_ssl': False,
        }
        
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = smtp_config
        
        mock_db = Mock()
        mock_db.add_notification_history = Mock()
        
        service = EmailService(mock_config, mock_db)
        
        # Mock SMTP send to fail twice then succeed
        with patch.object(service, '_send_smtp', new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = [
                Exception("Connection timeout"),
                Exception("Connection timeout"),
                None,  # Success on third attempt
            ]
            
            # Mock sleep to speed up test
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await service.send_email(
                    to_addresses=['test@example.com'],
                    subject='Test Subject',
                    body='Test body',
                )
        
        assert result is True
        assert mock_send.call_count == 3
        
        # Verify notification history logged success
        mock_db.add_notification_history.assert_called_once()
        call_args = mock_db.add_notification_history.call_args[1]
        assert call_args['status'] == 'sent'
    
    async def test_send_email_all_retries_fail(self):
        """Test email send when all retries fail."""
        smtp_config = {
            'host': 'smtp.example.com',
            'port': 587,
            'username': 'user',
            'password': 'pass',
            'from_email': 'sender@example.com',
            'use_tls': True,
            'use_ssl': False,
        }
        
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = smtp_config
        
        mock_db = Mock()
        mock_db.add_notification_history = Mock()
        
        service = EmailService(mock_config, mock_db)
        
        # Override to use fewer retries for faster test
        with patch.object(service, '_get_retry_delays', return_value=[0.01, 0.02]):
            with patch.object(service, '_get_max_retry_attempts', return_value=2):
                # Mock SMTP send to always fail
                with patch.object(service, '_send_smtp', new_callable=AsyncMock) as mock_send:
                    mock_send.side_effect = Exception("Connection refused")
                    
                    # Mock sleep
                    with patch('asyncio.sleep', new_callable=AsyncMock):
                        result = await service.send_email(
                            to_addresses=['test@example.com'],
                            subject='Test Subject',
                            body='Test body',
                        )
        
        assert result is False
        assert mock_send.call_count == 2
        
        # Verify notification history logged failure
        mock_db.add_notification_history.assert_called_once()
        call_args = mock_db.add_notification_history.call_args[1]
        assert call_args['status'] == 'failed'
        assert 'Connection refused' in call_args['error_message']


@pytest.mark.asyncio
class TestEmailServiceTemplateEmail:
    """Test send_template_email method."""
    
    async def test_send_template_email_disabled(self):
        """Test sending template email when service is disabled."""
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = None
        mock_db = Mock()
        
        service = EmailService(mock_config, mock_db)
        
        result = await service.send_template_email(
            to_addresses=['test@example.com'],
            template_type='subscription_end',
            variables={'name': 'John'},
        )
        
        assert result is False
    
    async def test_send_template_email_template_not_found(self):
        """Test sending template email when template doesn't exist."""
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = {'host': 'smtp.example.com'}
        
        mock_db = Mock()
        mock_db.get_active_template_by_type.return_value = None
        
        service = EmailService(mock_config, mock_db)
        service.enabled = True
        
        result = await service.send_template_email(
            to_addresses=['test@example.com'],
            template_type='nonexistent',
            variables={},
        )
        
        assert result is False
    
    async def test_send_template_email_success(self):
        """Test successful template email send."""
        smtp_config = {
            'host': 'smtp.example.com',
            'port': 587,
            'username': 'user',
            'password': 'pass',
            'from_email': 'sender@example.com',
            'use_tls': True,
            'use_ssl': False,
        }
        
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = smtp_config
        
        template_data = {
            'subject': 'Hello {{name}}',
            'html_content': '<p>Dear {{name}}, your subscription ends on {{date}}.</p>',
        }
        
        mock_db = Mock()
        mock_db.get_active_template_by_type.return_value = template_data
        mock_db.add_notification_history = Mock()
        
        service = EmailService(mock_config, mock_db)
        
        # Mock send_email
        with patch.object(service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            result = await service.send_template_email(
                to_addresses=['test@example.com'],
                template_type='subscription_end',
                variables={'name': 'John', 'date': '2024-12-31'},
            )
        
        assert result is True
        
        # Verify send_email was called with rendered template
        mock_send.assert_called_once()
        call_args = mock_send.call_args[1]
        assert call_args['subject'] == 'Hello John'
        assert 'Dear John' in call_args['html_body']
        assert '2024-12-31' in call_args['html_body']
    
    async def test_send_template_email_render_error(self):
        """Test template email send when rendering fails."""
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = {'host': 'smtp.example.com'}
        
        template_data = {
            'subject': 'Hello {{name}}',
            'html_content': '<p>Hello {{undefined_variable}}</p>',
        }
        
        mock_db = Mock()
        mock_db.get_active_template_by_type.return_value = template_data
        
        service = EmailService(mock_config, mock_db)
        service.enabled = True
        
        # Jinja2 will raise an error for undefined variables in strict mode
        # But by default it just renders empty string, so let's trigger a real error
        template_data['html_content'] = '{{ bad syntax'
        
        result = await service.send_template_email(
            to_addresses=['test@example.com'],
            template_type='test',
            variables={'name': 'John'},
        )
        
        assert result is False


@pytest.mark.asyncio
class TestEmailServiceBulkEmail:
    """Test send_bulk_email method."""
    
    async def test_send_bulk_email_disabled(self):
        """Test bulk email when service is disabled."""
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = None
        mock_db = Mock()
        
        service = EmailService(mock_config, mock_db)
        
        recipients = [
            {'email': 'test1@example.com'},
            {'email': 'test2@example.com'},
        ]
        
        result = await service.send_bulk_email(
            recipients=recipients,
            subject='Test',
            body='Test body',
        )
        
        assert result == {'sent': 0, 'failed': 2, 'total': 2}
    
    async def test_send_bulk_email_empty_recipients(self):
        """Test bulk email with empty recipient list."""
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = {'host': 'smtp.example.com'}
        mock_db = Mock()
        
        service = EmailService(mock_config, mock_db)
        service.enabled = True
        
        result = await service.send_bulk_email(
            recipients=[],
            subject='Test',
            body='Test body',
        )
        
        assert result == {'sent': 0, 'failed': 0, 'total': 0}
    
    async def test_send_bulk_email_success(self):
        """Test successful bulk email send."""
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = {'host': 'smtp.example.com'}
        mock_db = Mock()
        
        service = EmailService(mock_config, mock_db)
        service.enabled = True
        
        recipients = [
            {'email': 'test1@example.com', 'name': 'Alice'},
            {'email': 'test2@example.com', 'name': 'Bob'},
            {'email': 'test3@example.com'},
        ]
        
        # Mock send_email to succeed for all
        with patch.object(service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            result = await service.send_bulk_email(
                recipients=recipients,
                subject='Hello {{name}}',
                body='Dear {{name}}, welcome!',
                html_body='<p>Dear {{name}}, welcome!</p>',
            )
        
        assert result == {'sent': 3, 'failed': 0, 'total': 3}
        assert mock_send.call_count == 3
        
        # Verify personalization worked
        calls = mock_send.call_args_list
        assert 'Alice' in calls[0][1]['subject']
        assert 'Bob' in calls[1][1]['subject']
        # Third recipient has no name, so {{name}} stays
        assert '{{name}}' in calls[2][1]['subject']
    
    async def test_send_bulk_email_partial_failure(self):
        """Test bulk email with some failures."""
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = {'host': 'smtp.example.com'}
        mock_db = Mock()
        
        service = EmailService(mock_config, mock_db)
        service.enabled = True
        
        recipients = [
            {'email': 'test1@example.com'},
            {'email': 'test2@example.com'},
            {'email': 'test3@example.com'},
        ]
        
        # Mock send_email to succeed for first and third, fail for second
        with patch.object(service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = [True, False, True]
            
            result = await service.send_bulk_email(
                recipients=recipients,
                subject='Test',
                body='Test body',
            )
        
        assert result == {'sent': 2, 'failed': 1, 'total': 3}
    
    async def test_send_bulk_email_missing_email_field(self):
        """Test bulk email with recipient missing email field."""
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = {'host': 'smtp.example.com'}
        mock_db = Mock()
        
        service = EmailService(mock_config, mock_db)
        service.enabled = True
        
        recipients = [
            {'email': 'test1@example.com'},
            {'name': 'No Email'},  # Missing email field
        ]
        
        with patch.object(service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            result = await service.send_bulk_email(
                recipients=recipients,
                subject='Test',
                body='Test body',
            )
        
        # First succeeds, second fails due to missing email
        assert result['sent'] == 1
        assert result['failed'] == 1
        assert result['total'] == 2


class TestEmailServiceHelpers:
    """Test helper methods."""
    
    def test_build_message_plain_text_only(self):
        """Test building message with plain text only."""
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = None
        mock_db = Mock()
        
        service = EmailService(mock_config, mock_db)
        
        msg = service._build_message(
            to_addresses=['test@example.com'],
            subject='Test Subject',
            body='Plain text body',
            html_body=None,
            from_address='sender@example.com',
        )
        
        assert isinstance(msg, MIMEMultipart)
        assert msg['From'] == 'sender@example.com'
        assert msg['To'] == 'test@example.com'
        assert msg['Subject'] == 'Test Subject'
        assert msg['Date'] is not None
    
    def test_build_message_with_html(self):
        """Test building message with HTML."""
        mock_config = Mock()
        mock_config.get_smtp_config.return_value = None
        mock_db = Mock()
        
        service = EmailService(mock_config, mock_db)
        
        msg = service._build_message(
            to_addresses=['test1@example.com', 'test2@example.com'],
            subject='Test Subject',
            body='Plain text body',
            html_body='<p>HTML body</p>',
            from_address='sender@example.com',
        )
        
        assert msg['To'] == 'test1@example.com, test2@example.com'
    
    def test_render_template(self):
        """Test template rendering."""
        template_str = 'Hello {{name}}, you have {{count}} messages.'
        variables = {'name': 'Alice', 'count': 5}
        
        result = EmailService._render_template(template_str, variables)
        
        assert result == 'Hello Alice, you have 5 messages.'
    
    def test_html_to_text(self):
        """Test HTML to text conversion."""
        html = '<p>Hello <strong>World</strong></p><p>Line 2</p>'
        
        result = EmailService._html_to_text(html)
        
        assert 'Hello' in result
        assert 'World' in result
        assert 'Line 2' in result
        # Tags should be removed
        assert '<p>' not in result
        assert '<strong>' not in result
    
    def test_html_to_text_with_entities(self):
        """Test HTML to text with HTML entities."""
        html = '<p>5 &lt; 10 &amp; 10 &gt; 5</p>'
        
        result = EmailService._html_to_text(html)
        
        assert '<' in result
        assert '>' in result
        assert '&' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
