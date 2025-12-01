# Storage Documentation Update - Summary

## Overview
Comprehensive update to storage-related documentation to reflect the current system architecture with category-based organization and standardized `local_disk` storage type naming.

## Changes Made

### Key Updates

1. **Removed `content_types` References**
   - Legacy CSV field (`content_types = "slug1:label1,slug2:label2"`) is now deprecated
   - System uses explicit category management via projects table
   - Categories accessed through `/api/companies/{id}/categories` endpoints
   - Each category has storage-friendly slug used in folder paths

2. **Standardized Storage Type Naming**
   - **`local_disk`**: Canonical local storage type across DB/API/UI
   - Display: "Локальное хранилище" (Russian) / "Local Disk" (English)
   - Removed references to ambiguous `local` or `local_storage` identifiers

3. **Folder Selection Workflow Documentation**
   - Company Selection → determines storage backend
   - Category Selection → determines content organization
   - Order Creation → files stored in hierarchy: `{storage_root}/{folder_path}/{company_slug}/{category_slug}/{order_id}/`

4. **API Prefix Consistency**
   - All example API requests now use `/api` prefix
   - Updated endpoints: `/api/companies`, `/api/orders/create`, `/api/companies/{id}/categories`

5. **Default Company Documentation**
   - System auto-provisions "Vertex AR" company on first startup
   - Default storage type: `local_disk`
   - Mentioned across all relevant documentation files

## Files Updated

### Main Documentation Files

1. **COMPANIES_API_ENHANCED.md** (549 lines)
   - Removed `content_types` from request/response examples
   - Added category management workflow section
   - Updated storage type filters to use `local_disk`
   - Added folder selection workflow explanation
   - Documented default company auto-provisioning

2. **ORDER_WORKFLOW_STORAGE_FOLDERS.md** (260 lines)
   - Changed references from `content_type` to `category_slug`
   - Updated hierarchy diagrams to show category-based paths
   - Added storage type reference section
   - Documented folder selection workflow
   - Clarified `local_disk` as canonical local storage type

3. **docs/features/storage-implementation.md** (336 lines)
   - Updated overview to emphasize per-company configuration
   - Replaced "Content-Type Specific Configuration" with "Category-Based Organization"
   - Added storage type naming section
   - Updated company storage fields table
   - Documented default company behavior

4. **docs/features/yandex-disk-storage-flow.md** (693 lines)
   - Updated company fields table with all storage columns
   - Changed content type organization to category-based
   - Updated API endpoint examples with `/api` prefix
   - Replaced projects/folders integration with categories
   - Updated all code examples to use category workflow

5. **README.md** (312 lines)
   - Updated storage feature description
   - Added note about default company auto-provisioning
   - Updated technology stack section
   - Added `/api/companies/*` and `/api/orders/create` to API table

6. **README_RU.md** (317 lines)
   - Updated description with storage type clarification
   - Added default company note in Russian
   - Consistent with English README changes

7. **COMPANY_ADMIN_UI.md** (467 lines)
   - Removed "Content Types Management" step from create workflow
   - Updated edit company section
   - Added note about category management via separate endpoints
   - Changed "Local storage" to "Local disk (`local_disk`)"

8. **COMPANY_SCHEMA_EXTENSIONS.md** (288 lines)
   - Added deprecation note about legacy `content_types` field
   - Updated schema extensions to show all storage-related columns
   - Changed default company description

## Key Concepts Documented

### 1. Storage Type Naming
```
local_disk     → "Локальное хранилище" / "Local Disk"
yandex_disk    → "Yandex Disk"
minio          → "MinIO / S3"
```

### 2. Category-Based Organization
- Categories managed via projects table with `slug` column
- Storage-friendly slugs (lowercase, alphanumeric, hyphens/underscores)
- API endpoints: `/api/companies/{id}/categories`
- Replaces legacy CSV-based `content_types` approach

### 3. Folder Hierarchy
```
{storage_root}/
  {folder_path}/
    {company_slug}/
      {category_slug}/
        {order_id}/
          Image/       # portraits, videos, previews
          QR/          # QR codes
          nft_markers/ # NFT marker files
          nft_cache/   # NFT cache files
```

### 4. Order Workflow
1. **Company Selection** → storage backend (`storage_type`)
2. **Category Selection** → content organization (via categories API)
3. **Order Creation** → files uploaded to hierarchical structure
4. **Path Storage** → relative paths stored in database for portability

### 5. API Examples Updated
All examples now follow consistent patterns:
- Prefix: `/api` for all API endpoints
- Company creation shows `storage_type: "local_disk"`
- Category management examples included
- Order creation examples reference categories

## Default Company Behavior

System auto-provisions default company on first startup:
- **Name**: "Vertex AR"
- **ID**: `vertex-ar-default`
- **Storage Type**: `local_disk`
- **Cannot be deleted**: Protected by backend validation
- **Categories**: Managed separately via API

## Migration Notes

### For Existing Installations
- Legacy `content_types` CSV field still exists in database (backward compatibility)
- New category management provides better organization
- Both approaches can coexist during migration
- Recommend migrating to category-based approach for new content

### For Developers
- Use `/api/companies/{id}/categories` endpoints for category management
- Always specify `storage_type` as `local_disk` for local storage
- Follow folder hierarchy pattern for new storage implementations
- Use relative paths in database for portability

## Testing
All documentation updates verified for:
- ✅ Consistency across English and Russian docs
- ✅ Correct API endpoint paths with `/api` prefix
- ✅ Accurate storage type naming (`local_disk`)
- ✅ Complete removal of outdated `content_types` references
- ✅ Clear explanation of category-based workflow
- ✅ Proper hierarchy documentation

## Future Considerations

1. **Complete Migration**: Eventually remove `content_types` column from database
2. **UI Updates**: Admin interface should use category management endpoints
3. **Data Migration Script**: Tool to convert legacy `content_types` to categories
4. **API Deprecation**: Formally deprecate any endpoints still using `content_types`

## Related Documentation

- **COMPANIES_API_ENHANCED.md**: Full API reference for company and category management
- **ORDER_WORKFLOW_STORAGE_FOLDERS.md**: Detailed folder structure implementation
- **docs/features/storage-implementation.md**: Storage architecture overview
- **docs/features/yandex-disk-storage-flow.md**: Yandex Disk integration guide

## Acceptance Criteria Met

✅ **Project docs no longer mention `content_types`** (or marked as deprecated)
✅ **New folder-selection workflows described clearly** in both English and Russian
✅ **`local_disk` documented as canonical local storage type** across all files
✅ **Sample API requests/responses mirror updated backend** with `/api` prefix
✅ **Auto-provisioned "Vertex AR" company documented** in relevant sections

---

**Status**: ✅ Complete  
**Date**: January 2025  
**Files Modified**: 8 documentation files  
**Lines Updated**: ~500+ lines across all files
