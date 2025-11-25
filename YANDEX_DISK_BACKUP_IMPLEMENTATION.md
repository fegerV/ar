# Yandex Disk Integration and Large Backup Files Implementation

## Overview

This implementation adds comprehensive Yandex Disk storage integration to the Vertex AR admin dashboard, along with advanced backup management features including automatic file splitting for large backups.

## Features Implemented

### 1. Storage Settings Interface (`/admin/settings`)

**Yandex Disk Configuration:**
- OAuth token input field with secure handling
- Test connection functionality with real-time feedback
- Storage quota and usage information display
- Remote directory configuration
- Maximum backup size settings

**Backup Settings:**
- Compression options (gzip, bzip2, xz, none)
- Maximum backup retention count
- Automatic file splitting for large backups
- Test backup creation

### 2. Large Backup Files Handling

**Problem Solved:** Large backup files can cause upload failures, timeouts, and storage issues.

**Solution Implemented:** Automatic file splitting with configurable chunk sizes.

#### How It Works:

1. **Automatic Detection**: The system checks if backup files exceed the configured maximum size (default: 500MB)
2. **Intelligent Splitting**: Large files are automatically split into smaller chunks (default: 100MB per chunk)
3. **Metadata Tracking**: Split files are tracked with metadata for proper reconstruction
4. **Remote Sync**: All chunks are uploaded to remote storage sequentially
5. **Integrity Verification**: Checksums are maintained for each chunk and the complete backup

#### Configuration Options:

```json
{
  "auto_split_backups": true,      // Enable/disable automatic splitting
  "max_backup_size_mb": 500,     // Max size before splitting
  "compression": "gz",             // Compression type
  "max_backups": 7                 // Retention policy
}
```

### 3. API Endpoints

**Settings Management:**
- `GET /admin/settings` - Settings page
- `POST /admin/settings/backup` - Save backup settings
- `GET /admin/settings/backup` - Load backup settings

**Remote Storage:**
- `POST /remote-storage/config` - Update Yandex Disk configuration
- `GET /remote-storage/config` - Get current configuration (without sensitive data)
- `GET /remote-storage/test-connection/yandex_disk` - Test connection
- `GET /remote-storage/storage-info/yandex_disk` - Get storage quota

**Backup Operations:**
- `POST /backups/create` - Create backup (supports test mode)
- Enhanced to handle split files in remote sync operations

### 4. File Splitting Algorithm

**Splitting Logic:**
```python
def _split_large_file(self, file_path: Path, max_size_mb: int = 100) -> List[Path]:
    """
    Split large backup files into manageable chunks.
    
    - Files larger than max_size_mb are split
    - Each chunk is max_size_mb (default 100MB)
    - Chunk naming: filename.part001.ext, filename.part002.ext, etc.
    - Original file is preserved until splitting is complete
    """
```

**Merging Logic:**
```python
def _merge_split_files(self, split_files: List[Path], output_path: Path) -> bool:
    """
    Merge split files back into original format.
    
    - Files are merged in sequential order
    - Integrity is verified with checksums
    - Original file structure is preserved
    """
```

### 5. Best Practices for Large Backup Files

#### Splitting Strategy:
- **100MB chunks**: Optimal balance between upload reliability and number of files
- **Parallel uploads**: Can upload multiple chunks simultaneously (future enhancement)
- **Resume capability**: Failed uploads can be resumed from last successful chunk
- **Compression**: Applied before splitting to minimize total size

#### Storage Considerations:
1. **Yandex Disk Limits**: 
   - Free account: 10GB total, 2GB file size limit
   - Paid accounts: Higher limits available
   - Splitting helps work around file size limits

2. **Network Reliability**:
   - Smaller chunks are more resilient to network interruptions
   - Automatic retry mechanisms for failed chunks
   - Progress tracking for long-running operations

3. **Storage Efficiency**:
   - Compression reduces size before splitting
   - Deduplication at chunk level (future enhancement)
   - Garbage collection of orphaned chunks

### 6. User Interface Features

**Real-time Feedback:**
- Connection status indicators (connected/disconnected/testing)
- Progress bars for upload/download operations
- Storage quota visualization with color-coded warnings
- Error messages with actionable information

**Security Considerations:**
- OAuth tokens are never displayed back in the UI
- Configuration is stored securely
- Test operations use temporary credentials
- Audit logging for all configuration changes

### 7. Implementation Details

**File Structure:**
```
vertex-ar/
├── templates/
│   └── admin_settings.html          # New settings page
├── app/api/
│   └── admin.py                   # Updated with settings routes
├── backup_manager.py                # Enhanced with splitting logic
└── remote_storage.py               # Existing Yandex Disk integration
```

**Database Changes:**
- Settings stored in `app_data/backup_settings.json`
- No database schema changes required
- Backward compatible with existing configurations

**Error Handling:**
- Graceful degradation for non-split files
- Automatic cleanup of failed split operations
- Detailed logging for troubleshooting
- User-friendly error messages

## Usage Instructions

### Setting Up Yandex Disk:

1. **Get OAuth Token**:
   - Visit https://yandex.ru/dev/disk-api/doc/ru/concepts/quickstart
   - Create a new application
   - Generate OAuth token with required permissions

2. **Configure in Admin Panel**:
   - Navigate to `/admin/settings`
   - Enter token in "Yandex Disk OAuth Token" field
   - Click "Тестировать соединение" to verify
   - Configure remote directory and backup size limits

3. **Backup Settings**:
   - Choose compression type (gz recommended)
   - Set maximum backup retention
   - Enable automatic file splitting
   - Test with a sample backup

### Monitoring and Maintenance:

**Storage Information:**
- Real-time quota usage
- Visual indicators for space consumption
- Automatic alerts when approaching limits

**Backup Operations:**
- Monitor split backup progress
- Verify chunk integrity
- Track remote sync status

## Future Enhancements

### Planned Features:

1. **Parallel Chunk Uploads**: Upload multiple chunks simultaneously
2. **Delta Backups**: Only upload changed files
3. **Chunk Deduplication**: Store unique chunks only once
4. **Advanced Compression**: LZMA/ZSTD support for better ratios
5. **Multi-cloud Support**: Simultaneous backup to multiple providers
6. **Backup Scheduling**: Automated backup creation with configurable schedules

### Performance Optimizations:

1. **Streaming Compression**: Compress during backup creation
2. **Memory Management**: Optimize for large file operations
3. **Network Optimization**: Adaptive chunk sizes based on network conditions
4. **Caching**: Local caching of remote storage metadata

## Troubleshooting

### Common Issues:

**Token Authentication Errors**:
- Verify token has correct permissions
- Check token expiration
- Ensure application is properly registered

**Split File Issues**:
- Verify sufficient disk space for temporary files
- Check file permissions on backup directory
- Monitor system logs for error details

**Upload Failures**:
- Test network connectivity
- Verify Yandex Disk quota availability
- Check chunk size configuration

### Recovery Procedures:

**Manual File Merging**:
```bash
# If automatic merging fails, manually merge:
cat backup.part001.tar.gz backup.part002.tar.gz > backup.tar.gz
```

**Configuration Reset**:
```bash
# Reset backup settings to defaults:
rm app_data/backup_settings.json
```

## Conclusion

This implementation provides a robust solution for managing large backup files through intelligent splitting, comprehensive Yandex Disk integration, and user-friendly configuration options. The system maintains backward compatibility while adding advanced features for enterprise-scale backup requirements.

The splitting approach ensures reliable uploads even for multi-gigabyte backups, while the intuitive interface makes configuration accessible to administrators of all technical levels.