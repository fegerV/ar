"""
Company bootstrap service for initializing default company with proper storage settings,
categories, and folder structure.
"""
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

from logging_setup import get_logger
from app.database import Database
from app.services.folder_service import FolderService

logger = get_logger(__name__)


class CompanyBootstrapError(Exception):
    """Base exception for CompanyBootstrap errors."""
    pass


class CompanyBootstrap:
    """Service for bootstrapping company with default structure."""

    # Default categories/slugs for the company
    DEFAULT_CATEGORIES = [
        {
            "name": "Портреты",
            "slug": "portraits",
            "description": "Портреты с AR-анимацией"
        },
        {
            "name": "Дипломы AR",
            "slug": "diplomas",
            "description": "AR-дипломы с анимацией"
        },
        {
            "name": "Сертификаты",
            "slug": "certificates",
            "description": "Сертификаты с AR-эффектами"
        }
    ]

    def __init__(self, database: Database, storage_root: Path):
        """
        Initialize company bootstrap service.

        Args:
            database: Database instance
            storage_root: Storage root path for folder creation
        """
        self.database = database
        self.storage_root = storage_root

    def ensure_default_company(self) -> Dict[str, Any]:
        """
        Ensure the default company exists with proper storage configuration.
        Creates folder hierarchy for local storage if needed.
        Ensures the default company uses local_disk storage with vertex_ar_content folder path
        and that these settings cannot be changed.

        Returns:
            Dictionary with company data

        Raises:
            CompanyBootstrapError: If bootstrap fails
        """
        try:
            # Check if default company exists
            existing = self.database.get_company("vertex-ar-default")

            if existing:
                # Ensure default company always has correct immutable storage settings
                # This protects against manual database modifications or bugs
                if (existing.get("storage_type") != "local_disk" or
                    existing.get("storage_folder_path") != "vertex_ar_content"):
                    self.database.update_company(
                        "vertex-ar-default",
                        storage_type="local_disk",
                        storage_folder_path="vertex_ar_content"
                    )
                    logger.info("Corrected default company storage settings to local_disk/vertex_ar_content")
                company = existing
            else:
                # Create company with explicit local_disk storage and deterministic folder path
                try:
                    self.database.create_company(
                        company_id="vertex-ar-default",
                        name="Vertex AR",
                        storage_type="local_disk",
                        storage_folder_path="vertex_ar_content",
                        email="contact@vertex-ar.com",
                        description="Default company for Vertex AR platform",
                        city="Moscow",
                        phone="+7 (495) 000-00-00",
                        website="https://vertex-ar.com",
                        manager_name="System Administrator",
                        manager_phone="+7 (495) 000-00-00",
                        manager_email="admin@vertex-ar.com"
                    )
                    logger.info("Created default company 'Vertex AR' with storage_type=local_disk")
                    company = self.database.get_company("vertex-ar-default")
                except Exception as exc:
                    logger.error(f"Failed to create default company: {exc}")
                    raise CompanyBootstrapError(f"Failed to create default company: {exc}") from exc

            return company

        except Exception as e:
            logger.error(f"Error in ensure_default_company: {e}")
            raise CompanyBootstrapError(f"Failed to ensure default company: {e}") from e

    def seed_default_categories(self, company_id: str = "vertex-ar-default") -> List[Dict[str, Any]]:
        """
        Seed default categories (projects) for the company if they don't exist.

        Args:
            company_id: Company ID to seed categories for

        Returns:
            List of created/verified category dictionaries

        Raises:
            CompanyBootstrapError: If seeding fails
        """
        try:
            created_categories = []

            for category_data in self.DEFAULT_CATEGORIES:
                # Check if category already exists
                existing = self.database.get_category_by_slug(company_id, category_data["slug"])

                if not existing:
                    # Create category
                    category_id = f"cat-{uuid.uuid4().hex[:8]}"
                    category = self.database.create_category(
                        category_id=category_id,
                        company_id=company_id,
                        name=category_data["name"],
                        slug=category_data["slug"],
                        description=category_data["description"]
                    )
                    logger.info(
                        f"Created default category: {category_data['name']} "
                        f"(slug: {category_data['slug']})"
                    )
                    created_categories.append(category)
                else:
                    logger.info(
                        f"Default category already exists: {category_data['name']} "
                        f"(slug: {category_data['slug']})"
                    )
                    created_categories.append(existing)

            return created_categories

        except Exception as e:
            logger.error(f"Error seeding default categories: {e}")
            raise CompanyBootstrapError(f"Failed to seed default categories: {e}") from e

    def seed_default_folders(self, company_id: str = "vertex-ar-default") -> List[Dict[str, Any]]:
        """
        Seed at least one folder per category and keep folder↔category relationships consistent.

        Args:
            company_id: Company ID to seed folders for

        Returns:
            List of created/verified folder dictionaries

        Raises:
            CompanyBootstrapError: If seeding fails
        """
        try:
            created_folders = []

            # Get all categories for the company
            categories = self.database.list_categories(company_id=company_id)

            for category in categories:
                # Check if any folders exist for this category
                existing_folders = self.database.list_folders(project_id=category["id"])

                if not existing_folders:
                    # Create default folder for category
                    folder_id = f"folder-{uuid.uuid4().hex[:8]}"
                    folder_name = f"Default {category['name']}"

                    folder = self.database.create_folder(
                        folder_id=folder_id,
                        project_id=category["id"],
                        name=folder_name,
                        description=f"Default folder for {category['name']}"
                    )
                    logger.info(
                        f"Created default folder: {folder_name} "
                        f"for category {category['name']}"
                    )
                    created_folders.append(folder)
                else:
                    logger.info(
                        f"Folder(s) already exist for category {category['name']}, "
                        f"count: {len(existing_folders)}"
                    )
                    created_folders.extend(existing_folders)

            return created_folders

        except Exception as e:
            logger.error(f"Error seeding default folders: {e}")
            raise CompanyBootstrapError(f"Failed to seed default folders: {e}") from e

    def create_filesystem_hierarchy(
        self,
        company: Dict[str, Any],
        categories: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Create the matching directory hierarchy on disk using FolderService.

        Args:
            company: Company dictionary
            categories: Optional list of categories (will fetch if not provided)

        Returns:
            Dictionary with provisioning results

        Raises:
            CompanyBootstrapError: If filesystem creation fails
        """
        try:
            if categories is None:
                categories = self.database.list_categories(company_id=company["id"])

            # Extract category slugs
            category_slugs = [cat["slug"] for cat in categories]

            # Create folder service with the correct storage root
            folder_service = FolderService(self.storage_root)

            # Provision folder hierarchy using FolderService
            result = folder_service.provision_company_hierarchy(company, category_slugs)

            if result.get("success"):
                logger.info(
                    "Successfully created filesystem hierarchy for default company",
                    company_id=company["id"],
                    categories=len(categories),
                    paths_created=result.get("total_paths_created", 0)
                )
            else:
                logger.warning(
                    "Partial success creating filesystem hierarchy",
                    company_id=company["id"],
                    result=result
                )

            return result

        except Exception as e:
            logger.error(f"Error creating filesystem hierarchy: {e}")
            raise CompanyBootstrapError(f"Failed to create filesystem hierarchy: {e}") from e

    def bootstrap_complete_company(self) -> Dict[str, Any]:
        """
        Perform complete bootstrap of default company:
        1. Ensure company record exists with correct storage settings
        2. Seed default categories/projects
        3. Seed default folders
        4. Create filesystem hierarchy

        Returns:
            Dictionary with bootstrap results

        Raises:
            CompanyBootstrapError: If bootstrap fails
        """
        try:
            logger.info("Starting complete company bootstrap...")

            # 1. Ensure company exists
            company = self.ensure_default_company()

            # 2. Seed default categories
            categories = self.seed_default_categories(company["id"])

            # 3. Seed default folders
            folders = self.seed_default_folders(company["id"])

            # 4. Create filesystem hierarchy
            fs_result = self.create_filesystem_hierarchy(company, categories)

            logger.info("Complete company bootstrap finished successfully")

            return {
                "success": True,
                "company": company,
                "categories": categories,
                "folders": folders,
                "filesystem": fs_result
            }

        except Exception as e:
            logger.error(f"Complete company bootstrap failed: {e}")
            raise CompanyBootstrapError(f"Complete company bootstrap failed: {e}") from e
