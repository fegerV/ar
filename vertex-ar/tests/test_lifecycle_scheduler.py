"""
Tests for the lifecycle scheduler functionality.
"""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import os

from app.database import Database
from app.project_lifecycle import ProjectLifecycleScheduler


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    # Remove the file so Database can create it fresh
    os.unlink(db_path)
    
    db = Database(Path(db_path))
    
    yield db
    
    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass


def test_calculate_lifecycle_status_active():
    """Test calculating lifecycle status for active portraits."""
    scheduler = ProjectLifecycleScheduler()
    
    # Test active (30 days remaining)
    future_date = datetime.utcnow() + timedelta(days=30)
    status = scheduler.calculate_lifecycle_status(future_date)
    assert status == 'active'


def test_calculate_lifecycle_status_expiring():
    """Test calculating lifecycle status for expiring portraits."""
    scheduler = ProjectLifecycleScheduler()
    
    # Test expiring (5 days remaining)
    future_date = datetime.utcnow() + timedelta(days=5)
    status = scheduler.calculate_lifecycle_status(future_date)
    assert status == 'expiring'


def test_calculate_lifecycle_status_archived():
    """Test calculating lifecycle status for archived portraits."""
    scheduler = ProjectLifecycleScheduler()
    
    # Test archived (past expiry)
    past_date = datetime.utcnow() - timedelta(days=1)
    status = scheduler.calculate_lifecycle_status(past_date)
    assert status == 'archived'


def test_should_send_7day_notification():
    """Test 7-day notification logic."""
    scheduler = ProjectLifecycleScheduler()
    
    # Portrait with 5 days remaining, no notification sent yet
    subscription_end = datetime.utcnow() + timedelta(days=5)
    portrait = {
        'id': 'test-id',
        'subscription_end': subscription_end.isoformat(),
        'notification_7days_sent': None
    }
    
    should_send = scheduler.should_send_7day_notification(portrait, subscription_end)
    assert should_send is True
    
    # Portrait with notification already sent
    portrait['notification_7days_sent'] = datetime.utcnow().isoformat()
    should_send = scheduler.should_send_7day_notification(portrait, subscription_end)
    assert should_send is False


def test_should_send_24hour_notification():
    """Test 24-hour notification logic."""
    scheduler = ProjectLifecycleScheduler()
    
    # Portrait with 12 hours remaining, no notification sent yet
    subscription_end = datetime.utcnow() + timedelta(hours=12)
    portrait = {
        'id': 'test-id',
        'subscription_end': subscription_end.isoformat(),
        'notification_24hours_sent': None
    }
    
    should_send = scheduler.should_send_24hour_notification(portrait, subscription_end)
    assert should_send is True
    
    # Portrait with notification already sent
    portrait['notification_24hours_sent'] = datetime.utcnow().isoformat()
    should_send = scheduler.should_send_24hour_notification(portrait, subscription_end)
    assert should_send is False


def test_should_send_expired_notification():
    """Test expired notification logic."""
    scheduler = ProjectLifecycleScheduler()
    
    # Portrait expired, no notification sent yet
    subscription_end = datetime.utcnow() - timedelta(days=1)
    portrait = {
        'id': 'test-id',
        'subscription_end': subscription_end.isoformat(),
        'notification_expired_sent': None
    }
    
    should_send = scheduler.should_send_expired_notification(portrait, subscription_end)
    assert should_send is True
    
    # Portrait with notification already sent
    portrait['notification_expired_sent'] = datetime.utcnow().isoformat()
    should_send = scheduler.should_send_expired_notification(portrait, subscription_end)
    assert should_send is False


def test_database_lifecycle_methods(temp_db):
    """Test database lifecycle methods."""
    import uuid
    
    # Create test company
    company_id = str(uuid.uuid4())
    temp_db.create_company(company_id, "Test Company")
    company = temp_db.get_company(company_id)
    assert company is not None
    
    # Create test client
    client_id = str(uuid.uuid4())
    client = temp_db.create_client(client_id, "1234567890", "Test Client", company_id)
    assert client is not None
    
    # Create test portrait with subscription_end
    portrait_id = str(uuid.uuid4())
    subscription_end = datetime.utcnow() + timedelta(days=5)
    
    portrait = temp_db.create_portrait(
        portrait_id=portrait_id,
        client_id=client_id,
        image_path="/test/image.jpg",
        marker_fset="/test/marker.fset",
        marker_fset3="/test/marker.fset3",
        marker_iset="/test/marker.iset",
        permanent_link=f"test-link-{portrait_id}"
    )
    
    # Set subscription_end
    temp_db._execute(
        "UPDATE portraits SET subscription_end = ? WHERE id = ?",
        (subscription_end.isoformat(), portrait_id)
    )
    
    # Test get_portraits_for_lifecycle_check
    portraits = temp_db.get_portraits_for_lifecycle_check()
    assert len(portraits) == 1
    assert portraits[0]['id'] == portrait_id
    
    # Test update_portrait_lifecycle_status
    success = temp_db.update_portrait_lifecycle_status(portrait_id, 'expiring')
    assert success is True
    
    portrait = temp_db.get_portrait(portrait_id)
    assert portrait['lifecycle_status'] == 'expiring'
    
    # Test record_lifecycle_notification
    success = temp_db.record_lifecycle_notification(portrait_id, '7days')
    assert success is True
    
    portrait = temp_db.get_portrait(portrait_id)
    assert portrait['notification_7days_sent'] is not None
    
    # Test reset_lifecycle_notifications
    success = temp_db.reset_lifecycle_notifications(portrait_id)
    assert success is True
    
    portrait = temp_db.get_portrait(portrait_id)
    assert portrait['notification_7days_sent'] is None
    assert portrait['notification_24hours_sent'] is None
    assert portrait['notification_expired_sent'] is None


def test_scheduler_config():
    """Test scheduler configuration."""
    scheduler = ProjectLifecycleScheduler()
    
    # Check default values
    assert scheduler.check_interval > 0
    assert isinstance(scheduler.enabled, bool)
    assert isinstance(scheduler.notifications_enabled, bool)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
