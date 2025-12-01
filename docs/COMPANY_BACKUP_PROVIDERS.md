# Company Backup Providers

This document describes the company-specific remote backup provider functionality in Vertex AR.

## Overview

The Company Backup Providers feature allows administrators to assign specific remote storage providers (e.g., Yandex Disk, Google Drive) to individual companies. Each company can have its own backup configuration, enabling:

- **Per-company backup destinations**: Different companies can back up to different remote storage providers
- **Isolated backup management**: Each company's backups are stored in separate remote directories
- **Flexible backup workflows**: Trigger sync and restore operations on a per-company basis
- **Centralized configuration**: Manage all company backup settings from a single interface

## Database Schema

### Companies Table Extensions

Two new nullable columns have been added to the `companies` table:

```sql
ALTER TABLE companies ADD COLUMN backup_provider TEXT;
ALTER TABLE companies ADD COLUMN backup_remote_path TEXT;
```

**Fields:**

- `backup_provider` (TEXT, nullable): Provider name (e.g., `yandex_disk`, `google_drive`, `local`)
- `backup_remote_path` (TEXT, nullable): Remote directory path for storing backups (e.g., `/vertex-ar/company1/backups`)

## API Endpoints

All endpoints require admin authentication.

### List Available Providers

**GET** `/api/remote-storage/providers`

Lists all configured remote storage providers and their connection status.

**Response:**
```json
{
  "success": true,
  "providers": [
    {
      "name": "yandex_disk",
      "connected": true
    },
    {
      "name": "google_drive",
      "connected": false
    }
  ],
  "count": 2
}
```

### Set Company Backup Configuration

**POST** `/api/remote-storage/companies/{company_id}/backup-config`

Assigns a backup provider and remote path to a company.

**Request Body:**
```json
{
  "backup_provider": "yandex_disk",
  "backup_remote_path": "/vertex-ar/company1/backups"
}
```

**Response:**
```json
{
  "company_id": "company-123",
  "company_name": "Acme Corp",
  "backup_provider": "yandex_disk",
  "backup_remote_path": "/vertex-ar/company1/backups"
}
```

**Notes:**
- The provider must be configured and accessible
- Connection test is performed automatically
- Set both fields to `null` to unset backup configuration

### Get Company Backup Configuration

**GET** `/api/remote-storage/companies/{company_id}/backup-config`

Retrieves the backup configuration for a specific company.

**Response:**
```json
{
  "company_id": "company-123",
  "company_name": "Acme Corp",
  "backup_provider": "yandex_disk",
  "backup_remote_path": "/vertex-ar/company1/backups"
}
```

### List All Company Backup Configurations

**GET** `/api/remote-storage/companies/backup-configs`

Lists backup configurations for all companies.

**Response:**
```json
{
  "success": true,
  "companies": [
    {
      "company_id": "company-123",
      "company_name": "Acme Corp",
      "backup_provider": "yandex_disk",
      "backup_remote_path": "/vertex-ar/company1/backups"
    },
    {
      "company_id": "company-456",
      "company_name": "Widget Inc",
      "backup_provider": null,
      "backup_remote_path": null
    }
  ],
  "count": 2
}
```

### Sync Company Backup

**POST** `/api/remote-storage/companies/{company_id}/sync-backup?backup_path={path}`

Syncs a specific backup file to the company's configured remote storage.

**Query Parameters:**
- `backup_path` (required): Local path to the backup file

**Response:**
```json
{
  "success": true,
  "message": "Backup synced to yandex_disk",
  "company_id": "company-123",
  "company_name": "Acme Corp",
  "provider": "yandex_disk",
  "remote_path": "/vertex-ar/company1/backups/backup_20250129.tar.gz",
  "size_mb": 15.42
}
```

**Requirements:**
- Company must have a backup provider configured
- Backup file must exist on local filesystem
- Remote storage provider must be accessible

### Download Company Backup

**POST** `/api/remote-storage/companies/{company_id}/download-backup?remote_filename={filename}`

