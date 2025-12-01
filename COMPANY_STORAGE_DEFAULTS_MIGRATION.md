# Company Storage Defaults Migration to `local_disk`

## Overview

This document describes the changes made to migrate company storage defaults from `"local"` to `"local_disk"` while maintaining full backward compatibility with existing data.

## Changes Summary

### 1. New Storage Utility Module (`app/storage_utils.py`)

Created a centralized module for storage type checking and normalization:

- **`is_local_storage(storage_type: str) -> bool`**: Returns `True` for both `"local"` and `"local_disk"`, treating them equivalently.
- **`normalize_storage_type(storage_type: str) -> str`**: Converts legacy `"local"` to `"local_disk"`.

### 2. Pydantic Model Updates (`app/models.py`)

Updated all company-related Pydantic models to accept `"local_disk"` and default to it:

#### CompanyCreate
- `storage_type`: Default changed from `"local"` to `"local_disk"`
- `storage_folder_path`: Default changed from `None` to `"vertex_ar_content"`
- Validator updated to accept `['local', 'local_disk', 'minio', 'yandex_disk']`

#### CompanyUpdate
- Validator updated to accept `['local', 'local_disk', 'minio', 'yandex_disk']`

#### CompanyStorageUpdate
- Validator updated to accept `['local', 'local_disk', 'minio', 'yandex_disk']`

#### CompanyStorageTypeUpdate
- Description updated to include `local_disk`
- Validator updated to accept `['local', 'local_disk', 'minio', 'yandex_disk']`

### 3. Database Layer Updates (`app/database.py`)

#### Default Company Initialization (`_initialise_schema`)
- Default "Vertex AR" company now created with:
  - `storage_type="local_disk"`
  - `storage_folder_path="vertex_ar_content"`

#### Migration Logic
Added automatic migration in `_initialise_schema`:
```python
# Migrate legacy "local" storage_type to "local_disk"
cursor = self._connection.execute("SELECT COUNT(*) FROM companies WHERE storage_type = 'local'")
count = cursor.fetchone()[0]
if count > 0:
    self._connection.execute(
        "UPDATE companies SET storage_type = 'local_disk' WHERE storage_type = 'local'"
    )
    self._connection.commit()
    logger.info(f"Migrated {count} companies from storage_type='local' to 'local_disk'")
```

#### create_company Method
- `storage_type` parameter default changed from `"local"` to `"local_disk"`
- `storage_folder_path` parameter default changed from `None` to `"vertex_ar_content"`

### 4. API Layer Updates

Updated all modules that check `storage_type == "local"` to use the helper function:

#### `app/api/companies.py`
- Imported `is_local_storage` from `app.storage_utils`
- Replaced `company.storage_type != 'local'` with `not is_local_storage(company.storage_type)` (2 occurrences)
- Replaced `storage_type == "local"` with `is_local_storage(storage_type)` (1 occurrence)

#### `storage_manager.py`
- Imported `is_local_storage` from `app.storage_utils`
- Replaced `storage_type == "local"` with `is_local_storage(storage_type)` (2 occurrences in `_create_adapter` methods)

#### `app/api/storage_config.py`
- Imported `is_local_storage` from `app.storage_utils`
- Replaced `storage_type == "local"` with `is_local_storage(storage_type)` (1 occurrence)

#### `storage_adapter.py`
- Imported `is_local_storage` from `app.storage_utils`
- Replaced `storage_type == "local"` with `is_local_storage(storage_type)` (1 occurrence in `create_storage`)

### 5. Test Coverage (`test_files/unit/test_company_storage_defaults.py`)

Created comprehensive test suite with 34 tests covering:

- **Storage Utility Functions (7 tests)**:
  - `is_local_storage` recognizes both `"local"` and `"local_disk"`
  - `normalize_storage_type` converts legacy type
  - Non-local types are handled correctly

- **Pydantic Model Validation (17 tests)**:
  - Default values for `CompanyCreate`
  - Validation accepts both `"local"` and `"local_disk"`
  - Validation rejects invalid types
  - Tests for `CompanyUpdate`, `CompanyStorageUpdate`, `CompanyStorageTypeUpdate`

