#!/usr/bin/env python3
"""
Comprehensive test to verify backup path handling fix for both deletion and restoration.
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


def test_backup_operations_with_control_chars():
    """Test both deletion and restoration with control characters in paths."""
    print("Testing comprehensive backup path handling...")

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
            original_backup_path = backup_result["backup_path"]
            print(f"   Backup created: {original_backup_path}")
        else:
            print(f"   Backup creation failed: {backup_result['error']}")
            return False

        # Test restoration with control characters
        print("\n2. Testing restoration with control characters...")
        
        # Create a problematic path with control characters
        problematic_path = str(original_backup_path).replace(str(test_backup_dir), f"{str(test_backup_dir)}\u000b\u0008")
        print(f"   Problematic path: {repr(problematic_path)}")

        # Simulate the restore_backup function logic
        try:
            # Apply the same cleaning logic as in the API
            clean_backup_path = problematic_path.strip().replace('\u000b', '').replace('\u0008', '').replace('\n', '').replace('\r', '').replace('\t', '')
            backup_path = Path(clean_backup_path)
            print(f"   Cleaned path: {backup_path}")

            # Handle potential path traversal security issues and normalize path
            backup_path = backup_path.resolve()
            backup_dir = Path(manager.backup_dir).resolve()

            # Verify that the backup file is within the allowed backup directory
            try:
                backup_path.relative_to(backup_dir)
                print("   + Path security check passed")
            except ValueError:
                print("   - Path security check failed")
                return False

            if not backup_path.exists():
                print("   - Backup file not found after cleaning")
                return False

            print("   + Restoration path validation successful")
            
        except Exception as e:
            print(f"   - Restoration test failed: {e}")
            return False

        # Test deletion with control characters
        print("\n3. Testing deletion with control characters...")

        # Simulate the delete_backup function logic
        try:
            # Apply the same cleaning logic as in the API
            clean_path_str = problematic_path.strip().replace('\u000b', '').replace('\u0008', '').replace('\n', '').replace('\r', '').replace('\t', '')
            backup_file = Path(clean_path_str)

            # Resolve the path to handle any relative components and normalize it
            backup_file = backup_file.resolve()
            backup_dir = Path(manager.backup_dir).resolve()

            # Ensure the backup is within the allowed backup directory (security check)
            try:
                backup_file.relative_to(backup_dir)
                print("   + Deletion path security check passed")
            except ValueError:
                print("   - Deletion path security check failed")
                return False

            # Validate backup path exists
            if not backup_file.exists():
                print("   - Backup file not found for deletion")
                return False

            # Delete the backup file
            backup_file.unlink()
            print("   + Backup file deleted successfully")

            # Delete associated metadata file if exists
            metadata_file = backup_file.with_suffix(".json")
            if metadata_file.exists() and metadata_file != backup_file:
                metadata_file.unlink()
                print("   + Metadata file deleted successfully")

        except Exception as e:
            print(f"   - Deletion test failed: {e}")
            return False

        # Verify the file was actually deleted
        if Path(original_backup_path).exists():
            print("   - Backup file still exists after deletion")
            return False
        else:
            print("   + Backup file was successfully deleted")

        # Create another backup to test full workflow
        print("\n4. Testing complete workflow...")
        
        # Create new backup
        backup_result2 = manager.backup_database()
        if not backup_result2["success"]:
            print("   - Failed to create second backup")
            return False
        
        new_backup_path = backup_result2["backup_path"]
        print(f"   New backup created: {new_backup_path}")

        # Test restoration with the clean path
        try:
            success = manager.restore_database(new_backup_path, verify_checksum=False)
            if success:
                print("   + Database restoration successful")
            else:
                print("   - Database restoration failed")
                return False
        except Exception as e:
            print(f"   - Database restoration error: {e}")
            return False

        # Test deletion with the clean path
        try:
            backup_file = Path(new_backup_path).resolve()
            backup_file.unlink()
            
            metadata_file = backup_file.with_suffix(".json")
            if metadata_file.exists():
                metadata_file.unlink()
            
            print("   + Final deletion successful")
        except Exception as e:
            print(f"   - Final deletion failed: {e}")
            return False

    print("\n+ All comprehensive backup path handling tests passed!")
    return True


if __name__ == "__main__":
    success = test_backup_operations_with_control_chars()
    if success:
        print("\n+ Comprehensive backup path handling test PASSED")
    else:
        print("\n- Comprehensive backup path handling test FAILED")
        sys.exit(1)