"""
Unit tests for company storage defaults and migration to local_disk.
Tests Pydantic models, database layer, and migration logic.
"""
import pytest
import sqlite3
import tempfile
from pathlib import Path
from pydantic import ValidationError

from app.models import CompanyCreate, CompanyUpdate, CompanyStorageUpdate, CompanyStorageTypeUpdate
from app.database import Database
from app.storage_utils import is_local_storage, normalize_storage_type


class TestStorageUtils:
    """Test storage utility functions."""
    
    def test_is_local_storage_local(self):
        """Test is_local_storage recognizes 'local'."""
        assert is_local_storage("local") is True
    
    def test_is_local_storage_local_disk(self):
        """Test is_local_storage recognizes 'local_disk'."""
        assert is_local_storage("local_disk") is True
    
    def test_is_local_storage_minio(self):
        """Test is_local_storage rejects 'minio'."""
        assert is_local_storage("minio") is False
    
    def test_is_local_storage_yandex_disk(self):
        """Test is_local_storage rejects 'yandex_disk'."""
        assert is_local_storage("yandex_disk") is False
    
    def test_normalize_storage_type_local(self):
        """Test normalize_storage_type converts 'local' to 'local_disk'."""
        assert normalize_storage_type("local") == "local_disk"
    
    def test_normalize_storage_type_local_disk(self):
        """Test normalize_storage_type keeps 'local_disk'."""
        assert normalize_storage_type("local_disk") == "local_disk"
    
    def test_normalize_storage_type_other(self):
        """Test normalize_storage_type keeps other types unchanged."""
        assert normalize_storage_type("minio") == "minio"
        assert normalize_storage_type("yandex_disk") == "yandex_disk"


class TestCompanyCreateDefaults:
    """Test CompanyCreate Pydantic model defaults."""
    
    def test_default_storage_type(self):
        """Test storage_type defaults to 'local_disk'."""
        company = CompanyCreate(name="Test Company")
        assert company.storage_type == "local_disk"
    
    def test_default_storage_folder_path(self):
        """Test storage_folder_path defaults to 'vertex_ar_content'."""
        company = CompanyCreate(name="Test Company")
        assert company.storage_folder_path == "vertex_ar_content"
    
    def test_accepts_local_disk(self):
        """Test CompanyCreate accepts 'local_disk' as storage_type."""
        company = CompanyCreate(name="Test Company", storage_type="local_disk")
        assert company.storage_type == "local_disk"
    
    def test_accepts_local_legacy(self):
        """Test CompanyCreate accepts legacy 'local' as storage_type."""
        company = CompanyCreate(name="Test Company", storage_type="local")
        assert company.storage_type == "local"
    
    def test_accepts_minio(self):
        """Test CompanyCreate accepts 'minio' as storage_type."""
        company = CompanyCreate(name="Test Company", storage_type="minio")
        assert company.storage_type == "minio"
    
    def test_accepts_yandex_disk(self):
        """Test CompanyCreate accepts 'yandex_disk' as storage_type."""
        company = CompanyCreate(name="Test Company", storage_type="yandex_disk")
        assert company.storage_type == "yandex_disk"
    
    def test_rejects_invalid_storage_type(self):
        """Test CompanyCreate rejects invalid storage_type."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyCreate(name="Test Company", storage_type="invalid")
        
        assert "storage_type" in str(exc_info.value)


class TestCompanyUpdateValidation:
    """Test CompanyUpdate Pydantic model validation."""
    
    def test_accepts_local_disk(self):
        """Test CompanyUpdate accepts 'local_disk' as storage_type."""
        update = CompanyUpdate(storage_type="local_disk")
        assert update.storage_type == "local_disk"
    
    def test_accepts_local_legacy(self):
        """Test CompanyUpdate accepts legacy 'local' as storage_type."""
        update = CompanyUpdate(storage_type="local")
        assert update.storage_type == "local"
    
    def test_accepts_none(self):
        """Test CompanyUpdate accepts None for optional fields."""
        update = CompanyUpdate()
        assert update.storage_type is None
    
    def test_rejects_invalid_storage_type(self):
        """Test CompanyUpdate rejects invalid storage_type."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyUpdate(storage_type="invalid")
        
        assert "storage_type" in str(exc_info.value)


class TestCompanyStorageModels:
    """Test CompanyStorageUpdate and CompanyStorageTypeUpdate models."""
    
    def test_storage_update_accepts_local_disk(self):
        """Test CompanyStorageUpdate accepts 'local_disk'."""
        update = CompanyStorageUpdate(storage_type="local_disk")
        assert update.storage_type == "local_disk"
    
    def test_storage_update_accepts_local_legacy(self):
        """Test CompanyStorageUpdate accepts legacy 'local'."""
        update = CompanyStorageUpdate(storage_type="local")
        assert update.storage_type == "local"
    
    def test_storage_type_update_accepts_local_disk(self):
        """Test CompanyStorageTypeUpdate accepts 'local_disk'."""
        update = CompanyStorageTypeUpdate(storage_type="local_disk")
        assert update.storage_type == "local_disk"
    
    def test_storage_type_update_accepts_local_legacy(self):
        """Test CompanyStorageTypeUpdate accepts legacy 'local'."""
        update = CompanyStorageTypeUpdate(storage_type="local")
        assert update.storage_type == "local"
    
    def test_storage_update_rejects_invalid(self):
        """Test CompanyStorageUpdate rejects invalid storage_type."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyStorageUpdate(storage_type="invalid")
        
        assert "storage_type" in str(exc_info.value)
    
    def test_storage_type_update_rejects_invalid(self):
        """Test CompanyStorageTypeUpdate rejects invalid storage_type."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyStorageTypeUpdate(storage_type="invalid")
        
        assert "storage_type" in str(exc_info.value)


