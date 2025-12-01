"""
Storage folders service for Vertex AR.
Manages local storage folder structure for companies and order content.
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import settings
from logging_setup import get_logger

logger = get_logger(__name__)


class StorageFoldersService:
    """Service for managing storage folder structure."""
    
    # Required subdirectories for each order folder
    REQUIRED_SUBDIRS = ["Image", "QR", "nft_markers", "nft_cache"]
    
    # Base folder name for all Vertex AR content
    BASE_FOLDER_NAME = "vertex_ar_content"
    
    def __init__(self):
        """Initialize storage folders service."""
        self.storage_root = settings.STORAGE_ROOT
        self._ensure_base_folder()
    
    def _ensure_base_folder(self) -> Path:
        """
        Ensure the base vertex_ar_content folder exists.
        
        Returns:
            Path to the base folder
        """
        base_path = self.storage_root / self.BASE_FOLDER_NAME
        try:
            base_path.mkdir(parents=True, exist_ok=True)
            logger.info(
                "Base storage folder verified",
                path=str(base_path),
                exists=base_path.exists()
            )
            return base_path
        except Exception as exc:
            logger.error(
                "Failed to create base storage folder",
                path=str(base_path),
                error=str(exc)
            )
            raise
    
    def normalize_folder_name(self, name: str) -> str:
        """
        Normalize folder name to contain only letters, digits, dashes, and underscores.
        
        Args:
            name: Raw folder name
            
        Returns:
            Normalized folder name
            
        Raises:
            ValueError: If name is invalid after normalization
        """
        if not name or not name.strip():
            raise ValueError("Folder name cannot be empty")
        
        name = name.strip()
        
        # Check if name matches allowed pattern
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise ValueError(
                "Folder name can only contain letters, digits, dashes, and underscores"
            )
        
        return name
    
    def get_company_storage_root(self, company_id: str, content_type: Optional[str] = None) -> Path:
        """
        Resolve storage root for a company.
        
        Args:
            company_id: Company identifier
            content_type: Optional content type subdirectory
            
        Returns:
            Path to company storage root
        """
        base_path = self.storage_root / self.BASE_FOLDER_NAME / company_id
        
        if content_type:
            base_path = base_path / content_type
        
        return base_path
    
    def verify_permissions(self, path: Path) -> Dict[str, bool]:
        """
        Verify read/write/execute permissions for a path.
        
        Args:
            path: Path to check
            
        Returns:
            Dictionary with permission flags
        """
        permissions = {
            "exists": path.exists(),
            "readable": False,
            "writable": False,
            "executable": False,
        }
        
        if permissions["exists"]:
            permissions["readable"] = os.access(path, os.R_OK)
            permissions["writable"] = os.access(path, os.W_OK)
            permissions["executable"] = os.access(path, os.X_OK)
        
        return permissions
    
    def list_order_folders(
        self,
        company_id: str,
        content_type: Optional[str] = None
    ) -> List[Dict[str, any]]:
        """
        List existing order folders for a company.
        
        Args:
            company_id: Company identifier
            content_type: Optional content type filter
            
        Returns:
            List of folder information dictionaries
        """
        base_path = self.get_company_storage_root(company_id)
        
        if not base_path.exists():
            logger.info(
                "Company storage root does not exist",
                company_id=company_id,
                path=str(base_path)
            )
            return []
        
        folders = []
        
        # If content_type specified, only look in that subdirectory
        if content_type:
            content_path = base_path / content_type
            if content_path.exists() and content_path.is_dir():
                folders.extend(self._scan_content_type_folder(content_type, content_path))
        else:
            # Scan all content type subdirectories
            for item in base_path.iterdir():
                if item.is_dir():
                    content_type_name = item.name
                    folders.extend(self._scan_content_type_folder(content_type_name, item))
        
        return folders
    
    def _scan_content_type_folder(self, content_type: str, path: Path) -> List[Dict[str, any]]:
        """
        Scan a content type folder for order folders.
        
        Args:
            content_type: Content type name
            path: Path to content type folder
            
        Returns:
            List of folder information dictionaries
        """
        folders = []
        
        try:
            for item in path.iterdir():
                if item.is_dir():
                    folder_info = {
                        "folder_name": item.name,
                        "content_type": content_type,
                        "full_path": str(item),
                        "has_required_subdirs": self._check_required_subdirs(item),
                        "is_empty": self._is_folder_empty(item),
                    }
                    folders.append(folder_info)
        except Exception as exc:
            logger.error(
                "Error scanning content type folder",
                content_type=content_type,
                path=str(path),
                error=str(exc)
            )
        
        return folders
    
    def _check_required_subdirs(self, folder_path: Path) -> Dict[str, bool]:
        """
        Check if all required subdirectories exist.
        
        Args:
            folder_path: Path to order folder
            
        Returns:
            Dictionary mapping subdirectory names to existence flags
        """
        return {
            subdir: (folder_path / subdir).exists()
            for subdir in self.REQUIRED_SUBDIRS
        }
    
    def _is_folder_empty(self, folder_path: Path) -> bool:
        """
        Check if a folder is empty (no files in any subdirectory).
        
        Args:
            folder_path: Path to check
            
        Returns:
            True if folder is empty, False otherwise
        """
        try:
            for item in folder_path.rglob("*"):
                if item.is_file():
                    return False
            return True
        except Exception as exc:
            logger.error(
                "Error checking if folder is empty",
                path=str(folder_path),
                error=str(exc)
            )
            return False
    
    def create_order_folder(
        self,
        company_id: str,
        content_type: str,
        folder_name: str
    ) -> Tuple[bool, str, Optional[Path]]:
        """
        Create an order folder with required subdirectory structure.
        
        Args:
            company_id: Company identifier
            content_type: Content type (e.g., 'portraits', 'diplomas')
            folder_name: Folder name for the order
            
        Returns:
            Tuple of (success, message, path)
        """
        try:
            # Normalize folder name
            normalized_name = self.normalize_folder_name(folder_name)
            
            # Get target path
            base_path = self.get_company_storage_root(company_id, content_type)
            folder_path = base_path / normalized_name
            
            # Check if folder already exists
            if folder_path.exists():
                return False, f"Folder '{normalized_name}' already exists", None
            
            # Verify parent directory permissions
            base_path.mkdir(parents=True, exist_ok=True)
            permissions = self.verify_permissions(base_path)
            
            if not permissions.get("writable", False):
                return False, "Insufficient permissions to create folder", None
            
            # Create main folder
            folder_path.mkdir(parents=True, exist_ok=True)
            
            # Create required subdirectories
            for subdir in self.REQUIRED_SUBDIRS:
                subdir_path = folder_path / subdir
                subdir_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(
                "Created order folder with subdirectories",
                company_id=company_id,
                content_type=content_type,
                folder_name=normalized_name,
                path=str(folder_path)
            )
            
            return True, f"Folder '{normalized_name}' created successfully", folder_path
            
        except ValueError as exc:
            logger.warning(
                "Invalid folder name",
                company_id=company_id,
                folder_name=folder_name,
                error=str(exc)
            )
            return False, str(exc), None
        except Exception as exc:
            logger.error(
                "Failed to create order folder",
                company_id=company_id,
                content_type=content_type,
                folder_name=folder_name,
                error=str(exc)
            )
            return False, f"Failed to create folder: {str(exc)}", None
    
    def delete_order_folder(
        self,
        company_id: str,
        content_type: str,
        folder_name: str,
        force: bool = False
    ) -> Tuple[bool, str]:
        """
        Delete an order folder.
        
        Args:
            company_id: Company identifier
            content_type: Content type
            folder_name: Folder name to delete
            force: If True, delete even if not empty (default: False)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Normalize folder name
            normalized_name = self.normalize_folder_name(folder_name)
            
            # Get target path
            folder_path = self.get_company_storage_root(company_id, content_type) / normalized_name
            
            # Check if folder exists
            if not folder_path.exists():
                return False, f"Folder '{normalized_name}' does not exist"
            
            # Check if folder is empty (unless force is True)
            if not force and not self._is_folder_empty(folder_path):
                return False, f"Folder '{normalized_name}' is not empty. Cannot delete."
            
            # Delete the folder
            import shutil
            shutil.rmtree(folder_path)
            
            logger.info(
                "Deleted order folder",
                company_id=company_id,
                content_type=content_type,
                folder_name=normalized_name,
                path=str(folder_path),
                force=force
            )
            
            return True, f"Folder '{normalized_name}' deleted successfully"
            
        except ValueError as exc:
            logger.warning(
                "Invalid folder name",
                company_id=company_id,
                folder_name=folder_name,
                error=str(exc)
            )
            return False, str(exc)
        except Exception as exc:
            logger.error(
                "Failed to delete order folder",
                company_id=company_id,
                content_type=content_type,
                folder_name=folder_name,
                error=str(exc)
            )
            return False, f"Failed to delete folder: {str(exc)}"
    
    def get_storage_status(self, company_id: str) -> Dict[str, any]:
        """
        Get storage status and configuration for a company.
        
        Args:
            company_id: Company identifier
            
        Returns:
            Dictionary with storage status information
        """
        base_path = self.get_company_storage_root(company_id)
        permissions = self.verify_permissions(base_path)
        
        # Count folders by content type
        content_types = {}
        if base_path.exists():
            for item in base_path.iterdir():
                if item.is_dir():
                    content_type = item.name
                    folder_count = sum(1 for _ in item.iterdir() if _.is_dir())
                    content_types[content_type] = folder_count
        
        return {
            "company_id": company_id,
            "storage_root": str(self.storage_root),
            "company_path": str(base_path),
            "permissions": permissions,
            "content_types": content_types,
            "is_ready": permissions.get("writable", False) and permissions.get("readable", False),
        }


# Global service instance
_storage_folders_service: Optional[StorageFoldersService] = None


def get_storage_folders_service() -> StorageFoldersService:
    """Get global storage folders service instance."""
    global _storage_folders_service
    if _storage_folders_service is None:
        _storage_folders_service = StorageFoldersService()
    return _storage_folders_service
