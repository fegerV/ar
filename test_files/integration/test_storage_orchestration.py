"""
Integration tests for storage orchestration.
Tests end-to-end folder provisioning when companies configure storage and categories.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.database import Database
from storage_manager import StorageManager
from app.services.folder_service import FolderService


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db():
    """Create temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield db_path


@pytest.fixture
def database(temp_db):
    """Create test database instance."""
    db = Database(temp_db)
    
    # Create default company
    db.create_company(
        company_id="test-company",
        name="Test Company"
    )
    
    return db


@pytest.fixture
def storage_manager(temp_storage):
    """Create StorageManager instance."""
    return StorageManager(temp_storage)


@pytest.fixture
def mock_app(database, storage_manager):
    """Mock FastAPI app with database and storage manager."""
    app = MagicMock()
    app.state.database = database
    app.state.storage_manager = storage_manager
    
    # Patch get_current_app for both app.main and storage_manager imports
    with patch('app.main.get_current_app', return_value=app):
        yield app


@pytest.mark.asyncio
async def test_provision_company_storage_local(mock_app, database, storage_manager, temp_storage):
    """Test provisioning company storage for local storage type."""
    company_id = "test-company"
    category_slugs = ["portraits", "diplomas", "certificates"]
    
    result = await storage_manager.provision_company_storage(
        company_id,
        category_slugs
    )
    
    assert result["success"] is True
    assert result["company_id"] == company_id
    assert result["storage_type"] == "local"
    assert result["categories_provisioned"] == 3
    assert result["total_paths_created"] > 0
    
    # Verify hierarchy
    for slug in category_slugs:
        assert result["hierarchy"][slug]["success"] is True


@pytest.mark.asyncio
async def test_provision_company_storage_creates_directories(mock_app, database, storage_manager, temp_storage):
    """Test that provisioning actually creates directories."""
    company_id = "test-company"
    category_slugs = ["portraits"]
    
    result = await storage_manager.provision_company_storage(
        company_id,
        category_slugs
    )
    
    assert result["success"] is True
    
    # Verify directories exist
    company = database.get_company(company_id)
    company_slug = storage_manager._get_company_slug(company)
    
    base_path = temp_storage / company_slug / company_slug / "portraits"
    assert base_path.exists()
    
    for subfolder in FolderService.STANDARD_SUBFOLDERS:
        assert (base_path / subfolder).exists()


@pytest.mark.asyncio
async def test_verify_company_storage(mock_app, database, storage_manager):
    """Test verifying company storage hierarchy."""
    company_id = "test-company"
    category_slugs = ["portraits", "diplomas"]
    
    # Provision first
    await storage_manager.provision_company_storage(company_id, category_slugs)
    
    # Now verify
    result = await storage_manager.verify_company_storage(company_id, category_slugs)
    
    assert result["all_exist"] is True
    assert result["company_id"] == company_id
    
    for slug in category_slugs:
        assert result["categories"][slug]["exists"] is True


@pytest.mark.asyncio
async def test_verify_company_storage_missing(mock_app, database, storage_manager):
    """Test verification when directories don't exist."""
    company_id = "test-company"
    category_slugs = ["nonexistent"]
    
    result = await storage_manager.verify_company_storage(company_id, category_slugs)
    
    assert result["all_exist"] is False
    assert result["categories"]["nonexistent"]["exists"] is False


@pytest.mark.asyncio
async def test_provision_on_content_types_update(mock_app, database, storage_manager, temp_storage):
    """Test that storage is provisioned when content types are updated."""
    company_id = "test-company"
    
    # Update content types
    content_types_str = "portraits:Portraits,diplomas:Diplomas"
    success = database.update_company_content_types(company_id, content_types_str)
    assert success is True
    
    # Provision storage based on content types
    content_types_list = database.deserialize_content_types(content_types_str)
    category_slugs = [ct['slug'] for ct in content_types_list]
    
    result = await storage_manager.provision_company_storage(company_id, category_slugs)
    
    assert result["success"] is True
    assert result["categories_provisioned"] == 2
    
    # Verify directories exist
    company = database.get_company(company_id)
    company_slug = storage_manager._get_company_slug(company)
    
    for slug in category_slugs:
        base_path = temp_storage / company_slug / company_slug / slug
        assert base_path.exists()


@pytest.mark.asyncio
async def test_provision_with_custom_subfolders(mock_app, database, storage_manager, temp_storage):
    """Test provisioning with custom subfolders."""
    company_id = "test-company"
    category_slugs = ["portraits"]
    custom_subfolders = ["CustomFolder1", "CustomFolder2"]
    
    result = await storage_manager.provision_company_storage(
        company_id,
        category_slugs,
        subfolders=custom_subfolders
    )
    
    assert result["success"] is True
    
    # Verify custom subfolders exist
    company = database.get_company(company_id)
    company_slug = storage_manager._get_company_slug(company)
    
    base_path = temp_storage / company_slug / company_slug / "portraits"
    assert (base_path / "CustomFolder1").exists()
    assert (base_path / "CustomFolder2").exists()


