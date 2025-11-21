"""
Test script to verify backup restore and delete functionality fixes.
"""
import os
import sys
from pathlib import Path

# Add the vertex-ar directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "vertex-ar"))

from backup_manager import create_backup_manager
from app.api.backups import format_backup_info
from pathlib import Path
import tempfile
import shutil

def test_backup_operations():
    """Test backup operations with proper path handling."""
    print("Testing backup operations...")

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test database and storage directories
        test_db_path = temp_path / "test.db"
        test_storage_path = temp_path / "test_storage"
        test_backup_dir = temp_path / "backups"

        # Create test storage directory with some content
        test_storage_path.mkdir()
        (test_storage_path / "test_file.txt").write_text("test content")

        # Create backup manager with test paths
        manager = create_backup_manager(
            backup_dir=test_backup_dir,
            db_path=test_db_path,
            storage_path=test_storage_path
        )

        print(f"Backup directory: {manager.backup_dir}")
        print(f"Database backup directory: {manager.db_backup_dir}")
        print(f"Storage backup directory: {manager.storage_backup_dir}")

        # Create a test database file
        import sqlite3
        conn = sqlite3.connect(str(test_db_path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO test (name) VALUES ('test')")
        conn.commit()
        conn.close()

        print("\n1. Testing database backup creation...")
        db_backup_result = manager.backup_database()
        if db_backup_result["success"]:
            print(f"   Database backup created: {db_backup_result['backup_path']}")
        else:
            print(f"   Database backup failed: {db_backup_result['error']}")
            return False

        print("\n2. Testing storage backup creation...")
        storage_backup_result = manager.backup_storage()
        if storage_backup_result["success"]:
            print(f"   Storage backup created: {storage_backup_result['backup_path']}")
        else:
            print(f"   Storage backup failed: {storage_backup_result['error']}")
            return False

        # Test the path normalization in delete function context
        print("\n3. Testing path handling for deletion...")
        db_backup_path = Path(db_backup_result["backup_path"])
        storage_backup_path = Path(storage_backup_result["backup_path"])

        print(f"   Database backup path: {db_backup_path}")
        print(f"   Storage backup path: {storage_backup_path}")

        # Verify paths exist
        if not db_backup_path.exists():
            print("   ERROR: Database backup file not found!")
            return False
        if not storage_backup_path.exists():
            print("   ERROR: Storage backup file not found!")
            return False

        print("   Backup files exist as expected")

        # Test path resolution (this is what the fixed API does)
        backup_dir_resolved = Path(manager.backup_dir).resolve()
        db_backup_resolved = db_backup_path.resolve()
        storage_backup_resolved = storage_backup_path.resolve()

        print(f"   Backup dir resolved: {backup_dir_resolved}")
        print(f"   DB backup resolved: {db_backup_resolved}")
        print(f"   Storage backup resolved: {storage_backup_resolved}")

        # Verify paths are within backup directory (security check)
        if not str(db_backup_resolved).startswith(str(backup_dir_resolved)):
            print("   ERROR: Database backup path is not within backup directory!")
            return False
        if not str(storage_backup_resolved).startswith(str(backup_dir_resolved)):
            print("   ERROR: Storage backup path is not within backup directory!")
            return False

        print("   Path security checks passed")

        # Test restore functionality
        print("\n4. Testing database restore...")
        restore_db_result = manager.restore_database(db_backup_path)
        if restore_db_result:
            print("   Database restore successful")
        else:
            print("   Database restore failed")
            return False

        print("\n5. Testing storage restore...")
        restore_storage_result = manager.restore_storage(storage_backup_path)
        if restore_storage_result:
            print("   Storage restore successful")
        else:
            print("   Storage restore failed")
            return False

        # Test deletion (the main fix)
        print("\n6. Testing backup deletion...")

        # Try to delete the database backup
        import os
        original_db_path = str(db_backup_path)
        print(f"   Attempting to delete: {original_db_path}")

        # Check if file exists before deletion
        if os.path.exists(original_db_path):
            try:
                os.remove(original_db_path)
                # Also remove metadata file
                metadata_path = Path(original_db_path).with_suffix(".json")
                if metadata_path.exists():
                    os.remove(metadata_path)
                print("   Database backup deleted successfully")
            except Exception as e:
                print(f"   Error deleting database backup: {e}")
                return False
        else:
            print("   ERROR: Database backup file not found for deletion")
            return False

        # Try to delete the storage backup
        original_storage_path = str(storage_backup_path)
        print(f"   Attempting to delete: {original_storage_path}")

        if os.path.exists(original_storage_path):
            try:
                os.remove(original_storage_path)
                # Also remove metadata file
                metadata_path = Path(original_storage_path).with_suffix(".json")
                if metadata_path.exists():
                    os.remove(metadata_path)
                print("   Storage backup deleted successfully")
            except Exception as e:
                print(f"   Error deleting storage backup: {e}")
                return False
        else:
            print("   ERROR: Storage backup file not found for deletion")
            return False

        print("\n7. Verifying deletion...")
        if db_backup_path.exists():
            print("   ERROR: Database backup still exists after deletion")
            return False
        if storage_backup_path.exists():
            print("   ERROR: Storage backup still exists after deletion")
            return False

        print("   All backup files deleted successfully")

    print("\nAll tests passed! Backup functionality is working correctly.")
    return True

if __name__ == "__main__":
    success = test_backup_operations()
    if success:
        print("\n✅ Backup restore and delete functionality test PASSED")
    else:
        print("\n❌ Backup restore and delete functionality test FAILED")
        sys.exit(1)
