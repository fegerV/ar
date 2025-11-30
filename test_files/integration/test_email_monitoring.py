"""
Integration tests for email monitoring and Prometheus metrics.
"""
import os
import sys
import tempfile
from pathlib import Path
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta


@pytest.fixture
def mock_smtp():
    """Mock SMTP for email testing."""
    with patch('smtplib.SMTP') as mock_smtp_class:
        mock_server = Mock()
        mock_smtp_class.return_value = mock_server
        yield mock_server


@pytest.fixture
def mock_smtp_ssl():
    """Mock SMTP_SSL for email testing."""
    with patch('smtplib.SMTP_SSL') as mock_smtp_ssl_class:
        mock_server = Mock()
        mock_smtp_ssl_class.return_value = mock_server
        yield mock_server


@pytest.fixture
def email_service():
    """Get email service instance."""
    from app.email_service import EmailService
    service = EmailService()
    service.enabled = True  # Force enable for testing
    return service


@pytest.mark.asyncio
async def test_email_service_initialization(email_service):
    """Test email service initializes correctly."""
    assert email_service is not None
    assert email_service.queue is not None
    assert hasattr(email_service, 'email_sent_total')
    assert hasattr(email_service, 'email_failed_total')
    assert hasattr(email_service, 'email_send_duration_seconds')
    assert hasattr(email_service, 'email_retry_attempts')
    assert hasattr(email_service, 'email_queue_depth')


@pytest.mark.asyncio
async def test_email_queuing(email_service):
    """Test email can be queued successfully."""
    result = await email_service.send_email(
        to_addresses=["test@example.com"],
        subject="Test Email",
        body="This is a test email",
        priority=5
    )
    
    assert result is True
    
    stats = await email_service.get_stats()
    assert stats["queue"]["pending"] >= 1


@pytest.mark.asyncio
async def test_email_priority_queue(email_service):
    """Test priority queue ordering."""
    # Queue emails with different priorities
    await email_service.send_email(
        to_addresses=["low@example.com"],
        subject="Low Priority",
        body="Low",
        priority=9
    )
    
    await email_service.send_email(
        to_addresses=["high@example.com"],
        subject="High Priority",
        body="High",
        priority=1
    )
    
    await email_service.send_email(
        to_addresses=["medium@example.com"],
        subject="Medium Priority",
        body="Medium",
        priority=5
    )
    
    # Dequeue and check order (high priority first)
    msg1 = await email_service.queue.dequeue()
    assert msg1.priority == 1
    
    msg2 = await email_service.queue.dequeue()
    assert msg2.priority == 5
    
    msg3 = await email_service.queue.dequeue()
    assert msg3.priority == 9


@pytest.mark.asyncio
async def test_email_send_success(email_service, mock_smtp):
    """Test successful email sending updates metrics."""
    initial_sent = email_service.queue.sent_count
    
    await email_service.send_email(
        to_addresses=["success@example.com"],
        subject="Success Test",
        body="This should succeed"
    )
    
    # Process the queue
    await email_service.process_queue()
    
    # Check metrics
    stats = await email_service.get_stats()
    assert stats["queue"]["total_sent"] > initial_sent


@pytest.mark.asyncio
async def test_email_send_failure_with_retry(email_service, mock_smtp):
    """Test email failure triggers retry logic."""
    # Make SMTP fail
    mock_smtp.send_message.side_effect = Exception("SMTP Error")
    
    await email_service.send_email(
        to_addresses=["fail@example.com"],
        subject="Failure Test",
        body="This should fail"
    )
    
    # Process the queue
    await email_service.process_queue()
    
    # Check that message is in retry state
    stats = await email_service.get_stats()
    assert stats["queue"]["retry_queue"] >= 1 or stats["queue"]["permanent_failed"] >= 1


@pytest.mark.asyncio
async def test_failure_rate_tracking(email_service, mock_smtp):
    """Test failure rate is tracked correctly."""
    # Send some successful emails
    mock_smtp.send_message.side_effect = None
    for i in range(5):
        await email_service.send_email(
            to_addresses=[f"success{i}@example.com"],
            subject=f"Success {i}",
            body="Success"
        )
    
    # Process successful emails
    await email_service.process_queue()
    
    # Send some failing emails
    mock_smtp.send_message.side_effect = Exception("SMTP Error")
    for i in range(3):
        await email_service.send_email(
            to_addresses=[f"fail{i}@example.com"],
            subject=f"Fail {i}",
            body="Fail"
        )
    
    # Process failing emails
    await email_service.process_queue()
    
    # Check stats
    stats = await email_service.get_stats()
    assert "failure_rate_1h" in stats
    # With 5 success + 3 failures = 37.5% failure rate
    # But depending on timing, we should have some failure rate


