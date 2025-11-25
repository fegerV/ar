# Storage Configuration Implementation

This document describes the implementation of flexible storage configuration for Vertex AR, allowing different content types to be stored in different storage backends.

## Overview

The implementation provides:
1. **Multiple Storage Backends**: Local filesystem, MinIO, and Yandex Disk
2. **Content-Type Specific Configuration**: Different storage for portraits, videos, previews, and NFT markers
3. **Chunked Backup Support**: Large backup files can be split into configurable chunk sizes
4. **Unified Management Interface**: Single UI for managing all storage configurations

## Architecture

### Core Components

#### StorageManager (`storage_manager.py`)
- Manages different storage adapters for different content types
- Routes file operations to appropriate storage backend
- Provides unified API regardless of backend

#### Storage Adapters
- **LocalStorageAdapter**: Filesystem-based storage (existing)
- **MinioStorageAdapter**: MinIO S3-compatible storage (existing)
- **YandexDiskStorageAdapter**: Yandex Disk cloud storage (new)

#### StorageConfig (`storage_config.py`)
- Manages configuration for different content types
- Handles JSON-based configuration persistence
- Provides default settings

#### API Endpoints (`app/api/storage_config.py`)
- `/storage-config/config` - Get/set configuration
- `/storage-config/content-type/{type}` - Configure storage for content type
- `/storage-config/backup-settings` - Configure backup settings
- `/storage-config/test-connection/{type}` - Test storage connections

#### Yandex Disk API (`app/api/yandex_disk.py`)
- `/api/yandex-disk/file/{path}` - Serve files from Yandex Disk
- `/api/yandex-disk/download/{path}` - Download files from Yandex Disk

## Configuration Structure

```json
{
  "content_types": {
    "portraits": {
      "storage_type": "local",
      "yandex_disk": {
        "enabled": false,
        "base_path": "vertex-ar/portraits"
      }
    },
    "videos": {
      "storage_type": "local",
      "yandex_disk": {
        "enabled": false,
        "base_path": "vertex-ar/videos"
      }
    },
    "previews": {
      "storage_type": "local",
      "yandex_disk": {
        "enabled": false,
        "base_path": "vertex-ar/previews"
      }
    },
    "nft_markers": {
      "storage_type": "local",
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

### 2. Content-Type Specific Configuration

Each content type can be configured independently:
- **Portraits**: Main portrait images
- **Videos**: AR video content
- **Previews**: Generated thumbnails
- **NFT Markers**: AR tracking markers

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