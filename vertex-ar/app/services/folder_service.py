"""
Folder management service for organizing local storage.
Handles creation and management of folder hierarchy for local storage.
"""
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

from logging_setup import get_logger

logger = get_logger(__name__)


class FolderServiceError(Exception):
    """Base exception for FolderService errors."""
    pass


class FolderCreationError(FolderServiceError):
    """Exception raised when folder creation fails."""
    pass


class FolderService:
    """Service for managing local storage folder hierarchy."""
    
    STANDARD_SUBFOLDERS = ["Image", "QR", "nft_markers", "nft_cache"]
    
    def __init__(self, storage_root: Path):
        """
        Initialize folder service.
        
        Args:
            storage_root: Root directory for storage
        """
        self.storage_root = Path(storage_root)
        logger.info("FolderService initialized", storage_root=str(self.storage_root))
    
    @staticmethod
    def slugify(text: str) -> str:
        """
        Convert text to URL-safe slug format.
        
        Args:
            text: Text to slugify
            
        Returns:
            Slugified text safe for filesystem paths
        """
        # Convert to lowercase
        text = text.lower()
        # Replace spaces and special chars with underscore
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '_', text)
        return text.strip('_')
    
    def get_company_slug(self, company: Dict[str, Any]) -> str:
        """
        Get or generate slug for company.
        
        Args:
            company: Company dictionary from database
            
        Returns:
            Company slug for folder naming
        """
        # Use company ID as slug (already safe for filesystem)
        company_id = company.get('id', 'default')
        return self.slugify(company_id)
    
    def build_order_path(
        self,
        company: Dict[str, Any],
        content_type: str,
        order_id: str,
        subfolder: Optional[str] = None
    ) -> Path:
        """
        Build full path for order storage following hierarchy:
        <storage_root>/<folder_path>/<company_slug>/<content_type>/<order_id>/<subfolder>
        
        Args:
            company: Company dictionary from database
            content_type: Type of content (portraits, diplomas, certificates, etc.)
            order_id: Unique order/portrait identifier
            subfolder: Optional subfolder (Image, QR, nft_markers, nft_cache)
            
        Returns:
            Full path for order storage
        """
        # Get storage_folder_path from company, default to company slug
        folder_path = company.get('storage_folder_path')
        if not folder_path:
            folder_path = self.get_company_slug(company)
        
        # Get company slug
        company_slug = self.get_company_slug(company)
        
        # Build path: storage_root / folder_path / company_slug / content_type / order_id
        path = self.storage_root / folder_path / company_slug / content_type / order_id
        
        # Add subfolder if specified
        if subfolder:
            path = path / subfolder
        
        return path
    
    def build_relative_path(
        self,
        company: Dict[str, Any],
        content_type: str,
        order_id: str,
        filename: str,
        subfolder: Optional[str] = None
    ) -> str:
        """
        Build relative path (from storage_root) for storing in database.
        
        Args:
            company: Company dictionary from database
            content_type: Type of content
            order_id: Order identifier
            filename: File name
            subfolder: Optional subfolder
            
        Returns:
            Relative path string for database storage
        """
        # Get storage_folder_path from company, default to company slug
        folder_path = company.get('storage_folder_path')
        if not folder_path:
            folder_path = self.get_company_slug(company)
        
        company_slug = self.get_company_slug(company)
        
        # Build relative path
        parts = [folder_path, company_slug, content_type, order_id]
        if subfolder:
            parts.append(subfolder)
        parts.append(filename)
        
        return "/".join(parts)
    
    def ensure_order_structure(
        self,
        company: Dict[str, Any],
        content_type: str,
        order_id: str
    ) -> Dict[str, Any]:
        """
        Create complete folder structure for an order.
        Creates: Image/, QR/, nft_markers/, nft_cache/ subfolders.
        
        Args:
            company: Company dictionary from database
            content_type: Type of content
            order_id: Order identifier
            
        Returns:
            Dictionary with created paths and status
            
        Raises:
            PermissionError: If folder creation fails due to permissions
            OSError: If folder creation fails for other reasons
        """
        subfolders = ["Image", "QR", "nft_markers", "nft_cache"]
        created_paths = {}
        
        try:
            # Create base order directory
            base_path = self.build_order_path(company, content_type, order_id)
            base_path.mkdir(parents=True, exist_ok=True)
            created_paths["base"] = str(base_path)
            
            logger.info(
                "Created order base directory",
                company_id=company.get('id'),
                content_type=content_type,
                order_id=order_id,
                path=str(base_path)
            )
            
            # Create subfolders
            for subfolder in subfolders:
                subfolder_path = base_path / subfolder
                subfolder_path.mkdir(parents=True, exist_ok=True)
                created_paths[subfolder.lower()] = str(subfolder_path)
            
            logger.info(
                "Created order folder structure",
                company_id=company.get('id'),
                content_type=content_type,
                order_id=order_id,
                subfolders=subfolders
            )
            
            return {
                "success": True,
                "base_path": str(base_path),
                "created_paths": created_paths,
                "subfolders": subfolders
            }
            
        except PermissionError as e:
            logger.error(
                "Permission denied creating order folders",
                company_id=company.get('id'),
                content_type=content_type,
                order_id=order_id,
                error=str(e),
                exc_info=e
            )
            raise PermissionError(
                f"Permission denied creating storage folders for order {order_id}. "
                f"Check filesystem permissions on {self.storage_root}"
            ) from e
        
        except OSError as e:
            logger.error(
                "Failed to create order folders",
                company_id=company.get('id'),
                content_type=content_type,
                order_id=order_id,
                error=str(e),
                exc_info=e
            )
            raise OSError(
                f"Failed to create storage folders for order {order_id}: {str(e)}"
            ) from e
    
    def move_file(self, source: Path, destination: Path) -> None:
        """
        Move file from source to destination, creating parent directories.
        
        Args:
            source: Source file path
            destination: Destination file path
            
        Raises:
            FileNotFoundError: If source file doesn't exist
            PermissionError: If move fails due to permissions
            OSError: If move fails for other reasons
        """
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
        
        try:
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file (os.rename is atomic on same filesystem)
            if source.parent == destination.parent:
                # Same directory, just rename
                source.rename(destination)
            else:
                # Different directory, need to move
                import shutil
                shutil.move(str(source), str(destination))
            
            logger.debug(
                "Moved file",
                source=str(source),
                destination=str(destination)
            )
            
        except PermissionError as e:
            logger.error(
                "Permission denied moving file",
                source=str(source),
                destination=str(destination),
                error=str(e)
            )
            raise
        
        except OSError as e:
            logger.error(
                "Failed to move file",
                source=str(source),
                destination=str(destination),
                error=str(e)
            )
            raise
    
    def cleanup_temp_directory(self, temp_dir: Path) -> None:
        """
        Clean up temporary directory after moving files.
        
        Args:
            temp_dir: Temporary directory to remove
        """
        try:
            import shutil
            if temp_dir.exists() and temp_dir.is_dir():
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.debug("Cleaned up temp directory", path=str(temp_dir))
        except Exception as e:
            logger.warning(
                "Failed to cleanup temp directory",
                path=str(temp_dir),
                error=str(e)
            )
    
    def provision_company_hierarchy(
        self,
        company: Dict[str, Any],
        category_slugs: List[str]
    ) -> Dict[str, Any]:
        """
        Proactively provision the complete folder hierarchy for a company and its categories.
        Creates: {folder_path}/{company_slug}/{category_slug}/{Image|QR|nft_markers|nft_cache}
        
        Args:
            company: Company dictionary from database
            category_slugs: List of category slugs (content types)
            
        Returns:
            Dictionary with provisioning results and created paths
            
        Raises:
            FolderCreationError: If folder creation fails
        """
        created_paths = []
        failed_paths = []
        hierarchy = {}
        
        folder_path = company.get('storage_folder_path')
        if not folder_path:
            folder_path = self.get_company_slug(company)
        
        company_slug = self.get_company_slug(company)
        company_id = company.get('id', 'unknown')
        
        logger.info(
            "Provisioning company storage hierarchy",
            company_id=company_id,
            company_slug=company_slug,
            folder_path=folder_path,
            category_count=len(category_slugs)
        )
        
        try:
            for category_slug in category_slugs:
                category_paths = []
                
                # Build base category path
                base_path = self.storage_root / folder_path / company_slug / category_slug
                
                try:
                    # Create base category directory
                    base_path.mkdir(parents=True, exist_ok=True)
                    category_paths.append(str(base_path))
                    
                    # Create standard subfolders
                    for subfolder in self.STANDARD_SUBFOLDERS:
                        subfolder_path = base_path / subfolder
                        subfolder_path.mkdir(parents=True, exist_ok=True)
                        category_paths.append(str(subfolder_path))
                    
                    created_paths.extend(category_paths)
                    hierarchy[category_slug] = {
                        "base_path": str(base_path),
                        "subfolders": self.STANDARD_SUBFOLDERS,
                        "success": True
                    }
                    
                    logger.info(
                        "Provisioned category hierarchy",
                        company_id=company_id,
                        category_slug=category_slug,
                        paths_created=len(category_paths)
                    )
                    
                except (PermissionError, OSError) as e:
                    failed_paths.append({
                        "category": category_slug,
                        "path": str(base_path),
                        "error": str(e)
                    })
                    hierarchy[category_slug] = {
                        "base_path": str(base_path),
                        "success": False,
                        "error": str(e)
                    }
                    logger.error(
                        "Failed to provision category hierarchy",
                        company_id=company_id,
                        category_slug=category_slug,
                        error=str(e),
                        exc_info=e
                    )
            
            # Check if any failures occurred
            if failed_paths:
                error_summary = "; ".join([
                    f"{f['category']}: {f['error']}" for f in failed_paths
                ])
                raise FolderCreationError(
                    f"Failed to provision {len(failed_paths)} category hierarchies: {error_summary}"
                )
            
            logger.info(
                "Company hierarchy provisioned successfully",
                company_id=company_id,
                categories=len(category_slugs),
                total_paths=len(created_paths)
            )
            
            return {
                "success": True,
                "company_id": company_id,
                "company_slug": company_slug,
                "folder_path": folder_path,
                "categories_provisioned": len(category_slugs),
                "total_paths_created": len(created_paths),
                "hierarchy": hierarchy,
                "created_paths": created_paths
            }
            
        except FolderCreationError:
            raise
        except Exception as e:
            logger.error(
                "Unexpected error provisioning company hierarchy",
                company_id=company_id,
                error=str(e),
                exc_info=e
            )
            raise FolderCreationError(
                f"Unexpected error provisioning hierarchy for company {company_id}: {str(e)}"
            ) from e
    
    def provision_category_structure(
        self,
        company: Dict[str, Any],
        category_slug: str
    ) -> Dict[str, Any]:
        """
        Provision folder structure for a single category.
        
        Args:
            company: Company dictionary from database
            category_slug: Category slug (content type)
            
        Returns:
            Dictionary with provisioning results
            
        Raises:
            FolderCreationError: If folder creation fails
        """
        result = self.provision_company_hierarchy(company, [category_slug])
        
        category_result = result["hierarchy"].get(category_slug, {})
        
        return {
            "success": category_result.get("success", False),
            "company_id": result["company_id"],
            "category_slug": category_slug,
            "base_path": category_result.get("base_path"),
            "subfolders": category_result.get("subfolders", []),
            "error": category_result.get("error")
        }
    
    def verify_hierarchy(
        self,
        company: Dict[str, Any],
        category_slugs: List[str]
    ) -> Dict[str, Any]:
        """
        Verify that the folder hierarchy exists for company and categories.
        
        Args:
            company: Company dictionary from database
            category_slugs: List of category slugs to verify
            
        Returns:
            Dictionary with verification results
        """
        folder_path = company.get('storage_folder_path')
        if not folder_path:
            folder_path = self.get_company_slug(company)
        
        company_slug = self.get_company_slug(company)
        company_id = company.get('id', 'unknown')
        
        results = {}
        
        for category_slug in category_slugs:
            base_path = self.storage_root / folder_path / company_slug / category_slug
            
            category_result = {
                "base_path": str(base_path),
                "exists": base_path.exists() and base_path.is_dir(),
                "subfolders": {}
            }
            
            if category_result["exists"]:
                for subfolder in self.STANDARD_SUBFOLDERS:
                    subfolder_path = base_path / subfolder
                    category_result["subfolders"][subfolder] = {
                        "path": str(subfolder_path),
                        "exists": subfolder_path.exists() and subfolder_path.is_dir()
                    }
            
            results[category_slug] = category_result
        
        all_exist = all(r["exists"] for r in results.values())
        all_subfolders_exist = all(
            all(sf["exists"] for sf in r["subfolders"].values())
            for r in results.values()
            if r["exists"]
        )
        
        return {
            "company_id": company_id,
            "company_slug": company_slug,
            "folder_path": folder_path,
            "all_exist": all_exist and all_subfolders_exist,
            "categories": results
        }
