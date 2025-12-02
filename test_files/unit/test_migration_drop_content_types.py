"""
Unit tests for content_types column migration.

Tests the automatic migration that drops the legacy content_types column
from the companies table and normalizes storage_type values.
"""

import sqlite3
import tempfile
from pathlib import Path
import pytest
from app.database import Database, normalize_storage_type


class TestNormalizeStorageType:
    """Tests for normalize_storage_type helper function."""
    
    def test_normalize_local_to_local_disk(self):
        """Test that 'local' is normalized to 'local_disk'."""
        assert normalize_storage_type("local") == "local_disk"
    
    def test_preserve_local_disk(self):
        """Test that 'local_disk' remains unchanged."""
        assert normalize_storage_type("local_disk") == "local_disk"
    
    def test_preserve_minio(self):
        """Test that 'minio' remains unchanged."""
        assert normalize_storage_type("minio") == "minio"
    
    def test_preserve_yandex_disk(self):
        """Test that 'yandex_disk' remains unchanged."""
        assert normalize_storage_type("yandex_disk") == "yandex_disk"
    
    def test_preserve_other_values(self):
        """Test that other values pass through unchanged."""
        assert normalize_storage_type("s3") == "s3"
        assert normalize_storage_type("custom") == "custom"


class TestContentTypesMigration:
    """Tests for _migrate_drop_content_types method."""
    
    @pytest.fixture
    def db_with_content_types(self):
        """Create a test database with content_types column."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = Path(tmp.name)
        
        # Create database with OLD schema including content_types
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE companies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                storage_type TEXT NOT NULL DEFAULT 'local',
                storage_connection_id TEXT,
                yandex_disk_folder_id TEXT,
                content_types TEXT,
                storage_folder_path TEXT,
                backup_provider TEXT,
                backup_remote_path TEXT,
                email TEXT,
                description TEXT,
                city TEXT,
                phone TEXT,
                website TEXT,
                social_links TEXT,
                manager_name TEXT,
                manager_phone TEXT,
                manager_email TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert test data with legacy 'local' storage_type
        conn.execute("""
            INSERT INTO companies (id, name, storage_type, content_types, storage_folder_path)
            VALUES (?, ?, ?, ?, ?)
        """, ("test-1", "Test Company 1", "local", "portraits:Portraits", "test_content"))
        
        conn.execute("""
            INSERT INTO companies (id, name, storage_type, content_types, storage_folder_path)
            VALUES (?, ?, ?, ?, ?)
        """, ("test-2", "Test Company 2", "local_disk", "diplomas:Diplomas", "test_content"))
        
        conn.execute("""
            INSERT INTO companies (id, name, storage_type, content_types, storage_folder_path)
            VALUES (?, ?, ?, ?, ?)
        """, ("test-3", "Test Company 3", "minio", "certificates:Certificates", "test_content"))
        
        conn.commit()
        conn.close()
        
        yield db_path
        
        # Cleanup
        db_path.unlink(missing_ok=True)
    
    def test_migration_drops_content_types_column(self, db_with_content_types):
        """Test that migration removes content_types column."""
        # Before migration - verify column exists
        conn = sqlite3.connect(str(db_with_content_types))
        cursor = conn.execute("PRAGMA table_info(companies)")
        columns_before = [row[1] for row in cursor.fetchall()]
        assert "content_types" in columns_before
        conn.close()
        
        # Run migration by initializing Database
        # Note: We can't directly test _migrate_drop_content_types without creating
        # the full Database instance, so we test via normal initialization
        db = Database(db_with_content_types)
        
        # After migration - verify column removed
        cursor = db._connection.execute("PRAGMA table_info(companies)")
        columns_after = [row[1] for row in cursor.fetchall()]
        assert "content_types" not in columns_after
        
    def test_migration_normalizes_storage_type(self, db_with_content_types):
        """Test that migration normalizes storage_type values."""
        # Initialize database (triggers migration)
        db = Database(db_with_content_types)
        
        # Verify our test companies migrated (default company may also be created)
        cursor = db._connection.execute("SELECT COUNT(*) FROM companies WHERE id LIKE 'test-%'")
        assert cursor.fetchone()[0] == 3
        
        # Verify storage_type normalization for our test companies
        cursor = db._connection.execute("""
            SELECT id, name, storage_type FROM companies WHERE id LIKE 'test-%' ORDER BY id
        """)
        companies = cursor.fetchall()
        
        # Test Company 1: local -> local_disk
        assert companies[0][0] == "test-1"
        assert companies[0][2] == "local_disk"
        
        # Test Company 2: local_disk -> local_disk (unchanged)
        assert companies[1][0] == "test-2"
        assert companies[1][2] == "local_disk"
        
        # Test Company 3: minio -> minio (unchanged)
        assert companies[2][0] == "test-3"
        assert companies[2][2] == "minio"
    
    def test_migration_preserves_all_data(self, db_with_content_types):
        """Test that migration preserves all company data."""
        # Get data before migration (only our test companies)
        conn = sqlite3.connect(str(db_with_content_types))
        cursor = conn.execute("""
            SELECT id, name, storage_folder_path, email, description
            FROM companies WHERE id LIKE 'test-%' ORDER BY id
        """)
        companies_before = cursor.fetchall()
        conn.close()
        
        # Run migration
        db = Database(db_with_content_types)
        
        # Get data after migration (excluding content_types, only our test companies)
        cursor = db._connection.execute("""
            SELECT id, name, storage_folder_path, email, description
            FROM companies WHERE id LIKE 'test-%' ORDER BY id
        """)
        companies_after = cursor.fetchall()
        
        # Verify data preserved
        assert len(companies_after) == len(companies_before)
        assert len(companies_after) == 3
        for before, after in zip(companies_before, companies_after):
            assert before[0] == after[0]  # id
            assert before[1] == after[1]  # name
            assert before[2] == after[2]  # storage_folder_path
    
    def test_migration_idempotent(self, db_with_content_types):
        """Test that migration can run multiple times safely."""
        # First run
        db = Database(db_with_content_types)
        
        # Verify column removed
        cursor = db._connection.execute("PRAGMA table_info(companies)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "content_types" not in columns
        
        # Get count of our test companies after first migration
        cursor = db._connection.execute("SELECT COUNT(*) FROM companies WHERE id LIKE 'test-%'")
        count_after_first = cursor.fetchone()[0]
        assert count_after_first == 3
        
        # Second run - should detect already migrated and skip
        db2 = Database(db_with_content_types)
        
        # Verify still no column
        cursor = db2._connection.execute("PRAGMA table_info(companies)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "content_types" not in columns
        
        # Verify data still intact (same count as after first migration)
        cursor = db2._connection.execute("SELECT COUNT(*) FROM companies WHERE id LIKE 'test-%'")
        count_after_second = cursor.fetchone()[0]
        assert count_after_second == count_after_first


class TestDatabaseMethodsAfterMigration:
    """Tests for database methods with normalized storage_type."""
    
    @pytest.fixture
    def db(self):
        """Create a fresh database (migration runs automatically)."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = Path(tmp.name)
        
        db = Database(db_path)
        yield db
        
        # Cleanup
        db_path.unlink(missing_ok=True)
    
    def test_create_company_normalizes_storage_type(self, db):
        """Test that create_company normalizes 'local' to 'local_disk'."""
        db.create_company(
            company_id="test-normalize",
            name="Test Normalize",
            storage_type="local",  # Legacy value
            storage_folder_path="test"
        )
        
        company = db.get_company("test-normalize")
        assert company["storage_type"] == "local_disk"  # Normalized
    
    def test_create_company_preserves_local_disk(self, db):
        """Test that create_company preserves 'local_disk'."""
        db.create_company(
            company_id="test-preserve",
            name="Test Preserve",
            storage_type="local_disk",
            storage_folder_path="test"
        )
        
        company = db.get_company("test-preserve")
        assert company["storage_type"] == "local_disk"
    
    def test_update_company_normalizes_storage_type(self, db):
        """Test that update_company normalizes storage_type."""
        # Create with local_disk
        db.create_company(
            company_id="test-update",
            name="Test Update",
            storage_type="local_disk",
            storage_folder_path="test"
        )
        
        # Update with legacy 'local'
        db.update_company("test-update", storage_type="local")
        
        # Verify normalized
        company = db.get_company("test-update")
        assert company["storage_type"] == "local_disk"
    
    def test_update_company_storage_normalizes(self, db):
        """Test that update_company_storage normalizes storage_type."""
        # Create company
        db.create_company(
            company_id="test-storage",
            name="Test Storage",
            storage_type="local_disk",
            storage_folder_path="test"
        )
        
        # Update storage with legacy 'local'
        db.update_company_storage(
            "test-storage",
            storage_type="local",
            storage_connection_id=None
        )
        
        # Verify normalized
        company = db.get_company("test-storage")
        assert company["storage_type"] == "local_disk"
    
    def test_content_types_parameter_ignored(self, db):
        """Test that content_types parameter is accepted but ignored."""
        # Create with content_types (should be ignored)
        db.create_company(
            company_id="test-ignore",
            name="Test Ignore",
            storage_type="local_disk",
            content_types="portraits:Portraits",  # Should be ignored
            storage_folder_path="test"
        )
        
        # Verify company created without content_types
        company = db.get_company("test-ignore")
        assert "content_types" not in company or company.get("content_types") is None
        
        # Update with content_types (should be ignored)
        db.update_company("test-ignore", content_types="diplomas:Diplomas")
        
        # Verify still no content_types
        company = db.get_company("test-ignore")
        assert "content_types" not in company or company.get("content_types") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
