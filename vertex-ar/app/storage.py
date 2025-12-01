"""
Base storage adapter interface for Vertex AR.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict, Any


class StorageAdapter(ABC):
    """Abstract base class for storage adapters."""
    
    @abstractmethod
    async def save_file(self, file_data: bytes, file_path: str) -> str:
        """Save file data to storage.
        
        Args:
            file_data: Raw file data
            file_path: Destination path within storage
            
        Returns:
            Public URL or path to access the file
        """
        pass
    
    @abstractmethod
    async def get_file(self, file_path: str) -> bytes:
        """Get file data from storage.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            Raw file data
        """
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from storage.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """Check if file exists in storage.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_public_url(self, file_path: str) -> str:
        """Get public URL for file access.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            Public URL string
        """
        pass
    
    @abstractmethod
    async def create_directory(self, dir_path: str) -> bool:
        """Create a directory in storage.
        
        Args:
            dir_path: Directory path to create
            
        Returns:
            True if created successfully or already exists
        """
        pass
    
    @abstractmethod
    async def directory_exists(self, dir_path: str) -> bool:
        """Check if directory exists in storage.
        
        Args:
            dir_path: Directory path to check
            
        Returns:
            True if directory exists
        """
        pass
    
    @abstractmethod
    async def list_directories(self, base_path: str = "") -> List[str]:
        """List directories at the given path.
        
        Args:
            base_path: Base path to list directories from
            
        Returns:
            List of directory names (not full paths)
        """
        pass
    
    async def provision_hierarchy(
        self,
        company_slug: str,
        category_slugs: List[str],
        subfolders: List[str]
    ) -> Dict[str, Any]:
        """
        Provision complete folder hierarchy for company and categories.
        Creates: {company_slug}/{category_slug}/{subfolder} for each combination.
        
        Args:
            company_slug: Company identifier slug
            category_slugs: List of category slugs
            subfolders: List of subfolder names to create (e.g., Image, QR, nft_markers, nft_cache)
            
        Returns:
            Dictionary with provisioning results
        """
        created_paths = []
        failed_paths = []
        hierarchy = {}
        
        for category_slug in category_slugs:
            category_paths = []
            
            # Base category path
            base_path = f"{company_slug}/{category_slug}"
            
            try:
                # Create base category directory
                await self.create_directory(base_path)
                category_paths.append(base_path)
                
                # Create subfolders
                for subfolder in subfolders:
                    subfolder_path = f"{base_path}/{subfolder}"
                    await self.create_directory(subfolder_path)
                    category_paths.append(subfolder_path)
                
                created_paths.extend(category_paths)
                hierarchy[category_slug] = {
                    "base_path": base_path,
                    "subfolders": subfolders,
                    "success": True
                }
                
            except Exception as e:
                failed_paths.append({
                    "category": category_slug,
                    "path": base_path,
                    "error": str(e)
                })
                hierarchy[category_slug] = {
                    "base_path": base_path,
                    "success": False,
                    "error": str(e)
                }
        
        return {
            "success": len(failed_paths) == 0,
            "company_slug": company_slug,
            "categories_provisioned": len(category_slugs),
            "total_paths_created": len(created_paths),
            "hierarchy": hierarchy,
            "created_paths": created_paths,
            "failed_paths": failed_paths
        }