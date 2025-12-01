"""
Unit tests for FolderService provisioning functionality.
Tests proactive hierarchy provisioning with explicit category slugs.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from app.services.folder_service import FolderService, FolderCreationError, FolderServiceError


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def folder_service(temp_storage):
    """Create FolderService instance."""
    return FolderService(temp_storage)


@pytest.fixture
def sample_company():
    """Sample company data."""
    return {
        "id": "test-company-123",
        "name": "Test Company",
        "storage_folder_path": "test_folder"
    }


def test_folder_service_initialization(folder_service, temp_storage):
    """Test FolderService initializes correctly."""
    assert folder_service.storage_root == temp_storage
    assert FolderService.STANDARD_SUBFOLDERS == ["Image", "QR", "nft_markers", "nft_cache"]


def test_provision_company_hierarchy_success(folder_service, sample_company, temp_storage):
    """Test successful provisioning of complete company hierarchy."""
    category_slugs = ["portraits", "diplomas", "certificates"]
    
    result = folder_service.provision_company_hierarchy(sample_company, category_slugs)
    
    assert result["success"] is True
    assert result["company_id"] == "test-company-123"
    assert result["categories_provisioned"] == 3
    assert result["total_paths_created"] > 0
    assert "hierarchy" in result
    
    # Verify all categories were created
    for slug in category_slugs:
        assert slug in result["hierarchy"]
        assert result["hierarchy"][slug]["success"] is True
        assert "base_path" in result["hierarchy"][slug]
        assert result["hierarchy"][slug]["subfolders"] == FolderService.STANDARD_SUBFOLDERS


def test_provision_company_hierarchy_creates_directories(folder_service, sample_company, temp_storage):
    """Test that provisioning actually creates directories on filesystem."""
    category_slugs = ["portraits", "diplomas"]
    
    result = folder_service.provision_company_hierarchy(sample_company, category_slugs)
    
    assert result["success"] is True
    
    # Verify directories exist
    company_slug = folder_service.get_company_slug(sample_company)
    folder_path = sample_company["storage_folder_path"]
    
    for category_slug in category_slugs:
        base_path = temp_storage / folder_path / company_slug / category_slug
        assert base_path.exists()
        assert base_path.is_dir()
        
        # Verify subfolders
        for subfolder in FolderService.STANDARD_SUBFOLDERS:
            subfolder_path = base_path / subfolder
            assert subfolder_path.exists()
            assert subfolder_path.is_dir()


def test_provision_company_hierarchy_with_explicit_slugs(folder_service, sample_company):
    """Test provisioning with explicit category slugs."""
    category_slugs = ["custom_category_1", "custom_category_2"]
    
    result = folder_service.provision_company_hierarchy(sample_company, category_slugs)
    
    assert result["success"] is True
    assert all(slug in result["hierarchy"] for slug in category_slugs)


def test_provision_company_hierarchy_without_folder_path(folder_service, temp_storage):
    """Test provisioning for company without storage_folder_path (uses company slug)."""
    company = {
        "id": "company-456",
        "name": "Company Without Path"
    }
    category_slugs = ["portraits"]
    
    result = folder_service.provision_company_hierarchy(company, category_slugs)
    
    assert result["success"] is True
    
    # Should use company slug as folder path
    company_slug = folder_service.get_company_slug(company)
    base_path = temp_storage / company_slug / company_slug / "portraits"
    assert base_path.exists()


def test_provision_company_hierarchy_idempotent(folder_service, sample_company):
    """Test that provisioning is idempotent (can be run multiple times)."""
    category_slugs = ["portraits"]
    
    # First provision
    result1 = folder_service.provision_company_hierarchy(sample_company, category_slugs)
    assert result1["success"] is True
    
    # Second provision (should succeed without errors)
    result2 = folder_service.provision_company_hierarchy(sample_company, category_slugs)
    assert result2["success"] is True
    assert result1["hierarchy"]["portraits"]["base_path"] == result2["hierarchy"]["portraits"]["base_path"]


def test_provision_company_hierarchy_permission_error(folder_service, sample_company, temp_storage, monkeypatch):
    """Test provisioning handles permission errors correctly."""
    category_slugs = ["portraits"]
    
    # Mock mkdir to raise PermissionError
    original_mkdir = Path.mkdir
    def mock_mkdir(*args, **kwargs):
        raise PermissionError("Permission denied")
    
    monkeypatch.setattr(Path, "mkdir", mock_mkdir)
    
    with pytest.raises(FolderCreationError) as exc_info:
        folder_service.provision_company_hierarchy(sample_company, category_slugs)
    
    assert "Failed to provision" in str(exc_info.value)
    assert "portraits" in str(exc_info.value)


def test_provision_category_structure(folder_service, sample_company, temp_storage):
    """Test provisioning single category structure."""
    category_slug = "diplomas"
    
    result = folder_service.provision_category_structure(sample_company, category_slug)
    
    assert result["success"] is True
    assert result["company_id"] == "test-company-123"
    assert result["category_slug"] == "diplomas"
    assert "base_path" in result
    assert result["subfolders"] == FolderService.STANDARD_SUBFOLDERS
    
    # Verify directory exists
    base_path = Path(result["base_path"])
    assert base_path.exists()


def test_verify_hierarchy_all_exist(folder_service, sample_company, temp_storage):
    """Test verification when all directories exist."""
    category_slugs = ["portraits", "diplomas"]
    
    # Provision first
    folder_service.provision_company_hierarchy(sample_company, category_slugs)
    
    # Now verify
    result = folder_service.verify_hierarchy(sample_company, category_slugs)
    
    assert result["all_exist"] is True
    assert result["company_id"] == "test-company-123"
    
    for slug in category_slugs:
        assert result["categories"][slug]["exists"] is True
        for subfolder in FolderService.STANDARD_SUBFOLDERS:
            assert result["categories"][slug]["subfolders"][subfolder]["exists"] is True


def test_verify_hierarchy_missing_directories(folder_service, sample_company):
    """Test verification when directories don't exist."""
    category_slugs = ["portraits", "nonexistent"]
    
    result = folder_service.verify_hierarchy(sample_company, category_slugs)
    
    assert result["all_exist"] is False
    assert result["categories"]["portraits"]["exists"] is False
    assert result["categories"]["nonexistent"]["exists"] is False


