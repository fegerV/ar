"""
Unified Storage Adapter for Vertex AR
Supports local file storage and remote MinIO S3-compatible storage
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StorageAdapter(ABC):
    """Abstract base class for storage adapters"""
    
    @abstractmethod
    def upload_file(self, file_content: bytes, object_name: str, content_type: str = "application/octet-stream") -> Optional[str]:
        """Upload file to storage"""
        pass
    
    @abstractmethod
    def download_file(self, object_name: str) -> Optional[bytes]:
        """Download file from storage"""
        pass
    
    @abstractmethod
    def delete_file(self, object_name: str) -> bool:
        """Delete file from storage"""
        pass
    
    @abstractmethod
    def file_exists(self, object_name: str) -> bool:
        """Check if file exists in storage"""
        pass
    
    @abstractmethod
    def get_file_url(self, object_name: str) -> Optional[str]:
        """Get URL for accessing file"""
        pass


class LocalStorageAdapter(StorageAdapter):
    """Local filesystem storage adapter"""
    
    def __init__(self):
        self.bucket_name = os.getenv("MINIO_BUCKET", "vertex-art-bucket")
        base_dir = Path(__file__).resolve().parent
        storage_path = os.getenv("STORAGE_PATH", "./storage")
        
        # Support both relative and absolute paths
        if Path(storage_path).is_absolute():
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = base_dir / storage_path / self.bucket_name
        
        # Create storage directory if it doesn't exist
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalStorageAdapter initialized with path: {self.storage_path}")
    
    def upload_file(self, file_content: bytes, object_name: str, content_type: str = "application/octet-stream") -> Optional[str]:
        """Upload file to local storage"""
        try:
            # Create subdirectories if needed
            file_path = self.storage_path / object_name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"File {object_name} uploaded successfully to {file_path}")
            return f"file://{file_path}"
        except Exception as e:
            logger.error(f"Error uploading file {object_name}: {str(e)}")
            return None
    
    def download_file(self, object_name: str) -> Optional[bytes]:
        """Download file from local storage"""
        try:
            file_path = self.storage_path / object_name
            
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    content = f.read()
                logger.info(f"File {object_name} retrieved successfully, size: {len(content)} bytes")
                return content
            else:
                logger.warning(f"File {object_name} not found")
                return None
        except Exception as e:
            logger.error(f"Error retrieving file {object_name}: {str(e)}")
            return None
    
    def delete_file(self, object_name: str) -> bool:
        """Delete file from local storage"""
        try:
            file_path = self.storage_path / object_name
            
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File {object_name} deleted successfully")
                return True
            else:
                logger.warning(f"File {object_name} not found for deletion")
                return False
        except Exception as e:
            logger.error(f"Error deleting file {object_name}: {str(e)}")
            return False
    
    def file_exists(self, object_name: str) -> bool:
        """Check if file exists in local storage"""
        file_path = self.storage_path / object_name
        return file_path.exists()
    
    def get_file_url(self, object_name: str) -> Optional[str]:
        """Get URL for accessing file"""
        if self.file_exists(object_name):
            base_url = os.getenv("BASE_URL", "http://localhost:8000")
            return f"{base_url}/storage/{object_name}"
        return None


class MinIOStorageAdapter(StorageAdapter):
    """MinIO S3-compatible storage adapter (supports local and remote MinIO)"""
    
    def __init__(self, lazy_init: bool = False):
        from minio import Minio
        from minio.error import S3Error
        
        self.S3Error = S3Error
        self._load_config()
        self._initialize_client()
        
        # Only ensure bucket exists if not in lazy mode
        if not lazy_init:
            self._ensure_bucket_exists()
    
    def _load_config(self):
        """Load configuration from environment variables"""
        original_endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        
        # Remove http:// or https:// prefix if present
        if original_endpoint.startswith("http://") or original_endpoint.startswith("https://"):
            self.minio_endpoint = original_endpoint.split("://")[1]
        else:
            self.minio_endpoint = original_endpoint
        
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "admin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "password123")
        self.bucket_name = os.getenv("MINIO_BUCKET", "vertex-art-bucket")
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        
        # Public URL for accessing files (can be different from endpoint for remote MinIO)
        self.public_url = os.getenv("MINIO_PUBLIC_URL", f"{'https' if self.secure else 'http'}://{self.minio_endpoint}")
        
        logger.info(f"MinIO configuration: endpoint={self.minio_endpoint}, bucket={self.bucket_name}, secure={self.secure}")
    
    def _initialize_client(self):
        """Initialize MinIO client"""
        from minio import Minio
        
        self.client = Minio(
            self.minio_endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        logger.info("MinIO client initialized successfully")
    
    def _ensure_bucket_exists(self):
        """Ensure bucket exists, create if it doesn't"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Bucket {self.bucket_name} created")
            else:
                logger.info(f"Bucket {self.bucket_name} already exists")
        except self.S3Error as e:
            logger.error(f"Error working with bucket: {e}")
            raise
    
    def upload_file(self, file_content: bytes, object_name: str, content_type: str = "application/octet-stream") -> Optional[str]:
        """Upload file to MinIO"""
        try:
            from io import BytesIO
            
            result = self.client.put_object(
                self.bucket_name,
                object_name,
                data=BytesIO(file_content),
                length=len(file_content),
                content_type=content_type
            )
            logger.info(f"File {object_name} uploaded to {self.bucket_name}")
            return f"{self.public_url}/{self.bucket_name}/{result.object_name}"
        except self.S3Error as e:
            logger.error(f"Error uploading file {object_name}: {e}")
            return None
    
    def download_file(self, object_name: str) -> Optional[bytes]:
        """Download file from MinIO"""
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            try:
                content = response.read()
                logger.info(f"File {object_name} retrieved successfully, size: {len(content)} bytes")
                return content
            finally:
                response.close()
                response.release_conn()
        except self.S3Error as e:
            logger.error(f"Error retrieving file {object_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"General error retrieving file {object_name}: {e}")
            return None
    
    def delete_file(self, object_name: str) -> bool:
        """Delete file from MinIO"""
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"File {object_name} deleted")
            return True
        except self.S3Error as e:
            logger.error(f"Error deleting file {object_name}: {e}")
            return False
    
    def file_exists(self, object_name: str) -> bool:
        """Check if file exists in MinIO"""
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except self.S3Error:
            return False
    
    def get_file_url(self, object_name: str) -> Optional[str]:
        """Get URL for accessing file"""
        if self.file_exists(object_name):
            return f"{self.public_url}/{self.bucket_name}/{object_name}"
        return None