Downloads a backup from the company's configured remote storage.

**Query Parameters:**
- `remote_filename` (required): Name of the backup file to download

**Response:**
```json
{
  "success": true,
  "message": "Backup downloaded successfully",
  "company_id": "company-123",
  "company_name": "Acme Corp",
  "provider": "yandex_disk",
  "local_path": "/path/to/backups/backup_20250129.tar.gz",
  "backup_type": "full"
}
```

**Requirements:**
- Company must have a backup provider configured
- Remote file must exist
- Remote storage provider must be accessible

## Database Methods

### `create_company()`

Extended to accept optional `backup_provider` and `backup_remote_path` parameters.

```python
database.create_company(
    company_id="company-123",
    name="Acme Corp",
    backup_provider="yandex_disk",
    backup_remote_path="/vertex-ar/company1/backups"
)
```

### `update_company()`

Extended to support updating backup configuration fields.

```python
database.update_company(
    company_id="company-123",
    backup_provider="google_drive",
    backup_remote_path="/new/path"
)
```

### `set_company_backup_config()`

Dedicated method for setting backup configuration.

```python
success = database.set_company_backup_config(
    company_id="company-123",
    backup_provider="yandex_disk",
    backup_remote_path="/vertex-ar/backups"
)
```

### `get_company_backup_config()`

Retrieves only the backup configuration fields.

```python
config = database.get_company_backup_config("company-123")
# Returns: {"backup_provider": "yandex_disk", "backup_remote_path": "/vertex-ar/backups"}
```

## Pydantic Models

### `CompanyBackupConfig`

Request model for setting backup configuration.

```python
class CompanyBackupConfig(BaseModel):
    backup_provider: Optional[str] = None  # yandex_disk, google_drive, local
    backup_remote_path: Optional[str] = None
```

**Validation:**
- `backup_provider` must be one of: `yandex_disk`, `google_drive`, `local` (or `None`)

### `CompanyBackupConfigResponse`

Response model for backup configuration operations.

```python
class CompanyBackupConfigResponse(BaseModel):
    company_id: str
    company_name: str
    backup_provider: Optional[str] = None
    backup_remote_path: Optional[str] = None
```

### Extended Company Models

All company models (`CompanyCreate`, `CompanyResponse`, `CompanyUpdate`, `CompanyListItem`) now include:

```python
backup_provider: Optional[str] = None
backup_remote_path: Optional[str] = None
```

## Usage Examples

### 1. Configure Backup for a New Company

```python
# Create company with backup config
database.create_company(
    company_id="acme-corp",
    name="Acme Corporation",
    backup_provider="yandex_disk",
    backup_remote_path="/vertex-ar/acme/backups"
)
```

### 2. Update Backup Configuration

```bash
# Via API
curl -X POST "http://localhost:8000/api/remote-storage/companies/acme-corp/backup-config" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "backup_provider": "google_drive",
    "backup_remote_path": "/VertexAR/Acme/Backups"
  }'
```

### 3. Sync a Company Backup

```bash
curl -X POST "http://localhost:8000/api/remote-storage/companies/acme-corp/sync-backup?backup_path=/backups/db_20250129.tar.gz" \
  -H "Authorization: Bearer <token>"
```

### 4. Download a Company Backup

```bash
curl -X POST "http://localhost:8000/api/remote-storage/companies/acme-corp/download-backup?remote_filename=db_20250129.tar.gz" \
  -H "Authorization: Bearer <token>"
```

### 5. List All Company Configurations

```bash
curl -X GET "http://localhost:8000/api/remote-storage/companies/backup-configs" \
  -H "Authorization: Bearer <token>"
```

## Integration with Existing Systems

### RemoteStorageManager

The feature reuses the existing `RemoteStorageManager` from `remote_storage.py`:

- Provider configuration is centralized
- Connection testing is automatic
- All existing storage adapters (Yandex Disk, Google Drive) work seamlessly

### BackupManager

Uses the existing `BackupManager` from `backup_manager.py`:

