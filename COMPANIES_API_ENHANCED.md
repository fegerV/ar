# Enhanced Company API Documentation

This document describes the comprehensive enhancements made to the company management API, including full CRUD operations, pagination, filtering, category management, and storage workflow endpoints.

## Table of Contents

1. [Overview](#overview)
2. [Company CRUD Operations](#company-crud-operations)
3. [Category Management](#category-management)
4. [Storage Workflow](#storage-workflow)
5. [Database Schema](#database-schema)
6. [Testing](#testing)

---

## Overview

The enhanced company API provides complete lifecycle management for companies and their categories, with support for:

- **Full CRUD**: Create, Read, Update (PUT/PATCH), Delete operations
- **Pagination**: Paginated listings with configurable page size
- **Filtering**: Search by name and filter by storage type
- **Categories**: Explicit category management via projects table with storage-friendly slugs
- **Storage Workflow**: Helper endpoints for guided company setup
- **Auto-Provisioning**: Default "Vertex AR" company created automatically on first startup

---

## Company CRUD Operations

### List Companies (Paginated & Filtered)

**Endpoint**: `GET /api/companies`

**Query Parameters**:
- `page` (int, default: 1): Page number
- `page_size` (int, default: 50, max: 200): Items per page
- `search` (string, optional): Search query for company name
- `storage_type` (string, optional): Filter by storage type (`local_disk`, `minio`, `yandex_disk`)

**Response**:
```json
{
  "items": [
    {
      "id": "company-abc123",
      "name": "Acme Corp",
      "storage_type": "local_disk",
      "storage_connection_id": null,
      "yandex_disk_folder_id": null,
      "storage_folder_path": "acme_corp",
      "backup_provider": null,
      "backup_remote_path": null,
      "created_at": "2025-01-15T10:30:00",
      "client_count": 42
    }
  ],
  "total": 120,
  "page": 1,
  "page_size": 50,
  "total_pages": 3
}
```

**Example**:
```bash
curl "https://api.example.com/api/companies?page=1&page_size=20&search=Acme&storage_type=local_disk"
```

### Get Single Company

**Endpoint**: `GET /api/companies/{company_id}`

**Response**: Returns single `CompanyResponse` object with all company details.

### Create Company

**Endpoint**: `POST /api/companies`

**Request Body**:
```json
{
  "name": "New Company",
  "storage_type": "local_disk",
  "storage_connection_id": null,
  "yandex_disk_folder_id": null,
  "storage_folder_path": "new_company",
  "backup_provider": null,
  "backup_remote_path": null
}
```

**Notes**:
- `storage_type` defaults to `local_disk` if not specified
- System auto-provisions default "Vertex AR" company on first startup
- Categories (content organization) are managed separately via `/api/companies/{id}/categories`

**Response**: `CompanyResponse` with 201 Created status.

### Update Company (PUT/PATCH)

**Endpoints**:
- `PUT /api/companies/{company_id}` - Full replacement
- `PATCH /api/companies/{company_id}` - Partial update

**Request Body** (all fields optional for PATCH):
```json
{
  "name": "Updated Company Name",
  "storage_type": "yandex_disk",
  "storage_connection_id": "conn-xyz789",
  "yandex_disk_folder_id": "/Companies/UpdatedCompany",
  "storage_folder_path": "updated_company",
  "backup_provider": "yandex_disk",
  "backup_remote_path": "/Backups/UpdatedCompany"
}
```

**Features**:
- Validates storage configuration (connections must be active and tested)
- Prevents renaming default company
- Automatically clears storage adapter cache when storage config changes
- Supports partial updates (PATCH) - only provided fields are updated

**Response**: Updated `CompanyResponse` object.

### Delete Company

**Endpoint**: `DELETE /api/companies/{company_id}`

**Features**:
- Cascade deletes all related data (clients, portraits, videos, folders)
- Protected: Cannot delete default company (`vertex-ar-default`)

**Response**:
```json
{
  "message": "Company 'Acme Corp' deleted successfully"
}
```

---

## Category Management

Categories are organizational units within a company (implemented using the `projects` table) that provide structure for content organization. Each category has:
- A display name
- A storage-friendly slug (unique within the company)
- Optional description
- Automatic tracking of folders and portraits

### Why Categories?

Categories provide explicit content organization for orders and portraits:

- **Storage Hierarchy**: Each category slug is used in storage paths (e.g., `/storage-root/folder-path/company-slug/category-slug/order-id/`)
- **Content Grouping**: Portraits can be organized into category-specific folders
- **Flexible Organization**: Each company can define custom categories (e.g., "portraits", "diplomas", "certificates")
- **Extensible**: Can add metadata, permissions, settings per category in future

### Folder Selection Workflow

When creating orders, the system follows this workflow:

1. **Select Company** → determines storage backend (`local_disk`, `yandex_disk`, etc.)
2. **Select/Create Category** → organizes content within company storage
3. **Create Order** → files stored in hierarchy: `{storage_root}/{folder_path}/{company_slug}/{category_slug}/{order_id}/`

For local disk storage (`local_disk`), files are organized in subfolders:
- `Image/` - portraits, videos, and previews
- `QR/` - QR codes
- `nft_markers/` - NFT marker files
- `nft_cache/` - NFT cache files

### Create Category

**Endpoint**: `POST /api/companies/{company_id}/categories`

**Request Body**:
```json
{
  "name": "Diplomas",
  "slug": "diplomas",
  "description": "AR-enabled diplomas and certificates"
}
```

**Validations**:
- Slug must be unique within the company
- Slug format: lowercase letters, numbers, dashes, underscores only
- Name and slug are required

**Response**:
```json
{
  "id": "cat-a1b2c3d4",
  "company_id": "company-abc123",
  "name": "Diplomas",
  "slug": "diplomas",
  "description": "AR-enabled diplomas and certificates",
  "created_at": "2025-01-15T12:00:00",
  "folder_count": 0,
  "portrait_count": 0
}
```

### List Categories

**Endpoint**: `GET /api/companies/{company_id}/categories`

**Query Parameters**:
- `page` (int, default: 1): Page number
- `page_size` (int, default: 50, max: 200): Items per page

**Response**:
```json
{
  "items": [
    {
      "id": "cat-a1b2c3d4",
      "company_id": "company-abc123",
      "name": "Diplomas",
      "slug": "diplomas",
      "description": "AR-enabled diplomas",
      "created_at": "2025-01-15T12:00:00",
      "folder_count": 3,
      "portrait_count": 47
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 50,
  "total_pages": 1
}
```

### Get Single Category

**Endpoint**: `GET /api/companies/{company_id}/categories/{category_id}`

**Response**: Single `CategoryResponse` object.

### Update Category (PUT/PATCH)

**Endpoints**:
- `PUT /api/companies/{company_id}/categories/{category_id}`
- `PATCH /api/companies/{company_id}/categories/{category_id}`

**Request Body** (all fields optional for PATCH):
```json
{
  "name": "Updated Diplomas",
  "slug": "updated-diplomas",
  "description": "Updated description"
}
```

**Features**:
- Validates slug uniqueness if changed
- Supports partial updates (PATCH)

**Response**: Updated `CategoryResponse`.

### Delete Category

**Endpoint**: `DELETE /api/companies/{company_id}/categories/{category_id}`

**Warning**: Cascade deletes all folders and portraits within the category!

**Response**:
```json
{
  "message": "Category 'Diplomas' deleted successfully"
}
```

---

## Storage Workflow

Helper endpoints for guided company setup following the workflow: **Create Storage → Create Company → Choose Storage → Select/Create Folder**.

### Get Available Storage Options

**Endpoint**: `GET /api/companies/workflow/storage-options`

**Response**:
```json
[
  {
    "id": "local",
    "name": "Локальный диск",
    "type": "local",
    "connection_id": null,
    "is_available": true
  },
  {
    "id": "conn-xyz789",
    "name": "Yandex Disk Production",
    "type": "yandex_disk",
    "connection_id": "conn-xyz789",
    "is_available": true
  }
]
```

**Features**:
- Always includes `local_disk` storage option
- Only includes tested and active remote connections
- UI can use this to present storage selection dialog

**Note**: `local_disk` is the canonical local storage type across the system (DB, API, and UI display as "Локальное хранилище" in Russian, "Local Disk" in English).

### Additional Workflow Endpoints

The following existing endpoints support the storage workflow:

1. **List Storage Connections**: `GET /api/storage-connections`
   - See all configured storage connections

2. **Test Storage Connection**: `POST /api/storage-connections/test`
   - Validate connection before use

3. **Assign Storage to Company**: `PUT /api/companies/{id}/storage-type`
   - Set storage type for company

4. **Select Folder** (Yandex): `POST /api/companies/{id}/yandex-disk-folder`
   - Choose folder on remote storage

5. **Create Local Folder**: `POST /api/companies/{id}/storage-folder`
   - Create folder for local storage

---

## Database Schema

### Projects Table (used for categories)

```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    slug TEXT,  -- NEW: Storage-friendly identifier
    description TEXT,
    status TEXT DEFAULT 'active',
    subscription_end TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE,
    UNIQUE(company_id, name),
    UNIQUE(company_id, slug)  -- NEW: Slug must be unique per company
);
```

### New Database Methods

**Company Methods** (`app/database.py`):
- `list_companies_paginated(limit, offset, search, storage_type)`: Paginated listing with filters
- `count_companies_filtered(search, storage_type)`: Count matching companies

**Category Methods** (`app/database.py`):
- `create_category(category_id, company_id, name, slug, description)`: Create category
- `list_categories(company_id, limit, offset)`: List categories with pagination
- `count_categories(company_id)`: Count categories for a company
- `get_category_by_slug(company_id, slug)`: Get category by slug
- `rename_category(category_id, new_name, new_slug)`: Rename category
- `delete_category(category_id)`: Delete category
- `assign_category_folder(portrait_id, category_folder_id)`: Assign portrait to folder

---

## Testing

Comprehensive test coverage in `test_files/integration/test_companies_enhanced.py`:

### Test Categories

1. **Company Tests**:
   - `test_company_update()`: Update company fields
   - `test_company_pagination()`: Paginated listing
   - `test_company_filtering()`: Search and storage type filters
   - `test_company_count_filtered()`: Filtered counting

2. **Category Tests**:
   - `test_category_creation()`: Create categories
   - `test_category_slug_uniqueness()`: Slug validation within company
   - `test_category_slug_across_companies()`: Slug reuse across companies
   - `test_list_categories()`: List categories
   - `test_category_pagination()`: Paginated category listing
   - `test_get_category_by_slug()`: Get by slug
   - `test_rename_category()`: Update category
   - `test_delete_category()`: Delete category
   - `test_category_folder_assignment()`: Assign portraits to folders

### Running Tests

```bash
cd /home/engine/project/vertex-ar
source .venv/bin/activate
python3 ../test_files/integration/test_companies_enhanced.py
```

**Expected Output**:
```
✓ Company update test passed
✓ Company pagination test passed
✓ Company filtering test passed
✓ Category creation test passed
✓ Category slug uniqueness test passed
✓ Category slug across companies test passed
✓ List categories test passed
✓ Category pagination test passed
✓ Get category by slug test passed
✓ Rename category test passed
✓ Delete category test passed
✓ Category folder assignment test passed
✓ Company count filtered test passed

✅ All enhanced company tests passed!
```

---

## Migration Notes

### Backward Compatibility

All changes are **100% backward compatible**:

1. **Slug Column**: Added as nullable, existing projects work without slugs
2. **Pagination**: Default parameters match old behavior
3. **Categories**: Explicit category management via projects table replaces legacy CSV approach
4. **Update Methods**: New `update_company()` accepts optional parameters
5. **Storage Type**: System standardizes on `local_disk` as canonical local storage identifier

### Data Migration

For existing projects that should become categories:

```python
# Generate slugs for existing projects
import re

def slugify(text):
    slug = re.sub(r'[^a-z0-9-]+', '-', text.lower().strip())
    return re.sub(r'-+', '-', slug).strip('-')

# Apply to existing projects
projects = database.list_projects(company_id="company-1")
for project in projects:
    if not project.get('slug'):
        slug = slugify(project['name'])
        database.rename_category(project['id'], project['name'], slug)
```

---

## API Summary

### Company Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/companies` | List companies (paginated, filtered) |
| GET | `/api/companies/{id}` | Get single company |
| POST | `/api/companies` | Create company |
| PUT/PATCH | `/api/companies/{id}` | Update company |
| DELETE | `/api/companies/{id}` | Delete company |

### Category Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/companies/{id}/categories` | List categories (paginated) |
| GET | `/api/companies/{id}/categories/{cat_id}` | Get single category |
| POST | `/api/companies/{id}/categories` | Create category |
| PUT/PATCH | `/api/companies/{id}/categories/{cat_id}` | Update category |
| DELETE | `/api/companies/{id}/categories/{cat_id}` | Delete category |

### Workflow Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/companies/workflow/storage-options` | Get available storage options |

---

## Best Practices

### Category Slug Guidelines

1. **Use Descriptive Slugs**: `diplomas`, `certificates`, `portraits`
2. **Lowercase Only**: `diplomas` not `Diplomas`
3. **Hyphens for Multi-Word**: `ar-diplomas` not `ar_diplomas` or `arDiplomas`
4. **Avoid Special Characters**: Only `a-z`, `0-9`, `-`, `_`
5. **Keep Short**: 3-20 characters ideal for storage paths

### Pagination Guidelines

1. **Default Page Size**: 50 items (good balance for UX)
2. **Max Page Size**: 200 items (prevents memory issues)
3. **Always Show Total**: Help users understand result set size
4. **Implement Search First**: Better UX than scrolling pages

### Storage Workflow

1. **Test Connections**: Always test before assigning to company
2. **Validate Folders**: Verify folder exists before saving path
3. **Handle Errors Gracefully**: Storage failures should not block company creation
4. **Cache Clearing**: Remember to clear cache after storage changes

---

## Troubleshooting

### Common Issues

**Issue**: Slug conflicts when creating category
- **Cause**: Another category in same company uses that slug
- **Solution**: Choose different slug or update existing category

**Issue**: Pagination returns empty results
- **Cause**: Page number too high for total results
- **Solution**: Check `total_pages` in response

**Issue**: Update fails with "No fields to update"
- **Cause**: All fields in update request are `null`
- **Solution**: Provide at least one field to update

**Issue**: Storage cache not cleared after update
- **Cause**: Storage manager not available
- **Solution**: Warning logged but update succeeds; cache will clear on restart

---

## Future Enhancements

Potential improvements for future versions:

1. **Category Permissions**: Per-category access control
2. **Category Templates**: Pre-configured category sets
3. **Bulk Operations**: Create/update/delete multiple categories
4. **Category Analytics**: Usage statistics per category
5. **Advanced Filtering**: Filter categories by creation date, portrait count
6. **Category Sorting**: Custom sort order for categories
7. **Category Metadata**: Custom fields per category
8. **Category Icons**: Visual identifiers for categories

---

## Support

For questions or issues:
1. Check test files for usage examples
2. Review database method documentation
3. See implementation in `app/api/companies.py`
4. Consult memory notes for architecture details
