# Storage Connections UX Improvement - User Guide

## Overview

The storage connections management system has been improved to enforce a prerequisite-based workflow where administrators **first register storage connections**, then **bind companies to those connections**.

## Key Features

### 1. Encrypted Credential Storage
- All sensitive fields (OAuth tokens, access keys, secret keys) are **automatically encrypted** before being stored in the database
- Credentials are **masked** when displayed in the UI (e.g., `***token-suffix`)
- Full credentials are only decrypted when needed for testing or actual storage operations
- Uses AES-256 encryption via `app.encryption.EncryptionManager`

### 2. Storage Connection Registration Workflow

#### Step 1: Register a Storage Connection
Navigate to **Admin → Хранилища (Storage)** and click "Добавить хранилище" (Add Storage):

**For Yandex Disk:**
- **Name**: Descriptive name for the connection (e.g., "Main Yandex Storage")
- **Type**: Select "Яндекс Диск"
- **OAuth Token**: Paste your Yandex Disk OAuth token (required, will be encrypted)
- **Base Path**: Optional root folder path (default: `vertex-ar`)

**For MinIO / S3:**
- **Name**: Descriptive name (e.g., "Production MinIO")
- **Type**: Select "MinIO / S3-совместимое"
- **Endpoint**: Server address and port (e.g., `minio.example.com:9000`)
- **Access Key**: MinIO access key (required, will be encrypted)
- **Secret Key**: MinIO secret key (required, will be encrypted)
- **Bucket**: Bucket name (required, e.g., `vertex-ar`)
- **Use HTTPS**: Check if using SSL/TLS

After filling out the form, click **"Тест" (Test)** to verify the connection works, then click **"Сохранить" (Save)**.

#### Step 2: Verify Connection Health
In the storage connections table, check the **"Здоровье" (Health)** column:
- ✓ **Здоров** (Healthy): Connection is active and tested - ready to use
- ⚠ **Не тестировано** (Not Tested): Connection needs testing
- ⏸ **Неактивно** (Inactive): Connection is disabled

**Important:** Only connections with ✓ **Здоров** status can be assigned to companies.

#### Step 3: Bind Company to Connection
Navigate to **Admin → Компании (Companies)** and create/edit a company:

1. **Choose Storage Type**: Select from the dropdown:
   - 💻 Локальное хранилище (Local Storage)
   - 📁 Локальный диск (Local Disk)
   - ☁️ MinIO / S3
   - 📦 Яндекс.Диск

2. **Select Tested Connection** (for remote storage types only):
   - The dropdown will show only **active, tested connections** with ✓ indicator
   - Format: `✓ Connection Name (Storage Type)`
   - If no connections appear, register one in the Storage section first

3. **Choose Folder** (required for Yandex Disk, optional for others):
   - Click "📁 Выбрать папку" to browse available folders
   - Or enter a folder path manually for local storage

4. **Save** the company configuration

### 3. Validation Rules

The system enforces the following validation:

**Backend (API Level):**
- `StorageConnectionCreate`: Validates required fields based on storage type
  - Yandex Disk: Must have `oauth_token`
  - MinIO: Must have `endpoint`, `access_key`, `secret_key`, `bucket`
- `CompanyCreate/Update`: Validates storage configuration
  - Remote storage types (`minio`, `yandex_disk`) **must** have `storage_connection_id`
  - Yandex Disk companies **must** have `yandex_disk_folder_id` (folder path)

**Frontend (UI Level):**
- Storage type selection shows contextual help text explaining requirements
- Connection dropdown only shows healthy (tested + active) connections
- Folder field shows required indicator (*) for Yandex Disk
- Clear error messages guide users through the prerequisite workflow

### 4. Special Cases

**Vertex AR Default Company:**
- The default "Vertex AR" company is locked to local disk storage
- Cannot be deleted or have its storage type changed
- Always uses local `portraits` folder

**Existing Companies:**
- Companies created before this update continue working without changes
- Can be edited to use new storage connections if needed

## API Endpoints

### Storage Connections

```http
GET    /storages                    # List connections (masked credentials)
POST   /storages                    # Create connection (encrypts credentials)
GET    /storages/{id}               # Get connection details (masked)
PUT    /storages/{id}               # Update connection (encrypts new credentials)
DELETE /storages/{id}               # Delete connection
POST   /storages/test               # Test connection (decrypts for testing)
GET    /storage-options             # Available storage options for companies
```

### Company Management

```http
GET    /api/companies               # List companies with storage info
POST   /api/companies               # Create company (validates storage requirements)
PUT    /api/companies/{id}          # Update company (validates storage requirements)
DELETE /api/companies/{id}          # Delete company
```

## Security Considerations

1. **Encryption at Rest**: All secrets encrypted using PBKDF2-derived AES-256 key
2. **Masked Display**: Credentials never shown in full in API responses or UI
3. **Secure Testing**: Connection tests use decrypted credentials but don't expose them in responses
4. **Audit Logging**: All storage connection changes are logged with username and timestamp

## Troubleshooting

### Problem: "No tested connections available" in company form
**Solution**: 
1. Go to Admin → Хранилища
2. Create a new storage connection
3. Click "Тест" button to verify it works
4. Return to Companies page - connection should now appear

### Problem: Connection test fails
**Solution**:
- **Yandex Disk**: Verify OAuth token is valid (get new token from https://yandex.ru/dev/disk/poligon/)
- **MinIO**: Check endpoint is reachable, access key and secret key are correct, and bucket exists

### Problem: "storage_connection_id required" error when creating company
**Solution**: You selected a remote storage type (MinIO/Yandex Disk) but didn't select a connection. Either:
- Select an existing tested connection from the dropdown
- Or change storage type to Local/Local Disk

### Problem: "yandex_disk_folder_id required" error
**Solution**: Yandex Disk companies must have a folder configured. Click "📁 Выбрать папку" and select or create a folder.

## Migration Notes

- **Backward Compatible**: Existing companies without `storage_connection_id` continue working
- **No Data Migration Needed**: New validation only applies to new/updated companies
- **Existing Connections**: If you have old storage connections with plaintext credentials, they will be re-encrypted on next update

## Files Modified

**Backend:**
- `vertex-ar/app/models.py`: Enhanced validation for `StorageConnectionCreate/Update` and `CompanyCreate/Update`
- `vertex-ar/app/api/storage_management.py`: Added encryption/decryption/masking helpers, updated all endpoints
- `vertex-ar/app/encryption.py`: Existing encryption utilities (no changes needed)

**Frontend:**
- `vertex-ar/templates/admin_storage.html`: Enhanced form with help text and field descriptions
- `vertex-ar/templates/admin_companies.html`: Updated company modal with dynamic help text and connection selector
- `vertex-ar/static/js/admin-companies.js`: Improved flow logic, connection filtering, validation messages

**Documentation:**
- `STORAGE_CONNECTIONS_UX_GUIDE.md`: This guide

## Related Documentation

- [Company Backup Providers](docs/COMPANY_BACKUP_PROVIDERS.md)
- [Yandex Disk Storage Optimization](docs/YANDEX_STORAGE_OPTIMIZATION.md)
- [Companies API Enhanced](COMPANIES_API_ENHANCED.md)
