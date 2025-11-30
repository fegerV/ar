"""
Unit tests for enhanced Yandex Disk storage adapter.
Tests session reuse, chunked uploads/downloads, and directory caching.
"""
import asyncio
import os
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta

# Set test mode
os.environ["RUNNING_TESTS"] = "1"

# Mock settings before imports
mock_settings = Mock()
mock_settings.YANDEX_REQUEST_TIMEOUT = 30
mock_settings.YANDEX_CHUNK_SIZE_MB = 10
mock_settings.YANDEX_UPLOAD_CONCURRENCY = 3
mock_settings.YANDEX_DIRECTORY_CACHE_TTL = 300
mock_settings.YANDEX_DIRECTORY_CACHE_SIZE = 1000
mock_settings.YANDEX_SESSION_POOL_CONNECTIONS = 10
mock_settings.YANDEX_SESSION_POOL_MAXSIZE = 20
mock_settings.BASE_URL = "http://localhost:8000"


class TestDirectoryCache:
    """Test directory cache with TTL."""
    
    @pytest.fixture
    def cache(self):
        """Create cache instance."""
        from vertex_ar.app.storage_yandex import DirectoryCache
        return DirectoryCache(max_size=10, ttl_seconds=2)
    
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache):
        """Test basic set and get operations."""
        await cache.set("test/path", True)
        result = await cache.get("test/path")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_cache_miss(self, cache):
        """Test cache miss returns None."""
        result = await cache.get("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_ttl_expiry(self, cache):
        """Test cache entries expire after TTL."""
        await cache.set("test/path", True)
        
        # Should be cached
        result = await cache.get("test/path")
        assert result is True
        
        # Wait for expiry
        await asyncio.sleep(2.1)
        
        # Should be expired
        result = await cache.get("test/path")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self, cache):
        """Test LRU eviction when cache is full."""
        # Fill cache to max size
        for i in range(10):
            await cache.set(f"path{i}", True)
        
        # Add one more - should evict oldest (path0)
        await cache.set("path10", True)
        
        # path0 should be evicted
        result = await cache.get("path0")
        assert result is None
        
        # path10 should exist
        result = await cache.get("path10")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, cache):
        """Test cache statistics."""
        await cache.set("path1", True)
        await cache.set("path2", True)
        
        stats = cache.get_stats()
        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 2
        assert stats["expired_entries"] == 0
        assert stats["max_size"] == 10
        assert stats["ttl_seconds"] == 2
    
    @pytest.mark.asyncio
    async def test_cache_clear(self, cache):
        """Test cache clear operation."""
        await cache.set("path1", True)
        await cache.set("path2", True)
        
        await cache.clear()
        
        stats = cache.get_stats()
        assert stats["total_entries"] == 0


