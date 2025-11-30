"""
Tests for the database module.
"""
import pytest
import tempfile
from pathlib import Path
from app.database import Database


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)
    
    db = Database(db_path)
    yield db
    
    # Cleanup
    db_path.unlink(missing_ok=True)


class TestDatabase:
    """Test cases for Database class."""
    
    def test_initialise_schema(self, temp_db):
        """Test database schema initialization."""
        # Should not raise any exceptions
        assert temp_db.path.exists()
        
        # Check if tables exist
        cursor = temp_db._execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'users', 'ar_content', 'clients', 'portraits', 'videos'
        ]
        for table in expected_tables:
            assert table in tables
    
    def test_user_profile_operations(self, temp_db):
        """Test user profile management operations."""
        # Test that get_user works for existing admin users
        # Note: User creation is handled by ensure_admin_user, not create_user
        # This test focuses on profile management functionality
        
        # Create admin user using ensure_admin_user
        temp_db.ensure_admin_user(
            "testadmin",
            "hashed_password",
            email="admin@example.com",
            full_name="Test Admin"
        )
        
        # Get user
        user = temp_db.get_user("testadmin")
        assert user is not None
        assert user["username"] == "testadmin"
        assert user["hashed_password"] == "hashed_password"
        assert user["is_admin"] == 1
        assert user["is_active"] == 1
    
    def test_ensure_admin_user(self, temp_db):
        """Test ensuring default admin user creation and updates."""
        temp_db.ensure_admin_user(
            "superar",
            "initial_hash",
            email="admin@example.com",
            full_name="Super Admin",
        )
        user = temp_db.get_user("superar")
        assert user is not None
        assert user["hashed_password"] == "initial_hash"
        assert user["is_admin"] == 1
        assert user["is_active"] == 1
        assert user["email"] == "admin@example.com"
        assert user["full_name"] == "Super Admin"
    
        temp_db.ensure_admin_user(
            "superar",
            "updated_hash",
            email="new@example.com",
            full_name="Updated Admin",
        )
        updated_user = temp_db.get_user("superar")
        assert updated_user["hashed_password"] == "updated_hash"
        assert updated_user["email"] == "new@example.com"
        assert updated_user["full_name"] == "Updated Admin"
        assert updated_user["is_admin"] == 1
        assert updated_user["is_active"] == 1
    
    def test_client_operations(self, temp_db):
        """Test client CRUD operations."""
        # Create client
        client = temp_db.create_client("client1", "+1234567890", "John Doe")
        
        assert client["id"] == "client1"
        assert client["phone"] == "+1234567890"
        assert client["name"] == "John Doe"
        assert "created_at" in client
        
        # Get client
        retrieved = temp_db.get_client("client1")
        assert retrieved == client
        
        # Get client by phone
        by_phone = temp_db.get_client_by_phone("+1234567890")
        assert by_phone == client
        
        # Search clients
        search_results = temp_db.search_clients("123")
        assert len(search_results) == 1
        assert search_results[0] == client
        
        # List all clients
        all_clients = temp_db.list_clients()
        assert len(all_clients) == 1
        assert all_clients[0] == client
        
        # Update client
        updated = temp_db.update_client("client1", name="Jane Doe")
        assert updated is True
        
        updated_client = temp_db.get_client("client1")
        assert updated_client["name"] == "Jane Doe"
        assert updated_client["phone"] == "+1234567890"  # unchanged
        
        # Delete client
        deleted = temp_db.delete_client("client1")
        assert deleted is True
        
        # Verify deletion
        assert temp_db.get_client("client1") is None
    
    def test_portrait_operations(self, temp_db):
        """Test portrait CRUD operations."""
        # First create a client
        temp_db.create_client("client1", "+1234567890", "John Doe")
        
        # Create portrait
        portrait = temp_db.create_portrait(
            "portrait1",
            "client1",
            "/path/to/image.jpg",
            "/path/to/marker.fset",
            "/path/to/marker.fset3",
            "/path/to/marker.iset",
            "permanent_link_123"
        )
        
        assert portrait["id"] == "portrait1"
        assert portrait["client_id"] == "client1"
        assert portrait["permanent_link"] == "permanent_link_123"
        assert portrait["view_count"] == 0
        
        # Get portrait
        retrieved = temp_db.get_portrait("portrait1")
        assert retrieved == portrait
        
        # Get portrait by link
        by_link = temp_db.get_portrait_by_link("permanent_link_123")
        assert by_link == portrait
        
        # List portraits
        all_portraits = temp_db.list_portraits()
        assert len(all_portraits) == 1
        assert all_portraits[0] == portrait
        
        # List portraits for specific client
        client_portraits = temp_db.list_portraits("client1")
        assert len(client_portraits) == 1
        assert client_portraits[0] == portrait
        
        # Increment view count
        temp_db.increment_portrait_views("portrait1")
        viewed = temp_db.get_portrait("portrait1")
        assert viewed["view_count"] == 1
        
        # Delete portrait
        deleted = temp_db.delete_portrait("portrait1")
        assert deleted is True
        
        # Verify deletion
        assert temp_db.get_portrait("portrait1") is None
    
    def test_video_operations(self, temp_db):
        """Test video CRUD operations."""
        # First create client and portrait
        temp_db.create_client("client1", "+1234567890", "John Doe")
        temp_db.create_portrait(
            "portrait1",
            "client1",
            "/path/to/image.jpg",
            "/path/to/marker.fset",
            "/path/to/marker.fset3",
            "/path/to/marker.iset",
            "permanent_link_123"
        )
        
        # Create video
        video = temp_db.create_video(
            "video1",
            "portrait1",
            "/path/to/video.mp4",
            is_active=False
        )
        
        assert video["id"] == "video1"
        assert video["portrait_id"] == "portrait1"
        assert video["is_active"] == 0
        assert video["video_path"] == "/path/to/video.mp4"
        
        # Get video
        retrieved = temp_db.get_video("video1")
        assert retrieved == video
        
        # List videos for portrait
        portrait_videos = temp_db.list_videos("portrait1")
        assert len(portrait_videos) == 1
        assert portrait_videos[0] == video
        
        # No active video yet
        assert temp_db.get_active_video("portrait1") is None
        
        # Set video as active
        activated = temp_db.set_active_video("video1", "portrait1")
        assert activated is True
        
        # Get active video
        active = temp_db.get_active_video("portrait1")
        assert active is not None
        assert active["id"] == "video1"
        assert active["is_active"] == 1
        
        # Create another video
        video2 = temp_db.create_video(
            "video2",
            "portrait1",
            "/path/to/video2.mp4",
            is_active=False
        )
        
        # Set second video as active (should deactivate first)
        temp_db.set_active_video("video2", "portrait1")
        
        # Now video2 should be active, video1 inactive
        active_now = temp_db.get_active_video("portrait1")
        assert active_now["id"] == "video2"
        
        video1_now = temp_db.get_video("video1")
        assert video1_now["is_active"] == 0
        
        video2_now = temp_db.get_video("video2")
        assert video2_now["is_active"] == 1
        
        # Delete video
        deleted = temp_db.delete_video("video1")
        assert deleted is True
        
        # Verify deletion
        assert temp_db.get_video("video1") is None
    
    def test_ar_content_operations(self, temp_db):
        """Test AR content CRUD operations."""
        # First create a user
        temp_db.create_user("testuser", "hashed_password", is_admin=True)
        
        # Create AR content
        content = temp_db.create_ar_content(
            "content1",
            "testuser",
            "/path/to/image.jpg",
            "/path/to/video.mp4",
            "/path/to/marker.fset",
            "/path/to/marker.fset3",
            "/path/to/marker.iset",
            "http://example.com/ar/content1",
            "qr_code_data",
            "/path/to/image_preview.jpg",
            "/path/to/video_preview.jpg"
        )
        
        assert content["id"] == "content1"
        assert content["username"] == "testuser"
        assert content["ar_url"] == "http://example.com/ar/content1"
        
        # Get AR content
        retrieved = temp_db.get_ar_content("content1")
        assert retrieved == content
        
        # List AR content
        all_content = temp_db.list_ar_content()
        assert len(all_content) == 1
        assert all_content[0] == content
        
        # List AR content for specific user
        user_content = temp_db.list_ar_content("testuser")
        assert len(user_content) == 1
        assert user_content[0] == content
        
        # Increment view count
        temp_db.increment_view_count("content1")
        viewed = temp_db.get_ar_content("content1")
        assert viewed["view_count"] == 1
        
        # Increment click count
        temp_db.increment_click_count("content1")
        clicked = temp_db.get_ar_content("content1")
        assert clicked["click_count"] == 1
        
        # Delete AR content
        deleted = temp_db.delete_ar_content("content1")
        assert deleted is True
        
        # Verify deletion
        assert temp_db.get_ar_content("content1") is None
    
    def test_monitoring_settings_operations(self, temp_db):
        """Test monitoring settings persistence and retrieval."""
        # Get initial settings (should be auto-seeded)
        settings = temp_db.get_monitoring_settings()
        
        # Verify default settings exist
        assert settings is not None
        assert settings["cpu_threshold"] == 80.0
        assert settings["memory_threshold"] == 85.0
        assert settings["disk_threshold"] == 90.0
        assert settings["health_check_interval"] == 60
        assert settings["consecutive_failures"] == 3
        assert settings["dedup_window_seconds"] == 300
        assert settings["health_check_cooldown_seconds"] == 30
        assert settings["alert_recovery_minutes"] == 60
        assert settings["is_active"] == 1
        
        # Update some thresholds
        updated = temp_db.update_monitoring_settings(
            cpu_threshold=85.0,
            memory_threshold=90.0,
            disk_threshold=95.0
        )
        assert updated is True
        
        # Verify updates
        new_settings = temp_db.get_monitoring_settings()
        assert new_settings["cpu_threshold"] == 85.0
        assert new_settings["memory_threshold"] == 90.0
        assert new_settings["disk_threshold"] == 95.0
        # Other fields unchanged
        assert new_settings["health_check_interval"] == 60
        assert new_settings["consecutive_failures"] == 3
        
        # Update concurrency settings
        updated = temp_db.update_monitoring_settings(
            max_runtime_seconds=120,
            health_check_cooldown_seconds=45,
            alert_recovery_minutes=90
        )
        assert updated is True
        
        # Verify concurrency settings
        final_settings = temp_db.get_monitoring_settings()
        assert final_settings["max_runtime_seconds"] == 120
        assert final_settings["health_check_cooldown_seconds"] == 45
        assert final_settings["alert_recovery_minutes"] == 90
        # Thresholds still updated
        assert final_settings["cpu_threshold"] == 85.0
        assert final_settings["memory_threshold"] == 90.0
        assert final_settings["disk_threshold"] == 95.0
    
    def test_monitoring_settings_comprehensive_update(self, temp_db):
        """Test updating all monitoring settings at once."""
        # Get initial settings
        initial = temp_db.get_monitoring_settings()
        assert initial is not None
        
        # Update all fields
        updated = temp_db.update_monitoring_settings(
            cpu_threshold=75.0,
            memory_threshold=80.0,
            disk_threshold=85.0,
            health_check_interval=120,
            consecutive_failures=5,
            dedup_window_seconds=600,
            max_runtime_seconds=180,
            health_check_cooldown_seconds=60,
            alert_recovery_minutes=120
        )
        assert updated is True
        
        # Verify all updates
        new_settings = temp_db.get_monitoring_settings()
        assert new_settings["cpu_threshold"] == 75.0
        assert new_settings["memory_threshold"] == 80.0
        assert new_settings["disk_threshold"] == 85.0
        assert new_settings["health_check_interval"] == 120
        assert new_settings["consecutive_failures"] == 5
        assert new_settings["dedup_window_seconds"] == 600
        assert new_settings["max_runtime_seconds"] == 180
        assert new_settings["health_check_cooldown_seconds"] == 60
        assert new_settings["alert_recovery_minutes"] == 120
        
        # Verify timestamp was updated
        assert new_settings["updated_at"] != initial["updated_at"]
    
    def test_monitoring_settings_validation(self, temp_db):
        """Test monitoring settings with edge cases."""
        # Update with None values (should be ignored)
        updated = temp_db.update_monitoring_settings(
            cpu_threshold=None,
            memory_threshold=None
        )
        # Should return False since no valid updates
        assert updated is False
        
        # Settings should remain unchanged
        settings = temp_db.get_monitoring_settings()
        assert settings["cpu_threshold"] == 80.0  # default
        assert settings["memory_threshold"] == 85.0  # default
        
        # Update with extreme but valid values
        updated = temp_db.update_monitoring_settings(
            cpu_threshold=99.9,
            memory_threshold=1.0,
            max_runtime_seconds=1,
            health_check_cooldown_seconds=0
        )
        assert updated is True
        
        # Verify extreme values were stored
        settings = temp_db.get_monitoring_settings()
        assert settings["cpu_threshold"] == 99.9
        assert settings["memory_threshold"] == 1.0
        assert settings["max_runtime_seconds"] == 1
        assert settings["health_check_cooldown_seconds"] == 0