"""
Integration tests for the video schedule endpoint.
Tests the /videos GET endpoint for listing videos with scheduling filters.
"""
import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from app.main import create_app
from app.database import Database


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)
    
    yield db_path
    
    db_path.unlink(missing_ok=True)


@pytest.fixture
def test_app_with_data(temp_db):
    """Create a test FastAPI app with test data."""
    with patch.dict('os.environ', {
        'RUNNING_TESTS': '1',
        'RATE_LIMIT_ENABLED': 'false',
        'CORS_ORIGINS': 'http://localhost:8000'
    }):
        app = create_app()
        
        db = Database(temp_db)
        app.state.database = db
        
        from app.auth import TokenManager, AuthSecurityManager
        app.state.tokens = TokenManager(session_timeout_minutes=30)
        app.state.auth_security = AuthSecurityManager(max_attempts=5, lockout_minutes=15)
        
        # Create test data
        company_id = "test-company"
        db.create_company(company_id, "Test Company", "local", None)
        
        client_id = "test-client"
        db.create_client(client_id, "+1234567890", "Test Client", company_id, None)
        
        portrait_id = "test-portrait"
        db.create_portrait(
            portrait_id=portrait_id,
            client_id=client_id,
            image_path="test/image.jpg",
            marker_fset="test.fset",
            marker_fset3="test.fset3",
            marker_iset="test.iset",
            permanent_link="http://test.com/portrait",
            qr_code=None,
            image_preview_path=None,
            folder_id=None
        )
        
        # Create videos with different statuses and rotation types
        video1_id = "video-1"
        db.create_video(
            video_id=video1_id,
            portrait_id=portrait_id,
            video_path="test/video1.mp4",
            is_active=True,
            video_preview_path=None,
            description="Active video",
            file_size_mb=10
        )
        db.update_video_schedule(
            video_id=video1_id,
            start_datetime="2025-01-01T00:00:00",
            end_datetime="2025-12-31T23:59:59",
            rotation_type="sequential",
            status="active"
        )
        
        video2_id = "video-2"
        db.create_video(
            video_id=video2_id,
            portrait_id=portrait_id,
            video_path="test/video2.mp4",
            is_active=False,
            video_preview_path=None,
            description="Inactive video",
            file_size_mb=15
        )
        db.update_video_schedule(
            video_id=video2_id,
            start_datetime="2025-06-01T00:00:00",
            end_datetime="2025-12-31T23:59:59",
            rotation_type="cyclic",
            status="inactive"
        )
        
        video3_id = "video-3"
        db.create_video(
            video_id=video3_id,
            portrait_id=portrait_id,
            video_path="test/video3.mp4",
            is_active=False,
            video_preview_path=None,
            description="Archived video",
            file_size_mb=20
        )
        db.update_video_schedule(
            video_id=video3_id,
            start_datetime="2024-01-01T00:00:00",
            end_datetime="2024-12-31T23:59:59",
            rotation_type="none",
            status="archived"
        )
        
        return app, db, {
            'company_id': company_id,
            'client_id': client_id,
            'portrait_id': portrait_id,
            'video1_id': video1_id,
            'video2_id': video2_id,
            'video3_id': video3_id,
        }


@pytest.fixture
def client_with_data(test_app_with_data):
    """Create a test client with pre-populated data."""
    app, db, data = test_app_with_data
    return TestClient(app), data


