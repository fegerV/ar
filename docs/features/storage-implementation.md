# Storage Configuration Implementation

This document describes the implementation of flexible storage configuration for Vertex AR, supporting multiple storage backends with per-company configuration.

## Overview

The implementation provides:
1. **Multiple Storage Backends**: Local disk (`local_disk`), MinIO, and Yandex Disk
2. **Per-Company Storage Configuration**: Each company can use different storage backend
3. **Category-Based Organization**: Content organized via categories (managed through projects table)
4. **Chunked Backup Support**: Large backup files can be split into configurable chunk sizes
5. **Unified Management Interface**: Single UI for managing all storage configurations

## Storage Type Naming

The system uses consistent storage type identifiers:
- **`local_disk`**: Canonical local storage type (display: "Локальное хранилище" / "Local Disk")
- **`yandex_disk`**: Yandex Disk cloud storage
- **`minio`**: MinIO S3-compatible storage

## Architecture

### Core Components

#### StorageManager (`storage_manager.py`)
- Manages different storage adapters for different content types
- Routes file operations to appropriate storage backend
- Provides unified API regardless of backend

#### Storage Adapters
- **LocalStorageAdapter**: Filesystem-based storage with hierarchical folder structure
- **MinioStorageAdapter**: MinIO S3-compatible storage
- **YandexDiskStorageAdapter**: Yandex Disk cloud storage

#### Company Configuration
- Each company has `storage_type` field (e.g., `local_disk`, `yandex_disk`, `minio`)
- Storage adapters initialized per company based on configuration
- Categories managed via projects table with storage-friendly slugs

#### API Endpoints (`app/api/storage_config.py`)
- `/storage-config/config` - Get/set configuration
- `/storage-config/content-type/{type}` - Configure storage for content type
- `/storage-config/backup-settings` - Configure backup settings
- `/storage-config/test-connection/{type}` - Test storage connections

#### Yandex Disk API (`app/api/yandex_disk.py`)
- `/api/yandex-disk/file/{path}` - Serve files from Yandex Disk
- `/api/yandex-disk/download/{path}` - Download files from Yandex Disk

## Configuration Structure

**Note**: This configuration shows legacy structure. Modern system uses per-company storage configuration and category-based organization.

### Legacy Configuration (Deprecated)
```json
{
  "content_types": {
    "portraits": {
      "storage_type": "local_disk",
      "yandex_disk": {
        "enabled": false,
        "base_path": "vertex-ar/portraits"
      }
    },
    "videos": {
      "storage_type": "local_disk",
      "yandex_disk": {
        "enabled": false,
        "base_path": "vertex-ar/videos"
      }
    },
    "previews": {
      "storage_type": "local_disk",
      "yandex_disk": {
        "enabled": false,
        "base_path": "vertex-ar/previews"
      }
    },
    "nft_markers": {
      "storage_type": "local_disk",
      "yandex_disk": {
        "enabled": false,
        "base_path": "vertex-ar/nft_markers"
      }
    }
  },
  "backup_settings": {
    "auto_split_backups": true,
    "max_backup_size_mb": 500,
    "chunk_size_mb": 100,
    "compression": "gz"
  },
  "yandex_disk": {
    "oauth_token": "",
    "enabled": false
  },
  "minio": {
    "enabled": false,
    "endpoint": "",
    "access_key": "",
    "secret_key": "",
    "bucket": ""
  }
}
```

## Features

### 1. Multiple Storage Backends

#### Local Storage
- Default option
- Stores files in local filesystem
- No external dependencies

#### MinIO Storage
- S3-compatible object storage
- Self-hosted or cloud-based
- Requires MinIO server configuration

#### Yandex Disk Storage
- Cloud storage integration
- OAuth token authentication
- Automatic directory management
- Public link generation

### 2. Category-Based Organization

Content is organized by categories (managed via projects table):
- Each company defines custom categories (e.g., "portraits", "diplomas", "certificates")
- Categories have storage-friendly slugs used in folder paths
- Replaces legacy CSV-based `content_types` approach
- Files organized: `{storage_root}/{folder_path}/{company_slug}/{category_slug}/{order_id}/`

### 3. Chunked Backup Support

Large backup files are automatically split:
- Configurable maximum backup size (default: 500MB)
- Configurable chunk size (default: 100MB)
- Automatic merging during restore
- Progress tracking

### 4. Enhanced UI Features

#### Storage Configuration Page
- Dropdown selectors for each content type
- Real-time connection testing
- Storage usage information
- Configuration validation

#### Yandex Disk Integration
- OAuth token input with validation
- Storage quota display
- Connection status indicators
- Public link management

## Implementation Details

### File Organization

```
vertex-ar/
├── app/
│   ├── api/
│   │   ├── storage_config.py    # New storage configuration API
│   │   └── yandex_disk.py      # New Yandex Disk file serving
│   ├── storage_yandex.py          # New Yandex Disk adapter
│   └── main.py                  # Updated with storage manager
├── storage_config.py              # New configuration manager
├── storage_manager.py             # New storage manager
└── config/
    └── storage_config.json       # Configuration file (auto-created)
```

