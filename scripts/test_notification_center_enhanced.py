"""
Tests for enhanced notification center functionality.
"""
import pytest
import asyncio
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Add vertex-ar to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'vertex-ar'))

from vertex_ar.notifications import (
    NotificationCreate,
    NotificationFilter,
    NotificationPriority,
    NotificationStatus,
    create_notification,
    get_notifications,
    get_notification_groups,
    export_notifications_to_csv,
    export_notifications_to_json,
    update_notification_priority,
    bulk_update_notifications_status,
    get_notification_statistics
)
from vertex_ar.notification_integrations import (
    NotificationIntegrator,
    WebhookEvent,
    notification_integrator
)
from vertex_ar.notification_sync import (
    NotificationSyncManager,
    NotificationAggregator,
    notification_sync_manager,
    notification_aggregator
)


class TestNotificationPriority:
    """Test notification priority functionality."""
    
    def test_priority_enum(self):
        """Test priority enum values."""
        assert NotificationPriority.IGNORE.value == "ignore"
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.MEDIUM.value == "medium"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.CRITICAL.value == "critical"


class TestNotificationFilter:
    """Test notification filtering."""
    
    def test_filter_creation(self):
        """Test filter model creation."""
        filter_data = NotificationFilter(
            priority=NotificationPriority.HIGH,
            status=NotificationStatus.NEW,
            search="test"
        )
        
        assert filter_data.priority == NotificationPriority.HIGH
        assert filter_data.status == NotificationStatus.NEW
        assert filter_data.search == "test"


@pytest.mark.asyncio
class TestNotificationIntegrations:
    """Test notification integrations."""
    
    async def test_webhook_event_creation(self):
        """Test webhook event creation."""
        event = WebhookEvent(
            url="https://example.com/webhook",
            payload={"test": "data"},
            headers={"Authorization": "Bearer token"}
        )
        
        assert event.url == "https://example.com/webhook"
        assert event.payload["test"] == "data"
        assert event.headers["Authorization"] == "Bearer token"
        assert event.status.value == "pending"
        assert event.attempts == 0
    
    async def test_webhook_delivery_success(self):
        """Test successful webhook delivery."""
        integrator = NotificationIntegrator()
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await integrator.send_webhook(
                "https://example.com/webhook",
                {"test": "data"}
            )
            
            assert result is True
            assert len(integrator.webhook_queue) == 1
            assert integrator.webhook_queue[0].status.value == "delivered"
    
    async def test_webhook_delivery_failure(self):
        """Test webhook delivery failure."""
        integrator = NotificationIntegrator()
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value="Server Error")
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await integrator.send_webhook(
                "https://example.com/webhook",
                {"test": "data"}
            )
            
            assert result is False
    
    async def test_notification_routing(self):
        """Test notification routing through integrations."""
        integrator = NotificationIntegrator()
        
        # Mock handlers
        integrator.integration_handlers["test"] = AsyncMock(return_value=True)
        
        notification_data = {
            "title": "Test Notification",
            "message": "Test message"
        }
        
        results = await integrator.route_notification(
            notification_data,
            ["test"],
            "medium"
        )
        
        assert "test" in results
        assert results["test"] is True


@pytest.mark.asyncio
class TestNotificationSync:
    """Test notification synchronization."""
    
    async def test_sync_manager_initialization(self):
        """Test sync manager initialization."""
        sync_manager = NotificationSyncManager()
        
        assert sync_manager.running is False
        assert sync_manager.sync_interval == 300  # 5 minutes
        assert sync_manager.cleanup_interval == 3600  # 1 hour
        assert sync_manager.retention_days == 30
    
    async def test_aggregator_rule_addition(self):
        """Test adding aggregation rules."""
        aggregator = NotificationAggregator()
        
        aggregator.add_aggregation_rule(
            name="test_rule",
            pattern="test pattern",
            max_count=5,
            time_window=1800
        )
        
        assert "test_rule" in aggregator.aggregation_rules
        rule = aggregator.aggregation_rules["test_rule"]
        assert rule["pattern"] == "test pattern"
        assert rule["max_count"] == 5
        assert rule["time_window"] == 1800
    
    def test_should_aggregate(self):
        """Test aggregation decision logic."""
        aggregator = NotificationAggregator()
        
        # Add rule
        aggregator.add_aggregation_rule(
            name="cpu_high",
            pattern="high cpu",
            max_count=3,
            time_window=3600
        )
        
        # Test notification
        notification_data = {
            "title": "High CPU Usage Alert",
            "message": "CPU usage is above threshold"
        }
        
        # Should aggregate since pattern matches
        rule_name = aggregator.should_aggregate(notification_data, [])
        assert rule_name == "cpu_high"
        
        # Should not aggregate for different pattern
        notification_data2 = {
            "title": "Memory Usage Alert",
            "message": "Memory usage is high"
        }
        
        rule_name2 = aggregator.should_aggregate(notification_data2, [])
        assert rule_name2 is None