class TestVideosScheduleEndpoint:
    """Test the GET /videos endpoint for schedule management."""
    
    def test_database_method_exists(self, temp_db):
        """Test that the list_videos_for_schedule method exists in database."""
        db = Database(temp_db)
        assert hasattr(db, 'list_videos_for_schedule')
        assert callable(db.list_videos_for_schedule)
    
    def test_database_method_no_filters(self, temp_db):
        """Test database method returns all videos without filters."""
        db = Database(temp_db)
        videos = db.list_videos_for_schedule()
        assert isinstance(videos, list)
        assert len(videos) == 0  # New database has no videos
    
    def test_database_method_with_company_filter(self, test_app_with_data):
        """Test database method filters by company."""
        app, db, data = test_app_with_data
        
        videos = db.list_videos_for_schedule(company_id=data['company_id'])
        assert len(videos) == 3  # All 3 test videos belong to this company
        
        videos = db.list_videos_for_schedule(company_id="nonexistent-company")
        assert len(videos) == 0
    
    def test_database_method_with_status_filter(self, test_app_with_data):
        """Test database method filters by status."""
        app, db, data = test_app_with_data
        
        active_videos = db.list_videos_for_schedule(status="active")
        assert len(active_videos) == 1
        assert active_videos[0]['id'] == data['video1_id']
        
        inactive_videos = db.list_videos_for_schedule(status="inactive")
        assert len(inactive_videos) == 1
        assert inactive_videos[0]['id'] == data['video2_id']
        
        archived_videos = db.list_videos_for_schedule(status="archived")
        assert len(archived_videos) == 1
        assert archived_videos[0]['id'] == data['video3_id']
    
    def test_database_method_with_rotation_type_filter(self, test_app_with_data):
        """Test database method filters by rotation type."""
        app, db, data = test_app_with_data
        
        sequential_videos = db.list_videos_for_schedule(rotation_type="sequential")
        assert len(sequential_videos) == 1
        assert sequential_videos[0]['id'] == data['video1_id']
        
        cyclic_videos = db.list_videos_for_schedule(rotation_type="cyclic")
        assert len(cyclic_videos) == 1
        assert cyclic_videos[0]['id'] == data['video2_id']
        
        none_videos = db.list_videos_for_schedule(rotation_type="none")
        assert len(none_videos) == 1
        assert none_videos[0]['id'] == data['video3_id']
    
    def test_database_method_with_multiple_filters(self, test_app_with_data):
        """Test database method with multiple filters."""
        app, db, data = test_app_with_data
        
        videos = db.list_videos_for_schedule(
            company_id=data['company_id'],
            status="active",
            rotation_type="sequential"
        )
        assert len(videos) == 1
        assert videos[0]['id'] == data['video1_id']
        
        videos = db.list_videos_for_schedule(
            company_id=data['company_id'],
            status="active",
            rotation_type="cyclic"
        )
        assert len(videos) == 0  # No videos match these criteria
    
    def test_database_method_returns_correct_fields(self, test_app_with_data):
        """Test that database method returns all required fields."""
        app, db, data = test_app_with_data
        
        videos = db.list_videos_for_schedule()
        assert len(videos) > 0
        
        video = videos[0]
        assert 'id' in video
        assert 'portrait_id' in video
        assert 'video_path' in video
        assert 'is_active' in video
        assert 'created_at' in video
        assert 'status' in video
        assert 'rotation_type' in video
        assert 'start_datetime' in video
        assert 'end_datetime' in video
    
    def test_endpoint_requires_authentication(self, client_with_data):
        """Test that the endpoint requires authentication."""
        client, data = client_with_data
        
        response = client.get("/videos")
        assert response.status_code == 401
    
    def test_endpoint_with_mock_admin(self, client_with_data):
        """Test endpoint with mocked admin authentication."""
        client, data = client_with_data
        
        with patch('app.api.videos.require_admin') as mock_require_admin:
            mock_require_admin.return_value = "test-admin"
            
            response = client.get("/videos")
            assert response.status_code == 200
            
            videos = response.json()
            assert isinstance(videos, list)
            assert len(videos) == 3
    
    def test_endpoint_filters_by_company(self, client_with_data):
        """Test endpoint filters by company ID."""
        client, data = client_with_data
        
        with patch('app.api.videos.require_admin') as mock_require_admin:
            mock_require_admin.return_value = "test-admin"
            
            response = client.get(f"/videos?company_id={data['company_id']}")
            assert response.status_code == 200
            
            videos = response.json()
            assert len(videos) == 3
    
    def test_endpoint_filters_by_status(self, client_with_data):
        """Test endpoint filters by status."""
        client, data = client_with_data
        
        with patch('app.api.videos.require_admin') as mock_require_admin:
            mock_require_admin.return_value = "test-admin"
            
            response = client.get("/videos?status=active")
            assert response.status_code == 200
            
            videos = response.json()
            assert len(videos) == 1
            assert videos[0]['id'] == data['video1_id']
    
    def test_endpoint_filters_by_rotation_type(self, client_with_data):
        """Test endpoint filters by rotation type."""
        client, data = client_with_data
        
        with patch('app.api.videos.require_admin') as mock_require_admin:
            mock_require_admin.return_value = "test-admin"
            
            response = client.get("/videos?rotation_type=cyclic")
            assert response.status_code == 200
            
            videos = response.json()
            assert len(videos) == 1
            assert videos[0]['id'] == data['video2_id']
    
    def test_endpoint_with_multiple_filters(self, client_with_data):
        """Test endpoint with multiple query parameters."""
        client, data = client_with_data
        
        with patch('app.api.videos.require_admin') as mock_require_admin:
            mock_require_admin.return_value = "test-admin"
            
            response = client.get(
                f"/videos?company_id={data['company_id']}&status=inactive&rotation_type=cyclic"
            )
            assert response.status_code == 200
            
            videos = response.json()
            assert len(videos) == 1
            assert videos[0]['id'] == data['video2_id']
    
    def test_endpoint_returns_correct_response_structure(self, client_with_data):
        """Test that endpoint returns proper VideoResponse structure."""
        client, data = client_with_data
        
        with patch('app.api.videos.require_admin') as mock_require_admin:
            mock_require_admin.return_value = "test-admin"
            
            response = client.get("/videos")
            assert response.status_code == 200
            
            videos = response.json()
            assert len(videos) > 0
            
            video = videos[0]
            assert 'id' in video
            assert 'portrait_id' in video
            assert 'video_path' in video
            assert 'is_active' in video
            assert 'created_at' in video
            assert 'status' in video
            assert 'rotation_type' in video
            assert 'start_datetime' in video
            assert 'end_datetime' in video
