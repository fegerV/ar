"""
Integration tests for company backup API endpoints.
Tests the remote storage API for company-specific backup management.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "vertex-ar"))

from fastapi.testclient import TestClient


@pytest.fixture
def mock_storage_manager():
    """Mock RemoteStorageManager."""
    with patch('app.api.remote_storage.get_remote_storage_manager') as mock:
        manager = Mock()
        
        # Mock storage provider
        storage = Mock()
        storage.test_connection.return_value = True
        
        manager.get_storage.return_value = storage
        manager.list_providers.return_value = ["yandex_disk", "google_drive"]
        
        mock.return_value = manager
        yield manager


@pytest.fixture
def mock_backup_manager():
    """Mock BackupManager."""
    with patch('app.api.remote_storage.create_backup_manager') as mock:
        manager = Mock()
        
        # Mock sync_to_remote
        manager.sync_to_remote.return_value = {
            "success": True,
            "remote_path": "/backups/test_backup.tar.gz",
            "size": 1024 * 1024 * 10  # 10 MB
        }
        
        # Mock restore_from_remote
        manager.restore_from_remote.return_value = {
            "success": True,
            "message": "Backup downloaded successfully",
            "local_path": "/tmp/backups/restored_backup.tar.gz",
            "backup_type": "database"
        }
        
        mock.return_value = manager
        yield manager


@pytest.fixture
def client_with_auth(test_app, test_db):
    """Create test client with authenticated session."""
    from app.database import Database
    
    # Create admin user
    test_db.create_user("admin", "testpass123", is_admin=True)
    
    # Create test client
    client = TestClient(test_app)
    
    # Login
    response = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "testpass123"
    })
    assert response.status_code == 200
    
    # Store auth token
    client.cookies.set("authToken", response.json()["access_token"])
    
    return client


def test_list_providers(client_with_auth, mock_storage_manager):
    """Test listing available backup providers."""
    response = client_with_auth.get("/api/remote-storage/providers")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert "providers" in data
    assert data["count"] == 2
    assert len(data["providers"]) == 2
    
    # Check provider details
    provider_names = [p["name"] for p in data["providers"]]
    assert "yandex_disk" in provider_names
    assert "google_drive" in provider_names


def test_set_company_backup_config(client_with_auth, test_db, mock_storage_manager):
    """Test setting backup configuration for a company."""
    # Create test company
    company_id = "test-company-1"
    test_db.create_company(company_id=company_id, name="Test Company 1")
    
    # Set backup config
    response = client_with_auth.post(
        f"/api/remote-storage/companies/{company_id}/backup-config",
        json={
            "backup_provider": "yandex_disk",
            "backup_remote_path": "/vertex-ar/company1/backups"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["company_id"] == company_id
    assert data["company_name"] == "Test Company 1"
    assert data["backup_provider"] == "yandex_disk"
    assert data["backup_remote_path"] == "/vertex-ar/company1/backups"
    
    # Verify in database
    company = test_db.get_company(company_id)
    assert company["backup_provider"] == "yandex_disk"
    assert company["backup_remote_path"] == "/vertex-ar/company1/backups"


def test_set_company_backup_config_invalid_provider(client_with_auth, test_db, mock_storage_manager):
    """Test setting backup config with invalid provider."""
    # Create test company
    company_id = "test-company-2"
    test_db.create_company(company_id=company_id, name="Test Company 2")
    
    # Mock invalid provider
    mock_storage_manager.get_storage.return_value = None
    
    # Try to set backup config with invalid provider
    response = client_with_auth.post(
        f"/api/remote-storage/companies/{company_id}/backup-config",
        json={
            "backup_provider": "invalid_provider",
            "backup_remote_path": "/backups"
        }
    )
    
    assert response.status_code == 400
    assert "not configured" in response.json()["detail"]


def test_set_company_backup_config_company_not_found(client_with_auth, mock_storage_manager):
    """Test setting backup config for non-existent company."""
    response = client_with_auth.post(
        "/api/remote-storage/companies/non-existent/backup-config",
        json={
            "backup_provider": "yandex_disk",
            "backup_remote_path": "/backups"
        }
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_get_company_backup_config(client_with_auth, test_db):
    """Test getting backup configuration for a company."""
    # Create company with backup config
    company_id = "test-company-3"
    test_db.create_company(
        company_id=company_id,
        name="Test Company 3",
        backup_provider="google_drive",
        backup_remote_path="/company3/backups"
    )
    
    # Get backup config
    response = client_with_auth.get(
        f"/api/remote-storage/companies/{company_id}/backup-config"
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["company_id"] == company_id
    assert data["company_name"] == "Test Company 3"
    assert data["backup_provider"] == "google_drive"
    assert data["backup_remote_path"] == "/company3/backups"


def test_get_company_backup_config_not_found(client_with_auth):
    """Test getting backup config for non-existent company."""
    response = client_with_auth.get(
        "/api/remote-storage/companies/non-existent/backup-config"
    )
    
    assert response.status_code == 404


def test_list_companies_backup_configs(client_with_auth, test_db):
    """Test listing backup configurations for all companies."""
    # Create test companies
    test_db.create_company(
        company_id="company-1",
        name="Company 1",
        backup_provider="yandex_disk",
        backup_remote_path="/company1"
    )
    test_db.create_company(
        company_id="company-2",
        name="Company 2",
        backup_provider="google_drive",
        backup_remote_path="/company2"
    )
    test_db.create_company(
        company_id="company-3",
        name="Company 3"  # No backup config
    )
    
    # List all configs
    response = client_with_auth.get("/api/remote-storage/companies/backup-configs")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert "companies" in data
    assert data["count"] >= 3  # At least our 3 test companies
    
    # Verify our companies
    companies_dict = {c["company_id"]: c for c in data["companies"]}
    
    assert "company-1" in companies_dict
    assert companies_dict["company-1"]["backup_provider"] == "yandex_disk"
    
    assert "company-2" in companies_dict
    assert companies_dict["company-2"]["backup_provider"] == "google_drive"
    
    assert "company-3" in companies_dict
    assert companies_dict["company-3"]["backup_provider"] is None


def test_sync_company_backup(client_with_auth, test_db, mock_storage_manager, mock_backup_manager, tmp_path):
    """Test syncing a backup for a company."""
    # Create company with backup config
    company_id = "test-company-4"
    test_db.create_company(
        company_id=company_id,
        name="Test Company 4",
        backup_provider="yandex_disk",
        backup_remote_path="/company4/backups"
    )
    
    # Create a temporary backup file
    backup_file = tmp_path / "test_backup.tar.gz"
    backup_file.write_text("test backup content")
    
    # Sync backup
    response = client_with_auth.post(
        f"/api/remote-storage/companies/{company_id}/sync-backup",
        params={"backup_path": str(backup_file)}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert data["company_id"] == company_id
    assert data["company_name"] == "Test Company 4"
    assert data["provider"] == "yandex_disk"
    assert data["size_mb"] == 10.0
    
    # Verify backup manager was called
    mock_backup_manager.sync_to_remote.assert_called_once()


def test_sync_company_backup_no_provider(client_with_auth, test_db):
    """Test syncing backup for company without backup provider."""
    # Create company without backup config
    company_id = "test-company-5"
    test_db.create_company(company_id=company_id, name="Test Company 5")
    
    # Try to sync
    response = client_with_auth.post(
        f"/api/remote-storage/companies/{company_id}/sync-backup",
        params={"backup_path": "/tmp/backup.tar.gz"}
    )
    
    assert response.status_code == 400
    assert "does not have a backup provider" in response.json()["detail"]


def test_sync_company_backup_file_not_found(client_with_auth, test_db, mock_storage_manager):
    """Test syncing non-existent backup file."""
    # Create company with backup config
    company_id = "test-company-6"
    test_db.create_company(
        company_id=company_id,
        name="Test Company 6",
        backup_provider="yandex_disk",
        backup_remote_path="/backups"
    )
    
    # Try to sync non-existent file
    response = client_with_auth.post(
        f"/api/remote-storage/companies/{company_id}/sync-backup",
        params={"backup_path": "/non/existent/backup.tar.gz"}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_download_company_backup(client_with_auth, test_db, mock_storage_manager, mock_backup_manager):
    """Test downloading a backup for a company."""
    # Create company with backup config
    company_id = "test-company-7"
    test_db.create_company(
        company_id=company_id,
        name="Test Company 7",
        backup_provider="google_drive",
        backup_remote_path="/company7/backups"
    )
    
    # Download backup
    response = client_with_auth.post(
        f"/api/remote-storage/companies/{company_id}/download-backup",
        params={"remote_filename": "backup_20250101_120000.tar.gz"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert data["company_id"] == company_id
    assert data["company_name"] == "Test Company 7"
    assert data["provider"] == "google_drive"
    assert "local_path" in data
    assert data["backup_type"] == "database"
    
    # Verify backup manager was called
    mock_backup_manager.restore_from_remote.assert_called_once()


def test_download_company_backup_no_provider(client_with_auth, test_db):
    """Test downloading backup for company without backup provider."""
    # Create company without backup config
    company_id = "test-company-8"
    test_db.create_company(company_id=company_id, name="Test Company 8")
    
    # Try to download
    response = client_with_auth.post(
        f"/api/remote-storage/companies/{company_id}/download-backup",
        params={"remote_filename": "backup.tar.gz"}
    )
    
    assert response.status_code == 400
    assert "does not have a backup provider" in response.json()["detail"]


def test_unset_company_backup_config(client_with_auth, test_db, mock_storage_manager):
    """Test unsetting backup configuration."""
    # Create company with backup config
    company_id = "test-company-9"
    test_db.create_company(
        company_id=company_id,
        name="Test Company 9",
        backup_provider="yandex_disk",
        backup_remote_path="/backups"
    )
    
    # Unset backup config
    response = client_with_auth.post(
        f"/api/remote-storage/companies/{company_id}/backup-config",
        json={
            "backup_provider": None,
            "backup_remote_path": None
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["backup_provider"] is None
    assert data["backup_remote_path"] is None
    
    # Verify in database
    company = test_db.get_company(company_id)
    assert company["backup_provider"] is None
    assert company["backup_remote_path"] is None
