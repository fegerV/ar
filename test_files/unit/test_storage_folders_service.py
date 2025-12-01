"""
Unit tests for storage folders service.
Tests path validation, folder CRUD operations, and permission checking.
"""
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "vertex-ar"))

from app.services.storage_folders import StorageFoldersService


@pytest.fixture
def temp_storage_root(tmp_path):
    """Create a temporary storage root directory."""
    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    return storage_root


@pytest.fixture
def service(temp_storage_root, monkeypatch):
    """Create a storage folders service instance with temp storage."""
    # Patch settings before importing
    from app import config
    monkeypatch.setattr(config.settings, 'STORAGE_ROOT', temp_storage_root)
    service = StorageFoldersService()
    return service


class TestFolderNameNormalization:
    """Test folder name normalization and validation."""
    
    def test_valid_folder_names(self, service):
        """Test that valid folder names pass validation."""
        valid_names = [
            "folder123",
            "my-folder",
            "test_folder",
            "Folder-Name_123",
            "a",
            "123",
        ]
        
        for name in valid_names:
            assert service.normalize_folder_name(name) == name
    
    def test_invalid_folder_names(self, service):
        """Test that invalid folder names raise ValueError."""
        invalid_names = [
            "",
            "  ",
            "folder with spaces",
            "folder/with/slash",
            "folder\\with\\backslash",
            "folder.with.dots",
            "folder@special",
            "folder#hash",
            "folder*asterisk",
        ]
        
        for name in invalid_names:
            with pytest.raises(ValueError):
                service.normalize_folder_name(name)
    
    def test_whitespace_handling(self, service):
        """Test that whitespace is properly handled."""
        # Should strip whitespace
        assert service.normalize_folder_name("  folder  ") == "folder"
        assert service.normalize_folder_name("\tfolder\n") == "folder"


class TestBaseFolder:
    """Test base folder creation and verification."""
    
    def test_base_folder_creation(self, temp_storage_root, monkeypatch):
        """Test that base folder is created on service initialization."""
        from app import config
        monkeypatch.setattr(config.settings, 'STORAGE_ROOT', temp_storage_root)
        service = StorageFoldersService()
        
        base_folder = temp_storage_root / StorageFoldersService.BASE_FOLDER_NAME
        assert base_folder.exists()
        assert base_folder.is_dir()
    
    def test_base_folder_exists_no_error(self, temp_storage_root, monkeypatch):
        """Test that existing base folder doesn't cause errors."""
        base_folder = temp_storage_root / StorageFoldersService.BASE_FOLDER_NAME
        base_folder.mkdir(parents=True, exist_ok=True)
        
        from app import config
        monkeypatch.setattr(config.settings, 'STORAGE_ROOT', temp_storage_root)
        # Should not raise any errors
        service = StorageFoldersService()
        assert base_folder.exists()


class TestCompanyStorageRoot:
    """Test company storage root resolution."""
    
    def test_company_root_without_content_type(self, service, temp_storage_root):
        """Test getting company root without content type."""
        company_id = "company-123"
        root = service.get_company_storage_root(company_id)
        
        expected = temp_storage_root / StorageFoldersService.BASE_FOLDER_NAME / company_id
        assert root == expected
    
    def test_company_root_with_content_type(self, service, temp_storage_root):
        """Test getting company root with content type."""
        company_id = "company-123"
        content_type = "portraits"
        root = service.get_company_storage_root(company_id, content_type)
        
        expected = temp_storage_root / StorageFoldersService.BASE_FOLDER_NAME / company_id / content_type
        assert root == expected


class TestPermissionVerification:
    """Test permission checking for paths."""
    
    def test_permissions_for_existing_directory(self, service, temp_storage_root):
        """Test permission check for existing directory."""
        test_dir = temp_storage_root / "test"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        permissions = service.verify_permissions(test_dir)
        
        assert permissions["exists"] is True
        assert permissions["readable"] is True
        assert permissions["writable"] is True
        assert permissions["executable"] is True
    
    def test_permissions_for_nonexistent_path(self, service, temp_storage_root):
        """Test permission check for non-existent path."""
        test_dir = temp_storage_root / "nonexistent"
        
        permissions = service.verify_permissions(test_dir)
        
        assert permissions["exists"] is False
        assert permissions["readable"] is False
        assert permissions["writable"] is False
        assert permissions["executable"] is False


