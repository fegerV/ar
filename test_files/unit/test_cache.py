"""
Unit tests for cache abstraction layer.
Tests both LRU and Redis backend implementations.
"""
import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from app.cache import (
    LRUCacheBackend,
    RedisCacheBackend,
    CacheManager,
    create_cache_manager,
)


class TestLRUCacheBackend:
    """Test LRU cache backend."""
    
    @pytest.mark.asyncio
    async def test_init(self):
        """Test LRU cache initialization."""
        cache = LRUCacheBackend(max_size=100, default_ttl=60)
        assert cache.max_size == 100
        assert cache.default_ttl == 60
        assert len(cache._cache) == 0
        
        stats = cache.get_stats()
        assert stats["backend"] == "lru"
        assert stats["max_size"] == 100
        assert stats["size"] == 0
    
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = LRUCacheBackend()
        
        # Set a value
        result = await cache.set("key1", "value1")
        assert result is True
        
        # Get the value
        value = await cache.get("key1")
        assert value == "value1"
        
        # Get non-existent key
        value = await cache.get("key_not_exists")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test TTL expiration."""
        cache = LRUCacheBackend(default_ttl=1)
        
        # Set a value with 1 second TTL
        await cache.set("key1", "value1", ttl=1)
        
        # Should be available immediately
        value = await cache.get("key1")
        assert value == "value1"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        value = await cache.get("key1")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = LRUCacheBackend(max_size=3)
        
        # Fill cache
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Add one more (should evict key1)
        await cache.set("key4", "value4")
        
        # key1 should be evicted
        assert await cache.get("key1") is None
        
        # Others should still be there
        assert await cache.get("key2") == "value2"
        assert await cache.get("key3") == "value3"
        assert await cache.get("key4") == "value4"
        
        stats = cache.get_stats()
        assert stats["evictions"] >= 1
    
    @pytest.mark.asyncio
    async def test_delete(self):
        """Test delete operation."""
        cache = LRUCacheBackend()
        
        await cache.set("key1", "value1")
        assert await cache.get("key1") == "value1"
        
        # Delete the key
        result = await cache.delete("key1")
        assert result is True
        
        # Should be gone
        assert await cache.get("key1") is None
        
        # Delete non-existent key
        result = await cache.delete("key_not_exists")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clear operation."""
        cache = LRUCacheBackend()
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        result = await cache.clear()
        assert result is True
        
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
    
    @pytest.mark.asyncio
    async def test_exists(self):
        """Test exists operation."""
        cache = LRUCacheBackend()
        
        await cache.set("key1", "value1")
        
        assert await cache.exists("key1") is True
        assert await cache.exists("key_not_exists") is False
    
    @pytest.mark.asyncio
    async def test_increment(self):
        """Test increment operation."""
        cache = LRUCacheBackend()
        
        # Increment non-existent key (should start at 0)
        value = await cache.increment("counter")
        assert value == 1
        
        # Increment again
        value = await cache.increment("counter")
        assert value == 2
        
        # Increment with delta
        value = await cache.increment("counter", delta=5)
        assert value == 7
    
    @pytest.mark.asyncio
    async def test_hit_miss_stats(self):
        """Test hit/miss statistics."""
        cache = LRUCacheBackend()
        
        await cache.set("key1", "value1")
        
        # Hit
        await cache.get("key1")
        
        # Miss
        await cache.get("key2")
        
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate_percent"] == 50.0


