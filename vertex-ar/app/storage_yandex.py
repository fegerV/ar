"""
Yandex Disk storage adapter for Vertex AR.
Stores photos, videos, previews, and NFT files on Yandex Disk.

Enhanced with:
- Persistent session for connection pooling
- Configurable request timeouts
- Chunked uploads/downloads for large files
- Directory creation caching with TTL
- Prometheus metrics for monitoring
"""
import asyncio
import json
import os
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.storage import StorageAdapter
from logging_setup import get_logger

logger = get_logger(__name__)


class DirectoryCache:
    """LRU cache with TTL for directory existence checks."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, Tuple[bool, float]] = OrderedDict()
        # Lock will be created when needed in async context
        self._lock = None
    
    async def get(self, key: str) -> Optional[bool]:
        """Get cached value if not expired."""
        if key not in self.cache:
            return None
        
        value, timestamp = self.cache[key]
        if time.time() - timestamp > self.ttl_seconds:
            del self.cache[key]
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return value
    
    async def set(self, key: str, value: bool):
        """Set cache value with current timestamp."""
        if key in self.cache:
            del self.cache[key]
        elif len(self.cache) >= self.max_size:
            # Remove oldest item
            self.cache.popitem(last=False)
        
        self.cache[key] = (value, time.time())
    
    async def clear(self):
        """Clear all cached entries."""
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        now = time.time()
        expired = sum(1 for _, (_, ts) in self.cache.items() if now - ts > self.ttl_seconds)
        return {
            "total_entries": len(self.cache),
            "expired_entries": expired,
            "valid_entries": len(self.cache) - expired,
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds
        }


class YandexDiskStorageAdapter(StorageAdapter):
    """Yandex Disk storage implementation for media files."""
    
    BASE_URL = "https://cloud-api.yandex.net/v1/disk"
    
    # Prometheus metrics (initialized on first import)
    _metrics_initialized = False
    
    def __init__(
        self,
        oauth_token: str,
        base_path: str = "vertex-ar",
        timeout: int = 30,
        chunk_size_mb: int = 10,
        upload_concurrency: int = 3,
        cache_ttl: int = 300,
        cache_size: int = 1000,
        pool_connections: int = 10,
        pool_maxsize: int = 20
    ):
        """
        Initialize Yandex Disk storage adapter.
        
        Args:
            oauth_token: OAuth token for Yandex Disk API
            base_path: Base directory path on Yandex Disk
            timeout: Request timeout in seconds
            chunk_size_mb: Chunk size for uploads/downloads in megabytes
            upload_concurrency: Maximum concurrent chunk uploads
            cache_ttl: Directory cache TTL in seconds
            cache_size: Maximum directory cache entries
            pool_connections: Connection pool size
            pool_maxsize: Maximum pool size
        """
        self.oauth_token = oauth_token
        self.base_path = base_path.rstrip('/')
        self.timeout = timeout
        self.chunk_size = chunk_size_mb * 1024 * 1024  # Convert to bytes
        self.upload_concurrency = upload_concurrency
        
        # Initialize persistent session with connection pooling
        self.session = self._create_session(pool_connections, pool_maxsize)
        
        # Initialize directory cache
        self.directory_cache = DirectoryCache(max_size=cache_size, ttl_seconds=cache_ttl)
        
        # Initialize metrics
        self._init_metrics()
        
        # Ensure base directory exists
        self._ensure_directory_exists_sync(self.base_path)
        
        logger.info(
            "Yandex Disk adapter initialized",
            base_path=base_path,
            timeout=timeout,
            chunk_size_mb=chunk_size_mb,
            upload_concurrency=upload_concurrency,
            cache_ttl=cache_ttl,
            cache_size=cache_size
        )
    
    def _create_session(self, pool_connections: int, pool_maxsize: int) -> requests.Session:
        """Create persistent session with retry logic and connection pooling."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        # Mount adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            pool_block=False
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # Set default headers
        session.headers.update({
            "Authorization": f"OAuth {self.oauth_token}",
            "Accept": "application/json"
        })
        
        return session
    
    @classmethod
    def _init_metrics(cls):
        """Initialize Prometheus metrics (once per class)."""
        if cls._metrics_initialized:
            return
        
        try:
            from prometheus_client import Counter, Histogram, Gauge
            from app.prometheus_metrics import registry
            
            # Operation counters
            cls.operations_total = Counter(
                'vertex_ar_yandex_operations_total',
                'Total Yandex Disk operations',
                ['operation', 'status'],
                registry=registry
            )
            
            # Latency histogram
            cls.operation_duration = Histogram(
                'vertex_ar_yandex_operation_duration_seconds',
                'Yandex Disk operation duration',
                ['operation'],
                buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
                registry=registry
            )
            
            # Error counter
            cls.errors_total = Counter(
                'vertex_ar_yandex_errors_total',
                'Total Yandex Disk errors',
                ['operation', 'error_type'],
                registry=registry
            )
            
            # Chunk transfer metrics
            cls.chunks_transferred = Counter(
                'vertex_ar_yandex_chunks_total',
                'Total chunks transferred',
                ['operation'],
                registry=registry
            )
            
            cls.bytes_transferred = Counter(
                'vertex_ar_yandex_bytes_total',
                'Total bytes transferred',
                ['operation'],
                registry=registry
            )
            
            # Cache metrics
            cls.cache_hits = Counter(
                'vertex_ar_yandex_cache_hits_total',
                'Directory cache hits',
                registry=registry
            )
            
            cls.cache_misses = Counter(
                'vertex_ar_yandex_cache_misses_total',
                'Directory cache misses',
                registry=registry
            )
            
            cls.cache_size_gauge = Gauge(
                'vertex_ar_yandex_cache_size',
                'Current directory cache size',
                registry=registry
            )
            
            cls._metrics_initialized = True
            logger.info("Yandex Disk Prometheus metrics initialized")
            
        except Exception as e:
            logger.warning(f"Failed to initialize Yandex Disk metrics: {e}")
            # Create no-op metric stubs
            cls.operations_total = type('NoOpCounter', (), {'labels': lambda **k: type('NoOp', (), {'inc': lambda: None})()})()
            cls.operation_duration = type('NoOpHistogram', (), {'labels': lambda **k: type('NoOp', (), {'observe': lambda x: None})()})()
            cls.errors_total = type('NoOpCounter', (), {'labels': lambda **k: type('NoOp', (), {'inc': lambda: None})()})()
            cls.chunks_transferred = type('NoOpCounter', (), {'labels': lambda **k: type('NoOp', (), {'inc': lambda x: None})()})()
            cls.bytes_transferred = type('NoOpCounter', (), {'labels': lambda **k: type('NoOp', (), {'inc': lambda x: None})()})()
            cls.cache_hits = type('NoOpCounter', (), {'inc': lambda: None})()
            cls.cache_misses = type('NoOpCounter', (), {'inc': lambda: None})()
            cls.cache_size_gauge = type('NoOpGauge', (), {'set': lambda x: None})()
    
    def _record_operation(self, operation: str, duration: float, success: bool, error_type: Optional[str] = None):
        """Record operation metrics."""
        try:
            status = "success" if success else "error"
            self.operations_total.labels(operation=operation, status=status).inc()
            self.operation_duration.labels(operation=operation).observe(duration)
            
            if not success and error_type:
                self.errors_total.labels(operation=operation, error_type=error_type).inc()
        except Exception as e:
            logger.debug(f"Failed to record metrics: {e}")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to Yandex Disk API."""
        url = f"{self.BASE_URL}{endpoint}"
        kwargs.setdefault("timeout", self.timeout)
        
        start_time = time.time()
        success = False
        error_type = None
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            success = True
            return response
        except requests.exceptions.Timeout as e:
            error_type = "timeout"
            logger.error("Yandex Disk API request timeout", error=str(e), endpoint=endpoint, timeout=self.timeout)
            raise
        except requests.exceptions.HTTPError as e:
            error_type = f"http_{e.response.status_code}"
            logger.error("Yandex Disk API HTTP error", error=str(e), endpoint=endpoint, status_code=e.response.status_code)
            raise
        except requests.exceptions.ConnectionError as e:
            error_type = "connection"
            logger.error("Yandex Disk API connection error", error=str(e), endpoint=endpoint)
            raise
        except requests.exceptions.RequestException as e:
            error_type = "request"
            logger.error("Yandex Disk API request failed", error=str(e), endpoint=endpoint)
            raise
        finally:
            duration = time.time() - start_time
            self._record_operation(f"api_{method.lower()}_{endpoint.split('/')[1] if '/' in endpoint else 'root'}", duration, success, error_type)
    
    def _ensure_directory_exists_sync(self, dir_path: str):
        """Ensure directory exists on Yandex Disk (synchronous version for init)."""
        try:
            self._make_request("PUT", "/resources", params={"path": dir_path})
            logger.info("Created directory on Yandex Disk", directory=dir_path)
        except requests.exceptions.HTTPError as e:
            # Directory might already exist
            if e.response.status_code != 409:  # 409 = Conflict (already exists)
                raise
            logger.debug("Directory already exists on Yandex Disk", directory=dir_path)
    
    async def _ensure_directory_exists(self, dir_path: str) -> bool:
        """Ensure directory exists on Yandex Disk with caching."""
        # Check cache first
        cached = await self.directory_cache.get(dir_path)
        if cached is not None:
            self.cache_hits.inc()
            logger.debug("Directory cache hit", directory=dir_path)
            return True
        
        self.cache_misses.inc()
        
        start_time = time.time()
        success = False
        error_type = None
        
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._make_request("PUT", "/resources", params={"path": dir_path})
            )
            logger.info("Created directory on Yandex Disk", directory=dir_path)
            success = True
            await self.directory_cache.set(dir_path, True)
            return True
        except requests.exceptions.HTTPError as e:
            # Directory might already exist
            if e.response.status_code == 409:  # 409 = Conflict (already exists)
                logger.debug("Directory already exists on Yandex Disk", directory=dir_path)
                success = True
                await self.directory_cache.set(dir_path, True)
                return True
            error_type = f"http_{e.response.status_code}"
            raise
        except Exception as e:
            error_type = "unknown"
            logger.error("Failed to ensure directory exists", error=str(e), directory=dir_path)
            return False
        finally:
            duration = time.time() - start_time
            self._record_operation("ensure_directory", duration, success, error_type)
            # Update cache size gauge
            stats = self.directory_cache.get_stats()
            self.cache_size_gauge.set(stats["valid_entries"])
    
    def _get_full_path(self, file_path: str) -> str:
        """Get full path on Yandex Disk."""
        return f"{self.base_path}/{file_path}".replace('//', '/')
    
    def _get_upload_url(self, remote_path: str) -> str:
        """Get upload URL for a file."""
        response = self._make_request(
            "GET",
            "/resources/upload",
            params={"path": remote_path, "overwrite": "true"}
        )
        return response.json()["href"]
    
    async def _chunked_upload(self, file_data: bytes, upload_url: str) -> bool:
        """Upload file in chunks with concurrency control."""
        file_size = len(file_data)
        
        # Use direct upload for small files
        if file_size <= self.chunk_size:
            logger.debug("Using direct upload for small file", size_bytes=file_size)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.put(upload_url, data=file_data, timeout=self.timeout)
            )
            response.raise_for_status()
            self.bytes_transferred.labels(operation="upload").inc(file_size)
            return True
        
        # Chunked upload for large files
        logger.info("Starting chunked upload", size_bytes=file_size, chunk_size=self.chunk_size, chunks=file_size // self.chunk_size + 1)
        
        # Split into chunks
        chunks = []
        offset = 0
        while offset < file_size:
            end = min(offset + self.chunk_size, file_size)
            chunks.append((offset, end, file_data[offset:end]))
            offset = end
        
        # Upload chunks with concurrency control
        semaphore = asyncio.Semaphore(self.upload_concurrency)
        
        async def upload_chunk(chunk_data: Tuple[int, int, bytes]) -> bool:
            async with semaphore:
                start_offset, end_offset, data = chunk_data
                headers = {
                    "Content-Range": f"bytes {start_offset}-{end_offset-1}/{file_size}"
                }
                
                try:
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: requests.put(upload_url, data=data, headers=headers, timeout=self.timeout)
                    )
                    response.raise_for_status()
                    
                    self.chunks_transferred.labels(operation="upload").inc()
                    self.bytes_transferred.labels(operation="upload").inc(len(data))
                    
                    logger.debug(
                        "Chunk uploaded",
                        start=start_offset,
                        end=end_offset,
                        size=len(data)
                    )
                    return True
                except Exception as e:
                    logger.error(
                        "Chunk upload failed",
                        error=str(e),
                        start=start_offset,
                        end=end_offset
                    )
                    raise
        
        # Upload all chunks concurrently
        results = await asyncio.gather(*[upload_chunk(chunk) for chunk in chunks], return_exceptions=True)
        
        # Check for failures
        failures = [r for r in results if isinstance(r, Exception)]
        if failures:
            logger.error("Chunked upload failed", failures=len(failures), total_chunks=len(chunks))
            raise failures[0]
        
        logger.info("Chunked upload completed", chunks=len(chunks), size_bytes=file_size)
        return True
    
    async def save_file(self, file_data: bytes, file_path: str) -> str:
        """Save file data to Yandex Disk with chunked upload support.
        
        Args:
            file_data: Raw file data
            file_path: Destination path within storage
            
        Returns:
            Public URL to access the file
        """
        remote_path = self._get_full_path(file_path)
        
        start_time = time.time()
        success = False
        error_type = None
        
        try:
            # Ensure parent directory exists
            parent_dir = '/'.join(remote_path.split('/')[:-1])
            if parent_dir:
                await self._ensure_directory_exists(parent_dir)
            
            # Get upload URL
            loop = asyncio.get_event_loop()
            upload_url = await loop.run_in_executor(
                None,
                lambda: self._get_upload_url(remote_path)
            )
            
            # Upload file (with chunking for large files)
            await self._chunked_upload(file_data, upload_url)
            
            logger.info(
                "File saved to Yandex Disk",
                file_path=file_path,
                remote_path=remote_path,
                size_bytes=len(file_data)
            )
            
            success = True
            return self.get_public_url(file_path)
            
        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                "Failed to save file to Yandex Disk",
                error=str(e),
                file_path=file_path
            )
            raise Exception(f"Failed to save file to Yandex Disk: {str(e)}")
        finally:
            duration = time.time() - start_time
            self._record_operation("save_file", duration, success, error_type)
    
    async def _chunked_download(self, download_url: str, expected_size: Optional[int] = None) -> bytes:
        """Download file in chunks for better memory efficiency."""
        loop = asyncio.get_event_loop()
        
        # Get file size if not provided
        if expected_size is None:
            response = await loop.run_in_executor(
                None,
                lambda: requests.head(download_url, timeout=self.timeout)
            )
            expected_size = int(response.headers.get('Content-Length', 0))
        
        # Use direct download for small files
        if expected_size <= self.chunk_size:
            logger.debug("Using direct download for small file", size_bytes=expected_size)
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(download_url, timeout=self.timeout)
            )
            response.raise_for_status()
            self.bytes_transferred.labels(operation="download").inc(len(response.content))
            return response.content
        
        # Chunked download for large files
        logger.info("Starting chunked download", size_bytes=expected_size, chunk_size=self.chunk_size)
        
        chunks = []
        offset = 0
        
        while offset < expected_size:
            end = min(offset + self.chunk_size - 1, expected_size - 1)
            headers = {"Range": f"bytes={offset}-{end}"}
            
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(download_url, headers=headers, timeout=self.timeout)
            )
            response.raise_for_status()
            
            chunks.append(response.content)
            self.chunks_transferred.labels(operation="download").inc()
            self.bytes_transferred.labels(operation="download").inc(len(response.content))
            
            logger.debug(
                "Chunk downloaded",
                start=offset,
                end=end,
                size=len(response.content)
            )
            
            offset = end + 1
        
        logger.info("Chunked download completed", chunks=len(chunks), size_bytes=expected_size)
        return b''.join(chunks)
    
    async def get_file(self, file_path: str) -> bytes:
        """Get file data from Yandex Disk with chunked download support.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            Raw file data
        """
        remote_path = self._get_full_path(file_path)
        
        start_time = time.time()
        success = False
        error_type = None
        
        try:
            # Get download URL
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._make_request(
                    "GET",
                    "/resources/download",
                    params={"path": remote_path}
                )
            )
            download_url = response.json()["href"]
            
            # Download file (with chunking for large files)
            data = await self._chunked_download(download_url)
            
            logger.info(
                "File downloaded from Yandex Disk",
                file_path=file_path,
                remote_path=remote_path,
                size_bytes=len(data)
            )
            
            success = True
            return data
            
        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                "Failed to get file from Yandex Disk",
                error=str(e),
                file_path=file_path
            )
            raise FileNotFoundError(f"File not found on Yandex Disk: {file_path}")
        finally:
            duration = time.time() - start_time
            self._record_operation("get_file", duration, success, error_type)
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from Yandex Disk.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            True if deleted successfully, False otherwise
        """
        remote_path = self._get_full_path(file_path)
        
        start_time = time.time()
        success = False
        error_type = None
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._make_request(
                    "DELETE",
                    "/resources",
                    params={"path": remote_path, "permanently": "true"}
                )
            )
            
            logger.info(
                "File deleted from Yandex Disk",
                file_path=file_path,
                remote_path=remote_path
            )
            
            success = True
            return True
            
        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                "Failed to delete file from Yandex Disk",
                error=str(e),
                file_path=file_path
            )
            return False
        finally:
            duration = time.time() - start_time
            self._record_operation("delete_file", duration, success, error_type)
    
    async def file_exists(self, file_path: str) -> bool:
        """Check if file exists in Yandex Disk.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            True if file exists, False otherwise
        """
        remote_path = self._get_full_path(file_path)
        
        start_time = time.time()
        success = False
        error_type = None
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._make_request("GET", "/resources", params={"path": remote_path})
            )
            success = True
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:  # Not found
                success = True  # Not an error, just doesn't exist
                return False
            error_type = f"http_{e.response.status_code}"
            raise
        except Exception:
            error_type = "unknown"
            return False
        finally:
            duration = time.time() - start_time
            self._record_operation("file_exists", duration, success, error_type)
    
    def get_public_url(self, file_path: str) -> str:
        """Get public URL for file access.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            Public URL string
        """
        from app.config import settings
        
        # For Yandex Disk, we need to create a public link or use download URL
        # For now, return a special URL that will be handled by the API
        remote_path = self._get_full_path(file_path)
        encoded_path = quote(remote_path)
        return f"{settings.BASE_URL}/api/yandex-disk/file/{encoded_path}"
    
    def get_download_url(self, file_path: str) -> str:
        """Get direct download URL for a file."""
        remote_path = self._get_full_path(file_path)
        
        start_time = time.time()
        success = False
        error_type = None
        
        try:
            response = self._make_request(
                "GET",
                "/resources/download",
                params={"path": remote_path}
            )
            success = True
            return response.json()["href"]
        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                "Failed to get download URL",
                error=str(e),
                file_path=file_path
            )
            raise
        finally:
            duration = time.time() - start_time
            self._record_operation("get_download_url", duration, success, error_type)
    
    def create_public_link(self, file_path: str) -> str:
        """Create a public link for a file."""
        remote_path = self._get_full_path(file_path)
        
        start_time = time.time()
        success = False
        error_type = None
        
        try:
            response = self._make_request(
                "PUT",
                "/resources/publish",
                params={"path": remote_path}
            )
            
            # Get public URL
            info_response = self._make_request(
                "GET",
                "/resources",
                params={"path": remote_path, "public_key": True}
            )
            
            public_url = info_response.json().get("public_url")
            if public_url:
                logger.info(
                    "Public link created",
                    file_path=file_path,
                    public_url=public_url
                )
                success = True
                return public_url
            else:
                error_type = "no_public_url"
                raise Exception("Failed to get public URL")
                
        except Exception as e:
            error_type = error_type or type(e).__name__
            logger.error(
                "Failed to create public link",
                error=str(e),
                file_path=file_path
            )
            raise
        finally:
            duration = time.time() - start_time
            self._record_operation("create_public_link", duration, success, error_type)
    
    def get_storage_info(self) -> dict:
        """Get Yandex Disk storage information."""
        start_time = time.time()
        success = False
        error_type = None
        
        try:
            response = self._make_request("GET", "/")
            data = response.json()
            
            success = True
            return {
                "success": True,
                "provider": "yandex_disk",
                "total_space": data.get("total_space", 0),
                "used_space": data.get("used_space", 0),
                "available_space": data.get("total_space", 0) - data.get("used_space", 0),
                "trash_size": data.get("trash_size", 0)
            }
        except Exception as e:
            error_type = type(e).__name__
            logger.error("Failed to get Yandex Disk storage info", error=str(e))
            return {"success": False, "error": str(e)}
        finally:
            duration = time.time() - start_time
            self._record_operation("get_storage_info", duration, success, error_type)
    
    def test_connection(self) -> bool:
        """Test Yandex Disk connection."""
        start_time = time.time()
        success = False
        error_type = None
        
        try:
            response = self._make_request("GET", "/")
            success = response.status_code == 200
            return success
        except Exception as e:
            error_type = type(e).__name__
            logger.error("Yandex Disk connection test failed", error=str(e))
            return False
        finally:
            duration = time.time() - start_time
            self._record_operation("test_connection", duration, success, error_type)
    
    def ensure_directory(self, dir_path: str) -> bool:
        """
        Public method to ensure a directory exists on Yandex Disk.
        
        Args:
            dir_path: Directory path relative to base_path
            
        Returns:
            True if directory exists or was created, False on error
        """
        try:
            full_path = self._get_full_path(dir_path)
            # Run async method in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._ensure_directory_exists(full_path))
            loop.close()
            return result
        except Exception as e:
            logger.error(
                "Failed to ensure directory exists",
                error=str(e),
                dir_path=dir_path
            )
            return False
    
    def ensure_path(self, path: str) -> bool:
        """
        Public method to ensure all directories in a path exist on Yandex Disk.
        Creates parent directories recursively if needed.
        
        Args:
            path: Full path with nested directories (e.g., 'folder/subfolder/file.txt')
            
        Returns:
            True if all directories exist or were created, False on error
        """
        try:
            # Split path and build directory hierarchy
            parts = path.split('/')
            # Remove filename if present (if last part has extension)
            if '.' in parts[-1]:
                parts = parts[:-1]
            
            # Create event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Create each directory level
            current_path = ""
            for part in parts:
                if not part:  # Skip empty parts from double slashes
                    continue
                current_path = f"{current_path}/{part}" if current_path else part
                full_path = self._get_full_path(current_path)
                
                result = loop.run_until_complete(self._ensure_directory_exists(full_path))
                if not result:
                    loop.close()
                    return False
            
            loop.close()
            logger.info("Ensured path exists on Yandex Disk", path=path)
            return True
        except Exception as e:
            logger.error(
                "Failed to ensure path exists",
                error=str(e),
                path=path
            )
            return False
    
    def ensure_order_structure(self, folder_id: str, content_type: str, order_id: str) -> Dict[str, bool]:
        """
        Create the required folder structure for an order on Yandex Disk.
        Structure: {folder_id}/{content_type}/{order_id}/[Image|QR|nft_markers|nft_cache]
        
        Args:
            folder_id: Base folder ID for the company
            content_type: Content type (e.g., 'portraits', 'videos')
            order_id: Unique order identifier
            
        Returns:
            Dict with success status for each subdirectory
        """
        subdirs = ['Image', 'QR', 'nft_markers', 'nft_cache']
        results = {}
        
        try:
            # Create base order path
            base_path = f"{folder_id}/{content_type}/{order_id}"
            self.ensure_path(base_path)
            
            # Create subdirectories
            for subdir in subdirs:
                subdir_path = f"{base_path}/{subdir}"
                success = self.ensure_path(subdir_path)
                results[subdir] = success
                
                if success:
                    logger.info(
                        "Created order subdirectory",
                        folder_id=folder_id,
                        content_type=content_type,
                        order_id=order_id,
                        subdir=subdir
                    )
                else:
                    logger.warning(
                        "Failed to create order subdirectory",
                        folder_id=folder_id,
                        content_type=content_type,
                        order_id=order_id,
                        subdir=subdir
                    )
            
            return results
            
        except Exception as e:
            logger.error(
                "Failed to create order structure",
                error=str(e),
                folder_id=folder_id,
                content_type=content_type,
                order_id=order_id
            )
            return {subdir: False for subdir in subdirs}
    
    def list_directories(self, path: str = "", limit: int = 100, offset: int = 0) -> Dict[str, any]:
        """
        List directories at the given path on Yandex Disk.
        
        Args:
            path: Path to list directories from (relative to base_path, empty for root)
            limit: Maximum number of items to return
            offset: Number of items to skip (for pagination)
            
        Returns:
            Dict with 'items' (list of directory info), 'total' count, 'has_more' flag
        """
        start_time = time.time()
        success = False
        error_type = None
        
        try:
            # Build full path
            if path:
                full_path = self._get_full_path(path)
            else:
                full_path = self.base_path
            
            # Request directory listing from Yandex Disk API
            response = self._make_request(
                "GET",
                "/resources",
                params={
                    "path": full_path,
                    "limit": limit,
                    "offset": offset,
                    "fields": "name,path,type,_embedded.items.name,_embedded.items.path,_embedded.items.type,_embedded.total,_embedded.limit,_embedded.offset"
                }
            )
            
            data = response.json()
            embedded = data.get("_embedded", {})
            all_items = embedded.get("items", [])
            
            # Filter only directories
            directories = [
                {
                    "name": item["name"],
                    "path": item["path"],
                    "type": item["type"]
                }
                for item in all_items
                if item.get("type") == "dir"
            ]
            
            total = len(directories)
            has_more = (offset + limit) < total
            
            logger.info(
                "Listed Yandex Disk directories",
                path=full_path,
                count=len(directories),
                offset=offset,
                limit=limit
            )
            
            success = True
            return {
                "items": directories,
                "total": total,
                "has_more": has_more
            }
            
        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                "Failed to list Yandex Disk directories",
                error=str(e),
                path=path
            )
            raise Exception(f"Failed to list directories: {str(e)}")
        finally:
            duration = time.time() - start_time
            self._record_operation("list_directories", duration, success, error_type)
    
    async def clear_directory_cache(self):
        """Clear directory cache (useful when storage config changes)."""
        await self.directory_cache.clear()
        logger.info("Directory cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get directory cache statistics."""
        return self.directory_cache.get_stats()
    
    def close(self):
        """Close persistent session and cleanup resources."""
        if self.session:
            self.session.close()
            logger.info("Yandex Disk session closed")
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.close()
        except:
            pass