def test_verify_hierarchy_partial_exist(folder_service, sample_company, temp_storage):
    """Test verification when some directories exist and some don't."""
    category_slugs = ["portraits", "diplomas"]
    
    # Provision only portraits
    folder_service.provision_category_structure(sample_company, "portraits")
    
    # Verify both
    result = folder_service.verify_hierarchy(sample_company, category_slugs)
    
    assert result["all_exist"] is False
    assert result["categories"]["portraits"]["exists"] is True
    assert result["categories"]["diplomas"]["exists"] is False


def test_provision_logs_hierarchy(folder_service, sample_company, caplog):
    """Test that provisioning logs the hierarchy that was created."""
    import logging
    caplog.set_level(logging.INFO)
    
    category_slugs = ["portraits", "diplomas"]
    
    result = folder_service.provision_company_hierarchy(sample_company, category_slugs)
    
    assert result["success"] is True
    
    # Check log messages
    log_messages = [rec.message for rec in caplog.records]
    
    # Should log provisioning start
    assert any("Provisioning company storage hierarchy" in msg for msg in log_messages)
    
    # Should log each category provisioned
    assert any("Provisioned category hierarchy" in msg for msg in log_messages)
    
    # Should log completion
    assert any("Company hierarchy provisioned successfully" in msg for msg in log_messages)


def test_provision_surfaces_errors_in_result(folder_service, sample_company, monkeypatch):
    """Test that provisioning surfaces errors clearly in result."""
    category_slugs = ["portraits"]
    
    # Mock mkdir to raise OSError
    original_mkdir = Path.mkdir
    def mock_mkdir(*args, **kwargs):
        raise OSError("Disk full")
    
    monkeypatch.setattr(Path, "mkdir", mock_mkdir)
    
    with pytest.raises(FolderCreationError) as exc_info:
        folder_service.provision_company_hierarchy(sample_company, category_slugs)
    
    error_message = str(exc_info.value)
    assert "Disk full" in error_message
    assert "portraits" in error_message


def test_provision_company_hierarchy_empty_categories(folder_service, sample_company):
    """Test provisioning with empty category list."""
    category_slugs = []
    
    result = folder_service.provision_company_hierarchy(sample_company, category_slugs)
    
    assert result["success"] is True
    assert result["categories_provisioned"] == 0
    assert result["total_paths_created"] == 0


def test_provision_company_hierarchy_multiple_categories(folder_service, sample_company):
    """Test provisioning with many categories."""
    category_slugs = [f"category_{i}" for i in range(10)]
    
    result = folder_service.provision_company_hierarchy(sample_company, category_slugs)
    
    assert result["success"] is True
    assert result["categories_provisioned"] == 10
    assert len(result["hierarchy"]) == 10
    
    # All should succeed
    for slug in category_slugs:
        assert result["hierarchy"][slug]["success"] is True
