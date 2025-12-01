# Yandex Disk Storage Flow for AR Content

**Version:** 1.0  
**Last Updated:** January 2025  
**Status:** Production Ready

## Overview

This document describes the complete workflow for using Yandex Disk as a storage backend for AR content in Vertex AR. The system supports company-specific storage configuration, allowing each company to use different storage backends (local, MinIO, or Yandex Disk) with automatic folder organization and content routing.

## Architecture

### Storage Hierarchy

```
Company (storage_type: yandex_disk)
    ├── Project 1
    │   ├── Folder A
    │   │   ├── Portrait 1
    │   │   │   ├── image.jpg
    │   │   │   ├── image_preview.jpg
    │   │   │   ├── nft_markers/
    │   │   │   └── Video 1
    │   │   │       ├── video.mp4
    │   │   │       └── video_preview.jpg
    │   │   └── Portrait 2
    │   └── Folder B
    └── Project 2
```

### Company Fields

Each company in the database has the following storage-related fields:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `storage_type` | TEXT | Storage backend type | `local_disk`, `minio`, `yandex_disk` |
| `storage_connection_id` | TEXT (nullable) | Reference to storage_connections table | UUID of connection |
| `storage_folder_path` | TEXT (nullable) | Custom folder path | `my_company` |
| `yandex_disk_folder_id` | TEXT (nullable) | Yandex Disk folder path | `/Companies/MyCompany` |

**Note**: The system uses `local_disk` as the canonical local storage type (displayed as "Локальное хранилище" in Russian, "Local Disk" in English).

### Storage Connections Table

The `storage_connections` table stores reusable storage configurations:

```sql
CREATE TABLE storage_connections (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK (type IN ('local', 'minio', 'yandex_disk')),
    config TEXT NOT NULL,  -- JSON configuration
    is_active INTEGER NOT NULL DEFAULT 1,
    is_tested INTEGER NOT NULL DEFAULT 0,
    test_result TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
```

**Yandex Disk Config Structure:**
```json
{
  "oauth_token": "AgAAAAABCDEFG...",
  "base_path": "vertex-ar",
  "enabled": true
}
```

## Required Yandex Disk Scopes

To use Yandex Disk storage, you need an OAuth token with the following scopes:

| Scope | Purpose | Required |
|-------|---------|----------|
| `cloud_api:disk.read` | Read files and folder structure | ✅ Yes |
| `cloud_api:disk.write` | Upload and modify files | ✅ Yes |
| `cloud_api:disk.app_folder` | Access application folder | ⚠️ Recommended |
| `cloud_api:disk.info` | Get storage quota information | ⚠️ Recommended |

### Obtaining OAuth Token

