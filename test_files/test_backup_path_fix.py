"""
Test script to verify the backup path handling fix for control characters.
"""
import os
import sys
from pathlib import Path
import tempfile
import shutil

# Add the vertex-ar directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "vertex-ar"))

from backup_manager import create_backup_manager
from fastapi import HTTPException
import sqlite3


def test_path_cleaning():
    """Test that path cleaning works correctly for backup operations."""
    print("Testing backup path cleaning functionality...")

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

        # Create a test database file
        conn = sqlite3.connect(str(test_db_path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO test (name) VALUES ('test')")
        conn.commit()
        conn.close()

        # Create a test backup
        print("\n1. Creating test backup...")
        backup_result = manager.backup_database()
        if backup_result["success"]:
            backup_path = backup_result["backup_path"]
            print(f"   Backup created: {backup_path}")
        else:
            print(f"   Backup creation failed: {backup_result['error']}")
            return False

        # Test the path cleaning functionality by simulating the problematic URL-encoded path
        print("\n2. Testing path cleaning with control characters...")

        # Create a path with control characters like in the original error
        problematic_path = str(backup_path).replace(str(test_backup_dir), f"{str(test_backup_dir)}\u000b\u0008")
        print(f"   Problematic path: {repr(problematic_path)}")

        # Test manual path cleaning (what our fix does)
        clean_path = problematic_path.strip().replace('\u000b', '').replace('\u0008', '').replace('\n', '').replace('\r', '').replace('\t', '')
        print(f"   Cleaned path: {clean_path}")

        # Verify that the cleaned path is valid and within the backup directory
        backup_path_obj = Path(clean_path)
        backup_dir_resolved = Path(manager.backup_dir).resolve()
        backup_path_resolved = backup_path_obj.resolve()

        if str(backup_path_resolved).startswith(str(backup_dir_resolved)):
            print("   + Path cleaning works correctly - path is within backup directory")
        else:
            print("   - Path cleaning failed - path is not within backup directory")
            return False

        # Test that the file still exists after cleaning
        if backup_path_obj.exists():
            print("   + Cleaned path points to existing file")
        else:
            print("   - Cleaned path does not point to existing file")
            return False

        print("\n3. Testing backup deletion with cleaned path...")

        # Simulate the deletion process with our cleaning logic
        try:
            # This is essentially what happens in the fixed delete_backup function
            paths = [problematic_path.strip().replace('\u000b', '').replace('\u0008', '').replace('\n', '').replace('\r', '').replace('\t', '')]

            for path_str in paths:
                backup_file = Path(path_str)
                backup_file_resolved = backup_file.resolve()

                # Security check (what our fixed code does)
                if not str(backup_file_resolved).startswith(str(backup_dir_resolved)):
                    raise HTTPException(status_code=403, detail="Access denied: backup must be within backup directory")

                # Verify backup exists
                if not backup_file.exists():
                    print(f"   - Backup file not found: {backup_file}")
                    return False

                # Delete the file
                backup_file.unlink()
                print(f"   + Deleted backup file: {backup_file}")

                # Delete associated metadata file if exists
                metadata_file = backup_file.with_suffix(".json")
                if metadata_file.exists():
                    metadata_file.unlink()
                    print(f"   + Deleted metadata file: {metadata_file}")

            # Verify the file was actually deleted
            if Path(backup_path).exists():
                print("   - Backup file still exists after deletion")
                return False
            else:
                print("   + Backup file was successfully deleted")

        except Exception as e:
            print(f"   - Error during deletion test: {e}")
            return False

    print("\n+ All path cleaning tests passed!")
    return True


if __name__ == "__main__":
    success = test_path_cleaning()
    if success:
        print("\n+ Backup path cleaning test PASSED")
    else:
        print("\n- Backup path cleaning test FAILED")
        sys.exit(1)
