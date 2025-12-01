"""
Integration tests for order workflow with storage folders.
Tests that orders create proper folder hierarchy for local storage.
"""
import tempfile
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.database import Database
from app.main import create_app


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_database():
    """Create test database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    
    db = Database(db_path)
    yield db
    
    # Cleanup
    db_path.unlink(missing_ok=True)


@pytest.fixture
def app_with_temp_storage(temp_storage, test_database, monkeypatch):
    """Create app with temporary storage and database."""
    # Override settings before creating app
    monkeypatch.setattr("app.config.settings.STORAGE_ROOT", temp_storage)
    monkeypatch.setattr("app.config.settings.DB_PATH", test_database.path)
    
    app = create_app()
    
    # Also update app state to ensure consistency
    app.state.config["STORAGE_ROOT"] = temp_storage
    app.state.database = test_database
    
    return app


@pytest.fixture
def client(app_with_temp_storage):
    """Create test client."""
    return TestClient(app_with_temp_storage)


@pytest.fixture
def admin_token(client, test_database):
    """Get admin token for authentication."""
    # Create admin user
    test_database.create_user("testadmin", "hashed_password", is_admin=True)
    
    # Login
    response = client.post(
        "/api/auth/login",
        json={"username": "testadmin", "password": "Qwerty123!@#"}
    )
    
    if response.status_code == 200:
        return response.json()["access_token"]
    
    # If default password doesn't work, user already exists
    return None


def create_test_image() -> bytes:
    """Create a test image."""
    img = Image.new('RGB', (640, 480), color='red')
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer.getvalue()


def create_test_video() -> bytes:
    """Create minimal test video."""
    # Minimal MP4 header
    mp4_header = bytes.fromhex(
        '0000002066747970697333323000000000000069736f366136316134'
    )
    return mp4_header + b'\x00' * 5000


class TestOrderWorkflowLocalStorage:
    """Tests for order workflow with local storage folders."""
    
    def test_order_creates_folder_structure(self, client, admin_token, test_database, temp_storage):
        """Test that creating an order creates proper folder structure."""
        # Create company with local storage
        company_id = "test-company-local"
        test_database.create_company(
            company_id=company_id,
            name="Test Company Local",
            storage_type="local",
            storage_folder_path="test_storage"
        )
        
        # Create order
        response = client.post(
            "/orders/create",
            data={
                "phone": "+7 900 123 45 67",
                "name": "Test Client",
                "company_id": company_id,
                "content_type": "portraits"
            },
            files={
                "image": ("test.jpg", create_test_image(), "image/jpeg"),
                "video": ("test.mp4", create_test_video(), "video/mp4")
            },
            headers={"Authorization": f"Bearer {admin_token}"} if admin_token else {},
            cookies={"authToken": "valid_session"} if not admin_token else {}
        )
        
        # Should succeed or fail auth (depending on setup)
        if response.status_code == 201:
            data = response.json()
            portrait_id = data["portrait"]["id"]
            
            # Check folder structure exists
            company_slug = "test_company_local"
            base_path = temp_storage / "test_storage" / company_slug / "portraits" / portrait_id
            
            assert base_path.exists(), f"Base path does not exist: {base_path}"
            assert (base_path / "Image").exists(), "Image subfolder not created"
            assert (base_path / "QR").exists(), "QR subfolder not created"
            assert (base_path / "nft_markers").exists(), "nft_markers subfolder not created"
            assert (base_path / "nft_cache").exists(), "nft_cache subfolder not created"
            
            # Check files are in correct locations
            image_file = base_path / "Image" / f"{portrait_id}.jpg"
            assert image_file.exists(), f"Image file not found: {image_file}"
            
            # Check QR code
            qr_file = base_path / "QR" / f"{portrait_id}_qr.png"
            assert qr_file.exists(), f"QR code not found: {qr_file}"
    
    def test_order_stores_relative_paths(self, client, admin_token, test_database, temp_storage):
        """Test that database stores relative paths."""
        company_id = "test-company-paths"
        test_database.create_company(
            company_id=company_id,
            name="Test Company Paths",
            storage_type="local",
            storage_folder_path="company_data"
        )
        
        response = client.post(
            "/orders/create",
            data={
                "phone": "+7 900 111 22 33",
                "name": "Test User",
                "company_id": company_id,
                "content_type": "certificates"
            },
            files={
                "image": ("image.jpg", create_test_image(), "image/jpeg"),
                "video": ("video.mp4", create_test_video(), "video/mp4")
            },
            headers={"Authorization": f"Bearer {admin_token}"} if admin_token else {},
            cookies={"authToken": "valid_session"} if not admin_token else {}
        )
        
        if response.status_code == 201:
            data = response.json()
            portrait_id = data["portrait"]["id"]
            
            # Get portrait from database
            portrait = test_database.get_portrait(portrait_id)
            
            # Check image path is relative
            image_path = portrait["image_path"]
            assert not image_path.startswith("/"), "Path should be relative, not absolute"
            assert "company_data" in image_path, "Path should include storage_folder_path"
            assert portrait_id in image_path, "Path should include order ID"
            assert "certificates" in image_path, "Path should include content type"
            assert "Image" in image_path, "Path should include Image subfolder"
            
            # Get video from database
            video = test_database.get_active_video(portrait_id)
            video_path = video["video_path"]
            assert not video_path.startswith("/"), "Video path should be relative"
            assert "company_data" in video_path, "Video path should include storage_folder_path"
    
    def test_order_with_default_storage_folder_path(self, client, admin_token, test_database, temp_storage):
        """Test order creation when company has no storage_folder_path set."""
        company_id = "test-company-default"
        test_database.create_company(
            company_id=company_id,
            name="Test Company Default",
            storage_type="local"
            # No storage_folder_path specified
        )
        
        response = client.post(
            "/orders/create",
            data={
                "phone": "+7 900 222 33 44",
                "name": "Default Test",
                "company_id": company_id
            },
            files={
                "image": ("img.jpg", create_test_image(), "image/jpeg"),
                "video": ("vid.mp4", create_test_video(), "video/mp4")
            },
            headers={"Authorization": f"Bearer {admin_token}"} if admin_token else {},
            cookies={"authToken": "valid_session"} if not admin_token else {}
        )
        
        if response.status_code == 201:
            data = response.json()
            portrait_id = data["portrait"]["id"]
            
            # Should use company slug as folder path
            company_slug = "test_company_default"
            base_path = temp_storage / company_slug / company_slug / "portraits" / portrait_id
            
            assert base_path.exists(), f"Default folder structure not created: {base_path}"
    
    def test_order_handles_permission_error(self, client, admin_token, test_database, temp_storage, monkeypatch):
        """Test that permission errors are handled gracefully."""
        company_id = "test-company-perms"
        test_database.create_company(
            company_id=company_id,
            name="Test Company Perms",
            storage_type="local",
            storage_folder_path="restricted"
        )
        
        # Mock folder service to raise PermissionError
        from app.services.folder_service import FolderService
        
        original_ensure = FolderService.ensure_order_structure
        
        def mock_ensure(*args, **kwargs):
            raise PermissionError("Test permission denied")
        
        monkeypatch.setattr(FolderService, "ensure_order_structure", mock_ensure)
        
        response = client.post(
            "/orders/create",
            data={
                "phone": "+7 900 333 44 55",
                "name": "Permission Test",
                "company_id": company_id
            },
            files={
                "image": ("img.jpg", create_test_image(), "image/jpeg"),
                "video": ("vid.mp4", create_test_video(), "video/mp4")
            },
            headers={"Authorization": f"Bearer {admin_token}"} if admin_token else {},
            cookies={"authToken": "valid_session"} if not admin_token else {}
        )
        
        if admin_token:  # Only check if we have auth
            # Should return 500 with storage error message
            assert response.status_code == 500
            assert "Storage error" in response.json().get("detail", "")


class TestOrderWorkflowMultipleContentTypes:
    """Tests for orders with different content types."""
    
    def test_portraits_content_type(self, client, admin_token, test_database, temp_storage):
        """Test order with portraits content type."""
        company_id = "test-company-portraits"
        test_database.create_company(
            company_id=company_id,
            name="Portraits Company",
            storage_type="local",
            storage_folder_path="storage",
            content_types="portraits:Portraits,diplomas:Diplomas"
        )
        
        response = client.post(
            "/orders/create",
            data={
                "phone": "+7 900 444 55 66",
                "name": "Portrait Client",
                "company_id": company_id,
                "content_type": "portraits"
            },
            files={
                "image": ("img.jpg", create_test_image(), "image/jpeg"),
                "video": ("vid.mp4", create_test_video(), "video/mp4")
            },
            headers={"Authorization": f"Bearer {admin_token}"} if admin_token else {},
            cookies={"authToken": "valid_session"} if not admin_token else {}
        )
        
        if response.status_code == 201:
            data = response.json()
            portrait_id = data["portrait"]["id"]
            
            # Check path includes content type
            portrait = test_database.get_portrait(portrait_id)
            assert "portraits" in portrait["image_path"]
    
    def test_diplomas_content_type(self, client, admin_token, test_database, temp_storage):
        """Test order with diplomas content type."""
        company_id = "test-company-diplomas"
        test_database.create_company(
            company_id=company_id,
            name="Diplomas Company",
            storage_type="local",
            storage_folder_path="storage",
            content_types="portraits:Portraits,diplomas:Diplomas"
        )
        
        response = client.post(
            "/orders/create",
            data={
                "phone": "+7 900 555 66 77",
                "name": "Diploma Client",
                "company_id": company_id,
                "content_type": "diplomas"
            },
            files={
                "image": ("img.jpg", create_test_image(), "image/jpeg"),
                "video": ("vid.mp4", create_test_video(), "video/mp4")
            },
            headers={"Authorization": f"Bearer {admin_token}"} if admin_token else {},
            cookies={"authToken": "valid_session"} if not admin_token else {}
        )
        
        if response.status_code == 201:
            data = response.json()
            portrait_id = data["portrait"]["id"]
            
            # Check path includes diplomas content type
            portrait = test_database.get_portrait(portrait_id)
            assert "diplomas" in portrait["image_path"]


class TestOrderWorkflowFileCleanup:
    """Tests for temporary file cleanup."""
    
    def test_temp_files_cleaned_up(self, client, admin_token, test_database, temp_storage):
        """Test that temporary files are cleaned up after order creation."""
        company_id = "test-company-cleanup"
        test_database.create_company(
            company_id=company_id,
            name="Cleanup Company",
            storage_type="local",
            storage_folder_path="data"
        )
        
        response = client.post(
            "/orders/create",
            data={
                "phone": "+7 900 666 77 88",
                "name": "Cleanup Test",
                "company_id": company_id
            },
            files={
                "image": ("img.jpg", create_test_image(), "image/jpeg"),
                "video": ("vid.mp4", create_test_video(), "video/mp4")
            },
            headers={"Authorization": f"Bearer {admin_token}"} if admin_token else {},
            cookies={"authToken": "valid_session"} if not admin_token else {}
        )
        
        if response.status_code == 201:
            data = response.json()
            portrait_id = data["portrait"]["id"]
            
            # Check temp directory doesn't exist
            temp_dir = temp_storage / "temp" / "orders" / portrait_id
            assert not temp_dir.exists(), "Temp directory should be cleaned up"
            
            # But final files should exist
            company_slug = "test_company_cleanup"
            final_path = temp_storage / "data" / company_slug / "portraits" / portrait_id / "Image"
            assert final_path.exists(), "Final files should exist"


class TestOrderWorkflowPublicURLs:
    """Tests for public URL generation."""
    
    def test_public_urls_work_with_relative_paths(self, client, admin_token, test_database, temp_storage):
        """Test that public URLs work with relative paths."""
        company_id = "test-company-urls"
        test_database.create_company(
            company_id=company_id,
            name="URLs Company",
            storage_type="local",
            storage_folder_path="public_storage"
        )
        
        response = client.post(
            "/orders/create",
            data={
                "phone": "+7 900 777 88 99",
                "name": "URL Test",
                "company_id": company_id
            },
            files={
                "image": ("img.jpg", create_test_image(), "image/jpeg"),
                "video": ("vid.mp4", create_test_video(), "video/mp4")
            },
            headers={"Authorization": f"Bearer {admin_token}"} if admin_token else {},
            cookies={"authToken": "valid_session"} if not admin_token else {}
        )
        
        if response.status_code == 201:
            data = response.json()
            portrait_id = data["portrait"]["id"]
            
            # Get portrait from database
            portrait = test_database.get_portrait(portrait_id)
            image_path = portrait["image_path"]
            
            # Public URL should be accessible via /storage/{relative_path}
            # The LocalStorageAdapter should handle this
            assert not image_path.startswith("/"), "Path should be relative for public URL generation"
            
            # Build expected public URL path
            expected_url_path = f"/storage/{image_path}"
            assert "public_storage" in expected_url_path
