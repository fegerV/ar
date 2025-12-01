# Order Workflow Storage Folders Implementation

## Overview
Enhanced the order workflow to properly organize files in a structured folder hierarchy for local disk storage, aligning with the Yandex Disk organization pattern.

## Ticket Requirements ✅
- [x] Enhanced `_create_order_workflow` for `local_disk` storage type
- [x] Created folder-management service to resolve/create order directories
- [x] Implemented proper folder hierarchy: `<storage_root>/<folder_path>/<company_slug>/<category_slug>/<order_id>/{Image|QR|nft_markers|nft_cache}`
- [x] Move generated files from temp workspace to appropriate subfolders
- [x] Store relative paths in SQLite for public URL compatibility
- [x] Guard against missing folders/permission issues with descriptive errors
- [x] Added comprehensive regression test coverage

## Storage Type Reference

The system uses `local_disk` as the canonical local storage type:
- **Database field**: `companies.storage_type = 'local_disk'`
- **API references**: All endpoints use `local_disk` identifier
- **UI display**: "Локальное хранилище" (Russian) / "Local Disk" (English)

## Changes Made

### 1. New Folder Service (`app/services/folder_service.py`)
Created a dedicated service for managing local storage folder hierarchy:

**Key Features:**
- **Slugification**: Converts company names/IDs to filesystem-safe slugs
- **Path Building**: Constructs absolute and relative paths following the hierarchy
- **Structure Creation**: Creates all required subfolders (Image, QR, nft_markers, nft_cache)
- **File Operations**: Moves files safely with parent directory creation
- **Error Handling**: Descriptive PermissionError and OSError exceptions with logging
- **Cleanup**: Removes temporary directories after successful operations

**Methods:**
```python
FolderService(storage_root)
- slugify(text) -> str
- get_company_slug(company) -> str
- build_order_path(company, content_type, order_id, subfolder=None) -> Path
- build_relative_path(company, content_type, order_id, filename, subfolder=None) -> str
- ensure_order_structure(company, content_type, order_id) -> dict
- move_file(source, destination) -> None
- cleanup_temp_directory(temp_dir) -> None
```

### 2. Updated Order Workflow (`app/api/orders.py`)
Enhanced `_create_order_workflow` function to use folder service for local storage:

**Changes:**
1. **Temp Directory**: Create temp directory for initial file processing
   ```
   storage_root/temp/orders/<order_id>/
   ```

2. **Local Storage Detection**: Check if `storage_type` is `local_disk`

3. **Folder Structure Creation**: Use `FolderService.ensure_order_structure()`
   - Creates: `Image/`, `QR/`, `nft_markers/`, `nft_cache/` subfolders
   - Category determined by order parameters (replaces legacy `content_type` CSV field)

4. **File Organization**:
   - Image → `Image/<portrait_id>.jpg`
   - Video → `Image/<video_id>.mp4`
   - Image Preview → `Image/<portrait_id>_preview.jpg`
   - Video Preview → `Image/<video_id>_preview.jpg`
   - QR Code → `QR/<portrait_id>_qr.png`
   - NFT Markers → `nft_markers/<marker_files>`

5. **Database Storage**: Store relative paths (from storage_root) for public URL compatibility

6. **Error Handling**: 
   - Catch `PermissionError` and `OSError` during folder operations
   - Return HTTP 500 with descriptive "Storage error: {details}"
   - Log full context including company_id, order_id, error details

7. **Cleanup**: Remove temp directory after successful file organization

### 3. Services Export (`app/services/__init__.py`)
Added `FolderService` to package exports for easy importing.

### 4. Test Coverage
Created comprehensive test suites covering all aspects:

#### Unit Tests (`test_files/unit/test_folder_service.py`) - 19 tests
- Slugification (basic, special characters, multiple spaces)
- Company slug generation
- Path building (basic, with subfolders, without storage_folder_path)
- Relative path construction
- Order structure creation (all folders, idempotent, permission errors)
- File operations (move, create parent dirs, not found, cleanup)
- Complete workflow integration

#### Integration Tests - Simple (`test_files/integration/test_order_local_storage_simple.py`) - 6 tests
- Create order folder structure
- Move files to order folders
- Relative paths for database
- Cleanup temp directory
- Multiple content types
- Default storage folder path

#### Integration Tests - Full API (`test_files/integration/test_order_workflow_storage_folders.py`) - 8 tests
- Order creates folder structure via API
- Database stores relative paths
- Default storage folder path handling
- Permission error handling
- Multiple content types (portraits, diplomas)
- Temp file cleanup after order creation
- Public URLs work with relative paths

All tests passing: **33 tests total**

## Folder Hierarchy

### Structure
```
<storage_root>/
  <storage_folder_path>/          # From company.storage_folder_path (or company slug)
    <company_slug>/                # Slugified company ID
      <category_slug>/             # Category from projects table (e.g., "portraits", "diplomas")
        <order_id>/                # UUID of the portrait/order
          Image/                   # Images, videos, previews
            <portrait_id>.jpg
            <video_id>.mp4
            <portrait_id>_preview.jpg
            <video_id>_preview.jpg
          QR/                      # QR codes
            <portrait_id>_qr.png
          nft_markers/             # NFT marker files
            <portrait_id>.fset
            <portrait_id>.fset3
            <portrait_id>.iset
          nft_cache/               # NFT cache files (if any)
```

