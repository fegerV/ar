"""
Unit tests for folder service.
Tests folder hierarchy creation and management for local storage.
"""
import os
import tempfile
from pathlib import Path

import pytest

from app.services.folder_service import FolderService


@pytest.fixture
def temp_storage_root():
    """Create temporary storage root directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def folder_service(temp_storage_root):
    """Create FolderService instance with temp storage."""
    return FolderService(temp_storage_root)


@pytest.fixture
def sample_company():
    """Sample company data."""
    return {
        "id": "test-company-123",
        "name": "Test Company",
        "storage_type": "local",
        "storage_folder_path": "company_storage"
    }


class TestFolderServiceSlugify:
    """Tests for slugify method."""
    
    def test_slugify_basic(self, folder_service):
        """Test basic slugification."""
        assert folder_service.slugify("Test Company") == "test_company"
        assert folder_service.slugify("My-Test-123") == "my_test_123"
        assert folder_service.slugify("UPPERCASE") == "uppercase"
    
    def test_slugify_special_characters(self, folder_service):
        """Test slugify removes special characters."""
        assert folder_service.slugify("Test@Company!") == "testcompany"
        assert folder_service.slugify("Test & Company") == "test_company"
        assert folder_service.slugify("Test (Company)") == "test_company"
    
    def test_slugify_multiple_spaces(self, folder_service):
        """Test slugify handles multiple spaces."""
        assert folder_service.slugify("Test  Company  Name") == "test_company_name"
        assert folder_service.slugify("   Test   ") == "test"


class TestFolderServiceCompanySlug:
    """Tests for get_company_slug method."""
    
    def test_get_company_slug_uses_id(self, folder_service, sample_company):
        """Test company slug is derived from company ID."""
        slug = folder_service.get_company_slug(sample_company)
        assert slug == "test_company_123"
    
    def test_get_company_slug_default(self, folder_service):
        """Test company slug with missing ID."""
        company = {"name": "Test"}
        slug = folder_service.get_company_slug(company)
        assert slug == "default"


class TestFolderServicePathBuilding:
    """Tests for path building methods."""
    
    def test_build_order_path_basic(self, folder_service, sample_company, temp_storage_root):
        """Test basic order path construction."""
        path = folder_service.build_order_path(
            sample_company,
            "portraits",
            "order-123"
        )
        
        expected = temp_storage_root / "company_storage" / "test_company_123" / "portraits" / "order-123"
        assert path == expected
    
    def test_build_order_path_with_subfolder(self, folder_service, sample_company, temp_storage_root):
        """Test order path with subfolder."""
        path = folder_service.build_order_path(
            sample_company,
            "portraits",
            "order-123",
            "Image"
        )
        
        expected = temp_storage_root / "company_storage" / "test_company_123" / "portraits" / "order-123" / "Image"
        assert path == expected
    
    def test_build_order_path_no_storage_folder_path(self, folder_service, temp_storage_root):
        """Test order path when storage_folder_path is not set."""
        company = {
            "id": "company-456",
            "storage_type": "local"
        }
        
        path = folder_service.build_order_path(company, "certificates", "order-789")
        
        # Should use company slug as folder path
        expected = temp_storage_root / "company_456" / "company_456" / "certificates" / "order-789"
        assert path == expected
    
    def test_build_relative_path_basic(self, folder_service, sample_company):
        """Test relative path construction."""
        rel_path = folder_service.build_relative_path(
            sample_company,
            "portraits",
            "order-123",
            "image.jpg"
        )
        
        assert rel_path == "company_storage/test_company_123/portraits/order-123/image.jpg"
    
    def test_build_relative_path_with_subfolder(self, folder_service, sample_company):
        """Test relative path with subfolder."""
        rel_path = folder_service.build_relative_path(
            sample_company,
            "portraits",
            "order-123",
            "image.jpg",
            "Image"
        )
        
        assert rel_path == "company_storage/test_company_123/portraits/order-123/Image/image.jpg"


class TestFolderServiceStructureCreation:
    """Tests for ensure_order_structure method."""
    
    def test_ensure_order_structure_creates_all_folders(self, folder_service, sample_company, temp_storage_root):
        """Test that all required subfolders are created."""
        result = folder_service.ensure_order_structure(
            sample_company,
            "portraits",
            "order-123"
        )
        
        # Check result
        assert result["success"] is True
        assert "base_path" in result
        assert "created_paths" in result
        assert result["subfolders"] == ["Image", "QR", "nft_markers", "nft_cache"]
        
        # Check folders exist
        base_path = temp_storage_root / "company_storage" / "test_company_123" / "portraits" / "order-123"
        assert base_path.exists()
        assert (base_path / "Image").exists()
        assert (base_path / "QR").exists()
        assert (base_path / "nft_markers").exists()
        assert (base_path / "nft_cache").exists()
    
    def test_ensure_order_structure_idempotent(self, folder_service, sample_company):
        """Test that calling ensure_order_structure multiple times is safe."""
        # Create structure first time
        result1 = folder_service.ensure_order_structure(sample_company, "portraits", "order-456")
        assert result1["success"] is True
        
        # Create again - should not raise error
        result2 = folder_service.ensure_order_structure(sample_company, "portraits", "order-456")
        assert result2["success"] is True
    
    def test_ensure_order_structure_permission_error(self, folder_service, sample_company, temp_storage_root):
        """Test permission error handling."""
        # Create a directory and remove write permissions
        restricted_dir = temp_storage_root / "restricted"
        restricted_dir.mkdir()
        os.chmod(restricted_dir, 0o444)  # Read-only
        
        # Override storage_folder_path to use restricted dir
        company = {**sample_company, "storage_folder_path": "restricted"}
        
        try:
            with pytest.raises(PermissionError, match="Permission denied creating storage folders"):
                folder_service.ensure_order_structure(company, "portraits", "order-fail")
        finally:
            # Restore permissions for cleanup
            os.chmod(restricted_dir, 0o755)


class TestFolderServiceFileOperations:
    """Tests for file operation methods."""
    
    def test_move_file_basic(self, folder_service, temp_storage_root):
        """Test basic file move."""
        # Create source file
        source = temp_storage_root / "source.txt"
        source.write_text("test content")
        
        # Move file
        dest = temp_storage_root / "subdir" / "dest.txt"
        folder_service.move_file(source, dest)
        
        # Verify
        assert not source.exists()
        assert dest.exists()
        assert dest.read_text() == "test content"
    
    def test_move_file_creates_parent_dirs(self, folder_service, temp_storage_root):
        """Test that parent directories are created."""
        source = temp_storage_root / "source.txt"
        source.write_text("test")
        
        dest = temp_storage_root / "a" / "b" / "c" / "file.txt"
        folder_service.move_file(source, dest)
        
        assert dest.exists()
        assert dest.parent.exists()
    
    def test_move_file_not_found(self, folder_service, temp_storage_root):
        """Test moving non-existent file raises error."""
        source = temp_storage_root / "nonexistent.txt"
        dest = temp_storage_root / "dest.txt"
        
        with pytest.raises(FileNotFoundError, match="Source file not found"):
            folder_service.move_file(source, dest)
    
    def test_cleanup_temp_directory(self, folder_service, temp_storage_root):
        """Test temp directory cleanup."""
        # Create temp directory with files
        temp_dir = temp_storage_root / "temp_order"
        temp_dir.mkdir()
        (temp_dir / "file1.txt").write_text("test1")
        (temp_dir / "file2.txt").write_text("test2")
        
        # Cleanup
        folder_service.cleanup_temp_directory(temp_dir)
        
        # Verify removed
        assert not temp_dir.exists()
    
    def test_cleanup_temp_directory_nonexistent(self, folder_service, temp_storage_root):
        """Test cleanup of non-existent directory doesn't raise error."""
        temp_dir = temp_storage_root / "nonexistent"
        
        # Should not raise error
        folder_service.cleanup_temp_directory(temp_dir)