class TestFolderCreation:
    """Test order folder creation with subdirectories."""
    
    def test_create_folder_success(self, service, temp_storage_root):
        """Test successful folder creation."""
        company_id = "company-123"
        content_type = "portraits"
        folder_name = "order-001"
        
        success, message, path = service.create_order_folder(
            company_id, content_type, folder_name
        )
        
        assert success is True
        assert "created successfully" in message.lower()
        assert path is not None
        assert path.exists()
        
        # Check subdirectories
        for subdir in StorageFoldersService.REQUIRED_SUBDIRS:
            assert (path / subdir).exists()
            assert (path / subdir).is_dir()
    
    def test_create_folder_duplicate(self, service, temp_storage_root):
        """Test that duplicate folder creation fails."""
        company_id = "company-123"
        content_type = "portraits"
        folder_name = "order-001"
        
        # Create first time
        success1, _, _ = service.create_order_folder(
            company_id, content_type, folder_name
        )
        assert success1 is True
        
        # Try to create again
        success2, message2, path2 = service.create_order_folder(
            company_id, content_type, folder_name
        )
        
        assert success2 is False
        assert "already exists" in message2.lower()
        assert path2 is None
    
    def test_create_folder_invalid_name(self, service):
        """Test folder creation with invalid name."""
        company_id = "company-123"
        content_type = "portraits"
        folder_name = "invalid folder name"
        
        success, message, path = service.create_order_folder(
            company_id, content_type, folder_name
        )
        
        assert success is False
        assert path is None
    
    def test_create_folder_creates_parent_dirs(self, service, temp_storage_root):
        """Test that parent directories are created if needed."""
        company_id = "new-company"
        content_type = "new-content"
        folder_name = "order-001"
        
        # Parent directories don't exist yet
        company_root = service.get_company_storage_root(company_id, content_type)
        assert not company_root.exists()
        
        success, _, path = service.create_order_folder(
            company_id, content_type, folder_name
        )
        
        assert success is True
        assert company_root.exists()
        assert path.exists()


class TestFolderListing:
    """Test listing order folders."""
    
    def test_list_empty(self, service):
        """Test listing folders when none exist."""
        company_id = "company-123"
        folders = service.list_order_folders(company_id)
        
        assert folders == []
    
    def test_list_folders_in_content_type(self, service):
        """Test listing folders for a specific content type."""
        company_id = "company-123"
        content_type = "portraits"
        
        # Create a few folders
        for i in range(3):
            service.create_order_folder(company_id, content_type, f"order-{i:03d}")
        
        folders = service.list_order_folders(company_id, content_type)
        
        assert len(folders) == 3
        folder_names = {f["folder_name"] for f in folders}
        assert folder_names == {"order-000", "order-001", "order-002"}
        
        # All should be in the same content type
        for folder in folders:
            assert folder["content_type"] == content_type
    
    def test_list_all_folders(self, service):
        """Test listing all folders across content types."""
        company_id = "company-123"
        
        # Create folders in different content types
        service.create_order_folder(company_id, "portraits", "order-001")
        service.create_order_folder(company_id, "portraits", "order-002")
        service.create_order_folder(company_id, "diplomas", "diploma-001")
        
        folders = service.list_order_folders(company_id)
        
        assert len(folders) == 3
        content_types = {f["content_type"] for f in folders}
        assert content_types == {"portraits", "diplomas"}
    
    def test_folder_info_structure(self, service):
        """Test that folder info has correct structure."""
        company_id = "company-123"
        content_type = "portraits"
        folder_name = "order-001"
        
        service.create_order_folder(company_id, content_type, folder_name)
        folders = service.list_order_folders(company_id, content_type)
        
        assert len(folders) == 1
        folder_info = folders[0]
        
        assert "folder_name" in folder_info
        assert "content_type" in folder_info
        assert "full_path" in folder_info
        assert "has_required_subdirs" in folder_info
        assert "is_empty" in folder_info
        
        assert folder_info["folder_name"] == folder_name
        assert folder_info["content_type"] == content_type
        assert folder_info["is_empty"] is True
        
        # Check subdirectories flag
        subdirs = folder_info["has_required_subdirs"]
        for subdir in StorageFoldersService.REQUIRED_SUBDIRS:
            assert subdirs[subdir] is True


class TestFolderDeletion:
    """Test order folder deletion."""
    
    def test_delete_empty_folder(self, service):
        """Test deleting an empty folder."""
        company_id = "company-123"
        content_type = "portraits"
        folder_name = "order-001"
        
        # Create folder
        service.create_order_folder(company_id, content_type, folder_name)
        
        # Delete it
        success, message = service.delete_order_folder(
            company_id, content_type, folder_name
        )
        
        assert success is True
        assert "deleted successfully" in message.lower()
        
        # Verify it's gone
        folders = service.list_order_folders(company_id, content_type)
        assert len(folders) == 0
    
    def test_delete_nonexistent_folder(self, service):
        """Test deleting a folder that doesn't exist."""
        company_id = "company-123"
        content_type = "portraits"
        folder_name = "nonexistent"
        
        success, message = service.delete_order_folder(
            company_id, content_type, folder_name
        )
        
        assert success is False
        assert "does not exist" in message.lower()
    
    def test_delete_nonempty_folder_without_force(self, service):
        """Test that non-empty folder deletion fails without force."""
        company_id = "company-123"
        content_type = "portraits"
        folder_name = "order-001"
        
        # Create folder
        _, _, path = service.create_order_folder(company_id, content_type, folder_name)
        
        # Add a file
        (path / "Image" / "test.jpg").write_text("test content")
        
        # Try to delete without force
        success, message = service.delete_order_folder(
            company_id, content_type, folder_name, force=False
        )
        
        assert success is False
        assert "not empty" in message.lower()
    
    def test_delete_nonempty_folder_with_force(self, service):
        """Test that non-empty folder deletion succeeds with force."""
        company_id = "company-123"
        content_type = "portraits"
        folder_name = "order-001"
        
        # Create folder
        _, _, path = service.create_order_folder(company_id, content_type, folder_name)
        
        # Add a file
        (path / "Image" / "test.jpg").write_text("test content")
        
        # Delete with force
        success, message = service.delete_order_folder(
            company_id, content_type, folder_name, force=True
        )
        
        assert success is True
        assert "deleted successfully" in message.lower()
        
        # Verify it's gone
        assert not path.exists()