class TestNotificationFunctions:
    """Test notification core functions."""
    
    @patch('notifications.get_db')
    def test_create_notification_with_priority(self, mock_get_db):
        """Test creating notification with priority."""
        mock_db = Mock()
        mock_get_db.return_value.__next__.return_value = mock_db
        
        # Mock the database operations
        mock_notification = Mock()
        mock_notification.id = 1
        mock_notification.title = "Test"
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        with patch('notifications.Notification', return_value=mock_notification):
            notification_data = NotificationCreate(
                title="Test Notification",
                message="Test message",
                priority=NotificationPriority.HIGH,
                source="test_service",
                service_name="test_module"
            )
            
            result = create_notification(mock_db, notification_data)
            assert result is not None
    
    @patch('notifications.get_db')
    def test_get_notifications_with_filters(self, mock_get_db):
        """Test getting notifications with filters."""
        mock_db = Mock()
        mock_get_db.return_value.__next__.return_value = mock_db
        
        # Mock query chain
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []
        
        filters = NotificationFilter(
            priority=NotificationPriority.HIGH,
            status=NotificationStatus.NEW
        )
        
        result = get_notifications(mock_db, filters, limit=10)
        assert isinstance(result, list)
    
    @patch('notifications.get_db')
    def test_export_csv(self, mock_get_db):
        """Test CSV export functionality."""
        mock_db = Mock()
        mock_get_db.return_value.__next__.return_value = mock_db
        
        # Mock notification
        mock_notification = Mock()
        mock_notification.id = 1
        mock_notification.title = "Test"
        mock_notification.message = "Test message"
        mock_notification.user_id = "user1"
        mock_notification.notification_type = "info"
        mock_notification.priority = NotificationPriority.HIGH
        mock_notification.status = NotificationStatus.NEW
        mock_notification.is_read = False
        mock_notification.source = "test"
        mock_notification.service_name = "service"
        mock_notification.group_id = "group1"
        mock_notification.created_at = datetime.utcnow()
        mock_notification.expires_at = None
        mock_notification.processed_at = None
        
        with patch('notifications.get_notifications', return_value=[mock_notification]):
            csv_data = export_notifications_to_csv(mock_db, limit=1)
            
            assert csv_data is not None
            assert "ID,Title,Message" in csv_data
            assert "Test,Test message" in csv_data
    
    @patch('notifications.get_db')
    def test_export_json(self, mock_get_db):
        """Test JSON export functionality."""
        mock_db = Mock()
        mock_get_db.return_value.__next__.return_value = mock_db
        
        # Mock notification
        mock_notification = Mock()
        mock_notification.id = 1
        mock_notification.title = "Test"
        mock_notification.message = "Test message"
        mock_notification.user_id = "user1"
        mock_notification.notification_type = "info"
        mock_notification.priority = NotificationPriority.HIGH
        mock_notification.status = NotificationStatus.NEW
        mock_notification.is_read = False
        mock_notification.source = "test"
        mock_notification.service_name = "service"
        mock_notification.group_id = "group1"
        mock_notification.created_at = datetime.utcnow()
        mock_notification.expires_at = None
        mock_notification.processed_at = None
        mock_notification.event_data = None
        
        with patch('notifications.get_notifications', return_value=[mock_notification]):
            json_data = export_notifications_to_json(mock_db, limit=1)
            
            assert json_data is not None
            assert '"title": "Test"' in json_data
            assert '"priority": "high"' in json_data


@pytest.mark.asyncio
class TestNotificationStatistics:
    """Test notification statistics."""
    
    @patch('notifications.get_db')
    async def test_get_statistics(self, mock_get_db):
        """Test getting notification statistics."""
        mock_db = Mock()
        mock_get_db.return_value.__next__.return_value = mock_db
        
        # Mock query and count
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.count.return_value = 10
        
        # Mock group by queries
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.all.return_value = [
            (NotificationPriority.HIGH, 3),
            (NotificationPriority.MEDIUM, 7)
        ]
        
        stats = get_notification_statistics(mock_db)
        
        assert "total_count" in stats
        assert "by_priority" in stats
        assert "by_status" in stats
        assert "by_type" in stats
        assert stats["total_count"] == 10


class TestNotificationGroups:
    """Test notification grouping functionality."""
    
    @patch('notifications.get_db')
    def test_get_notification_groups(self, mock_get_db):
        """Test getting notification groups."""
        mock_db = Mock()
        mock_get_db.return_value.__next__.return_value = mock_db
        
        # Mock SQLAlchemy query result
        mock_row = Mock()
        mock_row.group_id = "test_group"
        mock_row.title = "Test Alert"
        mock_row.message = "Test message"
        mock_row.notification_type = "warning"
        mock_row.priority = NotificationPriority.HIGH
        mock_row.source = "monitoring"
        mock_row.service_name = "web"
        mock_row.count = 5
        mock_row.first_created_at = datetime.utcnow()
        mock_row.last_created_at = datetime.utcnow()
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_row]
        
        with patch('notifications.get_notification_groups') as mock_get_groups:
            mock_get_groups.return_value = []
            groups = get_notification_groups(mock_db, limit=10)
            assert isinstance(groups, list)


if __name__ == "__main__":
    pytest.main([__file__])