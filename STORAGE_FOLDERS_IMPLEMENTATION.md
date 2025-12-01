# Storage Folders Management API - Implementation Summary

## Overview
Implemented a comprehensive storage folders management system for Vertex AR with reusable service layer and admin-protected REST API endpoints.

## Components Created

### 1. Storage Folders Service (`app/services/storage_folders.py`)
A reusable service that provides:
- **Base folder management**: Auto-creates `vertex_ar_content` base folder under `settings.STORAGE_ROOT`
- **Folder name normalization**: Validates folder names (letters/digits/dash/underscore only)
- **Company storage root resolution**: Generates paths like `storage/vertex_ar_content/{company_id}/{content_type}/`
- **Permission verification**: Checks read/write/execute permissions
- **Folder listing**: Lists existing order folders with metadata
- **Folder creation**: Creates folders with required subdirectories: `[Image, QR, nft_markers, nft_cache]`
- **Folder deletion**: Safely deletes empty folders (with force option)
- **Storage status**: Provides comprehensive status information

**Key Methods:**
- `normalize_folder_name(name)` - Validates and normalizes folder names
- `get_company_storage_root(company_id, content_type)` - Resolves storage paths
- `verify_permissions(path)` - Checks folder permissions
- `list_order_folders(company_id, content_type)` - Lists existing folders
- `create_order_folder(company_id, content_type, folder_name)` - Creates folder structure
- `delete_order_folder(company_id, content_type, folder_name, force)` - Deletes folders
- `get_storage_status(company_id)` - Returns comprehensive status

### 2. API Endpoints (`app/api/storage_folders.py`)
Four new admin-protected REST endpoints:

#### GET `/api/companies/{company_id}/storage`
Returns current storage configuration and status including:
- Storage type (local/minio/yandex_disk)
- Storage root path
- Company-specific path
- Permissions (read/write/execute)
- Content type folder counts
- Configuration status

**Response Example:**
```json
{
  "company_id": "comp-123",
  "company_name": "Acme Corp",
  "storage_type": "local",
  "storage_root": "/app/storage",
  "company_path": "/app/storage/vertex_ar_content/comp-123",
  "permissions": {
    "exists": true,
    "readable": true,
    "writable": true,
    "executable": true
  },
  "content_types": {
    "portraits": 5,
    "diplomas": 3
  },
  "is_ready": true,
  "is_configured": true,
  "status_message": "✅ Ready (path: /app/storage/vertex_ar_content/comp-123)"
}
```

#### GET `/api/storage/folders/list?company_id={id}&content_type={type}`
Lists existing order folders for a company.

**Query Parameters:**
- `company_id` (required) - Company identifier
- `content_type` (optional) - Filter by content type

**Response Example:**
```json
{
  "company_id": "comp-123",
  "folders": [
    {
      "folder_name": "order-001",
      "content_type": "portraits",
      "full_path": "/app/storage/vertex_ar_content/comp-123/portraits/order-001",
      "has_required_subdirs": {
        "Image": true,
        "QR": true,
        "nft_markers": true,
        "nft_cache": true
      },
      "is_empty": false
    }
  ],
  "total": 1
}
```

#### POST `/api/storage/folders/create`
Creates a new order folder with required subdirectory structure.

**Request Body:**
```json
{
  "company_id": "comp-123",
  "content_type": "portraits",
  "folder_name": "order-001"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Folder 'order-001' created successfully",
  "folder_path": "/app/storage/vertex_ar_content/comp-123/portraits/order-001"
}
```

**Features:**
- Validates folder name format
- Enforces uniqueness
- Checks permissions
- Creates all required subdirectories
- Creates parent directories if needed

#### POST `/api/storage/folders/delete`
Deletes an order folder.

**Request Body:**
```json
{
  "company_id": "comp-123",
  "content_type": "portraits",
  "folder_name": "order-001",
  "force": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "Folder 'order-001' deleted successfully",
  "folder_path": null
}
```

**Features:**
- Only deletes empty folders by default
- `force=true` allows deletion of non-empty folders
- Validates folder existence
- Provides clear error messages

### 3. Pydantic Models (`app/models.py`)
Added comprehensive request/response models:
- `StorageFolderListRequest` - Query parameters for listing
- `StorageFolderItem` - Individual folder information
- `StorageFoldersListResponse` - List response with total
- `StorageFolderCreateRequest` - Create request with validation
- `StorageFolderDeleteRequest` - Delete request with force option
- `StorageFolderOperationResponse` - Operation result
- `CompanyStorageStatusResponse` - Comprehensive status information

### 4. Updated Existing Endpoint
Updated `/companies/{company_id}/storage-folder` endpoint to use the centralized service for consistency.

