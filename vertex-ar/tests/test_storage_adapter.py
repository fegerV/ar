"""
Tests for storage adapter functionality
"""
import os
import pytest
from pathlib import Path
import tempfile

# Set test mode before importing storage
os.environ["RUNNING_TESTS"] = "1"

from vertex-ar.storage_adapter import (
    StorageAdapter,
    LocalStorageAdapter,
    MinIOStorageAdapter,
    StorageFactory,
    get_storage
)


class TestLocalStorageAdapter:
    """Test local storage adapter"""
    
    @pytest.fixture
    def storage(self):
        """Create local storage adapter for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["STORAGE_PATH"] = tmpdir
            adapter = LocalStorageAdapter()
            yield adapter
    
    def test_upload_file(self, storage):
        """Test file upload"""
        content = b"test content"
        result = storage.upload_file(content, "test.txt", "text/plain")
        
        assert result is not None
        assert "test.txt" in result
    
    def test_download_file(self, storage):
        """Test file download"""
        content = b"test content"
        storage.upload_file(content, "test.txt", "text/plain")
        
        downloaded = storage.download_file("test.txt")
        assert downloaded == content
    
    def test_file_exists(self, storage):
        """Test file existence check"""
        content = b"test content"
        storage.upload_file(content, "test.txt", "text/plain")
        
        assert storage.file_exists("test.txt")
        assert not storage.file_exists("nonexistent.txt")
    
    def test_delete_file(self, storage):
        """Test file deletion"""
        content = b"test content"
        storage.upload_file(content, "test.txt", "text/plain")
        
        assert storage.file_exists("test.txt")
        assert storage.delete_file("test.txt")
        assert not storage.file_exists("test.txt")
    
    def test_get_file_url(self, storage):
        """Test getting file URL"""
        content = b"test content"
        storage.upload_file(content, "test.txt", "text/plain")
        
        url = storage.get_file_url("test.txt")
        assert url is not None
        assert "test.txt" in url
    
    def test_subdirectory_support(self, storage):
        """Test uploading files to subdirectories"""
        content = b"test content"
        result = storage.upload_file(content, "subdir/test.txt", "text/plain")
        
        assert result is not None
        assert storage.file_exists("subdir/test.txt")


class TestStorageFactory:
    """Test storage factory"""
    
    def test_factory_creates_local_storage(self):
        """Test factory creates local storage when configured"""
        os.environ["STORAGE_TYPE"] = "local"
        StorageFactory.reset()
        
        storage = StorageFactory.create_storage()
        assert isinstance(storage, LocalStorageAdapter)
    
    def test_factory_singleton(self):
        """Test factory returns same instance"""
        StorageFactory.reset()
        
        storage1 = StorageFactory.get_storage()
        storage2 = StorageFactory.get_storage()
        
        assert storage1 is storage2
    
    def test_factory_reset(self):
        """Test factory reset creates new instance"""
        StorageFactory.reset()
        storage1 = StorageFactory.get_storage()
        
        StorageFactory.reset()
        storage2 = StorageFactory.get_storage()
        
        assert storage1 is not storage2


class TestBackwardCompatibility:
    """Test backward compatibility functions"""
    
    @pytest.fixture
    def setup_storage(self):
        """Setup test storage"""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["STORAGE_TYPE"] = "local"
            os.environ["STORAGE_PATH"] = tmpdir
            StorageFactory.reset()
            yield
    
    def test_upload_file_function(self, setup_storage):
        """Test backward compatible upload_file function"""
        from vertex-ar.storage_adapter import upload_file
        
        content = b"test content"
        result = upload_file(content, "test.txt", "text/plain")
        
        assert result is not None
    
    def test_get_file_function(self, setup_storage):
        """Test backward compatible get_file function"""
        from vertex-ar.storage_adapter import upload_file, get_file
        
        content = b"test content"
        upload_file(content, "test.txt", "text/plain")
        
        downloaded = get_file("test.txt")
        assert downloaded == content
    
    def test_delete_file_function(self, setup_storage):
        """Test backward compatible delete_file function"""
        from vertex-ar.storage_adapter import upload_file, delete_file, file_exists
        
        content = b"test content"
        upload_file(content, "test.txt", "text/plain")
        
        assert delete_file("test.txt")
        assert not file_exists("test.txt")
    
    def test_get_nft_marker_urls(self, setup_storage):
        """Test backward compatible get_nft_marker_urls function"""
        from vertex-ar.storage_adapter import upload_file, get_nft_marker_urls
        
        # Upload test marker files
        for ext in ["iset", "fset", "fset3"]:
            upload_file(b"marker content", f"nft-markers/test.{ext}", "application/octet-stream")
        
        urls = get_nft_marker_urls("test")
        
        assert urls["iset"] is not None
        assert urls["fset"] is not None
        assert urls["fset3"] is not None


class TestMinIOIntegration:
    """Test MinIO integration (if MinIO is available)"""
    
    @pytest.fixture
    def minio_available(self):
        """Check if MinIO is available for testing"""
        try:
            import socket
            endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
            host, port = endpoint.split(":")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((host, int(port)))
            sock.close()
            return result == 0
        except:
            return False
    
    def test_minio_connection(self, minio_available):
        """Test MinIO connection if available"""
        if not minio_available:
            pytest.skip("MinIO not available for testing")
        
        os.environ["STORAGE_TYPE"] = "minio"
        StorageFactory.reset()
        
        storage = StorageFactory.create_storage()
        assert isinstance(storage, MinIOStorageAdapter)


def test_storage_type_configuration():
    """Test different storage type configurations"""
    
    # Test local storage
    os.environ["STORAGE_TYPE"] = "local"
    StorageFactory.reset()
    storage = StorageFactory.create_storage()
    assert isinstance(storage, LocalStorageAdapter)
    
    # Test unknown storage type defaults to local
    os.environ["STORAGE_TYPE"] = "unknown"
    StorageFactory.reset()
    storage = StorageFactory.create_storage()
    assert isinstance(storage, LocalStorageAdapter)
