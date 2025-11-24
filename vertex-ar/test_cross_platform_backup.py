#!/usr/bin/env python3
"""
Integration test for cross-platform backup path resolution.
Simulates the actual error scenario from the ticket.
"""
import re
import tempfile
from pathlib import Path
from typing import Optional


class MockBackupManager:
    """Mock backup manager that simulates a real backup environment."""
    
    def __init__(self, base_dir: Path):
        self.backup_dir = base_dir / "backups"
        self.db_backup_dir = self.backup_dir / "database"
        self.storage_backup_dir = self.backup_dir / "storage"
        self.full_backup_dir = self.backup_dir / "full"
        
        # Create directories
        self.db_backup_dir.mkdir(parents=True, exist_ok=True)
        self.storage_backup_dir.mkdir(parents=True, exist_ok=True)
        self.full_backup_dir.mkdir(parents=True, exist_ok=True)


def resolve_backup_path(path_str: str, manager) -> Optional[Path]:
    """
    Resolve a backup path that may be from a different platform.
    This is the actual implementation from app/api/backups.py
    """
    clean_path_str = path_str.strip().replace('\u000b', '').replace('\u0008', '').replace('\n', '').replace('\r', '').replace('\t', '')
    
    # Check if this is a Windows path (has drive letter with colon, backslashes, or mixed separators)
    is_windows_path = (
        re.match(r'^[A-Za-z]:[/\\]', clean_path_str) is not None or 
        '\\' in clean_path_str
    )
    
    if is_windows_path:
        # Extract filename from Windows path
        filename = clean_path_str.replace('\\', '/').split('/')[-1]
        
        # Determine backup type from filename and construct local path
        if filename.startswith('db_backup_'):
            return manager.db_backup_dir / filename
        elif filename.startswith('storage_backup_'):
            return manager.storage_backup_dir / filename
        else:
            # Try to find the file in all backup directories
            for search_dir in [manager.db_backup_dir, manager.storage_backup_dir]:
                potential_path = search_dir / filename
                if potential_path.exists():
                    return potential_path
            return None
    else:
        # Handle Unix-style path
        backup_file = Path(clean_path_str)
        backup_dir = Path(manager.backup_dir).resolve()
        
        # Try to resolve the path
        try:
            backup_file = backup_file.resolve()
            backup_file.relative_to(backup_dir)
            return backup_file
        except ValueError:
            # If relative path fails, try with original backup path
            try:
                original_path = Path(clean_path_str)
                if not original_path.is_absolute():
                    # If it's a relative path, join it with backup_dir
                    backup_file = (backup_dir / original_path).resolve()
                    backup_file.relative_to(backup_dir)
                    return backup_file
            except (ValueError, RuntimeError):
                pass
        
        return None


def test_ticket_scenario():
    """
    Test the exact scenario from the ticket:
    - Backup created on Windows with path: E:\Project\AR\vertex-ar\backups\database\db_backup_20251125_004717.db
    - Attempting to delete from Linux
    """
    print("=" * 80)
    print("INTEGRATION TEST: Cross-Platform Backup Deletion")
    print("=" * 80)
    print()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        manager = MockBackupManager(tmpdir)
        
        # Create a test backup file
        timestamp = "20251125_004717"
        backup_filename = f"db_backup_{timestamp}.db"
        backup_file = manager.db_backup_dir / backup_filename
        backup_file.write_text("test backup data")
        
        print(f"✓ Created test backup: {backup_file}")
        print()
        
        # Simulate the Windows path from the ticket
        windows_path = rf"E:\Project\AR\vertex-ar\backups\database\{backup_filename}"
        
        print(f"Scenario: Backup metadata contains Windows path:")
        print(f"  {windows_path}")
        print()
        
        # Try to resolve the path
        print("Attempting to resolve path...")
        resolved_path = resolve_backup_path(windows_path, manager)
        
        if resolved_path is None:
            print("✗ FAIL: Path resolution returned None")
            return False
        
        print(f"✓ Path resolved to: {resolved_path}")
        print()
        
        # Verify the resolved path exists
        if not resolved_path.exists():
            print(f"✗ FAIL: Resolved path does not exist: {resolved_path}")
            return False
        
        print(f"✓ Resolved path exists")
        print()
        
        # Verify the resolved path is correct
        if resolved_path != backup_file:
            print(f"✗ FAIL: Resolved path mismatch")
            print(f"  Expected: {backup_file}")
            print(f"  Got: {resolved_path}")
            return False
        
        print(f"✓ Resolved path matches expected backup file")
        print()
        
        # Simulate deletion
        print("Simulating backup deletion...")
        try:
            resolved_path.unlink()
            print("✓ Backup file deleted successfully")
        except Exception as e:
            print(f"✗ FAIL: Could not delete file: {e}")
            return False
        
        print()
        print("=" * 80)
        print("✓ ALL TESTS PASSED - Cross-platform backup deletion works!")
        print("=" * 80)
        return True