## Integration

### Service Registration
Service exported from `app/services/__init__.py`:
```python
from app.services.storage_folders import StorageFoldersService, get_storage_folders_service
```

### Router Registration
Router registered in `app/main.py`:
```python
from app.api import storage_folders
app.include_router(storage_folders.router, prefix="/api", tags=["storage_folders"])
```

## Testing

### Unit Tests (`test_files/unit/test_storage_folders_service.py`)
Comprehensive test suite with 29 tests covering:
- Folder name normalization (valid/invalid cases)
- Base folder creation
- Company storage root resolution
- Permission verification
- Folder creation (success, duplicates, invalid names, parent dirs)
- Folder listing (empty, filtered, all)
- Folder deletion (empty, non-empty, force)
- Storage status
- Empty folder detection
- Required subdirectory checking

**Test Results:** ✅ All 29 tests passing

### Manual Verification
- ✅ Service loads successfully
- ✅ Base `vertex_ar_content` folder auto-created
- ✅ App starts with all 4 endpoints registered
- ✅ Total routes: 212

## File Structure

```
vertex-ar/
├── app/
│   ├── services/
│   │   ├── __init__.py (updated)
│   │   └── storage_folders.py (NEW - 416 lines)
│   ├── api/
│   │   ├── storage_folders.py (NEW - 437 lines)
│   │   └── companies.py (updated - uses service)
│   ├── models.py (updated - added 9 new models)
│   └── main.py (updated - router registration)
├── storage/
│   └── vertex_ar_content/ (auto-created)
├── test_files/
│   └── unit/
│       └── test_storage_folders_service.py (NEW - 568 lines, 29 tests)
└── STORAGE_FOLDERS_IMPLEMENTATION.md (this file)
```

## Key Features

1. **Automatic Base Folder Creation**: The `vertex_ar_content` base folder is created when the service is first initialized (app startup or first API call).

2. **Required Subdirectory Structure**: Every order folder automatically gets:
   - `Image/` - For portrait images
   - `QR/` - For QR codes
   - `nft_markers/` - For NFT marker files
   - `nft_cache/` - For cached NFT data

3. **Path Normalization**: All folder names are validated to contain only:
   - Letters (a-z, A-Z)
   - Digits (0-9)
   - Dashes (-)
   - Underscores (_)

4. **Permission Checking**: Service verifies read/write/execute permissions before operations.

5. **Safe Deletion**: By default, only empty folders can be deleted to prevent data loss.

6. **Comprehensive Logging**: All operations emit structured logs with context.

7. **Admin Authentication**: All endpoints require admin authentication via cookie-based authToken.

8. **Company Isolation**: Each company gets its own isolated storage hierarchy.

## Usage Examples

### Creating a Folder
```bash
curl -X POST http://localhost:8000/api/storage/folders/create \
  -H "Cookie: authToken=<admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "comp-123",
    "content_type": "portraits",
    "folder_name": "order-001"
  }'
```

### Listing Folders
```bash
curl -X GET "http://localhost:8000/api/storage/folders/list?company_id=comp-123&content_type=portraits" \
  -H "Cookie: authToken=<admin-token>"
```

### Getting Storage Status
```bash
curl -X GET http://localhost:8000/api/companies/comp-123/storage \
  -H "Cookie: authToken=<admin-token>"
```

### Deleting a Folder
```bash
curl -X POST http://localhost:8000/api/storage/folders/delete \
  -H "Cookie: authToken=<admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "comp-123",
    "content_type": "portraits",
    "folder_name": "order-001",
    "force": false
  }'
```

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200 OK` - Success
- `400 Bad Request` - Invalid input (e.g., invalid folder name)
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Not an admin user
- `404 Not Found` - Company or folder not found
- `500 Internal Server Error` - Server-side errors

Error responses include descriptive messages:
```json
{
  "success": false,
  "message": "Folder name can only contain letters, digits, dashes, and underscores"
}
```

## Benefits

1. **Centralized Logic**: Single source of truth for folder management
2. **Reusable**: Service can be used by any part of the application
3. **Consistent**: All storage operations follow the same rules
4. **Safe**: Built-in validation and permission checking
5. **Well-Tested**: Comprehensive unit tests ensure reliability
6. **Well-Documented**: Clear API documentation and examples
7. **Maintainable**: Clean separation of concerns between service and API layers

## Future Enhancements

Potential improvements:
1. Batch folder operations (create/delete multiple)
2. Folder renaming capability
3. Storage quota management per company
4. Folder archival/restoration
5. Audit log for all folder operations
6. Webhooks for folder events
7. Integration with cloud storage providers
