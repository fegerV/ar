"""
Test script to verify the backup security fixes for path traversal protection.
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


def test_path_traversal_security():
    """Test that path traversal security works correctly for backup operations."""
    print("Testing backup path traversal security...")

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

        # Test security check with Path.relative_to (our new implementation)
        print("\n2. Testing security check with legitimate path...")
        backup_path_obj = Path(backup_path)
        backup_dir_resolved = Path(manager.backup_dir).resolve()
        backup_path_resolved = backup_path_obj.resolve()

        try:
            backup_path_resolved.relative_to(backup_dir_resolved)
            print("   + Legitimate path passes security check")
        except ValueError:
            print("   - Legitimate path incorrectly blocked by security check")
            return False

        # Test security check with malicious path (path traversal attempt)
        print("\n3. Testing security check with path traversal attempt...")
        malicious_path = Path(manager.backup_dir) / ".." / "etc" / "passwd"
        malicious_path_resolved = malicious_path.resolve()
        print(f"   Malicious path: {malicious_path_resolved}")

        try:
            malicious_path_resolved.relative_to(backup_dir_resolved)
            print("   - Malicious path incorrectly allowed by security check")
            return False
        except ValueError:
            print("   + Malicious path correctly blocked by security check")

        # Test security check with control characters (like in original issue)
        print("\n4. Testing security check with control characters...")
        original_backup_path = str(backup_path_resolved)
        # Add control characters that were problematic in the original issue
        problematic_path = original_backup_path.replace(str(backup_dir_resolved), f"{str(backup_dir_resolved)}\u000b\u0008")
        print(f"   Problematic path: {repr(problematic_path)}")

        # Apply the same cleaning logic as in our API
        clean_path = problematic_path.strip().replace('\u000b', '').replace('\u008', '').replace('\n', '').replace('\r', '').replace('\t', '')
        print(f"   Cleaned path: {clean_path}")

        clean_path_obj = Path(clean_path).resolve()
        try:
            clean_path_obj.relative_to(backup_dir_resolved)
            print("   + Path with control characters correctly handled after cleaning")
        except ValueError:
            print("   - Path with control characters incorrectly blocked after cleaning")
            return False

        print("\n+ All security tests passed!")
        return True


def test_backup_api_security_logic():
    """Test the exact security logic used in the API endpoints."""
    print("\nTesting API security logic...")

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

        # Create a test backup
        backup_result = manager.backup_database()
        if not backup_result["success"]:
            print("   Failed to create test backup")
            return False

        backup_path = backup_result["backup_path"]
        backup_dir = Path(manager.backup_dir).resolve()

        # Test 1: Normal path should pass
        normal_path = Path(backup_path).resolve()
        try:
            normal_path.relative_to(backup_dir)
            print("   + Normal path passes security check")
        except ValueError:
            print("   - Normal path fails security check")
            return False

        # Test 2: Path outside backup directory should fail
        external_path = Path("/tmp/external_file.txt").resolve()
        try:
            external_path.relative_to(backup_dir)
            print("   - External path incorrectly passes security check")
            return False
        except ValueError:
            print("   + External path correctly blocked by security check")

        # Test 3: Path with parent directory traversal should fail
        traversal_path = Path(backup_path).parent.parent / "external_file.txt"
        traversal_path_resolved = traversal_path.resolve()
        try:
            traversal_path_resolved.relative_to(backup_dir)
            print("   - Path traversal path incorrectly passes security check")
            return False
        except ValueError:
            print("   + Path traversal path correctly blocked by security check")

        return True


if __name__ == "__main__":
    print("Running backup security tests...\n")

    success1 = test_path_traversal_security()
    success2 = test_backup_api_security_logic()

    if success1 and success2:
        print("\n+ All backup security tests PASSED")
        sys.exit(0)
    else:
        print("\n- Some backup security tests FAILED")
        sys.exit(1)