class TestStorageStatus:
    """Test storage status retrieval."""
    
    def test_status_for_new_company(self, service):
        """Test status for company with no folders yet."""
        company_id = "company-123"
        
        status = service.get_storage_status(company_id)
        
        assert status["company_id"] == company_id
        assert "storage_root" in status
        assert "company_path" in status
        assert "permissions" in status
        assert "content_types" in status
        assert "is_ready" in status
        
        # No folders yet
        assert status["content_types"] == {}
    
    def test_status_with_folders(self, service):
        """Test status for company with existing folders."""
        company_id = "company-123"
        
        # Create folders in different content types
        service.create_order_folder(company_id, "portraits", "order-001")
        service.create_order_folder(company_id, "portraits", "order-002")
        service.create_order_folder(company_id, "diplomas", "diploma-001")
        
        status = service.get_storage_status(company_id)
        
        # Should count folders per content type
        assert "portraits" in status["content_types"]
        assert "diplomas" in status["content_types"]
        assert status["content_types"]["portraits"] == 2
        assert status["content_types"]["diplomas"] == 1
    
    def test_status_is_ready_flag(self, service, temp_storage_root):
        """Test that is_ready flag reflects permissions."""
        company_id = "company-123"
        company_root = service.get_company_storage_root(company_id)
        company_root.mkdir(parents=True, exist_ok=True)
        
        status = service.get_storage_status(company_id)
        
        # Should be ready if readable and writable
        assert status["is_ready"] is True


class TestEmptyFolderCheck:
    """Test empty folder detection."""
    
    def test_empty_folder(self, service):
        """Test that newly created folder is detected as empty."""
        company_id = "company-123"
        content_type = "portraits"
        folder_name = "order-001"
        
        _, _, path = service.create_order_folder(company_id, content_type, folder_name)
        
        assert service._is_folder_empty(path) is True
    
    def test_folder_with_file_in_subdirectory(self, service):
        """Test that folder with file is detected as not empty."""
        company_id = "company-123"
        content_type = "portraits"
        folder_name = "order-001"
        
        _, _, path = service.create_order_folder(company_id, content_type, folder_name)
        
        # Add file in subdirectory
        (path / "Image" / "test.jpg").write_text("content")
        
        assert service._is_folder_empty(path) is False
    
    def test_folder_with_nested_file(self, service):
        """Test detection of files in nested directories."""
        company_id = "company-123"
        content_type = "portraits"
        folder_name = "order-001"
        
        _, _, path = service.create_order_folder(company_id, content_type, folder_name)
        
        # Create nested directory and add file
        nested_dir = path / "Image" / "nested"
        nested_dir.mkdir(parents=True, exist_ok=True)
        (nested_dir / "test.jpg").write_text("content")
        
        assert service._is_folder_empty(path) is False


class TestRequiredSubdirectories:
    """Test required subdirectory checking."""
    
    def test_all_subdirs_present(self, service):
        """Test checking when all required subdirs are present."""
        company_id = "company-123"
        content_type = "portraits"
        folder_name = "order-001"
        
        _, _, path = service.create_order_folder(company_id, content_type, folder_name)
        
        subdirs = service._check_required_subdirs(path)
        
        for subdir in StorageFoldersService.REQUIRED_SUBDIRS:
            assert subdirs[subdir] is True
    
    def test_missing_subdir(self, service):
        """Test checking when a required subdir is missing."""
        company_id = "company-123"
        content_type = "portraits"
        folder_name = "order-001"
        
        _, _, path = service.create_order_folder(company_id, content_type, folder_name)
        
        # Remove one subdirectory
        import shutil
        shutil.rmtree(path / "Image")
        
        subdirs = service._check_required_subdirs(path)
        
        assert subdirs["Image"] is False
        assert subdirs["QR"] is True
        assert subdirs["nft_markers"] is True
        assert subdirs["nft_cache"] is True