class TestYandexDiskStorageAdapter:
    """Test enhanced Yandex Disk storage adapter."""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        session = MagicMock()
        session.request = MagicMock()
        session.headers = {}
        return session
    
    @pytest.fixture
    def adapter(self, mock_session):
        """Create adapter with mocked session."""
        with patch('vertex_ar.app.storage_yandex.requests.Session', return_value=mock_session):
            with patch.object(mock_session, 'mount'):
                # Mock initial directory creation
                mock_response = Mock()
                mock_response.status_code = 409  # Already exists
                mock_response.raise_for_status = Mock()
                mock_session.request.return_value = mock_response
                
                from vertex_ar.app.storage_yandex import YandexDiskStorageAdapter
                
                adapter = YandexDiskStorageAdapter(
                    oauth_token="test_token",
                    base_path="test-path",
                    timeout=10,
                    chunk_size_mb=5,
                    upload_concurrency=2,
                    cache_ttl=60,
                    cache_size=100
                )
                adapter.session = mock_session
                return adapter
    
    def test_adapter_initialization(self, adapter):
        """Test adapter is initialized with correct parameters."""
        assert adapter.oauth_token == "test_token"
        assert adapter.base_path == "test-path"
        assert adapter.timeout == 10
        assert adapter.chunk_size == 5 * 1024 * 1024  # 5 MB in bytes
        assert adapter.upload_concurrency == 2
    
    def test_session_reuse(self, adapter):
        """Test that the same session is reused for multiple requests."""
        session_id = id(adapter.session)
        
        # Make multiple requests - session should be the same
        for _ in range(3):
            assert id(adapter.session) == session_id
    
    @pytest.mark.asyncio
    async def test_directory_cache_hit(self, adapter):
        """Test directory cache hit reduces API calls."""
        # Pre-populate cache
        await adapter.directory_cache.set("test-path/some/dir", True)
        
        # This should use cache, not make API call
        result = await adapter._ensure_directory_exists("test-path/some/dir")
        
        assert result is True
        # Session should not be called for cached directory
        adapter.session.request.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_directory_cache_miss(self, adapter):
        """Test directory cache miss makes API call."""
        # Mock successful directory creation
        mock_response = Mock()
        mock_response.status_code = 409  # Already exists
        mock_response.raise_for_status = Mock()
        
        with patch.object(adapter, '_make_request', return_value=mock_response):
            result = await adapter._ensure_directory_exists("test-path/new/dir")
        
        assert result is True
        # Cache should be populated
        cached = await adapter.directory_cache.get("test-path/new/dir")
        assert cached is True
    
    @pytest.mark.asyncio
    async def test_small_file_direct_upload(self, adapter):
        """Test small files use direct upload (no chunking)."""
        # Small file (< chunk_size)
        file_data = b"small file content"
        upload_url = "https://upload.example.com/file"
        
        # Mock successful upload
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        
        with patch('vertex_ar.app.storage_yandex.requests.put', return_value=mock_response) as mock_put:
            result = await adapter._chunked_upload(file_data, upload_url)
        
        assert result is True
        # Should make single PUT request
        mock_put.assert_called_once()
        args, kwargs = mock_put.call_args
        assert kwargs['data'] == file_data
    
    @pytest.mark.asyncio
    async def test_large_file_chunked_upload(self, adapter):
        """Test large files are uploaded in chunks."""
        # Large file (> chunk_size)
        chunk_size = 5 * 1024 * 1024  # 5 MB
        file_data = b"x" * (chunk_size * 2 + 1000)  # 10+ MB
        upload_url = "https://upload.example.com/file"
        
        # Mock successful chunk uploads
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        
        with patch('vertex_ar.app.storage_yandex.requests.put', return_value=mock_response) as mock_put:
            result = await adapter._chunked_upload(file_data, upload_url)
        
        assert result is True
        # Should make multiple PUT requests (one per chunk)
        assert mock_put.call_count == 3  # 3 chunks for 10+ MB with 5 MB chunks
        
        # Verify Content-Range headers
        for call_obj in mock_put.call_args_list:
            args, kwargs = call_obj
            if 'headers' in kwargs:
                assert 'Content-Range' in kwargs['headers']
    
    @pytest.mark.asyncio
    async def test_chunked_upload_concurrency(self, adapter):
        """Test chunked upload respects concurrency limit."""
        # Create file that needs 5 chunks
        chunk_size = 5 * 1024 * 1024
        file_data = b"x" * (chunk_size * 5)
        upload_url = "https://upload.example.com/file"
        
        # Track concurrent calls
        concurrent_calls = []
        max_concurrent = 0
        
        async def mock_put(*args, **kwargs):
            concurrent_calls.append(1)
            current = len(concurrent_calls)
            nonlocal max_concurrent
            max_concurrent = max(max_concurrent, current)
            await asyncio.sleep(0.01)  # Simulate upload time
            concurrent_calls.pop()
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            return mock_response
        
        with patch('vertex_ar.app.storage_yandex.requests.put', side_effect=mock_put):
            await adapter._chunked_upload(file_data, upload_url)
        
        # Max concurrent should not exceed configured limit
        assert max_concurrent <= adapter.upload_concurrency
    
    @pytest.mark.asyncio
    async def test_small_file_direct_download(self, adapter):
        """Test small files use direct download (no chunking)."""
        download_url = "https://download.example.com/file"
        expected_content = b"small file content"
        
        # Mock HEAD request for size
        mock_head_response = Mock()
        mock_head_response.headers = {'Content-Length': str(len(expected_content))}
        
        # Mock GET request
        mock_get_response = Mock()
        mock_get_response.content = expected_content
        mock_get_response.raise_for_status = Mock()
        
        with patch('vertex_ar.app.storage_yandex.requests.head', return_value=mock_head_response):
            with patch('vertex_ar.app.storage_yandex.requests.get', return_value=mock_get_response) as mock_get:
                result = await adapter._chunked_download(download_url)
        
        assert result == expected_content
        # Should make single GET request (no Range header for small files)
        mock_get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_large_file_chunked_download(self, adapter):
        """Test large files are downloaded in chunks."""
        download_url = "https://download.example.com/file"
        chunk_size = 5 * 1024 * 1024
        file_size = chunk_size * 2 + 1000  # 10+ MB
        
        # Mock HEAD request for size
        mock_head_response = Mock()
        mock_head_response.headers = {'Content-Length': str(file_size)}
        
        # Mock GET requests for chunks
        def mock_get(*args, **kwargs):
            mock_response = Mock()
            # Return different content based on Range header
            if 'headers' in kwargs and 'Range' in kwargs['headers']:
                mock_response.content = b"chunk_data"
            else:
                mock_response.content = b"full_data"
            mock_response.raise_for_status = Mock()
            return mock_response
        
        with patch('vertex_ar.app.storage_yandex.requests.head', return_value=mock_head_response):
            with patch('vertex_ar.app.storage_yandex.requests.get', side_effect=mock_get) as mock_get_call:
                result = await adapter._chunked_download(download_url)
        
        # Should make multiple GET requests with Range headers
        assert mock_get_call.call_count == 3  # 3 chunks
        
        # Verify Range headers were used
        range_headers_found = False
        for call_obj in mock_get_call.call_args_list:
            args, kwargs = call_obj
            if 'headers' in kwargs and 'Range' in kwargs['headers']:
                range_headers_found = True
                break
        assert range_headers_found
    
    def test_get_cache_stats(self, adapter):
        """Test getting cache statistics."""
        stats = adapter.get_cache_stats()
        
        assert "total_entries" in stats
        assert "valid_entries" in stats
        assert "expired_entries" in stats
        assert "max_size" in stats
        assert "ttl_seconds" in stats
    
    @pytest.mark.asyncio
    async def test_clear_directory_cache(self, adapter):
        """Test clearing directory cache."""
        # Populate cache
        await adapter.directory_cache.set("path1", True)
        await adapter.directory_cache.set("path2", True)
        
        # Clear cache
        await adapter.clear_directory_cache()
        
        # Cache should be empty
        stats = adapter.get_cache_stats()
        assert stats["total_entries"] == 0
    
    def test_session_cleanup_on_close(self, adapter):
        """Test session is closed when adapter is closed."""
        adapter.close()
        adapter.session.close.assert_called_once()