@pytest.mark.asyncio
async def test_provision_nonexistent_company(mock_app, storage_manager):
    """Test provisioning for nonexistent company raises error."""
    with pytest.raises(ValueError) as exc_info:
        await storage_manager.provision_company_storage(
            "nonexistent-company",
            ["portraits"]
        )
    
    assert "Company not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_provision_idempotent(mock_app, database, storage_manager):
    """Test that provisioning is idempotent."""
    company_id = "test-company"
    category_slugs = ["portraits"]
    
    # First provision
    result1 = await storage_manager.provision_company_storage(company_id, category_slugs)
    assert result1["success"] is True
    
    # Second provision
    result2 = await storage_manager.provision_company_storage(company_id, category_slugs)
    assert result2["success"] is True
    
    # Results should be consistent
    assert result1["company_slug"] == result2["company_slug"]


@pytest.mark.asyncio
async def test_provision_multiple_companies(mock_app, database, storage_manager, temp_storage):
    """Test provisioning storage for multiple companies."""
    # Create additional companies
    database.create_company("company-1", "Company 1")
    database.create_company("company-2", "Company 2")
    
    category_slugs = ["portraits", "diplomas"]
    
    # Provision for each company
    for company_id in ["company-1", "company-2"]:
        result = await storage_manager.provision_company_storage(company_id, category_slugs)
        assert result["success"] is True
    
    # Verify both companies have separate directories
    company1 = database.get_company("company-1")
    company2 = database.get_company("company-2")
    
    slug1 = storage_manager._get_company_slug(company1)
    slug2 = storage_manager._get_company_slug(company2)
    
    assert slug1 != slug2
    
    for slug in [slug1, slug2]:
        for category in category_slugs:
            path = temp_storage / slug / slug / category
            assert path.exists()


@pytest.mark.asyncio
async def test_provision_with_storage_folder_path(mock_app, database, storage_manager, temp_storage):
    """Test provisioning with custom storage_folder_path."""
    company_id = "test-company"
    
    # Update company with custom storage_folder_path
    database.update_company(company_id, storage_folder_path="custom_storage")
    
    category_slugs = ["portraits"]
    
    result = await storage_manager.provision_company_storage(company_id, category_slugs)
    
    assert result["success"] is True
    assert result["folder_path"] == "custom_storage"
    
    # Verify directory uses custom path
    company = database.get_company(company_id)
    company_slug = storage_manager._get_company_slug(company)
    
    base_path = temp_storage / "custom_storage" / company_slug / "portraits"
    assert base_path.exists()


@pytest.mark.asyncio
async def test_clear_cache_on_storage_update(mock_app, database, storage_manager):
    """Test that adapter cache is cleared when storage configuration changes."""
    company_id = "test-company"
    
    # Create adapter (will be cached)
    adapter1 = storage_manager.get_company_adapter(company_id, "portraits")
    
    # Clear cache
    storage_manager.clear_company_cache(company_id)
    
    # Get adapter again (should be new instance)
    adapter2 = storage_manager.get_company_adapter(company_id, "portraits")
    
    # Adapters should be different instances after cache clear
    assert adapter1 is not adapter2


@pytest.mark.asyncio
async def test_provision_logs_detailed_info(mock_app, database, storage_manager, caplog):
    """Test that provisioning logs detailed information."""
    import logging
    caplog.set_level(logging.INFO)
    
    company_id = "test-company"
    category_slugs = ["portraits", "diplomas"]
    
    result = await storage_manager.provision_company_storage(company_id, category_slugs)
    
    assert result["success"] is True
    
    # Check for log messages
    log_messages = [rec.message for rec in caplog.records]
    
    # Should log provisioning operation
    assert any("Provisioning company storage hierarchy" in msg for msg in log_messages)


@pytest.mark.asyncio
async def test_provision_error_handling(mock_app, database, storage_manager, monkeypatch):
    """Test error handling during provisioning."""
    from app.services.folder_service import FolderCreationError
    
    company_id = "test-company"
    category_slugs = ["portraits"]
    
    # Mock FolderService to raise error
    def mock_provision(*args, **kwargs):
        raise FolderCreationError("Simulated error")
    
    with patch('app.services.folder_service.FolderService.provision_company_hierarchy', side_effect=mock_provision):
        result = await storage_manager.provision_company_storage(company_id, category_slugs)
        
        assert result["success"] is False
        assert "error" in result
        assert "Simulated error" in result["error"]