**Note**: Categories are managed via the `/api/companies/{id}/categories` endpoints. Each category has a storage-friendly slug used in the folder path.

### Example
```
storage/
  company_storage/
    vertex_ar_default/
      portraits/
        550e8400-e29b-41d4-a716-446655440000/
          Image/
            550e8400-e29b-41d4-a716-446655440000.jpg
            660e8400-e29b-41d4-a716-446655440001.mp4
            550e8400-e29b-41d4-a716-446655440000_preview.jpg
            660e8400-e29b-41d4-a716-446655440001_preview.jpg
          QR/
            550e8400-e29b-41d4-a716-446655440000_qr.png
          nft_markers/
            550e8400-e29b-41d4-a716-446655440000.fset
            550e8400-e29b-41d4-a716-446655440000.fset3
            550e8400-e29b-41d4-a716-446655440000.iset
          nft_cache/
```

## Database Storage
Paths stored in SQLite are **relative to storage_root** to enable:
- Portability across deployments
- Compatible with existing `/storage/<relative_path>` public URL pattern
- Consistent with Yandex Disk logical path approach

**Example database paths:**
```
image_path: "company_storage/vertex_ar_default/portraits/550e8400.../Image/550e8400....jpg"
video_path: "company_storage/vertex_ar_default/portraits/550e8400.../Image/660e8400....mp4"
marker_fset: "company_storage/vertex_ar_default/portraits/550e8400.../nft_markers/550e8400....fset"
```

## Public URLs
The `LocalStorageAdapter.get_public_url()` method already handles relative paths:
```python
return f"{settings.BASE_URL}/storage/{file_path}"
```

This works seamlessly with the new relative paths stored in the database.

## Error Handling

### Permission Errors
```python
try:
    folder_service.ensure_order_structure(company, content_type, order_id)
except PermissionError as e:
    raise HTTPException(
        status_code=500,
        detail=f"Storage error: Permission denied creating folders"
    )
```

**Logged context:**
- Company ID
- Content type
- Order ID
- Error message
- Stack trace

### File System Errors
```python
except OSError as e:
    raise HTTPException(
        status_code=500,
        detail=f"Storage error: {str(e)}"
    )
```

## Backward Compatibility
- Existing Yandex Disk workflow unchanged
- Companies without `storage_folder_path` use company slug as default
- Existing portraits with old paths continue to work
- New orders use new folder structure

## Storage Type Support
| Storage Type | Folder Service Used | Structure | Display Name |
|-------------|---------------------|-----------|--------------|
| `local_disk` | ✅ Yes | Hierarchical with categories | "Локальное хранилище" / "Local Disk" |
| `yandex_disk` | ❌ No | Existing Yandex structure | "Yandex Disk" |
| `minio` | ❌ No | Existing MinIO structure | "MinIO / S3" |

## Configuration
Companies can configure storage via:
- `storage_type`: `"local_disk"` for local file storage with folder service
- `storage_folder_path`: Custom folder path (optional, defaults to company slug)
- Categories: Managed via `/api/companies/{id}/categories` endpoints (replaces legacy `content_types` CSV)

## Folder Selection Workflow
When creating an order:
1. **Company Selection** → determines storage backend
2. **Category Selection** → determines folder hierarchy (e.g., "portraits", "diplomas")
3. **Order Creation** → files organized in: `{storage_root}/{folder_path}/{company_slug}/{category_slug}/{order_id}/`

## Performance Considerations
1. **Temp Directory**: Files written once to temp, then moved (not copied)
2. **Same Filesystem**: `os.rename` used when possible (atomic)
3. **Cross Filesystem**: Falls back to `shutil.move` when needed
4. **Parent Creation**: `mkdir(parents=True)` creates all intermediate directories

## Monitoring & Logging
All operations logged with structured logging:
- Order structure creation (success/failure)
- File moves (source → destination)
- Error details with full context
- Temp directory cleanup

## Testing Strategy
1. **Unit Tests**: Test folder service in isolation
2. **Integration Tests**: Test complete workflow with database
3. **Error Cases**: Permission errors, missing files, cleanup failures
4. **Multiple Scenarios**: Different content types, storage paths, company configs

## Files Modified
- `vertex-ar/app/api/orders.py` - Updated order workflow
- `vertex-ar/app/services/__init__.py` - Added FolderService export

## Files Created
- `vertex-ar/app/services/folder_service.py` - New folder management service (291 lines)
- `test_files/unit/test_folder_service.py` - 19 unit tests (301 lines)
- `test_files/integration/test_order_local_storage_simple.py` - 6 integration tests (275 lines)
- `test_files/integration/test_order_workflow_storage_folders.py` - 8 full API integration tests (426 lines)
- `ORDER_WORKFLOW_STORAGE_FOLDERS.md` - This document

## Next Steps (Optional Enhancements)
1. **Migration Script**: Reorganize existing local storage files to new structure
2. **Admin UI**: Display folder structure in company settings
3. **Storage Stats**: Add API endpoints for storage usage per company/content type
4. **Cleanup Jobs**: Automated cleanup of old temp directories
5. **Validation**: Verify folder structure integrity on startup

## References
- Original ticket: "Align order workflow with storage folders"
- Memory: YANDEX DISK ORDER STORAGE section
- Related: PROJECTS & FOLDERS HIERARCHY feature