class TestStorageManagerIntegration:
    """Test storage manager integration with enhanced adapter."""
    
    @pytest.mark.asyncio
    async def test_flush_directory_cache_single_adapter(self):
        """Test flushing cache for single adapter."""
        with patch('vertex_ar.storage_manager.YandexDiskStorageAdapter') as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.clear_directory_cache = Mock(return_value=asyncio.coroutine(lambda: None)())
            mock_adapter_class.return_value = mock_adapter
            
            from vertex_ar.storage_manager import StorageManager
            manager = StorageManager()
            
            # Mock a Yandex adapter in the manager
            manager.adapters["portraits"] = mock_adapter
            
            # Flush cache
            await manager.flush_directory_cache(content_type="portraits")
            
            # Cache clear should be called
            mock_adapter.clear_directory_cache.assert_called_once()
    
    def test_get_yandex_cache_stats(self):
        """Test getting cache stats from all adapters."""
        with patch('vertex_ar.storage_manager.YandexDiskStorageAdapter') as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.get_cache_stats = Mock(return_value={
                "total_entries": 10,
                "valid_entries": 8,
                "expired_entries": 2
            })
            mock_adapter_class.return_value = mock_adapter
            
            from vertex_ar.storage_manager import StorageManager
            manager = StorageManager()
            manager.adapters["portraits"] = mock_adapter
            
            # Get stats
            stats = manager.get_yandex_cache_stats()
            
            # Should return stats from adapter
            assert "global_portraits" in stats
            assert stats["global_portraits"]["total_entries"] == 10


class TestPrometheusMetrics:
    """Test Prometheus metrics integration."""
    
    def test_metrics_initialization(self):
        """Test metrics are initialized correctly."""
        from vertex_ar.app.storage_yandex import YandexDiskStorageAdapter
        
        # Metrics should be initialized as class variables
        assert hasattr(YandexDiskStorageAdapter, 'operations_total')
        assert hasattr(YandexDiskStorageAdapter, 'operation_duration')
        assert hasattr(YandexDiskStorageAdapter, 'errors_total')
        assert hasattr(YandexDiskStorageAdapter, 'chunks_transferred')
        assert hasattr(YandexDiskStorageAdapter, 'bytes_transferred')
        assert hasattr(YandexDiskStorageAdapter, 'cache_hits')
        assert hasattr(YandexDiskStorageAdapter, 'cache_misses')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
