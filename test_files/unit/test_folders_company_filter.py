"""
Unit tests for folders API with company_id filter.
Tests that the folders endpoint can filter by company_id.
"""
import pytest
import tempfile
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Add vertex-ar to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "vertex-ar"))

from app.database import Database
from app.api.folders import list_folders


class TestFoldersCompanyFilter:
    """Test folders API with company_id filter."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            yield db

    @pytest.fixture
    def mock_current_user(self):
        """Create a mock current user."""
        return {"username": "admin", "is_admin": True}

    def test_list_folders_with_company_id_filter(self, temp_db, mock_current_user):
        """Test listing folders filtered by company_id."""
        # Create test data
        # Create companies
        temp_db.create_company("company-1", "Test Company 1", storage_type="local_disk")
        temp_db.create_company("company-2", "Test Company 2", storage_type="local_disk")

        # Create projects for each company
        temp_db.create_project("project-1", "company-1", "Project 1")
        temp_db.create_project("project-2", "company-1", "Project 2")
        temp_db.create_project("project-3", "company-2", "Project 3")

        # Create folders for each project
        temp_db.create_folder("folder-1", "project-1", "Folder 1")
        temp_db.create_folder("folder-2", "project-1", "Folder 2")
        temp_db.create_folder("folder-3", "project-2", "Folder 3")
        temp_db.create_folder("folder-4", "project-3", "Folder 4")

        # Mock the get_database function
        with patch('app.api.folders.get_database', return_value=temp_db):
            # Test filtering by company_id
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # List folders for company-1 (should get folders from project-1 and project-2)
                response = loop.run_until_complete(
                    list_folders(
                        company_id="company-1",
                        page=1,
                        page_size=10,
                        current_user=mock_current_user,
                        db=temp_db
                    )
                )

                # Verify we got the right folders
                assert response.total == 3  # folder-1, folder-2, folder-3
                assert len(response.items) == 3
                folder_names = [item.name for item in response.items]
                assert "Folder 1" in folder_names
                assert "Folder 2" in folder_names
                assert "Folder 3" in folder_names
                assert "Folder 4" not in folder_names  # This belongs to company-2

                # List folders for company-2 (should get folders from project-3 only)
                response = loop.run_until_complete(
                    list_folders(
                        company_id="company-2",
                        page=1,
                        page_size=10,
                        current_user=mock_current_user,
                        db=temp_db
                    )
                )

                # Verify we got the right folders
                assert response.total == 1  # folder-4
                assert len(response.items) == 1
                assert response.items[0].name == "Folder 4"

                # List all folders (no filter)
                response = loop.run_until_complete(
                    list_folders(
                        page=1,
                        page_size=10,
                        current_user=mock_current_user,
                        db=temp_db
                    )
                )

                # Verify we got all folders
                assert response.total == 4
                assert len(response.items) == 4

            finally:
                loop.close()

    def test_list_folders_with_both_company_id_and_project_id_ignores_company_id(self, temp_db, mock_current_user):
        """Test that when both company_id and project_id are provided, project_id takes precedence."""
        # Create test data
        temp_db.create_company("company-1", "Test Company 1", storage_type="local_disk")
        temp_db.create_project("project-1", "company-1", "Project 1")
        temp_db.create_project("project-2", "company-1", "Project 2")
        temp_db.create_folder("folder-1", "project-1", "Folder 1")
        temp_db.create_folder("folder-2", "project-2", "Folder 2")

        # Mock the get_database function
        with patch('app.api.folders.get_database', return_value=temp_db):
            # Test with both company_id and project_id - should filter by project_id only
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                response = loop.run_until_complete(
                    list_folders(
                        project_id="project-1",
                        company_id="company-1",  # This should be ignored
                        page=1,
                        page_size=10,
                        current_user=mock_current_user,
                        db=temp_db
                    )
                )

                # Should only get folders from project-1, ignoring company_id
                assert response.total == 1
                assert len(response.items) == 1
                assert response.items[0].name == "Folder 1"

            finally:
                loop.close()

    def test_list_folders_pagination_with_company_id_filter(self, temp_db, mock_current_user):
        """Test pagination works correctly with company_id filter."""
        # Create test data
        temp_db.create_company("company-1", "Test Company 1", storage_type="local_disk")
        temp_db.create_project("project-1", "company-1", "Project 1")

        # Create multiple folders
        for i in range(1, 16):  # 15 folders
            temp_db.create_folder(f"folder-{i}", "project-1", f"Folder {i}")

        # Mock the get_database function
        with patch('app.api.folders.get_database', return_value=temp_db):
            # Test pagination
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # First page
                response = loop.run_until_complete(
                    list_folders(
                        company_id="company-1",
                        page=1,
                        page_size=5,
                        current_user=mock_current_user,
                        db=temp_db
                    )
                )

                assert response.total == 15
                assert len(response.items) == 5
                assert response.page == 1
                assert response.page_size == 5
                assert response.total_pages == 3

                # Second page
                response = loop.run_until_complete(
                    list_folders(
                        company_id="company-1",
                        page=2,
                        page_size=5,
                        current_user=mock_current_user,
                        db=temp_db
                    )
                )

                assert response.total == 15
                assert len(response.items) == 5
                assert response.page == 2
                assert response.page_size == 5
                assert response.total_pages == 3

                # Last page
                response = loop.run_until_complete(
                    list_folders(
                        company_id="company-1",
                        page=3,
                        page_size=5,
                        current_user=mock_current_user,
                        db=temp_db
                    )
                )

                assert response.total == 15
                assert len(response.items) == 5  # Last page has 5 items (15 total / 5 per page)
                assert response.page == 3
                assert response.page_size == 5
                assert response.total_pages == 3

            finally:
                loop.close()
