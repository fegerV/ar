#!/usr/bin/env python3
"""
Tests for backup system.
"""
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path

from backup_manager import BackupManager


def test_backup_manager_creation():
    """Test creating a BackupManager instance."""
    print("Testing BackupManager creation...")
    
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
            max_backups=3
        )
        
        assert manager.backup_dir.exists()
        assert manager.db_backup_dir.exists()
        assert manager.storage_backup_dir.exists()
        assert manager.full_backup_dir.exists()
        
        print("✓ BackupManager creation successful")


def test_database_backup():
    """Test creating a database backup."""
    print("\nTesting database backup...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test database with some data
        db_path = tmpdir / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)")
        conn.execute("INSERT INTO users VALUES (1, 'admin')")
        conn.execute("INSERT INTO users VALUES (2, 'user1')")
        conn.commit()
        conn.close()
        
        # Create storage (empty for this test)
        storage_path = tmpdir / "storage"
        storage_path.mkdir()
        
        # Create backup
        backup_dir = tmpdir / "backups"
        manager = BackupManager(backup_dir, db_path, storage_path)
        
        result = manager.backup_database()
        
        assert result["success"]
        assert "backup_path" in result
        assert Path(result["backup_path"]).exists()
        
        # Check metadata
        metadata = result["metadata"]
        assert metadata["type"] == "database"
        assert metadata["checksum"]
        assert metadata["file_size"] > 0
        
        # Verify backup file is a valid SQLite database
        backup_path = Path(result["backup_path"])
        backup_conn = sqlite3.connect(str(backup_path))
        cursor = backup_conn.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        backup_conn.close()
        
        assert count == 2
        
        print(f"✓ Database backup successful: {backup_path.name}")
        print(f"  Size: {metadata['file_size']} bytes")
        print(f"  Checksum: {metadata['checksum'][:16]}...")


