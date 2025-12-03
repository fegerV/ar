# Local Storage Configuration

<cite>
**Referenced Files in This Document**   
- [.env.example](file://.env.example)
- [app/config.py](file://vertex-ar/app/config.py)
- [storage_local.py](file://vertex-ar/storage_local.py)
- [storage_adapter.py](file://vertex-ar/storage_adapter.py)
- [storage_manager.py](file://vertex-ar/storage_manager.py)
- [storage_config.py](file://vertex-ar/storage_config.py)
- [backup_manager.py](file://vertex-ar/backup_manager.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Storage Type Configuration](#storage-type-configuration)
3. [Storage Root Path](#storage-root-path)
4. [Directory Creation and Management](#directory-creation-and-management)
5. [Configuration Parameters](#configuration-parameters)
6. [Integration Points](#integration-points)
7. [Common Issues and Troubleshooting](#common-issues-and-troubleshooting)
8. [Performance Optimization](#performance-optimization)
9. [Configuration Examples](#configuration-examples)
10. [Conclusion](#conclusion)

## Introduction
The Vertex AR system provides flexible storage configuration options, with local storage as the default backend. This documentation details the configuration of local storage, including environment variables, path management, directory creation, and integration with various system components. The local storage backend is designed for simplicity and reliability, making it ideal for development, testing, and production environments where cloud storage is not required.

## Storage Type Configuration
The storage backend for the Vertex AR system is configured through the `STORAGE_TYPE` environment variable. This variable determines which storage backend the system will use for file operations.

The valid value for activating the local storage backend is `local`. When `STORAGE_TYPE=local` is set in the environment, the system uses the local filesystem for storing and retrieving files. This is the default configuration in the `.env.example` file and is recommended for most deployment scenarios.

```mermaid
flowchart TD
A["STORAGE_TYPE Environment Variable"] --> B{"Value Check"}
B --> |local| C["Initialize LocalStorageAdapter"]
B --> |minio| D["Initialize MinIOStorageAdapter"]
B --> |yandex_disk| E["Initialize YandexDiskStorageAdapter"]
B --> |Other/Invalid| F["Default to LocalStorageAdapter"]
C --> G["Use Local Filesystem for Storage Operations"]
D --> H["Use MinIO S3-Compatible Storage"]
E --> I["Use Yandex Disk Cloud Storage"]
F --> G
```

**Diagram sources**
- [app/config.py](file://vertex-ar/app/config.py#L65)
- [storage_adapter.py](file://vertex-ar/storage_adapter.py#L264-L274)

**Section sources**
- [.env.example](file://.env.example#L42-L43)
- [app/config.py](file://vertex-ar/app/config.py#L65)

## Storage Root Path
The storage root path is derived from the `BASE_DIR` of the application and is configured as `STORAGE_ROOT` in the system settings. By default, the storage root is set to a `storage` directory within the application directory.

The `STORAGE_ROOT` is initialized in the `Settings` class within `app/config.py` using the following code:
```python
self.STORAGE_ROOT = self.BASE_DIR / "storage"
```

This creates a storage directory relative to the application's base directory. The default location is `./storage` within the application directory, which is created automatically when the application starts if it doesn't already exist.

```mermaid
graph TD
A["Application Directory"] --> B["BASE_DIR"]
B --> C["STORAGE_ROOT"]
C --> D["./storage"]
D --> E["portraits/"]
D --> F["videos/"]
D --> G["previews/"]
D --> H["nft-markers/"]
```

**Diagram sources**
- [app/config.py](file://vertex-ar/app/config.py#L24)
- [storage_manager.py](file://vertex-ar/storage_manager.py#L29)

**Section sources**
- [app/config.py](file://vertex-ar/app/config.py#L24)
- [storage_manager.py](file://vertex-ar/storage_manager.py#L29)

## Directory Creation and Management
The system ensures directory creation through the `mkdir(parents=True, exist_ok=True)` method in the `Settings` class. This approach guarantees that the storage directory and its parent directories are created if they don't exist, and no error is raised if the directory already exists.

In the `Settings` class initialization, the following code ensures the storage directory is created:
```python
self.STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
```

The `parents=True` parameter ensures that all parent directories are created if necessary, while `exist_ok=True` prevents raising an error if the directory already exists. This robust approach handles various deployment scenarios, including fresh installations and existing deployments.

The `LocalStorageAdapter` class also implements similar directory creation logic when uploading files, ensuring that subdirectories are created as needed:
```python
file_path.parent.mkdir(parents=True, exist_ok=True)
```

This ensures that when a file is uploaded to a specific path, all necessary subdirectories are created automatically.

```mermaid
flowchart TD
A["Application Start"] --> B["Initialize Settings Class"]
B --> C["Check STORAGE_ROOT Directory"]
C --> D{"Directory Exists?"}
D --> |No| E["Create Directory with mkdir()"]
D --> |Yes| F["Proceed with Existing Directory"]
E --> G["Set permissions and ownership"]
G --> H["Directory Ready for Use"]
F --> H
H --> I["Handle File Operations"]
I --> J["Upload File"]
J --> K{"Subdirectories in Path?"}
K --> |Yes| L["Create Subdirectories with mkdir()"]
K --> |No| M["Write File Directly"]
L --> N["Write File to Final Location"]
M --> N
```

**Diagram sources**
- [app/config.py](file://vertex-ar/app/config.py#L238)
- [storage_adapter.py](file://vertex-ar/storage_adapter.py#L63)

**Section sources**
- [app/config.py](file://vertex-ar/app/config.py#L238)
- [storage_adapter.py](file://vertex-ar/storage_adapter.py#L63)

## Configuration Parameters
The local storage configuration includes several parameters that affect file operations, disk usage, and system performance.

### File Permissions
File permissions for local storage are managed by the operating system and the user running the application. The system does not explicitly set file permissions, relying on the default permissions of the directory and the user's umask settings. It's recommended to ensure the application user has read and write permissions to the storage directory.

### Disk Space Requirements
The disk space requirements for local storage depend on the expected volume of content. The system stores various types of files including portraits, videos, previews, and NFT markers. For production deployments, it's recommended to have sufficient disk space to accommodate:
- User-uploaded portraits and videos
- Generated previews and thumbnails
- NFT marker files
- Database backups
- System logs

A minimum of 50GB is recommended for small deployments, with larger deployments requiring proportionally more storage based on expected content volume.

### High-I/O Operations
The system is designed to handle high-I/O operations efficiently. When using local storage, file operations are performed synchronously, which can impact performance under heavy load. To mitigate this, the system implements caching for frequently accessed files and uses efficient file handling patterns.

The `backup_manager.py` file shows that the system handles large file operations with consideration for performance:
```python
# Create backup directory if it doesn't exist
self.backup_dir.mkdir(parents=True, exist_ok=True)
```

This pattern is consistent across the codebase, ensuring reliable directory creation for various storage operations.

**Section sources**
- [app/config.py](file://vertex-ar/app/config.py)
- [backup_manager.py](file://vertex-ar/backup_manager.py#L49)

## Integration Points
The local storage system integrates with several key components of the Vertex AR application, including upload endpoints, preview generation, and backup systems.

### Upload Endpoints
The upload endpoints use the storage manager to save files to the appropriate storage backend. When `STORAGE_TYPE=local`, files are saved directly to the local filesystem. The `StorageManager` class routes file operations to the appropriate adapter based on the content type.

```mermaid
sequenceDiagram
participant Client as "Client Application"
participant API as "Upload API Endpoint"
participant Manager as "StorageManager"
participant Adapter as "LocalStorageAdapter"
participant FileSystem as "Local Filesystem"
Client->>API : POST /upload (file data)
API->>Manager : save_file(file_data, file_path, content_type)
Manager->>Manager : get_adapter(content_type)
Manager->>Adapter : save_file(file_data, file_path)
Adapter->>Adapter : Create subdirectories if needed
Adapter->>FileSystem : Write file to storage path
FileSystem-->>Adapter : Confirmation
Adapter-->>Manager : File URL
Manager-->>API : Success response with file URL
API-->>Client : 200 OK with file URL
```

**Diagram sources**
- [storage_manager.py](file://vertex-ar/storage_manager.py#L110-L122)
- [storage_adapter.py](file://vertex-ar/storage_adapter.py#L66-L78)

### Preview Generation
Preview generation relies on the local storage paths to access source files and save generated previews. The preview generator reads the original media files from the storage directory and saves the generated previews in the appropriate subdirectory.

### Backup Systems
The backup system uses the local storage paths as the source for creating backups. The `backup_manager.py` file shows that the system creates compressed archives of the storage directory:

```python
# Create compressed tar archive
compression_mode = f"w:{compression}" if compression else "w"
with tarfile.open(backup_path, compression_mode) as tar:
    tar.add(self.storage_path, arcname="storage")
```

This ensures that all files in the storage directory are included in the backup, maintaining the directory structure for restoration.

**Section sources**
- [storage_manager.py](file://vertex-ar/storage_manager.py#L110-L122)
- [backup_manager.py](file://vertex-ar/backup_manager.py#L307-L309)

## Common Issues and Troubleshooting
Several common issues can occur with local storage configuration, along with their troubleshooting steps.

### Insufficient Disk Space
When disk space is insufficient, the system may fail to save files or create backups. Symptoms include:
- File upload failures
- Backup creation failures
- System performance degradation

**Troubleshooting steps:**
1. Check available disk space using system tools (df on Linux, disk management on Windows)
2. Clean up old backups and unused files
3. Consider moving to a larger disk or implementing a storage rotation policy
4. Monitor disk usage regularly using the system's monitoring features

### Permission Denied Errors
Permission denied errors occur when the application lacks the necessary permissions to read from or write to the storage directory.

**Troubleshooting steps:**
1. Verify the application user has read and write permissions to the storage directory
2. Check directory ownership and modify if necessary
3. Ensure the directory permissions allow the application user to access the files
4. On Unix-like systems, use chmod and chown commands to set appropriate permissions

### Cross-Platform Path Compatibility
Cross-platform path compatibility issues can arise when deploying on different operating systems.

**Troubleshooting steps:**
1. Use the `Path` class from the `pathlib` module for path operations
2. Avoid hardcoded path separators; use `os.path.join()` or Path operations
3. Test the application on the target platform before deployment
4. Use relative paths when possible to improve portability

**Section sources**
- [storage_adapter.py](file://vertex-ar/storage_adapter.py)
- [app/config.py](file://vertex-ar/app/config.py)

## Performance Optimization
Several performance optimization techniques can be applied when using local storage.

### SSD Storage
Using SSD storage instead of traditional HDDs can significantly improve performance, especially for high-I/O operations. SSDs provide faster read and write speeds, reducing latency for file operations.

### Filesystem Selection
The choice of filesystem can impact performance. For Linux systems, ext4 or XFS are recommended for their reliability and performance. On Windows, NTFS is the preferred choice. Consider the following when selecting a filesystem:
- Journaling capabilities for data integrity
- Performance characteristics for the expected workload
- Support for large files and directories
- Compatibility with the operating system

### Directory Structure Optimization
Organizing files in a logical directory structure can improve performance. The system already implements a structured approach with separate directories for different content types (portraits, videos, previews, nft-markers). This helps prevent directory bloat and improves file lookup times.

### Caching Strategies
Implementing caching strategies can reduce disk I/O. The system uses caching for frequently accessed files, but additional caching layers can be added at the application or infrastructure level for improved performance.

**Section sources**
- [app/config.py](file://vertex-ar/app/config.py)
- [storage_manager.py](file://vertex-ar/storage_manager.py)

## Configuration Examples
The following examples show proper local storage setup in `.env` files.

### Basic Local Storage Configuration
```env
# Vertex AR - Environment Variables
DEBUG=True
SECRET_KEY=your-secret-key-here
APP_HOST=0.0.0.0
APP_PORT=8000
BASE_URL=http://localhost:8000

# Storage Settings
STORAGE_TYPE=local
STORAGE_PATH=./storage

# Database Settings
DATABASE_URL=sqlite:///./app_data.db
```

### Production Local Storage Configuration
```env
# Vertex AR - Production Environment Variables
DEBUG=False
SECRET_KEY=your-strong-production-secret-key
APP_HOST=0.0.0.0
APP_PORT=8000
BASE_URL=https://yourdomain.com

# Storage Settings
STORAGE_TYPE=local
STORAGE_PATH=/var/lib/vertex-ar/storage

# Database Settings
DATABASE_URL=postgresql://user:password@localhost:5432/vertex_ar

# Security Settings
CORS_ORIGINS=https://yourdomain.com
RATE_LIMIT_ENABLED=True
```

**Section sources**
- [.env.example](file://.env.example)

## Conclusion
The local storage configuration in the Vertex AR system provides a reliable and straightforward backend for file storage. By setting `STORAGE_TYPE=local` in the environment variables, the system uses the local filesystem for all storage operations. The `STORAGE_ROOT` is derived from the application's base directory and defaults to `./storage`, with automatic directory creation ensuring the storage path is always available.

The system handles file operations efficiently, with proper error handling and performance considerations. Integration with upload endpoints, preview generation, and backup systems is seamless, making local storage a viable option for various deployment scenarios. By following the configuration examples and troubleshooting guidelines, administrators can ensure a robust local storage setup that meets their requirements.

For optimal performance, consider using SSD storage and appropriate filesystems, while monitoring disk usage and implementing backup rotation policies to manage storage space effectively.