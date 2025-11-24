#!/usr/bin/env python3
"""
Test script to verify the backup path resolution fix.
"""
import re
from pathlib import Path
from typing import Optional


class MockBackupManager:
    """Mock backup manager for testing."""
    def __init__(self):
        self.backup_dir = Path("/home/engine/project/vertex-ar/backups")
        self.db_backup_dir = self.backup_dir / "database"
        self.storage_backup_dir = self.backup_dir / "storage"
        self.full_backup_dir = self.backup_dir / "full"


def resolve_backup_path(path_str: str, manager) -> Optional[Path]:
    """
    Resolve a backup path that may be from a different platform.
    Handles Windows paths on Linux and vice versa.
    
    Args:
        path_str: The path string from the backup metadata
        manager: BackupManager instance
        
    Returns:
        Resolved Path object or None if not found
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


def test_resolve_backup_path():
    """Test the resolve_backup_path function."""
    manager = MockBackupManager()
    
    # Test cases
    test_cases = [
        {
            "name": "Windows absolute path",
            "input": r"E:\Project\AR\vertex-ar\backups\database\db_backup_20251125_004717.db",
            "expected": manager.db_backup_dir / "db_backup_20251125_004717.db"
        },
        {
            "name": "Windows absolute path with storage",
            "input": r"E:\Project\AR\vertex-ar\backups\storage\storage_backup_20251125_004717.tar.gz",
            "expected": manager.storage_backup_dir / "storage_backup_20251125_004717.tar.gz"
        },
        {
            "name": "Unix absolute path",
            "input": "/home/engine/project/vertex-ar/backups/database/db_backup_20251125_004717.db",
            "expected": manager.db_backup_dir / "db_backup_20251125_004717.db"
        },
        {
            "name": "Relative path",
            "input": "database/db_backup_20251125_004717.db",
            "expected": manager.db_backup_dir / "db_backup_20251125_004717.db"
        }
    ]
    
    print("Testing resolve_backup_path function:\n")
    
    for test_case in test_cases:
        result = resolve_backup_path(test_case["input"], manager)
        expected = test_case["expected"]
        
        print(f"Test: {test_case['name']}")
        print(f"  Input: {test_case['input']}")
        print(f"  Expected: {expected}")
        print(f"  Result: {result}")
        print(f"  Status: {'✓ PASS' if result == expected else '✗ FAIL'}")
        print()


if __name__ == "__main__":
    test_resolve_backup_path()
