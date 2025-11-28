# Backup Path Resolution Fix

## Problem

When attempting to delete a backup from the system, users encountered an error:

```
Ошибка удаления бэкапа: Backup file not found: E:\Project\AR\vertex-ar\backups\ProjectARertex-arackupsdatabasedb_backup_20251125_004717.db
```

The path was malformed, showing concatenated path components without proper separators.

## Root Cause

The issue occurred due to cross-platform path incompatibility:

1. **Backup Creation**: A backup was created on a Windows system with a path like:
   ```
   E:\Project\AR\vertex-ar\backups\database\db_backup_20251125_004717.db
   ```

2. **Path Storage**: This Windows path (with backslashes and drive letter) was stored in the backup metadata.

3. **Path Resolution Issue**: When trying to delete/restore this backup on a Linux system:
   - Python's `Path()` class doesn't properly handle Windows paths on Linux
   - The `resolve()` method tried to interpret the Windows path as a relative Unix path
   - This caused path components to be incorrectly concatenated

## Solution

Implemented a cross-platform path resolution helper function `resolve_backup_path()` that:

1. **Detects Platform-Specific Paths**: Identifies Windows paths by checking for:
   - Drive letters with colon (e.g., `C:\`, `E:\`, `C:/`, `E:/`)
   - Backslash separators (`\`)
   - Mixed separators (e.g., `E:/path\to\file`)

2. **Extracts Filename**: For cross-platform paths, extracts just the filename:
   ```python
   filename = path_str.replace('\\', '/').split('/')[-1]
   # Example: "db_backup_20251125_004717.db"
   ```

3. **Reconstructs Local Path**: Builds the correct path using the local backup directory structure:
   ```python
   if filename.startswith('db_backup_'):
       backup_file = manager.db_backup_dir / filename
   elif filename.startswith('storage_backup_'):
       backup_file = manager.storage_backup_dir / filename
   ```

4. **Security Validation**: Still performs security checks to ensure the resolved path is within the backup directory.

## Changes Made

### Modified File: `app/api/backups.py`

1. **Added Helper Function** (lines 22-77):
   - `resolve_backup_path(path_str: str, manager) -> Optional[Path]`
   - Handles Windows paths on Linux
   - Handles Unix paths on Windows
   - Handles relative paths
   - Returns None if path cannot be resolved

2. **Updated Endpoints**:
   - `delete_backup()` - Uses helper for path resolution
   - `restore_backup()` - Uses helper for path resolution
   - `test_restore_backup()` - Uses helper for path resolution
   - `verify_backup()` - Uses helper for path resolution

### Test File: `test_backup_path_fix.py`

Created comprehensive tests validating:
- Windows absolute paths → Unix paths
- Unix absolute paths → Unix paths
- Relative paths → Unix paths
- Storage vs. database backup paths

## Verification

All test cases pass:
```
✓ Windows absolute path
✓ Windows absolute path with storage
✓ Unix absolute path
✓ Relative path
```

## Benefits

1. **Cross-Platform Compatibility**: Backups created on Windows can be deleted/restored on Linux and vice versa
2. **Backward Compatible**: Still handles native paths correctly
3. **Security Maintained**: All security checks remain in place
4. **Error Handling**: Returns clear error messages when paths cannot be resolved
5. **Consistent Behavior**: All backup operations (delete, restore, verify) use the same resolution logic

## Usage

No changes required for end users. The fix is transparent and automatically handles:
- Deleting backups created on different platforms
- Restoring backups from different platforms
- Verifying backup integrity regardless of original platform
- Testing restore operations

## Future Considerations

1. Consider storing only relative paths or filenames in backup metadata to avoid platform-specific issues
2. Add migration script to update existing backup metadata with platform-independent paths
3. Document backup portability in user documentation
