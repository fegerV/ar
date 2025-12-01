"""
Simple integration test for order workflow with local storage folders.
Tests the core functionality without requiring full authentication setup.
"""
import tempfile
import uuid
from pathlib import Path

import pytest

from app.database import Database
from app.services.folder_service import FolderService


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_db():
    """Create test database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    
    db = Database(db_path)
    yield db
    
    # Cleanup
    db_path.unlink(missing_ok=True)


class TestLocalStorageFolderWorkflow:
    """Test local storage folder workflow end-to-end."""
    
    def test_create_order_folder_structure(self, temp_storage, test_db):
        """Test creating order folder structure for local storage company."""
        # Create company with local storage
        company_id = str(uuid.uuid4())
        test_db.create_company(
            company_id=company_id,
            name="Local Storage Test Company",
            storage_type="local",
            storage_folder_path="test_orders"
        )
        
        # Get company from database
        company = test_db.get_company(company_id)
        assert company is not None
        assert company["storage_type"] == "local"
        assert company["storage_folder_path"] == "test_orders"
        
        # Initialize folder service
        folder_service = FolderService(temp_storage)
        
        # Create order structure
        order_id = str(uuid.uuid4())
        content_type = "portraits"
        
        result = folder_service.ensure_order_structure(
            company,
            content_type,
            order_id
        )
        
        # Verify structure was created
        assert result["success"] is True
        assert result["subfolders"] == ["Image", "QR", "nft_markers", "nft_cache"]
        
        # Verify all folders exist
        company_slug = folder_service.get_company_slug(company)
        base_path = temp_storage / "test_orders" / company_slug / content_type / order_id
        
        assert base_path.exists()
        assert (base_path / "Image").exists()
        assert (base_path / "QR").exists()
        assert (base_path / "nft_markers").exists()
        assert (base_path / "nft_cache").exists()
    
    def test_move_files_to_order_folders(self, temp_storage, test_db):
        """Test moving files to order folder structure."""
        # Setup company
        company_id = str(uuid.uuid4())
        test_db.create_company(
            company_id=company_id,
            name="Move Files Test",
            storage_type="local",
            storage_folder_path="file_storage"
        )
        
        company = test_db.get_company(company_id)
        folder_service = FolderService(temp_storage)
        
        # Create temp files
        temp_dir = temp_storage / "temp"
        temp_dir.mkdir()
        
        image_temp = temp_dir / "test_image.jpg"
        video_temp = temp_dir / "test_video.mp4"
        qr_temp = temp_dir / "test_qr.png"
        
        image_temp.write_bytes(b"fake image data")
        video_temp.write_bytes(b"fake video data")
        qr_temp.write_bytes(b"fake qr data")
        
        # Create order structure
        order_id = str(uuid.uuid4())
        folder_service.ensure_order_structure(company, "diplomas", order_id)
        
        # Move files to proper locations
        image_dest = folder_service.build_order_path(company, "diplomas", order_id, "Image") / "image.jpg"
        video_dest = folder_service.build_order_path(company, "diplomas", order_id, "Image") / "video.mp4"
        qr_dest = folder_service.build_order_path(company, "diplomas", order_id, "QR") / "qr.png"
        
        folder_service.move_file(image_temp, image_dest)
        folder_service.move_file(video_temp, video_dest)
        folder_service.move_file(qr_temp, qr_dest)
        
        # Verify files moved
        assert image_dest.exists()
        assert video_dest.exists()
        assert qr_dest.exists()
        
        assert image_dest.read_bytes() == b"fake image data"
        assert video_dest.read_bytes() == b"fake video data"
        assert qr_dest.read_bytes() == b"fake qr data"
        
        # Verify temp files removed
        assert not image_temp.exists()
        assert not video_temp.exists()
        assert not qr_temp.exists()
    
    def test_relative_paths_for_database(self, temp_storage, test_db):
        """Test generating relative paths for database storage."""
        # Setup
        company_id = str(uuid.uuid4())
        test_db.create_company(
            company_id=company_id,
            name="Relative Paths Test",
            storage_type="local",
            storage_folder_path="relative_storage"
        )
        
        company = test_db.get_company(company_id)
        folder_service = FolderService(temp_storage)
        
        order_id = str(uuid.uuid4())
        portrait_id = str(uuid.uuid4())
        video_id = str(uuid.uuid4())
        
        # Build relative paths
        image_rel = folder_service.build_relative_path(
            company, "certificates", order_id, f"{portrait_id}.jpg", "Image"
        )
        video_rel = folder_service.build_relative_path(
            company, "certificates", order_id, f"{video_id}.mp4", "Image"
        )
        qr_rel = folder_service.build_relative_path(
            company, "certificates", order_id, f"{portrait_id}_qr.png", "QR"
        )
        marker_rel = folder_service.build_relative_path(
            company, "certificates", order_id, f"{portrait_id}.fset", "nft_markers"
        )
        
        # Verify paths are relative (not absolute)
        assert not image_rel.startswith("/")
        assert not video_rel.startswith("/")
        assert not qr_rel.startswith("/")
        assert not marker_rel.startswith("/")
        
        # Verify path structure
        company_slug = folder_service.get_company_slug(company)
        assert image_rel.startswith("relative_storage/")
        assert company_slug in image_rel
        assert "certificates" in image_rel
        assert order_id in image_rel
        assert "Image" in image_rel
        assert f"{portrait_id}.jpg" in image_rel
        
        # Verify different subfolders
        assert "Image" in image_rel
        assert "Image" in video_rel
        assert "QR" in qr_rel
        assert "nft_markers" in marker_rel
    
    def test_cleanup_temp_directory(self, temp_storage):
        """Test temp directory cleanup after successful order."""
        folder_service = FolderService(temp_storage)
        
        # Create temp directory with files
        temp_dir = temp_storage / "temp" / "orders" / str(uuid.uuid4())
        temp_dir.mkdir(parents=True)
        
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.txt").write_text("content2")
        (temp_dir / "subdir").mkdir()
        (temp_dir / "subdir" / "file3.txt").write_text("content3")
        
        assert temp_dir.exists()
        
        # Cleanup
        folder_service.cleanup_temp_directory(temp_dir)
        
        # Verify cleanup
        assert not temp_dir.exists()
    
    def test_multiple_content_types(self, temp_storage, test_db):
        """Test handling multiple content types for same company."""
        # Setup company
        company_id = str(uuid.uuid4())
        test_db.create_company(
            company_id=company_id,
            name="Multi Content Test",
            storage_type="local",
            storage_folder_path="multi_content",
            content_types="portraits:Portraits,diplomas:Diplomas,certificates:Certificates"
        )
        
        company = test_db.get_company(company_id)
        folder_service = FolderService(temp_storage)
        
        # Create structures for different content types
        order_portrait = str(uuid.uuid4())
        order_diploma = str(uuid.uuid4())
        order_cert = str(uuid.uuid4())
        
        folder_service.ensure_order_structure(company, "portraits", order_portrait)
        folder_service.ensure_order_structure(company, "diplomas", order_diploma)
        folder_service.ensure_order_structure(company, "certificates", order_cert)
        
        # Verify all structures exist
        company_slug = folder_service.get_company_slug(company)
        base = temp_storage / "multi_content" / company_slug
        
        assert (base / "portraits" / order_portrait).exists()
        assert (base / "diplomas" / order_diploma).exists()
        assert (base / "certificates" / order_cert).exists()
        
        # Verify subfolders for each
        for content_type, order_id in [
            ("portraits", order_portrait),
            ("diplomas", order_diploma),
            ("certificates", order_cert)
        ]:
            order_path = base / content_type / order_id
            assert (order_path / "Image").exists()
            assert (order_path / "QR").exists()
            assert (order_path / "nft_markers").exists()
            assert (order_path / "nft_cache").exists()
    
    def test_default_storage_folder_path(self, temp_storage, test_db):
        """Test company without storage_folder_path uses company slug."""
        # Create company without storage_folder_path
        company_id = str(uuid.uuid4())
        test_db.create_company(
            company_id=company_id,
            name="Default Path Test",
            storage_type="local"
            # No storage_folder_path specified
        )
        
        company = test_db.get_company(company_id)
        folder_service = FolderService(temp_storage)
        
        order_id = str(uuid.uuid4())
        folder_service.ensure_order_structure(company, "portraits", order_id)
        
        # Should use company slug as folder path
        company_slug = folder_service.get_company_slug(company)
        expected_path = temp_storage / company_slug / company_slug / "portraits" / order_id
        
        assert expected_path.exists()
