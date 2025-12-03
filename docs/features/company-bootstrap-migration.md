# Company Bootstrap Migration

## Overview

As of this update, the Vertex AR application now automatically initializes the default company with a complete folder structure during startup. This enhancement ensures that both the database records and filesystem hierarchy are properly provisioned for immediate use.

## What's New

### Automatic Bootstrap Process

The `ensure_default_company` function now performs a complete initialization that includes:

1. **Company Record Creation**: Ensures the default "Vertex AR" company exists with proper storage settings
2. **Category Seeding**: Automatically creates default categories (portraits, diplomas, certificates) with stable IDs and slugs
3. **Folder Seeding**: Creates at least one folder per category to maintain consistent folder↔category relationships
4. **Filesystem Hierarchy**: Uses `FolderService` to create the complete directory structure on disk

### Reusable Bootstrap Helper

A new reusable service `app/services/company_bootstrap.py` has been introduced with the `CompanyBootstrap` class that encapsulates all bootstrap logic. This service can be used for:
- Initializing the default company during application startup
- Creating new companies with consistent folder structures
- Verifying and repairing company folder hierarchies

## Migration Notes for Existing Environments

### Automatic Upgrade

Existing installations will automatically benefit from this enhancement during the next application restart. The bootstrap process is designed to be idempotent, meaning it safely handles cases where:
- The default company already exists
- Some or all categories already exist
- Some or all folders already exist
- Partial filesystem hierarchy already exists

### Storage Path Standardization

The default company is now strictly enforced to use:
- **Storage Type**: `local_disk`
- **Storage Folder Path**: `vertex_ar_content`

These settings are immutable for the default company and will be automatically corrected if manually modified.

### Directory Structure

The new bootstrap creates the following directory hierarchy:

```
<STORAGE_ROOT>/
└── vertex_ar_content/
    └── vertex-ar-default/
        ├── portraits/
        │   ├── Image/
        │   ├── QR/
        │   ├── nft_markers/
        │   └── nft_cache/
        ├── diplomas/
        │   ├── Image/
        │   ├── QR/
        │   ├── nft_markers/
        │   └── nft_cache/
        └── certificates/
            ├── Image/
            ├── QR/
            ├── nft_markers/
            └── nft_cache/
```

## Testing

An updated test script `test_default_company_folders.py` verifies both database records and filesystem hierarchy creation. Run this script to confirm proper bootstrap functionality:

```bash
python test_default_company_folders.py
```

## Backward Compatibility

The implementation maintains full backward compatibility:
- Existing databases will be automatically upgraded
- The original bootstrap logic is preserved as a fallback
- No breaking changes to existing APIs or functionality

## Troubleshooting

If bootstrap fails during startup:
1. Check application logs for specific error messages
2. Verify filesystem permissions on the storage root directory
3. Manually run the test script to diagnose issues
4. The system will fall back to the original implementation if the new bootstrap fails
