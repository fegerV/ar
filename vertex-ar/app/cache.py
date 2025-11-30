"""
Cache abstraction for Vertex AR application.
Supports Redis backend with LRU in-memory fallback.
"""
import hashlib
import json
import pickle
from abc import ABC, abstractmethod
from collections import OrderedDict
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Optional

from logging_setup import get_logger

logger = get_logger(__name__)


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL in seconds."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass
    
    @abstractmethod
    async def increment(self, key: str, delta: int = 1) -> int:
        """Increment a numeric value in cache."""
        pass
    
    @abstractmethod
    def get_stats(self) -> dict:
        """Get cache statistics."""
        pass


class LRUCacheBackend(CacheBackend):
    """In-memory LRU cache implementation with TTL support."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, tuple[Any, Optional[datetime]]] = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        logger.info(
            "LRU cache backend initialized",
            max_size=max_size,
            default_ttl=default_ttl
        )
    
    def _evict_expired(self) -> None:
        """Remove expired entries."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, (_, expiry) in self._cache.items()
            if expiry is not None and expiry < now
        ]
        for key in expired_keys:
            del self._cache[key]
            self._evictions += 1
    
    def _evict_lru(self) -> None:
        """Remove least recently used entry if cache is full."""
        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)
            self._evictions += 1
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            self._evict_expired()
            
            if key not in self._cache:
                self._misses += 1
                return None
            
            value, expiry = self._cache[key]
            
            # Check expiry
            if expiry is not None and expiry < datetime.utcnow():
                del self._cache[key]
                self._misses += 1
                self._evictions += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL in seconds."""
        with self._lock:
            self._evict_expired()
            self._evict_lru()
            
            ttl_seconds = ttl if ttl is not None else self.default_ttl
            expiry = datetime.utcnow() + timedelta(seconds=ttl_seconds) if ttl_seconds > 0 else None
            
            self._cache[key] = (value, expiry)
            self._cache.move_to_end(key)
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            return True
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        value = await self.get(key)
        return value is not None
    
    async def increment(self, key: str, delta: int = 1) -> int:
        """Increment a numeric value in cache."""
        with self._lock:
            # Get current value without await (direct access)
            if key not in self._cache:
                current = 0
            else:
                value, expiry = self._cache[key]
                # Check expiry
                if expiry is not None and expiry < datetime.utcnow():
                    del self._cache[key]
                    current = 0
                else:
                    current = int(value)
            
            new_value = current + delta
            
            # Set new value without await (direct access)
            ttl_seconds = self.default_ttl
            expiry = datetime.utcnow() + timedelta(seconds=ttl_seconds) if ttl_seconds > 0 else None
            self._cache[key] = (new_value, expiry)
            self._cache.move_to_end(key)
            
            return new_value
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "backend": "lru",
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate_percent": round(hit_rate, 2),
            }


class RedisCacheBackend(CacheBackend):
    """Redis cache implementation."""
    
    def __init__(self, redis_url: str, default_ttl: int = 300):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds
        """
        try:
            import redis.asyncio as redis
            self.redis = redis.from_url(redis_url, decode_responses=False)
            self.default_ttl = default_ttl
            self._hits = 0
            self._misses = 0
            
            logger.info(
                "Redis cache backend initialized",
                redis_url=redis_url.split('@')[-1],  # Hide credentials
                default_ttl=default_ttl
            )
        except ImportError:
            raise ImportError(
                "redis package is required for Redis cache. "
                "Install with: pip install redis"
            )
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = await self.redis.get(key)
            if value is None:
                self._misses += 1
                return None
            
            self._hits += 1
            return pickle.loads(value)
        except Exception as e:
            logger.error("Redis get failed", key=key, error=str(e))
            self._misses += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL in seconds."""
        try:
            ttl_seconds = ttl if ttl is not None else self.default_ttl
            serialized = pickle.dumps(value)
            
            if ttl_seconds > 0:
                await self.redis.setex(key, ttl_seconds, serialized)
            else:
                await self.redis.set(key, serialized)
            
            return True
        except Exception as e:
            logger.error("Redis set failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error("Redis delete failed", key=key, error=str(e))
            return False
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        try:
            await self.redis.flushdb()
            return True
        except Exception as e:
            logger.error("Redis clear failed", error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            result = await self.redis.exists(key)
            return result > 0
        except Exception as e:
            logger.error("Redis exists failed", key=key, error=str(e))
            return False
    
    async def increment(self, key: str, delta: int = 1) -> int:
        """Increment a numeric value in cache."""
        try:
            return await self.redis.incrby(key, delta)
        except Exception as e:
            logger.error("Redis increment failed", key=key, error=str(e))
            return 0
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "backend": "redis",
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
        }
    
    async def close(self) -> None:
        """Close Redis connection."""
        try:
            await self.redis.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error("Failed to close Redis connection", error=str(e))


class CacheManager:
    """High-level cache manager with namespacing and key generation."""
    
    def __init__(
        self,
        backend: CacheBackend,
        namespace: str = "vertex_ar",
        enabled: bool = True
    ):
        """
        Initialize cache manager.
        
        Args:
            backend: Cache backend implementation
            namespace: Namespace prefix for all keys
            enabled: Whether caching is enabled
        """
        self.backend = backend
        self.namespace = namespace
        self.enabled = enabled
        self._version_key = f"{namespace}:cache_version"
        
        logger.info(
            "Cache manager initialized",
            namespace=namespace,
            enabled=enabled,
            backend=backend.__class__.__name__
        )
    
    def _make_key(self, *parts: Any) -> str:
        """Generate cache key from parts."""
        # Create a stable string representation
        key_parts = [str(part) for part in parts]
        key_string = ":".join(key_parts)
        
        # Use hash for long keys to avoid Redis key length limits
        if len(key_string) > 200:
            key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
            key_string = f"{key_parts[0]}:hash:{key_hash}"
        
        return f"{self.namespace}:{key_string}"
    
    async def get_cache_version(self) -> int:
        """Get current cache version for invalidation."""
        if not self.enabled:
            return 0
        
        version = await self.backend.get(self._version_key)
        if version is None:
            await self.backend.set(self._version_key, 0, ttl=0)  # No expiry
            return 0
        return int(version)
    
    async def increment_cache_version(self) -> int:
        """Increment cache version to invalidate all cached data."""
        if not self.enabled:
            return 0
        
        new_version = await self.backend.increment(self._version_key)
        logger.info("Cache version incremented", new_version=new_version)
        return new_version
    
    async def get(self, *key_parts: Any) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled:
            return None
        
        version = await self.get_cache_version()
        key = self._make_key(version, *key_parts)
        return await self.backend.get(key)
    
    async def set(self, value: Any, *key_parts: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        if not self.enabled:
            return False
        
        version = await self.get_cache_version()
        key = self._make_key(version, *key_parts)
        return await self.backend.set(key, value, ttl=ttl)
    
    async def delete(self, *key_parts: Any) -> bool:
        """Delete value from cache."""
        if not self.enabled:
            return False
        
        version = await self.get_cache_version()
        key = self._make_key(version, *key_parts)
        return await self.backend.delete(key)
    
    async def clear_all(self) -> bool:
        """Clear all cache entries."""
        if not self.enabled:
            return False
        
        return await self.backend.clear()
    
    async def invalidate_all(self) -> int:
        """Invalidate all cached data by incrementing version."""
        return await self.increment_cache_version()
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        stats = self.backend.get_stats()
        stats["namespace"] = self.namespace
        stats["enabled"] = self.enabled
        return stats
    
    async def close(self) -> None:
        """Close cache backend connections."""
        if isinstance(self.backend, RedisCacheBackend):
            await self.backend.close()


def create_cache_manager(
    redis_url: Optional[str] = None,
    namespace: str = "vertex_ar",
    default_ttl: int = 300,
    max_size: int = 1000,
    enabled: bool = True
) -> CacheManager:
    """
    Create cache manager with appropriate backend.
    
    Args:
        redis_url: Redis connection URL (if None, uses LRU cache)
        namespace: Cache namespace prefix
        default_ttl: Default TTL in seconds
        max_size: Max size for LRU cache
        enabled: Whether caching is enabled
    
    Returns:
        Configured CacheManager instance
    """
    if redis_url and enabled:
        try:
            backend = RedisCacheBackend(redis_url, default_ttl=default_ttl)
            logger.info("Using Redis cache backend")
        except Exception as e:
            logger.warning(
                "Failed to initialize Redis cache, falling back to LRU",
                error=str(e)
            )
            backend = LRUCacheBackend(max_size=max_size, default_ttl=default_ttl)
    else:
        backend = LRUCacheBackend(max_size=max_size, default_ttl=default_ttl)
        logger.info("Using LRU cache backend")
    
    return CacheManager(backend=backend, namespace=namespace, enabled=enabled)