- `sync_to_remote()` method for uploads
- `restore_from_remote()` method for downloads
- Full compatibility with existing backup workflows

## Admin UI Integration

The admin backups interface should be extended to:

1. **Display per-company backup status**
   - Show which provider is assigned to each company
   - Indicate connection status
   - Display last sync time (if tracked)

2. **Provider assignment UI**
   - Dropdown to select available providers
   - Input field for remote path
   - "Test Connection" button
   - "Save" and "Clear" actions

3. **Per-company backup actions**
   - "Sync Now" button for each company
   - "Download" button with remote file selection
   - Status indicators (success, in progress, error)

4. **Bulk operations**
   - "Sync All Companies" to sync all configured backups
   - Filter companies by backup provider
   - Summary statistics (companies with/without backup config)

## Error Handling

### Common Error Scenarios

1. **Provider Not Configured** (400)
   - Attempting to set a provider that doesn't exist in RemoteStorageManager
   - **Solution**: Configure the provider first via admin settings

2. **Provider Connection Failed** (400)
   - Provider configured but not accessible (auth failure, network issue)
   - **Solution**: Check credentials and network connectivity

3. **Company Not Found** (404)
   - Invalid company_id in request
   - **Solution**: Verify company exists

4. **Backup File Not Found** (404)
   - Sync operation with non-existent local file
   - **Solution**: Verify backup file path

5. **No Backup Provider** (400)
   - Attempting sync/download for company without backup config
   - **Solution**: Configure backup provider for the company first

## Best Practices

### 1. Remote Path Naming

Use a consistent naming scheme for remote paths:

```
/vertex-ar/{company_slug}/backups
/vertex-ar/{company_slug}/{backup_type}
```

Example:
- `/vertex-ar/acme-corp/backups`
- `/vertex-ar/widget-inc/database`

### 2. Provider Selection

- **Yandex Disk**: Best for Russian companies, good storage limits
- **Google Drive**: Good for international companies, generous free tier
- **Local**: Testing/development only

### 3. Security

- Always use encrypted credentials for remote storage
- Implement audit logging for all backup operations
- Restrict access to backup endpoints (admin only)

### 4. Monitoring

Track important metrics:
- Last successful sync per company
- Failed sync attempts
- Remote storage usage per company
- Backup file sizes and counts

### 5. Backup Rotation

Consider implementing company-specific retention policies:
- Keep last N backups per company
- Auto-delete backups older than X days
- Separate retention for full vs incremental backups

## Testing

### Unit Tests

Located in `test_files/unit/test_company_backup_config.py`:

- Database column creation
- CRUD operations for backup configuration
- Validation of backup provider values

### Integration Tests

Located in `test_files/integration/test_company_backup_api.py`:

- API endpoint authentication
- Provider listing and validation
- Company backup configuration management
- Sync and download workflows
- Error handling scenarios

Run tests:

```bash
# Unit tests only
pytest test_files/unit/test_company_backup_config.py -v

# Integration tests only
pytest test_files/integration/test_company_backup_api.py -v

# All backup-related tests
pytest test_files/ -k "backup_config" -v
```

## Migration

Existing companies will have `NULL` values for backup fields. No migration is required, but administrators should:

1. Review all companies
2. Assign backup providers where needed
3. Set appropriate remote paths
4. Test sync/restore for each company

## Future Enhancements

Potential improvements:

1. **Automatic Backup Scheduling**: Per-company cron schedules
2. **Backup Verification**: Automatic integrity checks after sync
3. **Multi-Provider Support**: Allow multiple backup destinations per company
4. **Backup Encryption**: Company-specific encryption keys
5. **Restore Testing**: Automated periodic restore tests
6. **Backup Notifications**: Email/Telegram alerts for backup status
7. **Usage Reporting**: Per-company storage usage and cost tracking

## See Also

- [Remote Storage API Documentation](../README.md#remote-storage)
- [Backup Management Guide](../README.md#backup-management)
- [Company Management API](../README.md#companies)
- [Admin Interface Guide](./admin/dashboard-features.md)
