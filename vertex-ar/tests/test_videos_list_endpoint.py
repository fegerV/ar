"""
Simple tests for the video list endpoint that don't depend on complex fixtures.
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
    
    db_path.unlink(missing_ok=True)


class TestVideosListDatabaseMethod:
    """Test the database method for listing videos."""
    
    def test_method_exists(self, temp_db):
        """Test that the list_videos_for_schedule method exists."""
        assert hasattr(temp_db, 'list_videos_for_schedule')
        assert callable(temp_db.list_videos_for_schedule)
    
    def test_empty_database(self, temp_db):
        """Test listing videos from empty database."""
        videos = temp_db.list_videos_for_schedule()
        assert isinstance(videos, list)
        assert len(videos) == 0
    
    def test_with_sample_data(self, temp_db):
        """Test with sample data."""
        # Create company (default one is created automatically)
        company_id = "vertex-ar-default"
        
        # Create client
        client_id = "test-client"
        temp_db.create_client(client_id, "+1234567890", "Test Client", company_id)
        
        # Create portrait
        portrait_id = "test-portrait"
        temp_db.create_portrait(
            portrait_id,
            client_id,
            "test/image.jpg",
            "test.fset",
            "test.fset3",
            "test.iset",
            "http://test.com/portrait"
        )
        
        # Create video
        video_id = "test-video"
        temp_db.create_video(
            video_id,
            portrait_id,
            "test/video.mp4",
            is_active=True
        )
        
        # Update video schedule
        temp_db.update_video_schedule(
            video_id,
            start_datetime="2025-01-01T00:00:00",
            end_datetime="2025-12-31T23:59:59",
            rotation_type="sequential",
            status="active"
        )
        
        # Test list all videos
        videos = temp_db.list_videos_for_schedule()
        assert len(videos) == 1
        assert videos[0]['id'] == video_id
        assert videos[0]['status'] == 'active'
        assert videos[0]['rotation_type'] == 'sequential'
        
        # Test filter by company
        videos_by_company = temp_db.list_videos_for_schedule(company_id=company_id)
        assert len(videos_by_company) == 1
        
        # Test filter by status
        active_videos = temp_db.list_videos_for_schedule(status="active")
        assert len(active_videos) == 1
        
        inactive_videos = temp_db.list_videos_for_schedule(status="inactive")
        assert len(inactive_videos) == 0
        
        # Test filter by rotation type
        sequential_videos = temp_db.list_videos_for_schedule(rotation_type="sequential")
        assert len(sequential_videos) == 1
        
        cyclic_videos = temp_db.list_videos_for_schedule(rotation_type="cyclic")
        assert len(cyclic_videos) == 0
        
        # Test multiple filters
        filtered_videos = temp_db.list_videos_for_schedule(
            company_id=company_id,
            status="active",
            rotation_type="sequential"
        )
        assert len(filtered_videos) == 1
    
    def test_returns_all_fields(self, temp_db):
        """Test that the method returns all required fields."""
        # Create company (default one is created automatically)
        company_id = "vertex-ar-default"
        
        # Create client
        client_id = "test-client"
        temp_db.create_client(client_id, "+1234567890", "Test Client", company_id)
        
        # Create portrait
        portrait_id = "test-portrait"
        temp_db.create_portrait(
            portrait_id,
            client_id,
            "test/image.jpg",
            "test.fset",
            "test.fset3",
            "test.iset",
            "http://test.com/portrait"
        )
        
        # Create video with all fields
        video_id = "test-video"
        temp_db.create_video(
            video_id,
            portrait_id,
            "test/video.mp4",
            is_active=True,
            video_preview_path="test/preview.jpg",
            description="Test video",
            file_size_mb=100
        )
        
        # Get videos
        videos = temp_db.list_videos_for_schedule()
        assert len(videos) == 1
        
        video = videos[0]
        # Check all required fields exist
        required_fields = [
            'id', 'portrait_id', 'video_path', 'is_active', 'created_at',
            'status', 'rotation_type', 'start_datetime', 'end_datetime',
            'file_size_mb', 'description', 'video_preview_path'
        ]
        for field in required_fields:
            assert field in video, f"Field '{field}' missing from video record"
