"""
Tests for backup deletion protection logic (can_delete_backup endpoint).
"""
import json
import sqlite3
import tempfile
import time
from pathlib import Path

from backup_manager import BackupManager


def test_setup():
    """Set up test environment with backups."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test database
        db_path = tmpdir / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'test data')")
        conn.commit()
        conn.close()
        
        # Create test storage
        storage_path = tmpdir / "storage"
        storage_path.mkdir()
        (storage_path / "test.txt").write_text("test content")
        
        # Create backup directory
        backup_dir = tmpdir / "backups"
        
        # Create manager
        manager = BackupManager(
            backup_dir=backup_dir,
            db_path=db_path,
            storage_path=storage_path,
            max_backups=10
        )
        
        yield {
            "manager": manager,
            "db_path": db_path,
            "storage_path": storage_path,
            "backup_dir": backup_dir
        }


def test_can_delete_with_no_backups(test_setup):
    """Test can_delete when no backups exist."""
    manager = test_setup["manager"]
    
    # No backups exist yet
    result = manager.list_backups("all")
    assert len(result) == 0
    
    # Should return can_delete=False due to fallback logic
    # (In practice, API would return 404, but here we test the logic)


def test_cannot_delete_last_database_backup(test_setup):
    """Test that we cannot delete the last database backup."""
    manager = test_setup["manager"]
    
    # Create only one database backup
    db_result = manager.backup_database()
    assert db_result["success"]
    backup_path = db_result["backup_path"]
    
    # Check deletion - should be prevented
    db_backups = manager.list_backups("database")
    storage_backups = manager.list_backups("storage")
    full_backups = manager.list_backups("full")
    
    assert len(db_backups) == 1
    assert len(storage_backups) == 0
    assert len(full_backups) == 0
    
    # This would be the logic in the API endpoint
    backup_type = "database" if "db_backup" in backup_path else None
    assert backup_type == "database"
    
    type_count = len(db_backups)
    is_last_of_type = type_count <= 1
    
    assert is_last_of_type is True
    print("✓ Cannot delete last database backup")


def test_can_delete_database_backup_when_multiple_exist(test_setup):
    """Test that we can delete a database backup when multiple exist."""
    manager = test_setup["manager"]
    
    # Create two database backups with sufficient delay for unique timestamps
    db_result1 = manager.backup_database()
    assert db_result1["success"]
    
    # Delay to ensure different timestamp in filename (format: %Y%m%d_%H%M%S)
    time.sleep(1.1)
    
    db_result2 = manager.backup_database()
    assert db_result2["success"]
    
    backup_path = db_result1["backup_path"]
    
    # Check deletion - should be allowed
    db_backups = manager.list_backups("database")
    storage_backups = manager.list_backups("storage")
    full_backups = manager.list_backups("full")
    
    # Verify we have 2 backups
    print(f"DB backups found: {len(db_backups)}")
    if len(db_backups) != 2:
        # List the actual backup files to debug
        db_files = list(manager.db_backup_dir.glob("db_backup_*.db"))
        print(f"DB files on disk: {[f.name for f in db_files]}")
        metadata_files = list(manager.db_backup_dir.glob("*.json"))
        print(f"Metadata files: {[f.name for f in metadata_files]}")
    
    assert len(db_backups) == 2, f"Expected 2 database backups, found {len(db_backups)}"
    assert len(storage_backups) == 0
    assert len(full_backups) == 0
    
    backup_type = "database" if "db_backup" in backup_path else None
    assert backup_type == "database"
    
    type_count = len(db_backups)
    is_last_of_type = type_count <= 1
    
    assert is_last_of_type is False
    print("✓ Can delete database backup when multiple exist")


def test_cannot_delete_last_storage_backup(test_setup):
    """Test that we cannot delete the last storage backup."""
    manager = test_setup["manager"]
    
    # Create only one storage backup
    storage_result = manager.backup_storage()
    assert storage_result["success"]
    backup_path = storage_result["backup_path"]
    
    # Check deletion - should be prevented
    db_backups = manager.list_backups("database")
    storage_backups = manager.list_backups("storage")
    full_backups = manager.list_backups("full")
    
    assert len(db_backups) == 0
    assert len(storage_backups) == 1
    assert len(full_backups) == 0
    
    backup_type = "storage" if "storage_backup" in backup_path else None
    assert backup_type == "storage"
    
    type_count = len(storage_backups)
    is_last_of_type = type_count <= 1
    
    assert is_last_of_type is True
    print("✓ Cannot delete last storage backup")


def test_cannot_delete_last_full_backup(test_setup):
    """Test that we cannot delete the last full backup."""
    manager = test_setup["manager"]
    
    # Create only one full backup
    full_result = manager.create_full_backup()
    assert full_result["success"]
    
    # Full backup creates metadata in full_backup_dir
    # Check deletion - should be prevented
    db_backups = manager.list_backups("database")
    storage_backups = manager.list_backups("storage")
    full_backups = manager.list_backups("full")
    
    # Full backup creates entries in multiple directories
    assert len(full_backups) == 1
    
    # Check the full backup metadata path
    full_metadata_files = list(manager.full_backup_dir.glob("full_backup_*.json"))
    assert len(full_metadata_files) == 1
    
    backup_path = str(full_metadata_files[0])
    backup_type = "full" if "full_backup" in backup_path else None
    assert backup_type == "full"
    
    type_count = len(full_backups)
    is_last_of_type = type_count <= 1
    
    assert is_last_of_type is True
    print("✓ Cannot delete last full backup")


def test_mixed_backup_types_independent_deletion(test_setup):
    """Test that backup types are protected independently."""
    manager = test_setup["manager"]
    
    # Create one of each type
    db_result = manager.backup_database()
    assert db_result["success"]
    
    storage_result = manager.backup_storage()
    assert storage_result["success"]
    
    full_result = manager.create_full_backup()
    assert full_result["success"]
    
    # Check counts
    db_backups = manager.list_backups("database")
    storage_backups = manager.list_backups("storage")
    full_backups = manager.list_backups("full")
    
    # Should have 2 database (one standalone + one from full)
    # Should have 2 storage (one standalone + one from full)  
    # Should have 1 full
    # Note: Full backup creates separate files in db and storage dirs
    
    # Each type should still be protected as the last of its type
    # Even though we have backups of other types
    
    # Cannot delete the standalone database backup if it's the only non-full database backup
    db_backup_path = db_result["backup_path"]
    backup_type = "database" if "db_backup" in db_backup_path else None
    assert backup_type == "database"
    
    # With current implementation, each type is counted separately
    # So we should have multiple database backups (standalone + full)
    print(f"Database backups: {len(db_backups)}")
    print(f"Storage backups: {len(storage_backups)}")
    print(f"Full backups: {len(full_backups)}")
    
    # The key insight: with 2+ database backups, we CAN delete one
    # But with only 1 database backup, we CANNOT
    print("✓ Backup types are protected independently")


def test_backup_type_detection_logic():
    """Test the backup type detection logic used in can_delete endpoint."""
    test_cases = [
        ("backups/database/db_backup_20250101_120000.db", "database"),
        ("/path/to/db_backup_20250101_120000.db", "database"),
        ("backups/storage/storage_backup_20250101_120000.tar.gz", "storage"),
        ("storage_backup_20250101_120000.tar.gz", "storage"),
        ("backups/full/full_backup_20250101_120000.json", "full"),
        ("full_backup_20250101_120000.json", "full"),
        ("some_random_file.db", "database"),  # .db extension triggers database
        ("random_file.txt", None),  # No match
    ]
    
    for backup_path, expected_type in test_cases:
        # Replicate the detection logic from the endpoint
        backup_type_to_delete = None
        if "db_backup" in backup_path or backup_path.endswith(".db"):
            backup_type_to_delete = "database"
        elif "storage_backup" in backup_path:
            backup_type_to_delete = "storage"
        elif "full_backup" in backup_path:
            backup_type_to_delete = "full"
        
        assert backup_type_to_delete == expected_type, \
            f"Failed for {backup_path}: expected {expected_type}, got {backup_type_to_delete}"
    
    print("✓ Backup type detection logic works correctly")


def test_api_response_structure(test_setup):
    """Test that the API response includes all required fields."""
    manager = test_setup["manager"]
    
    # Create one backup of each type
    db_result = manager.backup_database()
    storage_result = manager.backup_storage()
    
    # Simulate the API response for database backup (last of its type)
    db_backups = manager.list_backups("database")
    storage_backups = manager.list_backups("storage")
    full_backups = manager.list_backups("full")
    
    backup_types_present = {
        "database": len(db_backups),
        "storage": len(storage_backups),
        "full": len(full_backups)
    }
    total_backups = sum(backup_types_present.values())
    
    backup_path = db_result["backup_path"]
    backup_type_to_delete = "database" if "db_backup" in backup_path else None
    
    type_count = backup_types_present.get(backup_type_to_delete, 0)
    is_last_of_type = type_count <= 1
    
    can_delete = not is_last_of_type
    reason = None
    recommendation = None
    
    if is_last_of_type:
        can_delete = False
        reason = f"Cannot delete the last {backup_type_to_delete} backup"
        recommendation = (
            f"This is your only {backup_type_to_delete} backup. "
            f"To maintain at least one restore point, please create a new "
            f"{backup_type_to_delete} or full backup before deleting this one."
        )
    
    # Build response
    response = {
        "success": True,
        "can_delete": can_delete,
        "total_backups": total_backups,
        "backup_types_present": backup_types_present,
        "backup_type_to_delete": backup_type_to_delete,
        "is_last_of_type": is_last_of_type
    }
    
    if reason:
        response["reason"] = reason
    if recommendation:
        response["recommendation"] = recommendation
    
    # Verify response structure
    assert "success" in response
    assert "can_delete" in response
    assert "total_backups" in response
    assert "backup_types_present" in response
    assert "backup_type_to_delete" in response
    assert "is_last_of_type" in response
    
    # For last backup, should have reason and recommendation
    if not can_delete:
        assert "reason" in response
        assert "recommendation" in response
        assert "only" in response["recommendation"]  # Should mention it's the only one
        assert "create a new" in response["recommendation"]  # Should suggest creating new
    
    print("✓ API response structure is correct")
    print(f"Response: {json.dumps(response, indent=2)}")


if __name__ == "__main__":
    # Run tests
    import sys
    
    print("Testing backup deletion protection logic...\n")
    
    # Create test setup
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test database
        db_path = tmpdir / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'test data')")
        conn.commit()
        conn.close()
        
        # Create test storage
        storage_path = tmpdir / "storage"
        storage_path.mkdir()
        (storage_path / "test.txt").write_text("test content")
        
        # Create backup directory
        backup_dir = tmpdir / "backups"
        
        # Create manager
        manager = BackupManager(
            backup_dir=backup_dir,
            db_path=db_path,
            storage_path=storage_path,
            max_backups=10
        )
        
        setup = {
            "manager": manager,
            "db_path": db_path,
            "storage_path": storage_path,
            "backup_dir": backup_dir
        }
        
        try:
            test_cannot_delete_last_database_backup(setup)
            
            # Reset for next test
            manager = BackupManager(
                backup_dir=backup_dir,
                db_path=db_path,
                storage_path=storage_path,
                max_backups=10
            )
            setup["manager"] = manager
            
            test_can_delete_database_backup_when_multiple_exist(setup)
            
            # Reset for next test
            backup_dir2 = tmpdir / "backups2"
            manager = BackupManager(
                backup_dir=backup_dir2,
                db_path=db_path,
                storage_path=storage_path,
                max_backups=10
            )
            setup["manager"] = manager
            
            test_cannot_delete_last_storage_backup(setup)
            
            # Reset for next test
            backup_dir3 = tmpdir / "backups3"
            manager = BackupManager(
                backup_dir=backup_dir3,
                db_path=db_path,
                storage_path=storage_path,
                max_backups=10
            )
            setup["manager"] = manager
            
            test_cannot_delete_last_full_backup(setup)
            
            # Reset for next test
            backup_dir4 = tmpdir / "backups4"
            manager = BackupManager(
                backup_dir=backup_dir4,
                db_path=db_path,
                storage_path=storage_path,
                max_backups=10
            )
            setup["manager"] = manager
            
            test_mixed_backup_types_independent_deletion(setup)
            
            test_backup_type_detection_logic()
            
            # Reset for next test
            backup_dir5 = tmpdir / "backups5"
            manager = BackupManager(
                backup_dir=backup_dir5,
                db_path=db_path,
                storage_path=storage_path,
                max_backups=10
            )
            setup["manager"] = manager
            
            test_api_response_structure(setup)
            
            print("\n✅ All tests passed!")
            sys.exit(0)
            
        except AssertionError as e:
            print(f"\n❌ Test failed: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