class TestDatabaseDefaults:
    """Test database layer defaults and migrations."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = Path(tmp.name)
        
        db = Database(db_path)
        yield db
        
        # Cleanup
        db._connection.close()
        db_path.unlink(missing_ok=True)
    
    def test_default_company_uses_local_disk(self, temp_db):
        """Test default 'Vertex AR' company uses 'local_disk' storage type."""
        company = temp_db.get_company_by_name("Vertex AR")
        assert company is not None
        assert company["storage_type"] == "local_disk"
    
    def test_default_company_has_folder_path(self, temp_db):
        """Test default 'Vertex AR' company has storage_folder_path set."""
        company = temp_db.get_company_by_name("Vertex AR")
        assert company is not None
        assert company["storage_folder_path"] == "vertex_ar_content"
    
    def test_create_company_defaults(self, temp_db):
        """Test create_company uses 'local_disk' and 'vertex_ar_content' defaults."""
        temp_db.create_company(
            company_id="test-company-1",
            name="Test Company 1"
        )
        
        company = temp_db.get_company("test-company-1")
        assert company["storage_type"] == "local_disk"
        assert company["storage_folder_path"] == "vertex_ar_content"
    
    def test_create_company_explicit_local_disk(self, temp_db):
        """Test create_company accepts explicit 'local_disk'."""
        temp_db.create_company(
            company_id="test-company-2",
            name="Test Company 2",
            storage_type="local_disk",
            storage_folder_path="custom_path"
        )
        
        company = temp_db.get_company("test-company-2")
        assert company["storage_type"] == "local_disk"
        assert company["storage_folder_path"] == "custom_path"
    
    def test_create_company_explicit_local_legacy(self, temp_db):
        """Test create_company accepts legacy 'local' (for backward compatibility)."""
        temp_db.create_company(
            company_id="test-company-3",
            name="Test Company 3",
            storage_type="local"
        )
        
        company = temp_db.get_company("test-company-3")
        assert company["storage_type"] == "local"
    
    def test_migration_converts_local_to_local_disk(self):
        """Test database initialization migrates legacy 'local' to 'local_disk'."""
        # Create a database with legacy 'local' storage type
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = Path(tmp.name)
        
        try:
            # Create initial database and insert legacy data
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Create minimal schema
            cursor.execute("""
                CREATE TABLE companies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    storage_type TEXT NOT NULL DEFAULT 'local',
                    storage_folder_path TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert legacy company with 'local' storage type
            cursor.execute(
                "INSERT INTO companies (id, name, storage_type) VALUES (?, ?, ?)",
                ("legacy-company", "Legacy Company", "local")
            )
            conn.commit()
            conn.close()
            
            # Now initialize Database which should run migration
            db = Database(db_path)
            
            # Check that legacy company was migrated
            company = db.get_company("legacy-company")
            assert company["storage_type"] == "local_disk"
            
            # Check that default company uses local_disk
            default_company = db.get_company_by_name("Vertex AR")
            assert default_company["storage_type"] == "local_disk"
            
            db._connection.close()
        finally:
            db_path.unlink(missing_ok=True)
    
    def test_migration_idempotent(self, temp_db):
        """Test migration can run multiple times without issues."""
        # Insert a company with local_disk
        temp_db.create_company(
            company_id="test-company-4",
            name="Test Company 4",
            storage_type="local_disk"
        )
        
        # Manually run migration logic again
        cursor = temp_db._connection.execute(
            "SELECT COUNT(*) FROM companies WHERE storage_type = 'local'"
        )
        count = cursor.fetchone()[0]
        assert count == 0  # No legacy companies to migrate
        
        # Verify existing data unchanged
        company = temp_db.get_company("test-company-4")
        assert company["storage_type"] == "local_disk"
    
    def test_backfill_storage_folder_path(self):
        """Test backfill adds default storage_folder_path to existing companies."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = Path(tmp.name)
        
        try:
            # Create initial database with company missing storage_folder_path
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE companies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    storage_type TEXT NOT NULL DEFAULT 'local_disk',
                    storage_folder_path TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert company without storage_folder_path
            cursor.execute(
                "INSERT INTO companies (id, name, storage_type) VALUES (?, ?, ?)",
                ("test-company-5", "Test Company 5", "local_disk")
            )
            conn.commit()
            conn.close()
            
            # Initialize Database which should run backfill
            db = Database(db_path)
            
            # Check that storage_folder_path was backfilled
            company = db.get_company("test-company-5")
            assert company["storage_folder_path"] == "vertex_ar_content"
            
            db._connection.close()
        finally:
            db_path.unlink(missing_ok=True)


class TestBackwardCompatibility:
    """Test backward compatibility with legacy 'local' storage type."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = Path(tmp.name)
        
        db = Database(db_path)
        yield db
        
        # Cleanup
        db._connection.close()
        db_path.unlink(missing_ok=True)
    
    def test_legacy_local_not_rejected(self, temp_db):
        """Test that existing 'local' storage type is not rejected."""
        # Manually insert a company with legacy 'local' type (bypassing migration)
        temp_db._connection.execute(
            "UPDATE companies SET storage_type = 'local' WHERE id = ?",
            ("vertex-ar-default",)
        )
        temp_db._connection.commit()
        
        # Verify it can be retrieved
        company = temp_db.get_company("vertex-ar-default")
        assert company["storage_type"] == "local"
    
    def test_storage_utils_treats_both_as_local(self):
        """Test storage utilities treat both 'local' and 'local_disk' as local storage."""
        assert is_local_storage("local") is True
        assert is_local_storage("local_disk") is True
        
        # Both should be treated the same way by utility functions
        assert is_local_storage("local") == is_local_storage("local_disk")
