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
from app.storage_utils import is_local_storage
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
        self._company_adapters: Dict[str, Dict[str, StorageAdapter]] = {}
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
        if is_local_storage(storage_type):
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
            
            # Get tuning parameters from settings
            from app.config import settings
            
            return YandexDiskStorageAdapter(
                oauth_token=token,
                base_path=base_path,
                timeout=settings.YANDEX_REQUEST_TIMEOUT,
                chunk_size_mb=settings.YANDEX_CHUNK_SIZE_MB,
                upload_concurrency=settings.YANDEX_UPLOAD_CONCURRENCY,
                cache_ttl=settings.YANDEX_DIRECTORY_CACHE_TTL,
                cache_size=settings.YANDEX_DIRECTORY_CACHE_SIZE,
                pool_connections=settings.YANDEX_SESSION_POOL_CONNECTIONS,
                pool_maxsize=settings.YANDEX_SESSION_POOL_MAXSIZE
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
    
    def get_company_adapter(self, company_id: str, content_type: str) -> StorageAdapter:
        """Get storage adapter for specific company and content type."""
        # Check if we have cached adapter for this company
        if company_id in self._company_adapters and content_type in self._company_adapters[company_id]:
            return self._company_adapters[company_id][content_type]
        
        # Get company storage configuration from database
        from app.main import get_current_app
        app = get_current_app()
        database = app.state.database
        
        company = database.get_company(company_id)
        if not company:
            logger.error(f"Company not found: {company_id}, using default storage")
            return self.get_adapter(content_type)
        
        storage_type = company.get('storage_type', 'local')
        storage_connection_id = company.get('storage_connection_id')
        yandex_disk_folder_id = company.get('yandex_disk_folder_id')
        
        # Create adapter based on company configuration
        adapter = self._create_adapter_for_company(
            storage_type, 
            storage_connection_id, 
            content_type,
            yandex_disk_folder_id
        )
        
        # Cache the adapter
        if company_id not in self._company_adapters:
            self._company_adapters[company_id] = {}
        self._company_adapters[company_id][content_type] = adapter
        
        logger.info(
            "Created company storage adapter",
            company_id=company_id,
            content_type=content_type,
            storage_type=storage_type,
            storage_connection_id=storage_connection_id,
            yandex_disk_folder_id=yandex_disk_folder_id
        )
        
        return adapter
    
    def _create_adapter_for_company(
        self, 
        storage_type: str, 
        storage_connection_id: Optional[str], 
        content_type: str,
        yandex_disk_folder_id: Optional[str] = None
    ) -> StorageAdapter:
        """Create storage adapter for company-specific configuration."""
        if is_local_storage(storage_type):
            return LocalStorageAdapter(self.storage_root)
        
        elif storage_type in ("minio", "yandex_disk") and storage_connection_id:
            # Get storage connection from database
            from app.main import get_current_app
            app = get_current_app()
            database = app.state.database
            
            connection = database.get_storage_connection(storage_connection_id)
            if not connection or not connection.get('is_active', False):
                logger.error(f"Storage connection not found or inactive: {storage_connection_id}, falling back to local")
                return LocalStorageAdapter(self.storage_root)
            
            config = connection.get('config', {})
            
            if storage_type == "minio":
                return MinioStorageAdapter(
                    endpoint=config.get("endpoint", "localhost:9000"),
                    access_key=config.get("access_key", "minioadmin"),
                    secret_key=config.get("secret_key", "minioadmin"),
                    bucket=config.get("bucket", "vertex-ar"),
                    secure=config.get("secure", False)
                )
            
            elif storage_type == "yandex_disk":
                token = config.get("oauth_token", "")
                if not token:
                    logger.error(f"Yandex Disk token not configured for connection {storage_connection_id}, falling back to local")
                    return LocalStorageAdapter(self.storage_root)
                
                # Honor yandex_disk_folder_id as base path if provided
                if yandex_disk_folder_id:
                    base_path = yandex_disk_folder_id
                    logger.info(
                        "Using company-specific Yandex Disk folder",
                        folder_id=yandex_disk_folder_id,
                        content_type=content_type
                    )
                else:
                    base_path = config.get("base_path", f"vertex-ar/{content_type}")
                
                # Get tuning parameters from settings
                from app.config import settings
                
                return YandexDiskStorageAdapter(
                    oauth_token=token,
                    base_path=base_path,
                    timeout=settings.YANDEX_REQUEST_TIMEOUT,
                    chunk_size_mb=settings.YANDEX_CHUNK_SIZE_MB,
                    upload_concurrency=settings.YANDEX_UPLOAD_CONCURRENCY,
                    cache_ttl=settings.YANDEX_DIRECTORY_CACHE_TTL,
                    cache_size=settings.YANDEX_DIRECTORY_CACHE_SIZE,
                    pool_connections=settings.YANDEX_SESSION_POOL_CONNECTIONS,
                    pool_maxsize=settings.YANDEX_SESSION_POOL_MAXSIZE
                )
        
        else:
            logger.warning(
                "Unknown or unsupported storage type for company, falling back to local",
                storage_type=storage_type,
                storage_connection_id=storage_connection_id
            )
            return LocalStorageAdapter(self.storage_root)
    
    def clear_company_cache(self, company_id: Optional[str] = None):
        """Clear cached company adapters."""
        if company_id:
            self._company_adapters.pop(company_id, None)
            logger.info(f"Cleared storage adapter cache for company: {company_id}")
        else:
            self._company_adapters.clear()
            logger.info("Cleared all company storage adapter caches")
    
    def get_adapter_for_content(self, company_id: Optional[str], content_type: str) -> StorageAdapter:
        """Get storage adapter for content, using company-specific if available."""
        if company_id:
            return self.get_company_adapter(company_id, content_type)
        return self.get_adapter(content_type)
    
    def get_storage_type_for_content(self, company_id: Optional[str], content_type: str) -> str:
        """
        Get the storage type configured for a specific company and content type.
        
        Args:
            company_id: Company ID (optional)
            content_type: Type of content (portraits, videos, etc.)
            
        Returns:
            Storage type string ('local', 'minio', 'yandex_disk')
        """
        if company_id:
            from app.main import get_current_app
            app = get_current_app()
            database = app.state.database
            
            company = database.get_company(company_id)
            if company:
                return company.get('storage_type', 'local')
        
        return self.config.get_storage_type(content_type)
    
    def get_public_url_for_company(self, company_id: Optional[str], file_path: str, content_type: str = "portraits") -> str:
        """
        Get public URL for a file using company-specific adapter.
        
        Args:
            company_id: Company ID (optional)
            file_path: Path to the file in storage
            content_type: Type of content
            
        Returns:
            Public URL string
        """
        if company_id:
            adapter = self.get_company_adapter(company_id, content_type)
        else:
            adapter = self.get_adapter(content_type)
        
        return adapter.get_public_url(file_path)
    
    async def flush_directory_cache(self, company_id: Optional[str] = None, content_type: Optional[str] = None):
        """
        Flush directory cache for Yandex Disk adapters.
        Useful when storage configuration changes or directory structure is modified externally.
        
        Args:
            company_id: Optional company ID to flush cache for specific company adapter
            content_type: Optional content type to flush cache for specific adapter
        """
        adapters_to_flush = []
        
        if company_id and content_type:
            # Flush specific company adapter
            if company_id in self._company_adapters and content_type in self._company_adapters[company_id]:
                adapters_to_flush.append(self._company_adapters[company_id][content_type])
        elif company_id:
            # Flush all adapters for company
            if company_id in self._company_adapters:
                adapters_to_flush.extend(self._company_adapters[company_id].values())
        elif content_type:
            # Flush global adapter for content type
            if content_type in self.adapters:
                adapters_to_flush.append(self.adapters[content_type])
        else:
            # Flush all adapters
            adapters_to_flush.extend(self.adapters.values())
            for company_adapters in self._company_adapters.values():
                adapters_to_flush.extend(company_adapters.values())
        
        # Clear cache for each Yandex adapter
        for adapter in adapters_to_flush:
            if isinstance(adapter, YandexDiskStorageAdapter):
                await adapter.clear_directory_cache()
                logger.info(
                    "Flushed Yandex Disk directory cache",
                    adapter_type=type(adapter).__name__,
                    company_id=company_id,
                    content_type=content_type
                )
    
    def get_yandex_cache_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get directory cache statistics for all Yandex Disk adapters.
        
        Returns:
            Dictionary mapping adapter identifiers to cache stats
        """
        stats = {}
        
        # Get stats from global adapters
        for content_type, adapter in self.adapters.items():
            if isinstance(adapter, YandexDiskStorageAdapter):
                stats[f"global_{content_type}"] = adapter.get_cache_stats()
        
        # Get stats from company adapters
        for company_id, company_adapters in self._company_adapters.items():
            for content_type, adapter in company_adapters.items():
                if isinstance(adapter, YandexDiskStorageAdapter):
                    stats[f"company_{company_id}_{content_type}"] = adapter.get_cache_stats()
        
        return stats
    
    async def provision_company_storage(
        self,
        company_id: str,
        category_slugs: list,
        subfolders: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Provision complete storage hierarchy for a company across all configured storage types.
        
        Args:
            company_id: Company ID
            category_slugs: List of category slugs (content types)
            subfolders: List of subfolder names (defaults to standard subfolders)
            
        Returns:
            Dictionary with provisioning results
        """
        from app.main import get_current_app
        app = get_current_app()
        database = app.state.database
        
        company = database.get_company(company_id)
        if not company:
            raise ValueError(f"Company not found: {company_id}")
        
        if subfolders is None:
            from app.services.folder_service import FolderService
            subfolders = FolderService.STANDARD_SUBFOLDERS
        
        storage_type = company.get('storage_type', 'local')
        company_slug = self._get_company_slug(company)
        
        results = {
            "company_id": company_id,
            "company_slug": company_slug,
            "storage_type": storage_type,
            "categories": category_slugs,
            "subfolders": subfolders
        }
        
        logger.info(
            "Provisioning company storage hierarchy",
            company_id=company_id,
            storage_type=storage_type,
            categories=len(category_slugs)
        )
        
        if is_local_storage(storage_type):
            # Use FolderService for local storage
            from app.services.folder_service import FolderService, FolderCreationError
            try:
                folder_service = FolderService(self.storage_root)
                provision_result = folder_service.provision_company_hierarchy(company, category_slugs)
                results.update(provision_result)
            except FolderCreationError as e:
                logger.error(f"Failed to provision local storage: {e}")
                results["success"] = False
                results["error"] = str(e)
        else:
            # Use storage adapter for remote storage
            try:
                # Get content_type from first category or use 'portraits' as default
                content_type = category_slugs[0] if category_slugs else 'portraits'
                adapter = self.get_company_adapter(company_id, content_type)
                
                provision_result = await adapter.provision_hierarchy(
                    company_slug,
                    category_slugs,
                    subfolders
                )
                results.update(provision_result)
            except Exception as e:
                logger.error(f"Failed to provision remote storage: {e}", exc_info=e)
                results["success"] = False
                results["error"] = str(e)
        
        return results
    
    async def verify_company_storage(
        self,
        company_id: str,
        category_slugs: list
    ) -> Dict[str, Any]:
        """
        Verify that storage hierarchy exists for company and categories.
        
        Args:
            company_id: Company ID
            category_slugs: List of category slugs to verify
            
        Returns:
            Dictionary with verification results
        """
        from app.main import get_current_app
        app = get_current_app()
        database = app.state.database
        
        company = database.get_company(company_id)
        if not company:
            raise ValueError(f"Company not found: {company_id}")
        
        storage_type = company.get('storage_type', 'local')
        
        if is_local_storage(storage_type):
            from app.services.folder_service import FolderService
            folder_service = FolderService(self.storage_root)
            return folder_service.verify_hierarchy(company, category_slugs)
        else:
            # For remote storage, check via adapter
            content_type = category_slugs[0] if category_slugs else 'portraits'
            adapter = self.get_company_adapter(company_id, content_type)
            company_slug = self._get_company_slug(company)
            
            results = {}
            for category_slug in category_slugs:
                base_path = f"{company_slug}/{category_slug}"
                exists = await adapter.directory_exists(base_path)
                results[category_slug] = {
                    "base_path": base_path,
                    "exists": exists
                }
            
            all_exist = all(r["exists"] for r in results.values())
            
            return {
                "company_id": company_id,
                "company_slug": company_slug,
                "storage_type": storage_type,
                "all_exist": all_exist,
                "categories": results
            }
    
    def _get_company_slug(self, company: Dict[str, Any]) -> str:
        """Get or generate slug for company."""
        from app.services.folder_service import FolderService
        return FolderService.slugify(company.get('id', 'default'))


# Global storage manager instance
_storage_manager = None


def get_storage_manager(storage_root: Optional[Path] = None) -> StorageManager:
    """Get global storage manager instance."""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager(storage_root)
    return _storage_manager