- **Database Layer (8 tests)**:
  - Default company uses `"local_disk"` and `"vertex_ar_content"`
  - `create_company` defaults work correctly
  - Migration converts legacy `"local"` to `"local_disk"`
  - Migration is idempotent
  - Backfill adds missing `storage_folder_path`

- **Backward Compatibility (2 tests)**:
  - Legacy `"local"` storage type still works
  - Both types treated equivalently by utilities

All tests pass successfully ✅

## Backward Compatibility

The migration maintains full backward compatibility:

1. **Automatic Migration**: Existing companies with `storage_type="local"` are automatically converted to `"local_disk"` on database initialization.

2. **Validation Accepts Both**: All Pydantic validators accept both `"local"` and `"local_disk"` values.

3. **Equivalent Treatment**: The `is_local_storage()` helper treats both values identically for branching logic.

4. **No Breaking Changes**: Existing API responses continue to work; no changes to external contracts.

## Migration Behavior

When the application starts with an existing database:

1. The `_initialise_schema` method in `Database.__init__()` runs
2. Migration logic checks for companies with `storage_type='local'`
3. If found, all such companies are updated to `storage_type='local_disk'`
4. A log message is emitted: `"Migrated {count} companies from storage_type='local' to 'local_disk'"`
5. Companies with missing `storage_folder_path` are backfilled with `"vertex_ar_content"`

## API Behavior

### Creating New Companies

**Before:**
```python
# Default behavior
company = CompanyCreate(name="Test Company")
# storage_type = "local", storage_folder_path = None
```

**After:**
```python
# Default behavior
company = CompanyCreate(name="Test Company")
# storage_type = "local_disk", storage_folder_path = "vertex_ar_content"
```

### Retrieving Existing Companies

Companies that were created before this migration will have:
- `storage_type = "local_disk"` (automatically migrated)
- `storage_folder_path = "vertex_ar_content"` (backfilled if NULL)

### Storage Type Checking

**Before:**
```python
if company.storage_type == "local":
    # Handle local storage
```

**After:**
```python
from app.storage_utils import is_local_storage

if is_local_storage(company.storage_type):
    # Handle local storage (works for both "local" and "local_disk")
```

## Files Modified

1. **Created**:
   - `vertex-ar/app/storage_utils.py` - Storage utility functions

2. **Modified**:
   - `vertex-ar/app/models.py` - Pydantic model defaults and validators
   - `vertex-ar/app/database.py` - Database defaults and migration logic
   - `vertex-ar/app/api/companies.py` - Use storage utility helpers
   - `vertex-ar/storage_manager.py` - Use storage utility helpers
   - `vertex-ar/app/api/storage_config.py` - Use storage utility helpers
   - `vertex-ar/storage_adapter.py` - Use storage utility helpers

3. **Tests**:
   - `test_files/unit/test_company_storage_defaults.py` - Comprehensive test coverage (34 tests)

## Testing

Run the new test suite:
```bash
pytest test_files/unit/test_company_storage_defaults.py -v
```

All 34 tests pass successfully, covering:
- Storage utility functions
- Pydantic model validation
- Database defaults and migrations
- Backward compatibility

## Rollback Plan

If rollback is needed:

1. The changes maintain backward compatibility, so rollback should be straightforward
2. To revert to legacy behavior:
   - Revert the Pydantic model defaults back to `"local"`
   - Remove the migration logic from `_initialise_schema`
   - Optionally update existing `"local_disk"` entries back to `"local"` via SQL:
     ```sql
     UPDATE companies SET storage_type = 'local' WHERE storage_type = 'local_disk';
     ```

## Future Considerations

- The `"local"` value is still accepted for backward compatibility
- Consider deprecating `"local"` in a future major version
- Update API documentation to recommend `"local_disk"` for new integrations
- Monitor logs for any remaining usage of legacy `"local"` type