class StorageFactory:
    """Factory for creating storage adapters based on configuration"""
    
    _instance: Optional[StorageAdapter] = None
    
    @classmethod
    def get_storage(cls) -> StorageAdapter:
        """Get or create storage adapter instance"""
        if cls._instance is None:
            cls._instance = cls.create_storage()
        return cls._instance
    
    @classmethod
    def create_storage(cls) -> StorageAdapter:
        """Create storage adapter based on STORAGE_TYPE environment variable"""
        storage_type = os.getenv("STORAGE_TYPE", "local").lower()
        
        if storage_type == "minio":
            logger.info("Using MinIO storage adapter (remote or local)")
            return MinIOStorageAdapter()
        elif storage_type == "local":
            logger.info("Using local file storage adapter")
            return LocalStorageAdapter()
        else:
            logger.warning(f"Unknown storage type '{storage_type}', defaulting to local storage")
            return LocalStorageAdapter()
    
    @classmethod
    def reset(cls):
        """Reset storage instance (useful for testing)"""
        cls._instance = None


# Global storage instance
_storage_instance: Optional[StorageAdapter] = None


def get_storage() -> StorageAdapter:
    """Get global storage adapter instance"""
    global _storage_instance
    
    # Don't initialize storage in test mode
    if os.getenv("RUNNING_TESTS") == "1":
        if _storage_instance is None:
            _storage_instance = StorageFactory.create_storage()
        return _storage_instance
    
    if _storage_instance is None:
        _storage_instance = StorageFactory.get_storage()
    
    return _storage_instance


# Backward compatibility functions
def upload_file(file_content: bytes, object_name: str, content_type: str = "application/octet-stream") -> Optional[str]:
    """Upload file to storage (backward compatibility)"""
    return get_storage().upload_file(file_content, object_name, content_type)


def get_file(object_name: str) -> Optional[bytes]:
    """Download file from storage (backward compatibility)"""
    return get_storage().download_file(object_name)


def delete_file(object_name: str) -> bool:
    """Delete file from storage (backward compatibility)"""
    return get_storage().delete_file(object_name)


def file_exists(object_name: str) -> bool:
    """Check if file exists in storage (backward compatibility)"""
    return get_storage().file_exists(object_name)


def get_nft_marker_urls(record_id: str) -> Dict[str, Optional[str]]:
    """Get URLs for NFT markers (backward compatibility)"""
    try:
        storage = get_storage()
        marker_extensions = ["iset", "fset", "fset3"]
        marker_urls = {}
        
        for ext in marker_extensions:
            file_name = f"nft-markers/{record_id}.{ext}"
            marker_urls[ext] = storage.get_file_url(file_name)
            
            if marker_urls[ext] is None:
                logger.warning(f"NFT marker file {file_name} not found in storage")
        
        return marker_urls
    except Exception as e:
        logger.error(f"Error getting NFT marker URLs: {e}")
        return {"iset": None, "fset": None, "fset3": None}