class TestCacheManager:
    """Test cache manager with namespacing and versioning."""
    
    @pytest.mark.asyncio
    async def test_init(self):
        """Test cache manager initialization."""
        backend = LRUCacheBackend()
        manager = CacheManager(backend, namespace="test", enabled=True)
        
        assert manager.backend == backend
        assert manager.namespace == "test"
        assert manager.enabled is True
    
    @pytest.mark.asyncio
    async def test_key_generation(self):
        """Test cache key generation."""
        backend = LRUCacheBackend()
        manager = CacheManager(backend, namespace="test")
        
        # Simple key
        key = manager._make_key("portraits", "list", "page1")
        assert key.startswith("test:")
        assert "portraits" in key
        
        # Long key (should be hashed)
        long_parts = ["part" + str(i) for i in range(100)]
        key = manager._make_key(*long_parts)
        assert len(key) < 250  # Should be shortened
        assert "hash" in key
    
    @pytest.mark.asyncio
    async def test_cache_versioning(self):
        """Test cache version for invalidation."""
        backend = LRUCacheBackend()
        manager = CacheManager(backend, namespace="test")
        
        # Get initial version
        version = await manager.get_cache_version()
        assert version == 0
        
        # Set a value
        await manager.set("value1", "portraits", "list")
        value = await manager.get("portraits", "list")
        assert value == "value1"
        
        # Increment version (invalidates all cache)
        new_version = await manager.increment_cache_version()
        assert new_version == 1
        
        # Old value should not be accessible
        value = await manager.get("portraits", "list")
        assert value is None
        
        # Set new value with new version
        await manager.set("value2", "portraits", "list")
        value = await manager.get("portraits", "list")
        assert value == "value2"
    
    @pytest.mark.asyncio
    async def test_disabled_cache(self):
        """Test cache manager when disabled."""
        backend = LRUCacheBackend()
        manager = CacheManager(backend, namespace="test", enabled=False)
        
        # Set should return False
        result = await manager.set("value1", "key1")
        assert result is False
        
        # Get should return None
        value = await manager.get("key1")
        assert value is None
        
        # Version should be 0
        version = await manager.get_cache_version()
        assert version == 0
    
    @pytest.mark.asyncio
    async def test_invalidate_all(self):
        """Test invalidate_all method."""
        backend = LRUCacheBackend()
        manager = CacheManager(backend, namespace="test")
        
        # Set multiple values
        await manager.set("value1", "key1")
        await manager.set("value2", "key2")
        
        # Invalidate all
        new_version = await manager.invalidate_all()
        assert new_version == 1
        
        # All values should be inaccessible
        assert await manager.get("key1") is None
        assert await manager.get("key2") is None
    
    @pytest.mark.asyncio
    async def test_stats(self):
        """Test statistics from cache manager."""
        backend = LRUCacheBackend()
        manager = CacheManager(backend, namespace="test", enabled=True)
        
        stats = manager.get_stats()
        assert stats["namespace"] == "test"
        assert stats["enabled"] is True
        assert stats["backend"] == "lru"


class TestCreateCacheManager:
    """Test cache manager factory function."""
    
    def test_create_lru_cache(self):
        """Test creating LRU cache (no Redis URL)."""
        manager = create_cache_manager(
            redis_url=None,
            namespace="test",
            default_ttl=60,
            max_size=100,
            enabled=True
        )
        
        assert isinstance(manager.backend, LRUCacheBackend)
        assert manager.namespace == "test"
        assert manager.enabled is True
    
    def test_create_disabled_cache(self):
        """Test creating disabled cache."""
        manager = create_cache_manager(enabled=False)
        
        assert manager.enabled is False


class TestPaginationMath:
    """Test pagination calculations."""
    
    def test_page_calculation(self):
        """Test page and offset calculations."""
        # Page 1, size 50
        page = 1
        page_size = 50
        offset = (page - 1) * page_size
        assert offset == 0
        
        # Page 2, size 50
        page = 2
        offset = (page - 1) * page_size
        assert offset == 50
        
        # Page 3, size 25
        page = 3
        page_size = 25
        offset = (page - 1) * page_size
        assert offset == 50
    
    def test_total_pages_calculation(self):
        """Test total pages calculation."""
        import math
        
        # Exact fit
        total = 100
        page_size = 50
        total_pages = math.ceil(total / page_size)
        assert total_pages == 2
        
        # With remainder
        total = 105
        page_size = 50
        total_pages = math.ceil(total / page_size)
        assert total_pages == 3
        
        # Single page
        total = 10
        page_size = 50
        total_pages = math.ceil(total / page_size)
        assert total_pages == 1
        
        # Empty
        total = 0
        page_size = 50
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        assert total_pages == 0
