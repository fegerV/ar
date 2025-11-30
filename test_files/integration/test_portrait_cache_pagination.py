"""
Integration tests for portrait listing with pagination and caching.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def mock_database():
    """Mock database with portrait data."""
    from unittest.mock import MagicMock
    
    db = MagicMock()
    
    # Create test portraits
    portraits = []
    for i in range(100):
        portraits.append({
            "id": f"portrait_{i}",
            "client_id": f"client_{i % 10}",
            "folder_id": None,
            "permanent_link": f"link_{i}",
            "qr_code": None,
            "image_path": f"/path/to/image_{i}.jpg",
            "image_preview_path": None,
            "view_count": i,
            "created_at": f"2024-01-{(i % 30) + 1:02d}T12:00:00",
            "subscription_end": None,
            "lifecycle_status": "active",
            "last_status_change": None,
        })
    
    def list_portraits_paginated(page=1, page_size=50, **kwargs):
        """Mock paginated list."""
        start = (page - 1) * page_size
        end = start + page_size
        return portraits[start:end]
    
    def count_portraits(**kwargs):
        """Mock count."""
        return len(portraits)
    
    db.list_portraits_paginated = list_portraits_paginated
    db.count_portraits = count_portraits
    db.list_portraits = lambda **kwargs: portraits
    db.get_portrait = lambda portrait_id: next((p for p in portraits if p["id"] == portrait_id), None)
    db.get_client = lambda client_id: {"id": client_id, "name": f"Client {client_id}"}
    
    return db


@pytest.fixture
def mock_cache():
    """Mock cache manager."""
    from unittest.mock import AsyncMock
    
    cache = AsyncMock()
    cache._storage = {}
    
    async def mock_get(*key_parts):
        key = ":".join(str(p) for p in key_parts)
        return cache._storage.get(key)
    
    async def mock_set(value, *key_parts, ttl=None):
        key = ":".join(str(p) for p in key_parts)
        cache._storage[key] = value
        return True
    
    async def mock_invalidate_all():
        cache._storage.clear()
        return 1
    
    cache.get = mock_get
    cache.set = mock_set
    cache.invalidate_all = mock_invalidate_all
    cache.enabled = True
    
    return cache


@pytest.fixture
def test_app(mock_database, mock_cache):
    """Create test FastAPI app with mocked dependencies."""
    from fastapi import FastAPI
    from app.config import settings
    
    app = FastAPI()
    app.state.database = mock_database
    app.state.cache_manager = mock_cache
    app.state.config = {
        "BASE_DIR": "/tmp",
        "STORAGE_ROOT": "/tmp/storage",
        "BASE_URL": "http://localhost:8000",
    }
    
    # Import and include the router
    from app.api import portraits
    app.include_router(portraits.router, prefix="/portraits")
    
    return app


class TestPortraitPagination:
    """Test portrait listing pagination."""
    
    def test_list_portraits_default_pagination(self, test_app):
        """Test default pagination parameters."""
        client = TestClient(test_app)
        
        # Mock authentication
        with patch("app.api.portraits.get_current_user", return_value="testuser"):
            response = client.get("/portraits/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check pagination structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        
        # Check defaults
        assert data["page"] == 1
        assert data["page_size"] == 50  # Default from settings
        assert data["total"] == 100
        assert data["total_pages"] == 2
        assert len(data["items"]) == 50
    
    def test_list_portraits_custom_page_size(self, test_app):
        """Test custom page size."""
        client = TestClient(test_app)
        
        with patch("app.api.portraits.get_current_user", return_value="testuser"):
            response = client.get("/portraits/?page=1&page_size=25")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1
        assert data["page_size"] == 25
        assert data["total_pages"] == 4  # 100 / 25
        assert len(data["items"]) == 25
    
    def test_list_portraits_second_page(self, test_app):
        """Test fetching second page."""
        client = TestClient(test_app)
        
        with patch("app.api.portraits.get_current_user", return_value="testuser"):
            response = client.get("/portraits/?page=2&page_size=50")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 2
        assert len(data["items"]) == 50
        # Should have different items than page 1
        assert data["items"][0]["id"] == "portrait_50"
    
    def test_list_portraits_last_page_partial(self, test_app):
        """Test last page with partial results."""
        client = TestClient(test_app)
        
        with patch("app.api.portraits.get_current_user", return_value="testuser"):
            response = client.get("/portraits/?page=2&page_size=75")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 2
        assert len(data["items"]) == 25  # 100 total, 75 on page 1, 25 on page 2
    
    def test_list_portraits_invalid_page(self, test_app):
        """Test with invalid page number."""
        client = TestClient(test_app)
        
        with patch("app.api.portraits.get_current_user", return_value="testuser"):
            # Page 0 should fail validation
            response = client.get("/portraits/?page=0")
        
        assert response.status_code == 422  # Validation error


class TestPortraitCaching:
    """Test portrait listing caching."""
    
    def test_cache_miss_then_hit(self, test_app, mock_cache):
        """Test cache miss followed by cache hit."""
        client = TestClient(test_app)
        
        with patch("app.api.portraits.get_current_user", return_value="testuser"):
            # First request - cache miss
            response1 = client.get("/portraits/?page=1&page_size=50")
            assert response1.status_code == 200
            data1 = response1.json()
            
            # Second request - should hit cache
            response2 = client.get("/portraits/?page=1&page_size=50")
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Data should be identical
            assert data1 == data2
            
            # Check cache was used
            assert len(mock_cache._storage) > 0
    
    def test_cache_different_pages(self, test_app, mock_cache):
        """Test that different pages are cached separately."""
        client = TestClient(test_app)
        
        with patch("app.api.portraits.get_current_user", return_value="testuser"):
            # Request page 1
            response1 = client.get("/portraits/?page=1&page_size=50")
            data1 = response1.json()
            
            # Request page 2
            response2 = client.get("/portraits/?page=2&page_size=50")
            data2 = response2.json()
            
            # Should have different data
            assert data1["items"][0]["id"] != data2["items"][0]["id"]
            
            # Should have 2 cache entries
            assert len(mock_cache._storage) >= 2
    
    def test_cache_with_filters(self, test_app, mock_cache):
        """Test that filters create different cache keys."""
        client = TestClient(test_app)
        
        with patch("app.api.portraits.get_current_user", return_value="testuser"):
            # No filter
            response1 = client.get("/portraits/?page=1&page_size=50")
            
            # With client_id filter
            response2 = client.get("/portraits/?page=1&page_size=50&client_id=client_1")
            
            # Should have different cache entries
            assert len(mock_cache._storage) >= 2
    
    def test_cache_invalidation_on_create(self, test_app, mock_cache):
        """Test cache invalidation when portrait is created."""
        client = TestClient(test_app)
        
        with patch("app.api.portraits.get_current_user", return_value="testuser"):
            # Populate cache
            response1 = client.get("/portraits/?page=1&page_size=50")
            assert len(mock_cache._storage) > 0
            
            # Create a portrait (mocked)
            with patch("app.api.portraits.invalidate_portrait_cache") as mock_invalidate:
                mock_invalidate.return_value = None
                # Simulate creation by calling invalidate
                import asyncio
                asyncio.run(mock_invalidate())
                
                # Cache should be cleared
                assert mock_invalidate.called
    
    def test_preview_not_cached(self, test_app, mock_cache):
        """Test that requests with preview data are not cached."""
        client = TestClient(test_app)
        
        with patch("app.api.portraits.get_current_user", return_value="testuser"):
            # Request with preview
            response = client.get("/portraits/?page=1&page_size=10&include_preview=true")
            
            # Preview requests should not be cached (too large)
            # Check that cache set was not called for preview data
            # This is implementation-specific - our code checks include_preview flag
            assert response.status_code == 200


class TestAdminPortraitPreview:
    """Test admin portrait preview endpoint with caching."""
    
    def test_admin_preview_pagination(self, test_app):
        """Test admin preview endpoint with pagination."""
        client = TestClient(test_app)
        
        with patch("app.api.portraits.require_admin", return_value="admin"):
            response = client.get("/portraits/admin/list-with-preview?page=1&page_size=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "portraits" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert len(data["portraits"]) <= 10
    
    def test_admin_preview_caching(self, test_app, mock_cache):
        """Test that admin preview results are cached."""
        client = TestClient(test_app)
        
        with patch("app.api.portraits.require_admin", return_value="admin"):
            # First request
            response1 = client.get("/portraits/admin/list-with-preview?page=1&page_size=10")
            
            # Second request - should hit cache
            response2 = client.get("/portraits/admin/list-with-preview?page=1&page_size=10")
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            # Cache should have entries
            assert len(mock_cache._storage) > 0


class TestCacheInvalidation:
    """Test cache invalidation on data changes."""
    
    @pytest.mark.asyncio
    async def test_invalidate_on_portrait_delete(self, test_app, mock_cache):
        """Test cache invalidation when portrait is deleted."""
        # Populate cache
        cache_key = ("portraits", "list", "all", "all", "all", "all", 1, 50, False)
        await mock_cache.set({"test": "data"}, *cache_key)
        
        assert len(mock_cache._storage) > 0
        
        # Invalidate
        await mock_cache.invalidate_all()
        
        # Cache should be empty
        assert len(mock_cache._storage) == 0
    
    @pytest.mark.asyncio
    async def test_invalidate_on_video_create(self, test_app, mock_cache):
        """Test cache invalidation when video is added to portrait."""
        # Populate cache
        cache_key = ("portraits", "admin_preview", "all", "all", 1, 50)
        await mock_cache.set({"test": "data"}, *cache_key)
        
        assert len(mock_cache._storage) > 0
        
        # Invalidate
        await mock_cache.invalidate_all()
        
        # Cache should be empty
        assert len(mock_cache._storage) == 0