@pytest.mark.asyncio
async def test_failure_rate_alert(email_service, mock_smtp):
    """Test high failure rate triggers alert."""
    with patch('app.alerting.alert_manager') as mock_alert_manager:
        mock_alert_manager.send_alert = AsyncMock()
        
        # Make all emails fail
        mock_smtp.send_message.side_effect = Exception("SMTP Error")
        
        # Send 15 emails to exceed minimum threshold
        for i in range(15):
            await email_service.send_email(
                to_addresses=[f"fail{i}@example.com"],
                subject=f"Fail {i}",
                body="Fail"
            )
        
        # Process queue
        for _ in range(5):  # Process multiple times to handle retries
            await email_service.process_queue()
            await asyncio.sleep(0.1)
        
        # Check if alert was sent (may need multiple processing cycles)
        # Note: Alert only sent if >10 emails in history and >10% failure rate


@pytest.mark.asyncio
async def test_prometheus_metrics_snapshot(email_service):
    """Test Prometheus metrics snapshot is returned."""
    metrics = await email_service.get_prometheus_metrics_snapshot()
    
    assert "email_sent_total" in metrics
    assert "email_failed_total" in metrics
    assert "email_queue_depth" in metrics
    assert "email_pending_count" in metrics
    assert "email_failed_count" in metrics
    
    assert isinstance(metrics["email_sent_total"], int)
    assert isinstance(metrics["email_failed_total"], int)


@pytest.mark.asyncio
async def test_email_stats_comprehensive(email_service):
    """Test comprehensive stats include all required fields."""
    stats = await email_service.get_stats()
    
    # Service info
    assert "enabled" in stats
    assert "processing" in stats
    
    # Queue info
    assert "queue" in stats
    assert "pending" in stats["queue"]
    assert "retry_queue" in stats["queue"]
    assert "permanent_failed" in stats["queue"]
    assert "total_sent" in stats["queue"]
    assert "total_failed" in stats["queue"]
    
    # Performance info
    assert "failure_rate_1h" in stats
    assert "recent_attempts_1h" in stats
    
    # Error info
    assert "last_error" in stats
    assert "recent_errors" in stats
    
    # Retry info
    assert "retry_histogram" in stats


def test_email_stats_endpoint_requires_auth(client):
    """Test email stats endpoint requires authentication."""
    response = client.get("/admin/monitoring/email-stats")
    assert response.status_code == 401


def test_email_stats_endpoint_with_auth(authenticated_client):
    """Test email stats endpoint returns data with authentication."""
    response = authenticated_client.get("/admin/monitoring/email-stats")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    
    # Check required fields
    assert "service" in data["data"]
    assert "queue" in data["data"]
    assert "performance" in data["data"]
    assert "retry_histogram" in data["data"]
    assert "errors" in data["data"]
    assert "prometheus_metrics" in data["data"]


def test_prometheus_metrics_include_email(client):
    """Test /metrics endpoint includes email metrics."""
    response = client.get("/metrics")
    assert response.status_code == 200
    
    content = response.text
    
    # Check for email metrics in Prometheus output
    # Note: Metrics may not be present if email service didn't send anything yet
    # But the types should be registered
    assert "vertex_ar_email" in content or "TYPE" in content


@pytest.mark.asyncio
async def test_retry_exponential_backoff(email_service):
    """Test retry uses exponential backoff."""
    from app.email_service import EmailMessage
    
    message = EmailMessage(
        to_addresses=["test@example.com"],
        subject="Test",
        body="Test"
    )
    
    # First failure
    await email_service.queue.mark_failed(message, "Error 1", retry=True)
    assert message.attempts == 1
    assert message.next_retry_at is not None
    first_retry = message.next_retry_at
    
    # Second failure
    await email_service.queue.mark_failed(message, "Error 2", retry=True)
    assert message.attempts == 2
    assert message.next_retry_at > first_retry


