"""
Unit tests for company backup configuration functionality.
Tests database methods for managing backup provider assignments.
"""
import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "vertex-ar"))

from app.database import Database


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        yield db


def test_create_company_with_backup_config(test_db):
    """Test creating a company with backup configuration."""
    company_id = "test-company-1"
    
    test_db.create_company(
        company_id=company_id,
        name="Test Company",
        backup_provider="yandex_disk",
        backup_remote_path="/backups/test-company"
    )
    
    company = test_db.get_company(company_id)
    assert company is not None
    assert company["name"] == "Test Company"
    assert company["backup_provider"] == "yandex_disk"
    assert company["backup_remote_path"] == "/backups/test-company"


def test_create_company_without_backup_config(test_db):
    """Test creating a company without backup configuration."""
    company_id = "test-company-2"
    
    test_db.create_company(
        company_id=company_id,
        name="Test Company 2"
    )
    
    company = test_db.get_company(company_id)
    assert company is not None
    assert company["name"] == "Test Company 2"
    assert company["backup_provider"] is None
    assert company["backup_remote_path"] is None


def test_set_company_backup_config(test_db):
    """Test setting backup configuration for an existing company."""
    company_id = "test-company-3"
    
    # Create company without backup config
    test_db.create_company(company_id=company_id, name="Test Company 3")
    
    # Set backup config
    success = test_db.set_company_backup_config(
        company_id=company_id,
        backup_provider="google_drive",
        backup_remote_path="/vertex-ar/backups"
    )
    
    assert success is True
    
    # Verify config
    company = test_db.get_company(company_id)
    assert company["backup_provider"] == "google_drive"
    assert company["backup_remote_path"] == "/vertex-ar/backups"


def test_update_company_backup_config(test_db):
    """Test updating existing backup configuration."""
    company_id = "test-company-4"
    
    # Create company with backup config
    test_db.create_company(
        company_id=company_id,
        name="Test Company 4",
        backup_provider="yandex_disk",
        backup_remote_path="/old/path"
    )
    
    # Update backup config
    success = test_db.set_company_backup_config(
        company_id=company_id,
        backup_provider="google_drive",
        backup_remote_path="/new/path"
    )
    
    assert success is True
    
    # Verify updated config
    company = test_db.get_company(company_id)
    assert company["backup_provider"] == "google_drive"
    assert company["backup_remote_path"] == "/new/path"


def test_unset_company_backup_config(test_db):
    """Test unsetting backup configuration."""
    company_id = "test-company-5"
    
    # Create company with backup config
    test_db.create_company(
        company_id=company_id,
        name="Test Company 5",
        backup_provider="yandex_disk",
        backup_remote_path="/backups"
    )
    
    # Unset backup config
    success = test_db.set_company_backup_config(
        company_id=company_id,
        backup_provider=None,
        backup_remote_path=None
    )
    
    assert success is True
    
    # Verify config is unset
    company = test_db.get_company(company_id)
    assert company["backup_provider"] is None
    assert company["backup_remote_path"] is None


def test_get_company_backup_config(test_db):
    """Test getting backup configuration for a company."""
    company_id = "test-company-6"
    
    # Create company with backup config
    test_db.create_company(
        company_id=company_id,
        name="Test Company 6",
        backup_provider="yandex_disk",
        backup_remote_path="/test/backups"
    )
    
    # Get backup config
    config = test_db.get_company_backup_config(company_id)
    
    assert config is not None
    assert config["backup_provider"] == "yandex_disk"
    assert config["backup_remote_path"] == "/test/backups"


def test_get_company_backup_config_not_found(test_db):
    """Test getting backup configuration for non-existent company."""
    config = test_db.get_company_backup_config("non-existent")
    assert config is None


def test_update_company_with_backup_fields(test_db):
    """Test updating company using update_company method."""
    company_id = "test-company-7"
    
    # Create company
    test_db.create_company(company_id=company_id, name="Test Company 7")
    
    # Update with backup config
    success = test_db.update_company(
        company_id=company_id,
        backup_provider="yandex_disk",
        backup_remote_path="/vertex-backups"
    )
    
    assert success is True
    
    # Verify
    company = test_db.get_company(company_id)
    assert company["backup_provider"] == "yandex_disk"
    assert company["backup_remote_path"] == "/vertex-backups"


def test_companies_with_client_count_includes_backup_fields(test_db):
    """Test that get_companies_with_client_count includes backup fields."""
    company_id = "test-company-8"
    
    test_db.create_company(
        company_id=company_id,
        name="Test Company 8",
        backup_provider="google_drive",
        backup_remote_path="/company8/backups"
    )
    
    companies = test_db.get_companies_with_client_count()
    
    # Find our company
    company = next((c for c in companies if c["id"] == company_id), None)
    
    assert company is not None
    assert company["backup_provider"] == "google_drive"
    assert company["backup_remote_path"] == "/company8/backups"


def test_list_companies_includes_backup_fields(test_db):
    """Test that list_companies includes backup fields."""
    company_id = "test-company-9"
    
    test_db.create_company(
        company_id=company_id,
        name="Test Company 9",
        backup_provider="yandex_disk",
        backup_remote_path="/company9/remote"
    )
    
    companies = test_db.list_companies()
    
    # Find our company
    company = next((c for c in companies if c["id"] == company_id), None)
    
    assert company is not None
    assert company["backup_provider"] == "yandex_disk"
    assert company["backup_remote_path"] == "/company9/remote"