1. **Register Application** at [Yandex OAuth](https://oauth.yandex.ru/)
2. **Request Scopes**: Select `cloud_api:disk.read` and `cloud_api:disk.write`
3. **Get Token**: Complete OAuth flow to receive access token
4. **Store Securely**: Save token in storage connection configuration

**Example OAuth Request:**
```
https://oauth.yandex.ru/authorize?response_type=token&client_id=YOUR_CLIENT_ID&scope=cloud_api:disk.read%20cloud_api:disk.write
```

## On-Disk Structure for Orders

### Directory Layout

When an order is created, the system organizes files in a hierarchical structure:

#### Local Storage Path Pattern
```
storage/
└── portraits/
    └── {client_id}/
        └── {portrait_id}/
            ├── {portrait_id}.jpg              # Original portrait image
            ├── {portrait_id}_preview.jpg      # Portrait preview (WebP optimized)
            ├── {video_id}.mp4                 # Video file
            ├── {video_id}_preview.jpg         # Video thumbnail
            └── nft_markers/
                ├── {portrait_id}.fset         # NFT marker feature set
                ├── {portrait_id}.fset3        # NFT marker feature set 3
                └── {portrait_id}.iset         # NFT marker image set
```

#### Yandex Disk Path Pattern
```
{base_path}/
└── companies/
    └── {company_id}/
        └── portraits/
            └── {client_id}/
                └── {portrait_id}/
                    ├── {portrait_id}.jpg
                    ├── {portrait_id}_preview.jpg
                    ├── {video_id}.mp4
                    ├── {video_id}_preview.jpg
                    └── nft_markers/
                        ├── {portrait_id}.fset
                        ├── {portrait_id}.fset3
                        └── {portrait_id}.iset
```

### Path Building Logic

The system automatically builds the correct path based on company storage configuration:

```python
# For Yandex-enabled company
base_path = "vertex-ar"  # From storage connection config
company_path = f"{base_path}/companies/{company_id}"
portrait_path = f"{company_path}/portraits/{client_id}/{portrait_id}"

# For local disk storage (fallback)
portrait_path = f"storage/portraits/{client_id}/{portrait_id}"
```

**Note**: The code shows simplified example. Actual system uses category slugs for path construction.

### Category-Based Organization

Content is organized by categories (managed via projects table):

| Content Type | Local Disk Path | Yandex Path |
|--------------|----------------|-------------|
| All Content | `{storage_root}/{folder_path}/{company_slug}/{category_slug}/{order_id}/Image/` | `{base_path}/{folder_path}/{company_slug}/{category_slug}/{order_id}/Image/` |
| QR Codes | `{storage_root}/{folder_path}/{company_slug}/{category_slug}/{order_id}/QR/` | `{base_path}/{folder_path}/{company_slug}/{category_slug}/{order_id}/QR/` |
| NFT Markers | `{storage_root}/{folder_path}/{company_slug}/{category_slug}/{order_id}/nft_markers/` | `{base_path}/{folder_path}/{company_slug}/{category_slug}/{order_id}/nft_markers/` |

**Categories**: Managed via `/api/companies/{id}/categories` endpoints. Each category has a storage-friendly slug (e.g., "portraits", "diplomas", "certificates").

## API Endpoints

### Company Storage Configuration

#### Create Company with Yandex Storage
```http
POST /api/companies
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "Acme Corp",
  "storage_type": "yandex_disk",
  "storage_connection_id": "uuid-of-yandex-connection",
  "storage_folder_path": "acme_corp"
}
```

**Note**: System auto-provisions a default "Vertex AR" company with `storage_type = 'local_disk'` on first startup.

**Response:**
```json
{
  "id": "company-uuid",
  "name": "Acme Corp",
  "storage_type": "yandex_disk",
  "storage_connection_id": "uuid-of-yandex-connection",
  "created_at": "2025-01-15T10:00:00Z"
}
```

#### Update Company Storage Type
```http
PATCH /api/companies/{company_id}
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "storage_type": "yandex_disk",
  "storage_connection_id": "uuid-of-yandex-connection",
  "yandex_disk_folder_id": "/Companies/AcmeCorp"
}
```

### Storage Connection Management

#### Create Yandex Disk Connection
```http
POST /api/storage-management/connections
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "Primary Yandex Disk",
  "type": "yandex_disk",
  "config": {
    "oauth_token": "AgAAAAABCDEFG...",
    "base_path": "vertex-ar",
    "enabled": true
  }
}
```

#### Test Connection
```http
GET /storage-config/test-connection/yandex_disk
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "success": true,
  "storage_type": "yandex_disk",
  "connected": true,
  "info": {
    "success": true,
    "provider": "yandex_disk",
    "total_space": 10737418240,
    "used_space": 1073741824,
    "available_space": 9663676416,
    "trash_size": 104857600
  }
}
```

### Content Type Storage Configuration

#### Configure Portraits to Use Yandex Disk
```http
POST /storage-config/content-type/portraits
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "storage_type": "yandex_disk",
  "yandex_disk": {
    "enabled": true,
    "base_path": "vertex-ar/portraits"
  }
}
```

#### Get Storage Configuration
```http
GET /storage-config/config
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "success": true,
  "config": {
    "content_types": {
      "portraits": {
        "storage_type": "yandex_disk",
        "yandex_disk": {
          "enabled": true,
          "base_path": "vertex-ar/portraits"
        }
      },
      "videos": {...},
      "previews": {...},
      "nft_markers": {...}
    },
    "yandex_disk": {
      "oauth_token": "[REDACTED]",
      "enabled": true
    }
  },
  "storage_info": {...},
  "yandex_enabled": true
}
```

### Yandex Disk File Access

#### Serve File from Yandex Disk
```http
GET /api/yandex-disk/file/{encoded_path}
```

The system automatically encodes paths and serves files through a proxy endpoint.

**Example:**
```
GET /api/yandex-disk/file/vertex-ar%2Fcompanies%2Fcompany-uuid%2Fportraits%2Fclient-uuid%2Fportrait-uuid%2Fportrait-uuid.jpg
```

#### Download File from Yandex Disk
```http
GET /api/yandex-disk/download/{encoded_path}
```

Returns file with `Content-Disposition: attachment` header for direct download.

## Order Workflow with Yandex Storage

### Step-by-Step Flow

#### 1. Company Setup
```python
# Create company with Yandex storage
company = database.create_company(
    company_id=str(uuid.uuid4()),
    name="Acme Corp",
    storage_type="yandex_disk",
    storage_connection_id="yandex-connection-uuid"
)
```

#### 2. Create Order
```http
POST /orders/create
Authorization: Bearer {admin_token}
Content-Type: multipart/form-data

name: John Doe
phone: +79991234567
company_id: company-uuid
image: [portrait.jpg file]
video: [video.mp4 file]
```

#### 3. Backend Processing

The `_create_order_workflow` function handles storage routing:

```python
async def _create_order_workflow(...):
    # 1. Get company configuration
    company = database.get_company(company_id)
    storage_type = company.get("storage_type", "local")
    
    # 2. Determine storage adapter
    if storage_type == "yandex_disk":
        storage_connection = database.get_storage_connection(
            company["storage_connection_id"]
        )
        adapter = YandexDiskStorageAdapter(
            oauth_token=storage_connection["config"]["oauth_token"],
            base_path=storage_connection["config"]["base_path"]
        )
    else:
        adapter = LocalStorageAdapter(storage_root)
    
    # 3. Build file paths
    portrait_path = f"companies/{company_id}/portraits/{client_id}/{portrait_id}"
    
    # 4. Upload files
    image_url = await adapter.save_file(
        image_data,
        f"{portrait_path}/{portrait_id}.jpg"
    )
    
    video_url = await adapter.save_file(
        video_data,
        f"{portrait_path}/{video_id}.mp4"
    )
    
    # 5. Generate and upload previews
    image_preview = PreviewGenerator.generate_image_preview(image_data)
    await adapter.save_file(
        image_preview,
        f"{portrait_path}/{portrait_id}_preview.jpg"
    )
    
    # 6. Generate and upload NFT markers
    marker_files = NFTMarkerGenerator.generate(image_data, portrait_id)
    for marker_file, marker_data in marker_files.items():
        await adapter.save_file(
            marker_data,
            f"{portrait_path}/nft_markers/{marker_file}"
        )
```

#### 4. Response with Public URLs

```json
{
  "portrait": {
    "id": "portrait-uuid",
    "image_path": "/api/yandex-disk/file/vertex-ar%2Fcompanies%2F...",
    "image_preview_path": "/api/yandex-disk/file/...",
    "permanent_link": "abc123def"
  },
  "video": {
    "id": "video-uuid",
    "video_path": "/api/yandex-disk/file/...",
    "video_preview_path": "/api/yandex-disk/file/..."
  }
}
```

### Fallback Behavior

If Yandex Disk storage fails, the system automatically falls back to local storage:

```python
try:
    url = await yandex_adapter.save_file(data, path)
except Exception as e:
    logger.error("Yandex upload failed, falling back to local", error=str(e))
    local_adapter = LocalStorageAdapter(storage_root)
    url = await local_adapter.save_file(data, path)
```

## Folder Selection Workflow

### Category-Based Organization

Companies organize content using categories (managed via projects table with storage-friendly slugs):

```
Company → Category → Order/Portrait → Video
```

#### Create Category
```http
POST /api/companies/{company_id}/categories
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "Diplomas",
  "slug": "diplomas",
  "description": "AR-enabled diplomas and certificates"
}
```

#### List Categories
```http
GET /api/companies/{company_id}/categories
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "items": [
    {
      "id": "cat-uuid",
      "company_id": "company-uuid",
      "name": "Diplomas",
      "slug": "diplomas",
      "folder_count": 0,
      "portrait_count": 0
    }
  ],
  "total": 1
}
```

#### Create Order with Category
```http
POST /api/orders/create
Authorization: Bearer {admin_token}
Content-Type: multipart/form-data

company_id: company-uuid
category_slug: diplomas
name: John Doe
image: [file]
video: [file]
```

### Category-Based Storage Paths

Files are organized by category slug in the storage hierarchy:

```
{storage_root}/{folder_path}/{company_slug}/{category_slug}/{order_id}/
  ├── Image/       # portraits, videos, previews
  ├── QR/          # QR codes
  └── nft_markers/ # NFT marker files
```

This allows for better organization and easier bulk operations on categories.

## Logging and Monitoring

### Key Log Events

The system logs all storage operations with structured logging:

#### File Upload Success
```json
{
  "event": "file_saved",
  "storage_type": "yandex_disk",
  "file_path": "companies/company-uuid/portraits/...",
  "size_bytes": 1048576,
  "duration_ms": 1234,
  "level": "info"
}
```

#### File Upload Error
```json
{
  "event": "file_save_failed",
  "storage_type": "yandex_disk",
  "file_path": "companies/company-uuid/portraits/...",
  "error": "OAuth token expired",
  "level": "error"
}
```

#### Folder Creation
```json
{
  "event": "folder_created",
  "storage_type": "yandex_disk",
  "folder_path": "companies/company-uuid/portraits/client-uuid",
  "level": "info"
}
```

### Where to Look for Logs

Operators should monitor the following log locations:

| Log Type | Location | Purpose |
|----------|----------|---------|
| Application Logs | `logs/app.log` | All storage operations |
| Error Logs | `logs/error.log` | Failed uploads, connection errors |
| Storage Audit | `logs/storage_audit.log` | All file operations |
| Monitoring | `/api/monitoring/detailed-metrics` | Real-time storage metrics |

### Monitoring Endpoints

#### Storage Health Check
```http
GET /api/monitoring/metrics
Authorization: Bearer {admin_token}
```

Look for `storage_adapter_status` metric:
```json
{
  "storage_adapter_status": {
    "yandex_disk": {
      "connected": true,
      "last_check": "2025-01-15T10:00:00Z",
      "available_space_gb": 9.0
    }
  }
}
```

## Error Handling

### Common Errors and Solutions

#### OAuth Token Expired
**Error:** `401 Unauthorized from Yandex API`

**Solution:**
1. Refresh OAuth token at [Yandex OAuth](https://oauth.yandex.ru/)
2. Update storage connection configuration
3. Test connection: `GET /storage-config/test-connection/yandex_disk`

#### Insufficient Storage Space
**Error:** `Insufficient space on Yandex Disk`

**Solution:**
1. Check storage info: `GET /storage-config/storage-info/yandex_disk`
2. Clean up old backups or unused files
3. Upgrade Yandex Disk plan if needed

#### Network Timeout
**Error:** `Connection timeout to cloud-api.yandex.net`

**Solution:**
1. Check server internet connectivity
2. Verify firewall rules allow outbound HTTPS to `cloud-api.yandex.net`
3. Check Yandex API status: https://yandex.ru/dev/disk-api/

#### Invalid Path
**Error:** `Path not found: vertex-ar/companies/...`

**Solution:**
1. Verify `base_path` in storage connection configuration
2. Ensure folder structure exists on Yandex Disk
3. Check folder creation logs for errors

## Performance Considerations

### Upload Performance

- **Average Upload Time**: 2-5 seconds for 2MB file
- **Large Files** (>10MB): Use chunked upload (automatic)
- **Concurrent Uploads**: Limited to 5 simultaneous per company

### Caching Strategy

Files served through `/api/yandex-disk/file/` are cached:
```http
Cache-Control: public, max-age=3600
```

### Optimization Tips

1. **Use Previews**: Generate and serve WebP previews for faster loading
2. **Batch Operations**: Group multiple file uploads in single transaction
3. **Local Cache**: Maintain local cache of frequently accessed files
4. **CDN Integration**: Consider CDN for serving Yandex-hosted files

## Security Best Practices

### Token Security

1. **Never Log Tokens**: OAuth tokens are redacted in logs
2. **Encrypted Storage**: Tokens stored encrypted in database
3. **Token Rotation**: Rotate tokens every 90 days
4. **Least Privilege**: Request only required OAuth scopes

### Access Control

1. **Admin-Only**: Only admins can configure storage connections
2. **Company Isolation**: Each company's files isolated by path
3. **Public URLs**: Use proxy endpoints, not direct Yandex links
4. **Audit Trail**: All storage operations logged with user context

## Migration Guide

### Migrating Existing Company to Yandex Disk

```bash
# 1. Create Yandex Disk connection
curl -X POST http://localhost:8000/api/storage-management/connections \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Primary Yandex",
    "type": "yandex_disk",
    "config": {
      "oauth_token": "YOUR_TOKEN",
      "base_path": "vertex-ar"
    }
  }'

# 2. Update company
curl -X PATCH http://localhost:8000/companies/company-uuid \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "storage_type": "yandex_disk",
    "storage_connection_id": "connection-uuid"
  }'

# 3. Migrate existing files (manual script)
python scripts/migrate_company_storage.py \
  --company-id company-uuid \
  --from local \
  --to yandex_disk
```

## Testing

See [test_yandex_disk_storage_flow.py](../../test_files/integration/test_yandex_disk_storage_flow.py) for comprehensive test coverage including:

- Company storage configuration
- Order workflow with Yandex storage
- Fallback to local storage
- Folder-based organization
- Path building logic
- Mock Yandex API responses

## References

- [Yandex Disk API Documentation](https://yandex.ru/dev/disk-api/doc/ru/)
- [Storage Implementation Guide](storage-implementation.md)
- [Remote Storage Setup](../operations/remote-storage-setup.md)
- [Projects and Folders Feature](projects-folders.md)
- [Storage Scaling Guide](storage-scaling.md)

## Changelog

### Version 1.0 (January 2025)
- Initial documentation of Yandex Disk storage flow
- Company-level storage configuration
- Folder-based organization
- OAuth scope requirements
- Path structure documentation
- Error handling guide
- Logging and monitoring guide
