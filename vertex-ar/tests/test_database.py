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
    
    def test_user_operations(self, temp_db):
        """Test user CRUD operations."""
        # Create user
        temp_db.create_user("testuser", "hashed_password", is_admin=True)
        
        # Get user
        user = temp_db.get_user("testuser")
        assert user is not None
        assert user["username"] == "testuser"
        assert user["hashed_password"] == "hashed_password"
        assert user["is_admin"] == 1
        
        # Duplicate user should raise error
        with pytest.raises(ValueError, match="user_already_exists"):
            temp_db.create_user("testuser", "another_password")
    
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