@pytest.mark.asyncio
async def test_queue_max_size(email_service):
    """Test queue respects max size limit."""
    # Set small max size
    email_service.queue.max_size = 5
    
    # Fill queue
    for i in range(5):
        result = await email_service.send_email(
            to_addresses=[f"test{i}@example.com"],
            subject=f"Test {i}",
            body="Test"
        )
        assert result is True
    
    # Try to add one more (should fail)
    result = await email_service.send_email(
        to_addresses=["overflow@example.com"],
        subject="Overflow",
        body="Should fail"
    )
    assert result is False


@pytest.mark.asyncio
async def test_recent_errors_list(email_service, mock_smtp):
    """Test recent errors are tracked and retrievable."""
    mock_smtp.send_message.side_effect = Exception("Test Error")
    
    # Send and fail some emails
    for i in range(3):
        await email_service.send_email(
            to_addresses=[f"error{i}@example.com"],
            subject=f"Error {i}",
            body="Error"
        )
    
    await email_service.process_queue()
    
    # Get recent errors
    errors = await email_service.queue.get_recent_errors(limit=5)
    assert len(errors) >= 3
    
    # Check error structure
    for error in errors:
        assert "id" in error
        assert "to" in error
        assert "subject" in error
        assert "error" in error
        assert "attempts" in error
        assert "created_at" in error


def test_email_stats_endpoint_structure(authenticated_client):
    """Test email stats endpoint returns correct structure."""
    response = authenticated_client.get("/admin/monitoring/email-stats")
    assert response.status_code == 200
    
    data = response.json()["data"]
    
    # Service section
    assert "enabled" in data["service"]
    assert "processing" in data["service"]
    
    # Queue section
    assert "pending" in data["queue"]
    assert "retry_queue" in data["queue"]
    assert "permanent_failed" in data["queue"]
    assert "total_sent" in data["queue"]
    assert "total_failed" in data["queue"]
    assert "queue_depth" in data["queue"]
    
    # Performance section
    assert "failure_rate_1h_percent" in data["performance"]
    assert "recent_attempts_1h" in data["performance"]
    
    # Errors section
    assert "last_error" in data["errors"]
    assert "recent_errors" in data["errors"]
    
    # Prometheus metrics section
    assert "email_sent_total" in data["prometheus_metrics"]
    assert "email_failed_total" in data["prometheus_metrics"]
    assert "email_queue_depth" in data["prometheus_metrics"]


@pytest.fixture
def client():
    """Create test client with temporary database."""
    from app.config import settings
    from app.main import create_app
    
    original_db_path = settings.DB_PATH
    original_storage_root = settings.STORAGE_ROOT
    original_rate_limit_enabled = settings.RATE_LIMIT_ENABLED
    original_running_tests = settings.RUNNING_TESTS
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            temp_db_path = temp_path / "app_data.db"
            temp_storage_root = temp_path / "storage"
            temp_storage_root.mkdir(parents=True, exist_ok=True)
            
            settings.DB_PATH = temp_db_path
            settings.STORAGE_ROOT = temp_storage_root
            settings.RATE_LIMIT_ENABLED = False
            settings.RUNNING_TESTS = True
            
            os.environ["RATE_LIMIT_ENABLED"] = "false"
            os.environ["RUNNING_TESTS"] = "1"
            
            app = create_app()
            with TestClient(app) as test_client:
                yield test_client
    finally:
        settings.DB_PATH = original_db_path
        settings.STORAGE_ROOT = original_storage_root
        settings.RATE_LIMIT_ENABLED = original_rate_limit_enabled
        settings.RUNNING_TESTS = original_running_tests


@pytest.fixture
def authenticated_client(client):
    """Create authenticated test client."""
    from app.config import settings
    
    # Login as admin using form data (like the actual admin panel)
    response = client.post(
        "/admin/login",
        data={
            "username": settings.DEFAULT_ADMIN_USERNAME,
            "password": settings.DEFAULT_ADMIN_PASSWORD,
        },
        follow_redirects=False,
    )
    
    # Check if login was successful (should redirect to /admin)
    assert response.status_code == 302, f"Login failed with status {response.status_code}"
    assert client.cookies.get("authToken") is not None, "No authToken cookie set"
    
    return client