def test_multiple_scenarios():
    """Test multiple cross-platform scenarios."""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE CROSS-PLATFORM TESTS")
    print("=" * 80)
    print()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        manager = MockBackupManager(tmpdir)
        
        # Create test files
        test_files = [
            ("db_backup_20251125_004717.db", manager.db_backup_dir),
            ("storage_backup_20251125_120000.tar.gz", manager.storage_backup_dir),
            ("db_backup_20251201_000000.db", manager.db_backup_dir),
        ]
        
        for filename, directory in test_files:
            (directory / filename).write_text("test data")
        
        # Test scenarios
        test_cases = [
            {
                "name": "Windows database backup path",
                "path": r"E:\Project\AR\vertex-ar\backups\database\db_backup_20251125_004717.db",
                "expected_file": test_files[0][0],
                "should_exist": True
            },
            {
                "name": "Windows storage backup path",
                "path": r"C:\Users\Admin\vertex-ar\backups\storage\storage_backup_20251125_120000.tar.gz",
                "expected_file": test_files[1][0],
                "should_exist": True
            },
            {
                "name": "Windows path with forward slashes",
                "path": "E:/Project/AR/vertex-ar/backups/database/db_backup_20251201_000000.db",
                "expected_file": test_files[2][0],
                "should_exist": True
            },
            {
                "name": "Non-existent backup",
                "path": r"E:\Project\AR\vertex-ar\backups\database\db_backup_99999999_999999.db",
                "expected_file": None,
                "should_exist": False
            },
        ]
        
        passed = 0
        failed = 0
        
        for test_case in test_cases:
            print(f"Test: {test_case['name']}")
            print(f"  Path: {test_case['path']}")
            
            resolved = resolve_backup_path(test_case['path'], manager)
            
            if test_case['should_exist']:
                if resolved is None:
                    print(f"  ✗ FAIL: Expected resolution, got None")
                    failed += 1
                elif not resolved.exists():
                    print(f"  ✗ FAIL: Resolved path does not exist")
                    failed += 1
                elif resolved.name != test_case['expected_file']:
                    print(f"  ✗ FAIL: Wrong file resolved")
                    print(f"    Expected: {test_case['expected_file']}")
                    print(f"    Got: {resolved.name}")
                    failed += 1
                else:
                    print(f"  ✓ PASS: Resolved to {resolved.name}")
                    passed += 1
            else:
                if resolved is not None and resolved.exists():
                    print(f"  ✗ FAIL: Should not exist but got {resolved}")
                    failed += 1
                else:
                    print(f"  ✓ PASS: Correctly handled non-existent file")
                    passed += 1
            
            print()
        
        print("=" * 80)
        print(f"Results: {passed} passed, {failed} failed")
        print("=" * 80)
        
        return failed == 0


if __name__ == "__main__":
    success = test_ticket_scenario()
    if success:
        success = test_multiple_scenarios()
    
    exit(0 if success else 1)