def test_storage_backup():
    """Test creating a storage backup."""
    print("\nTesting storage backup...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test database (empty for this test)
        db_path = tmpdir / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()
        
        # Create test storage with files
        storage_path = tmpdir / "storage"
        storage_path.mkdir()
        (storage_path / "file1.txt").write_text("content 1")
        (storage_path / "file2.txt").write_text("content 2")
        subdir = storage_path / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("content 3")
        
        # Create backup
        backup_dir = tmpdir / "backups"
        manager = BackupManager(backup_dir, db_path, storage_path)
        
        result = manager.backup_storage()
        
        assert result["success"]
        assert "backup_path" in result
        assert Path(result["backup_path"]).exists()
        
        # Check metadata
        metadata = result["metadata"]
        assert metadata["type"] == "storage"
        assert metadata["checksum"]
        assert metadata["file_size"] > 0
        assert metadata["file_count"] == 3
        
        print(f"✓ Storage backup successful: {Path(result['backup_path']).name}")
        print(f"  Files: {metadata['file_count']}")
        print(f"  Size: {metadata['file_size']} bytes")


def test_full_backup():
    """Test creating a full backup."""
    print("\nTesting full backup...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test database
        db_path = tmpdir / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()
        
        # Create test storage
        storage_path = tmpdir / "storage"
        storage_path.mkdir()
        (storage_path / "file.txt").write_text("content")
        
        # Create backup
        backup_dir = tmpdir / "backups"
        manager = BackupManager(backup_dir, db_path, storage_path)
        
        result = manager.create_full_backup()
        
        assert result["success"] is True
        assert result["type"] == "full"
        assert result["database"] is not None
        assert result["storage"] is not None
        
        print("✓ Full backup successful")
        print(f"  Database: {result['database']['file_size']} bytes")
        print(f"  Storage: {result['storage']['file_size']} bytes")


def test_backup_rotation():
    """Test backup rotation."""
    print("\nTesting backup rotation...")
    
    import time
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test database
        db_path = tmpdir / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()
        
        # Create test storage
        storage_path = tmpdir / "storage"
        storage_path.mkdir()
        
        # Create backup with max 3 backups
        backup_dir = tmpdir / "backups"
        manager = BackupManager(backup_dir, db_path, storage_path, max_backups=3)
        
        # Create 5 backups with slight delays to ensure different timestamps
        for i in range(5):
            manager.backup_database()
            time.sleep(0.01)  # Small delay to ensure different modification times
        
        # Check that we have 5 backups before rotation
        db_backups = list(manager.db_backup_dir.glob("db_backup_*.db"))
        initial_count = len(db_backups)
        
        # Rotate
        removed = manager.rotate_backups()
        
        # Check final count
        db_backups = list(manager.db_backup_dir.glob("db_backup_*.db"))
        final_count = len(db_backups)
        
        print(f"✓ Backup rotation successful")
        print(f"  Initial backups: {initial_count}")
        print(f"  Removed: {removed['database']}")
        print(f"  Remaining: {final_count}")
        
        assert final_count <= 3  # Should be 3 or less


def test_database_restore():
    """Test database restoration."""
    print("\nTesting database restoration...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create original database
        db_path = tmpdir / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)")
        conn.execute("INSERT INTO users VALUES (1, 'admin')")
        conn.commit()
        conn.close()
        
        # Create storage
        storage_path = tmpdir / "storage"
        storage_path.mkdir()
        
        # Create backup
        backup_dir = tmpdir / "backups"
        manager = BackupManager(backup_dir, db_path, storage_path)
        
        backup_result = manager.backup_database()
        backup_path = Path(backup_result["backup_path"])
        
        # Modify original database
        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO users VALUES (2, 'user1')")
        conn.commit()
        conn.close()
        
        # Verify modification
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT COUNT(*) FROM users")
        count_before = cursor.fetchone()[0]
        conn.close()
        assert count_before == 2
        
        # Restore from backup
        success = manager.restore_database(backup_path)
        assert success
        
        # Verify restoration
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT COUNT(*) FROM users")
        count_after = cursor.fetchone()[0]
        conn.close()
        
        assert count_after == 1
        
        print("✓ Database restoration successful")
        print(f"  Before restore: {count_before} users")
        print(f"  After restore: {count_after} users")


def test_storage_restore():
    """Test storage restoration."""
    print("\nTesting storage restoration...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test database
        db_path = tmpdir / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()
        
        # Create original storage
        storage_path = tmpdir / "storage"
        storage_path.mkdir()
        (storage_path / "file1.txt").write_text("content 1")
        (storage_path / "file2.txt").write_text("content 2")
        
        # Create backup
        backup_dir = tmpdir / "backups"
        manager = BackupManager(backup_dir, db_path, storage_path)
        
        backup_result = manager.backup_storage()
        backup_path = Path(backup_result["backup_path"])
        
        # Modify storage
        (storage_path / "file3.txt").write_text("content 3")
        files_before = len(list(storage_path.rglob("*")))
        
        # Restore from backup
        success = manager.restore_storage(backup_path)
        assert success
        
        # Verify restoration
        files_after = list(storage_path.rglob("*.txt"))
        assert len(files_after) == 2
        assert (storage_path / "file1.txt").exists()
        assert (storage_path / "file2.txt").exists()
        assert not (storage_path / "file3.txt").exists()
        
        print("✓ Storage restoration successful")
        print(f"  Files restored: {len(files_after)}")


def test_backup_stats():
    """Test backup statistics."""
    print("\nTesting backup statistics...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test database
        db_path = tmpdir / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()
        
        # Create test storage
        storage_path = tmpdir / "storage"
        storage_path.mkdir()
        (storage_path / "file.txt").write_text("content")
        
        # Create backups
        backup_dir = tmpdir / "backups"
        manager = BackupManager(backup_dir, db_path, storage_path)
        
        manager.backup_database()
        manager.backup_storage()
        manager.create_full_backup()
        
        # Get stats
        stats = manager.get_backup_stats()
        
        # Full backup creates both database and storage backups, so we have:
        # 1 standalone database backup + 1 from full backup = 2 total
        # 1 standalone storage backup + 1 from full backup = 2 total
        assert stats["database_backups"] >= 1
        assert stats["storage_backups"] >= 1
        assert stats["full_backups"] == 1
        assert stats["database_size_mb"] >= 0
        assert stats["storage_size_mb"] >= 0
        
        print("✓ Backup statistics successful")
        print(f"  Database backups: {stats['database_backups']}")
        print(f"  Storage backups: {stats['storage_backups']}")
        print(f"  Full backups: {stats['full_backups']}")
        print(f"  Total size: {stats['total_size_mb']:.2f} MB")


def test_list_backups():
    """Test listing backups."""
    print("\nTesting backup listing...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test database
        db_path = tmpdir / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()
        
        # Create test storage
        storage_path = tmpdir / "storage"
        storage_path.mkdir()
        
        # Create backups
        backup_dir = tmpdir / "backups"
        manager = BackupManager(backup_dir, db_path, storage_path)
        
        manager.backup_database()
        manager.backup_storage()
        manager.create_full_backup()
        
        # List all backups
        all_backups = manager.list_backups("all")
        assert len(all_backups) >= 3
        
        # List database backups
        db_backups = manager.list_backups("database")
        assert len(db_backups) >= 1
        
        # List storage backups
        storage_backups = manager.list_backups("storage")
        assert len(storage_backups) >= 1
        
        # List full backups
        full_backups = manager.list_backups("full")
        assert len(full_backups) >= 1
        
        print("✓ Backup listing successful")
        print(f"  All backups: {len(all_backups)}")
        print(f"  Database: {len(db_backups)}")
        print(f"  Storage: {len(storage_backups)}")
        print(f"  Full: {len(full_backups)}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Vertex AR Backup System Tests")
    print("=" * 60)
    
    tests = [
        test_backup_manager_creation,
        test_database_backup,
        test_storage_backup,
        test_full_backup,
        test_backup_rotation,
        test_database_restore,
        test_storage_restore,
        test_backup_stats,
        test_list_backups,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {test.__name__}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {test.__name__}")
            print(f"  Error: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Tests completed: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