### API Integration

#### Portraits API (`app/api/portraits.py`)
- Uses `storage_manager.save_file()` for portraits
- Uses `storage_manager.save_file()` for previews
- Returns public URLs in response

#### Videos API (`app/api/videos.py`)
- Uses `storage_manager.save_file()` for videos
- Uses `storage_manager.save_file()` for previews
- Returns public URLs in response

#### AR Page (`app/main.py`)
- Uses `storage_manager.get_public_url()` for video URLs
- Works with any storage backend

### Backup Integration

#### Backup Manager (`backup_manager.py`)
- Uses `storage_config.get_backup_settings()`
- Configurable chunk sizes
- Automatic file splitting
- Metadata tracking

## Usage

### 1. Basic Setup

1. Navigate to **⚙️ Настройки** in admin panel
2. Configure storage types for each content type
3. Enter Yandex Disk OAuth token (if using cloud storage)
4. Test connections
5. Save configuration

### 2. Yandex Disk Setup

1. Get OAuth token from [Yandex Disk API](https://yandex.ru/dev/disk-api/doc/ru/concepts/quickstart)
2. Enter token in Yandex Disk configuration
3. Click "Тестировать соединение"
4. Verify storage information displays correctly
5. Save configuration

### 3. Backup Configuration

1. Set maximum backup size (default: 500MB)
2. Configure chunk size (default: 100MB)
3. Enable/disable automatic splitting
4. Choose compression type
5. Test backup creation

## Migration Notes

### Existing Installations
- Configuration automatically migrates to new format
- Existing files remain in local storage
- No data loss during upgrade
- Backward compatibility maintained

### Storage Migration
- Files can be moved between storage types
- Use backup/restore for bulk migration
- Configuration preserves file paths
- URL generation adapts automatically

## Security Considerations

### Token Management
- OAuth tokens stored securely in configuration
- Tokens not exposed in UI after entry
- Connection testing validates token validity
- Revocation support through Yandex Disk

### File Access
- Public URLs generated per storage type
- Yandex Disk files served through proxy
- Access logging and monitoring
- Optional public link generation

## Troubleshooting

### Common Issues

#### Yandex Disk Connection
- Verify OAuth token validity
- Check API permissions
- Ensure token has Disk access
- Monitor rate limits

#### File Access Issues
- Check storage configuration
- Verify file paths
- Test public URL generation
- Check storage adapter logs

#### Backup Problems
- Verify chunk size settings
- Check available disk space
- Test with smaller files first
- Review backup logs

### Debug Information

Configuration location: `config/storage_config.json`
Logs: Available through admin panel
Connection tests: Built into UI
Storage info: Real-time display

## Company-Specific Storage Configuration

### Overview

Starting in version 1.5.0, Vertex AR supports company-level storage configuration. Each company can use a different storage backend, enabling:
- Multi-tenant storage isolation
- Per-company cost management
- Flexible migration strategies
- Compliance with data residency requirements

### Company Storage Fields

| Field | Type | Description |
|-------|------|-------------|
| `storage_type` | TEXT | Storage backend: `local_disk`, `minio`, or `yandex_disk` |
| `storage_connection_id` | TEXT | Reference to `storage_connections` table |
| `storage_folder_path` | TEXT | Custom folder path (optional, defaults to company slug) |

### Default Company

The system auto-provisions a default "Vertex AR" company on first startup with `storage_type = 'local_disk'`.

### Workflow

When an order is created:
1. **Company Selection** → determines storage backend (`storage_type`)
2. **Category Selection** → determines content organization (via `/api/companies/{id}/categories`)
3. **Path Building** → constructs hierarchy: `{storage_root}/{folder_path}/{company_slug}/{category_slug}/{order_id}/`
4. **File Upload** → uploads all files (portrait, video, previews, markers) to appropriate subfolders
5. **URL Generation** → returns public URLs based on storage type

### Example: Company with Yandex Disk

```json
{
  "id": "company-uuid",
  "name": "Acme Corp",
  "storage_type": "yandex_disk",
  "storage_connection_id": "yandex-connection-uuid"
}
```

Files for this company are stored at:
```
vertex-ar/companies/company-uuid/portraits/{client_id}/{portrait_id}/
```

**See also:** [Yandex Disk Storage Flow](yandex-disk-storage-flow.md) for complete documentation.

## Future Enhancements

### Planned Features
1. **Additional Storage Backends**: Google Drive, Dropbox, AWS S3
2. **Advanced Backup**: Incremental backups, compression options
3. **Storage Analytics**: Usage statistics, cost tracking
4. **Migration Tools**: Automated storage-to-storage migration

### Extensibility
The architecture supports:
- New storage adapters through base class
- Additional content types
- Custom backup strategies
- Plugin-style extensions