class TestFolderServiceIntegration:
    """Integration tests for complete workflow."""
    
    def test_complete_order_workflow(self, folder_service, sample_company, temp_storage_root):
        """Test complete order file organization workflow."""
        order_id = "order-complete-123"
        content_type = "portraits"
        
        # 1. Create order structure
        result = folder_service.ensure_order_structure(sample_company, content_type, order_id)
        assert result["success"] is True
        
        # 2. Create temp files
        temp_dir = temp_storage_root / "temp"
        temp_dir.mkdir()
        image_file = temp_dir / "image.jpg"
        video_file = temp_dir / "video.mp4"
        qr_file = temp_dir / "qr.png"
        
        image_file.write_bytes(b"fake image")
        video_file.write_bytes(b"fake video")
        qr_file.write_bytes(b"fake qr")
        
        # 3. Move files to proper locations
        image_dest = folder_service.build_order_path(sample_company, content_type, order_id, "Image") / "image.jpg"
        video_dest = folder_service.build_order_path(sample_company, content_type, order_id, "Image") / "video.mp4"
        qr_dest = folder_service.build_order_path(sample_company, content_type, order_id, "QR") / "qr.png"
        
        folder_service.move_file(image_file, image_dest)
        folder_service.move_file(video_file, video_dest)
        folder_service.move_file(qr_file, qr_dest)
        
        # 4. Verify files are in correct locations
        assert image_dest.exists()
        assert video_dest.exists()
        assert qr_dest.exists()
        assert image_dest.read_bytes() == b"fake image"
        assert video_dest.read_bytes() == b"fake video"
        assert qr_dest.read_bytes() == b"fake qr"
        
        # 5. Get relative paths for database
        image_rel = folder_service.build_relative_path(sample_company, content_type, order_id, "image.jpg", "Image")
        video_rel = folder_service.build_relative_path(sample_company, content_type, order_id, "video.mp4", "Image")
        qr_rel = folder_service.build_relative_path(sample_company, content_type, order_id, "qr.png", "QR")
        
        assert image_rel == "company_storage/test_company_123/portraits/order-complete-123/Image/image.jpg"
        assert video_rel == "company_storage/test_company_123/portraits/order-complete-123/Image/video.mp4"
        assert qr_rel == "company_storage/test_company_123/portraits/order-complete-123/QR/qr.png"
        
        # 6. Cleanup temp
        folder_service.cleanup_temp_directory(temp_dir)
        assert not temp_dir.exists()
