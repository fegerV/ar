"""
Storage manager for Vertex AR.
Manages different storage adapters for different content types.
"""
from pathlib import Path
from typing import Dict, Any, Optional

from app.storage import StorageAdapter
from app.storage_local import LocalStorageAdapter
from app.storage_minio import MinioStorageAdapter
from app.storage_yandex import YandexDiskStorageAdapter
from storage_config import get_storage_config
from logging_setup import get_logger

logger = get_logger(__name__)


class StorageManager:
    """Manages storage adapters for different content types."""
    
    def __init__(self, storage_root: Optional[Path] = None):
        """
        Initialize storage manager.
        
        Args:
            storage_root: Root directory for local storage
        """
        self.storage_root = storage_root or Path("storage")
        self.config = get_storage_config()
        self.adapters: Dict[str, StorageAdapter] = {}
        self._initialize_adapters()
    
    def _initialize_adapters(self):
        """Initialize storage adapters for different content types."""
        content_types = ["portraits", "videos", "previews", "nft_markers"]
        
        for content_type in content_types:
            storage_type = self.config.get_storage_type(content_type)
            adapter = self._create_adapter(storage_type, content_type)
            self.adapters[content_type] = adapter
            
            logger.info(
                "Storage adapter initialized",
                content_type=content_type,
                storage_type=storage_type
            )
    
    def _create_adapter(self, storage_type: str, content_type: str) -> StorageAdapter:
        """Create storage adapter for given type and content."""
        if storage_type == "local":
            return LocalStorageAdapter(self.storage_root)
        
        elif storage_type == "minio":
            minio_config = self.config.get_minio_config()
            return MinioStorageAdapter(
                endpoint=minio_config.get("endpoint", "localhost:9000"),
                access_key=minio_config.get("access_key", "minioadmin"),
                secret_key=minio_config.get("secret_key", "minioadmin"),
                bucket=minio_config.get("bucket", "vertex-ar")
            )
        
        elif storage_type == "yandex_disk":
            token = self.config.get_yandex_token()
            if not token:
                logger.error("Yandex Disk token not configured, falling back to local storage")
                return LocalStorageAdapter(self.storage_root)
            
            yandex_config = self.config.get_yandex_config(content_type)
            base_path = yandex_config.get("base_path", f"vertex-ar/{content_type}")
            
            return YandexDiskStorageAdapter(
                oauth_token=token,
                base_path=base_path
            )
        
        else:
            logger.warning(
                "Unknown storage type, falling back to local",
                storage_type=storage_type
            )
            return LocalStorageAdapter(self.storage_root)
    
    def get_adapter(self, content_type: str) -> StorageAdapter:
        """Get storage adapter for content type."""
        if content_type not in self.adapters:
            logger.error(
                "Unknown content type, using local storage",
                content_type=content_type
            )
            return self.adapters.get("portraits", LocalStorageAdapter(self.storage_root))
        
        return self.adapters[content_type]
    
    def reinitialize_adapters(self):
        """Reinitialize all adapters (useful after config change)."""
        self._initialize_adapters()
    
    async def save_file(self, file_data: bytes, file_path: str, content_type: str = "portraits") -> str:
        """Save file using appropriate adapter.
        
        Args:
            file_data: Raw file data
            file_path: Destination path within storage
            content_type: Type of content (portraits, videos, previews, nft_markers)
            
        Returns:
            Public URL to access the file
        """
        adapter = self.get_adapter(content_type)
        return await adapter.save_file(file_data, file_path)
    
    async def get_file(self, file_path: str, content_type: str = "portraits") -> bytes:
        """Get file using appropriate adapter.
        
        Args:
            file_path: Path to the file in storage
            content_type: Type of content
            
        Returns:
            Raw file data
        """
        adapter = self.get_adapter(content_type)
        return await adapter.get_file(file_path)
    
    async def delete_file(self, file_path: str, content_type: str = "portraits") -> bool:
        """Delete file using appropriate adapter.
        
        Args:
            file_path: Path to the file in storage
            content_type: Type of content
            
        Returns:
            True if deleted successfully
        """
        adapter = self.get_adapter(content_type)
        return await adapter.delete_file(file_path)
    
    async def file_exists(self, file_path: str, content_type: str = "portraits") -> bool:
        """Check if file exists using appropriate adapter.
        
        Args:
            file_path: Path to the file in storage
            content_type: Type of content
            
        Returns:
            True if file exists
        """
        adapter = self.get_adapter(content_type)
        return await adapter.file_exists(file_path)
    
    def get_public_url(self, file_path: str, content_type: str = "portraits") -> str:
        """Get public URL using appropriate adapter.
        
        Args:
            file_path: Path to the file in storage
            content_type: Type of content
            
        Returns:
            Public URL string
        """
        adapter = self.get_adapter(content_type)
        return adapter.get_public_url(file_path)
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage information for all configured adapters."""
        info = {
            "content_types": {},
            "global": {}
        }
        
        for content_type, adapter in self.adapters.items():
            storage_type = self.config.get_storage_type(content_type)
            info["content_types"][content_type] = {
                "storage_type": storage_type,
                "adapter_type": type(adapter).__name__
            }
            
            # Get additional info for Yandex Disk adapters
            if isinstance(adapter, YandexDiskStorageAdapter):
                try:
                    yandex_info = adapter.get_storage_info()
                    info["content_types"][content_type]["yandex_disk_info"] = yandex_info
                except Exception as e:
                    logger.error("Failed to get Yandex Disk info", error=str(e))
        
        return info


# Global storage manager instance
_storage_manager = None


def get_storage_manager(storage_root: Optional[Path] = None) -> StorageManager:
    """Get global storage manager instance."""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager(storage_root)
    return _storage_manager