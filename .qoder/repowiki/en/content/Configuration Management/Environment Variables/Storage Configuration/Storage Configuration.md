# Storage Configuration

<cite>
**Referenced Files in This Document**   
- [config.py](file://vertex-ar/app/config.py)
- [storage_config.py](file://vertex-ar/storage_config.py)
- [storage.py](file://vertex-ar/storage.py)
- [storage_local.py](file://vertex-ar/storage_local.py)
- [storage_manager.py](file://vertex-ar/storage_manager.py)
- [storage_config.py](file://vertex-ar/app/api/storage_config.py)
- [storage_management.py](file://vertex-ar/app/api/storage_management.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Storage Configuration Overview](#storage-configuration-overview)
3. [STORAGE_TYPE Configuration](#storage_type-configuration)
4. [Local Storage Configuration](#local-storage-configuration)
5. [MinIO/S3 Storage Configuration](#minio-s3-storage-configuration)
6. [Configuration Loading and Validation](#configuration-loading-and-validation)
7. [Development and Production Examples](#development-and-production-examples)
8. [Common Configuration Issues](#common-configuration-issues)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Performance Optimization](#performance-optimization)

## Introduction

The Vertex AR system provides flexible storage configuration options to accommodate different deployment scenarios and requirements. This documentation details the storage configuration environment variables, focusing on the STORAGE_TYPE setting that allows choosing between local and MinIO/S3 storage backends. The system supports both simple single-backend configurations and complex multi-tenant setups with per-company storage configurations.

The storage system is designed to be extensible, currently supporting local filesystem storage, MinIO/S3-compatible object storage, and Yandex Disk integration. The configuration is managed through environment variables for global settings and JSON configuration files for more complex storage hierarchies and multi-tenant scenarios.

**Section sources**
- [config.py](file://vertex-ar/app/config.py#L65-L70)
- [storage_config.py](file://vertex-ar/storage_config.py#L58-L107)

## Storage Configuration Overview

The Vertex AR storage system is configured through a combination of environment variables and configuration files. The primary configuration mechanism is environment variables defined in the `Settings` class in `config.py`, which are loaded at application startup. These environment variables provide the basic storage configuration that determines the storage backend and its connection parameters.

For more complex scenarios, particularly in multi-tenant deployments, the system uses a JSON-based configuration file (`config/storage_config.json`) that allows different content types (portraits, videos, previews, NFT markers) to use different storage backends. This enables granular control over where different types of assets are stored.

The storage system is managed by the `StorageManager` class, which instantiates appropriate storage adapters based on the configuration. The system supports three storage types: local, MinIO, and Yandex Disk. Each storage type has its own adapter class that implements the common storage interface, allowing the application to interact with different storage backends through a consistent API.

```mermaid
classDiagram
class StorageManager {
+storage_root Path
+config StorageConfig
+adapters Dict[str, StorageAdapter]
+get_adapter(content_type) StorageAdapter
+save_file(file_data, file_path, content_type) str
+get_file(file_path, content_type) bytes
+delete_file(file_path, content_type) bool
+file_exists(file_path, content_type) bool
+get_public_url(file_path, content_type) str
}
class StorageConfig {
+config_path Path
+config Dict[str, Any]
+get_storage_type(content_type) str
+set_storage_type(content_type, storage_type)
+get_minio_config() Dict[str, Any]
+set_minio_config(config)
}
class StorageAdapter {
<<interface>>
+save_file(file_data, file_path) str
+get_file(file_path) bytes
+delete_file(file_path) bool
+file_exists(file_path) bool
+get_public_url(file_path) str
}
class LocalStorageAdapter {
+save_file(file_data, file_path) str
+get_file(file_path) bytes
+delete_file(file_path) bool
+file_exists(file_path) bool
+get_public_url(file_path) str
}
class MinioStorageAdapter {
+save_file(file_data, file_path) str
+get_file(file_path) bytes
+delete_file(file_path) bool
+file_exists(file_path) bool
+get_public_url(file_path) str
}
class YandexDiskStorageAdapter {
+save_file(file_data, file_path) str
+get_file(file_path) bytes
+delete_file(file_path) bool
+file_exists(file_path) bool
+get_public_url(file_path) str
}
StorageManager --> StorageConfig : "uses"
StorageManager --> StorageAdapter : "manages"
StorageAdapter <|-- LocalStorageAdapter
StorageAdapter <|-- MinioStorageAdapter
StorageAdapter <|-- YandexDiskStorageAdapter
```

**Diagram sources**
- [storage_manager.py](file://vertex-ar/storage_manager.py#L19-L582)
- [storage_config.py](file://vertex-ar/storage_config.py#L15-L203)
- [storage.py](file://vertex-ar/app/storage.py)
- [storage_local.py](file://vertex-ar/app/storage_local.py)
- [storage_minio.py](file://vertex-ar/app/storage_minio.py)
- [storage_yandex.py](file://vertex-ar/app/storage_yandex.py)

**Section sources**
- [config.py](file://vertex-ar/app/config.py#L65-L70)
- [storage_config.py](file://vertex-ar/storage_config.py#L58-L107)
- [storage_manager.py](file://vertex-ar/storage_manager.py#L19-L582)

## STORAGE_TYPE Configuration

The `STORAGE_TYPE` environment variable is the primary configuration setting that determines which storage backend the Vertex AR system will use. This variable accepts two main values: `local` for filesystem storage and `minio` for MinIO/S3-compatible object storage.

The `STORAGE_TYPE` setting is defined in the `Settings` class within `config.py` and defaults to `local` if not explicitly set. This default ensures that the application can run out-of-the-box without requiring external storage dependencies, making it ideal for development and testing environments.

When `STORAGE_TYPE` is set to `local`, the system uses the local filesystem for storing all assets. When set to `minio`, the system connects to a MinIO or S3-compatible object storage service using the connection parameters specified in the corresponding environment variables.

The storage type can also be configured on a per-content-type basis through the `storage_config.json` file, allowing different types of assets to be stored in different locations. For example, portraits could be stored locally while videos are stored in MinIO to optimize performance and cost.

```mermaid
flowchart TD
Start([Application Start]) --> CheckStorageType["Check STORAGE_TYPE environment variable"]
CheckStorageType --> |Not Set| UseDefault["Use default: local"]
CheckStorageType --> |Set to local| UseLocal["Use Local Storage Adapter"]
CheckStorageType --> |Set to minio| ValidateMinIO["Validate MinIO Configuration"]
ValidateMinIO --> |Valid| UseMinIO["Use MinIO Storage Adapter"]
ValidateMinIO --> |Invalid| UseDefault
UseDefault --> InitializeStorage["Initialize Storage System"]
UseLocal --> InitializeStorage
UseMinIO --> InitializeStorage
InitializeStorage --> Ready["Application Ready"]
style Start fill:#f9f,stroke:#333
style Ready fill:#bbf,stroke:#333
```

**Diagram sources**
- [config.py](file://vertex-ar/app/config.py#L65)
- [storage_manager.py](file://vertex-ar/storage_manager.py#L50-L93)

**Section sources**
- [config.py](file://vertex-ar/app/config.py#L65)
- [storage_manager.py](file://vertex-ar/storage_manager.py#L50-L93)

## Local Storage Configuration

Local storage configuration in the Vertex AR system is primarily controlled by the `STORAGE_TYPE` environment variable set to `local`. When using local storage, the system stores all assets directly on the server's filesystem in a designated storage directory.

The storage root directory is determined by the `STORAGE_ROOT` setting in the `Settings` class, which defaults to a `storage` directory within the application's base directory. This directory is automatically created if it doesn't exist when the application starts.

For local storage, no additional configuration parameters are required beyond setting `STORAGE_TYPE=local`. The system automatically handles the creation of necessary subdirectories for different content types (portraits, videos, previews, NFT markers) within the storage root.

The local storage adapter (`LocalStorageAdapter`) provides a simple file-based storage mechanism that writes files directly to the filesystem and reads them back when requested. Each file is stored with its original name, and the system generates file:// URLs for accessing the stored assets.

Local storage is recommended for development environments, small-scale deployments, or situations where external storage services are not available or desired. It offers the simplest setup with minimal configuration requirements.

```mermaid
flowchart TB
subgraph "Local Storage Structure"
StorageRoot["Storage Root: /app/storage"]
StorageRoot --> Portraits["portraits/"]
StorageRoot --> Videos["videos/"]
StorageRoot --> Previews["previews/"]
StorageRoot --> NFTMarkers["nft_markers/"]
Portraits --> Portrait1["portrait1.jpg"]
Portraits --> Portrait2["portrait2.png"]
Videos --> Video1["video1.mp4"]
Videos --> Video2["video2.webm"]
Previews --> Preview1["preview1.jpg"]
NFTMarkers --> Marker1["marker1.iset"]
NFTMarkers --> Marker2["marker2.fset"]
end
Application --> |Writes to| StorageRoot
Application --> |Reads from| StorageRoot
style StorageRoot fill:#eef,stroke:#333
style Portraits fill:#eef,stroke:#333
style Videos fill:#eef,stroke:#333
style Previews fill:#eef,stroke:#333
style NFTMarkers fill:#eef,stroke:#333
```

**Diagram sources**
- [storage_local.py](file://vertex-ar/storage_local.py#L14-L92)
- [config.py](file://vertex-ar/app/config.py#L24)
- [storage_manager.py](file://vertex-ar/storage_manager.py#L52-L53)

**Section sources**
- [storage_local.py](file://vertex-ar/storage_local.py#L14-L92)
- [config.py](file://vertex-ar/app/config.py#L24)

## MinIO/S3 Storage Configuration

MinIO/S3 storage configuration in the Vertex AR system is controlled by several environment variables that specify the connection parameters for the object storage service. When `STORAGE_TYPE` is set to `minio`, these variables are used to establish a connection to the MinIO or S3-compatible storage backend.

The key configuration parameters for MinIO/S3 storage are:

- `MINIO_ENDPOINT`: The hostname and port of the MinIO server (e.g., `localhost:9000` or `s3.amazonaws.com`)
- `MINIO_ACCESS_KEY`: The access key for authenticating with the MinIO server
- `MINIO_SECRET_KEY`: The secret key for authenticating with the MinIO server
- `MINIO_BUCKET`: The name of the bucket to use for storing assets
- `MINIO_SECURE`: Whether to use HTTPS/TLS for the connection (true/false)

These environment variables are defined in the `Settings` class in `config.py` and have default values that are suitable for a local MinIO development setup. The `MINIO_ENDPOINT` defaults to `localhost:9000`, with `minioadmin` as both the access and secret key, and `vertex-ar` as the default bucket name.

When the application starts with `STORAGE_TYPE=minio`, it initializes the `MinioStorageAdapter` with these configuration parameters. The adapter automatically checks if the specified bucket exists and creates it if necessary. All asset operations (upload, download, delete) are then performed against this bucket in the MinIO server.

For production deployments, it's recommended to use secure endpoints (HTTPS) and strong, randomly generated access and secret keys. The system handles the connection securely and uses the MinIO Python SDK to interact with the storage backend.

```mermaid
sequenceDiagram
participant App as "Vertex AR Application"
participant Adapter as "MinioStorageAdapter"
participant MinIO as "MinIO Server"
App->>Adapter : save_file(file_data, "portraits/photo.jpg")
activate Adapter
Adapter->>MinIO : put_object("vertex-ar", "portraits/photo.jpg", file_data)
activate MinIO
MinIO-->>Adapter : Success response
deactivate MinIO
Adapter-->>App : Return file URL
deactivate Adapter
App->>Adapter : get_file("portraits/photo.jpg")
activate Adapter
Adapter->>MinIO : get_object("vertex-ar", "portraits/photo.jpg")
activate MinIO
MinIO-->>Adapter : File data
deactivate MinIO
Adapter-->>App : Return file data
deactivate Adapter
App->>Adapter : delete_file("portraits/photo.jpg")
activate Adapter
Adapter->>MinIO : remove_object("vertex-ar", "portraits/photo.jpg")
activate MinIO
MinIO-->>Adapter : Success response
deactivate MinIO
Adapter-->>App : Return success status
deactivate Adapter
Note over App,MinIO : All operations use MinIO's S3-compatible API
```

**Diagram sources**
- [config.py](file://vertex-ar/app/config.py#L66-L70)
- [storage.py](file://vertex-ar/storage.py#L14-L195)
- [storage_manager.py](file://vertex-ar/storage_manager.py#L57-L62)

**Section sources**
- [config.py](file://vertex-ar/app/config.py#L66-L70)
- [storage.py](file://vertex-ar/storage.py#L14-L195)

## Configuration Loading and Validation

The Vertex AR system loads and validates storage configuration through a well-defined process that occurs during application startup. The configuration loading is handled by the `Settings` class in `config.py`, which reads environment variables and applies default values when necessary.

The configuration process begins with the initialization of the `Settings` object, which calls the `load_environment()` method to populate all configuration parameters. For storage-related settings, the system first checks for the presence of environment variables and uses their values if available. If an environment variable is not set, the system applies a sensible default value.

For the storage configuration, the system validates the `STORAGE_TYPE` value to ensure it is either `local` or `minio`. If an invalid value is provided, the system defaults to `local` storage to ensure the application can still start, while logging a warning about the invalid configuration.

The MinIO configuration parameters are validated for completeness when `STORAGE_TYPE` is set to `minio`. While the system will attempt to connect with whatever values are provided (including defaults), it's important to ensure that the endpoint, access key, secret key, and bucket name are correctly configured for the target environment.

The system also supports runtime configuration updates through API endpoints that allow administrators to modify storage settings without restarting the application. When such changes are made, the `StorageManager` reinitializes its adapters to use the new configuration.

```mermaid
flowchart TD
Start([Application Start]) --> InitializeSettings["Initialize Settings Object"]
InitializeSettings --> LoadEnvironment["Call load_environment()"]
LoadEnvironment --> ReadSTORAGE_TYPE["Read STORAGE_TYPE from environment"]
ReadSTORAGE_TYPE --> |Not Set| SetDefaultSTORAGE_TYPE["Set STORAGE_TYPE = local"]
ReadSTORAGE_TYPE --> |Set| ValidateSTORAGE_TYPE["Validate STORAGE_TYPE value"]
ValidateSTORAGE_TYPE --> |Invalid| SetDefaultSTORAGE_TYPE
ValidateSTORAGE_TYPE --> |Valid| Continue
Continue --> ReadMinIOConfig["Read MinIO configuration variables"]
ReadMinIOConfig --> |STORAGE_TYPE=minio| ValidateMinIO["Validate MinIO configuration"]
ReadMinIOConfig --> |STORAGE_TYPE=local| SkipMinIOValidation["Skip MinIO validation"]
ValidateMinIO --> |Incomplete| LogWarning["Log warning about incomplete MinIO config"]
ValidateMinIO --> |Complete| InitializeStorage["Initialize Storage System"]
SkipMinIOValidation --> InitializeStorage
LogWarning --> InitializeStorage
InitializeStorage --> CreateStorageManager["Create StorageManager instance"]
CreateStorageManager --> InitializeAdapters["Initialize storage adapters based on config"]
InitializeAdapters --> ApplicationReady["Application Ready"]
style Start fill:#f9f,stroke:#333
style ApplicationReady fill:#bbf,stroke:#333
```

**Diagram sources**
- [config.py](file://vertex-ar/app/config.py#L15-L244)
- [storage_manager.py](file://vertex-ar/storage_manager.py#L31-L33)
- [storage_config.py](file://vertex-ar/app/api/storage_config.py#L108-L110)

**Section sources**
- [config.py](file://vertex-ar/app/config.py#L15-L244)
- [storage_manager.py](file://vertex-ar/storage_manager.py#L31-L33)

## Development and Production Examples

The Vertex AR system provides different storage configuration examples for development and production environments, reflecting the different requirements and constraints of each deployment scenario.

For development environments, the system is configured to use local storage by default, with minimal configuration required. The `.env.example` file provides a basic configuration that sets `STORAGE_TYPE=local` and uses default values for other settings. This allows developers to quickly start the application without needing to set up external storage services.

```env
# Development Environment (.env)
STORAGE_TYPE=local
BASE_URL=http://localhost:8000
SECRET_KEY=dev-secret-key-change-in-production
```

For production deployments, the configuration typically uses MinIO or S3 storage to ensure data durability, scalability, and high availability. The `.env.production.example` file demonstrates a production-ready configuration with secure settings:

```env
# Production Environment (.env.production)
STORAGE_TYPE=minio
MINIO_ENDPOINT=storage.example.com
MINIO_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
MINIO_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
MINIO_BUCKET=vertex-ar-production
MINIO_SECURE=true
BASE_URL=https://app.vertex-ar.com
SECRET_KEY=a-very-long-random-string-changed-in-production
```

The system also supports hybrid configurations where different content types use different storage backends. This can be configured through the `storage_config.json` file, allowing organizations to optimize their storage strategy based on performance requirements and cost considerations.

For example, a company might choose to store frequently accessed portraits in a high-performance MinIO cluster while archiving older videos in a more cost-effective storage solution. The JSON configuration allows this level of granularity:

```json
{
  "content_types": {
    "portraits": {
      "storage_type": "minio",
      "yandex_disk": {
        "enabled": false,
        "base_path": "vertex-ar/portraits"
      }
    },
    "videos": {
      "storage_type": "local",
      "yandex_disk": {
        "enabled": true,
        "base_path": "vertex-ar/videos"
      }
    }
  }
}
```

**Section sources**
- [config.py](file://vertex-ar/app/config.py#L65-L70)
- [storage_config.py](file://vertex-ar/storage_config.py#L58-L107)
- [.env.example](file://vertex-ar/.env.example)
- [.env.production.example](file://vertex-ar/.env.production.example)

## Common Configuration Issues

Several common configuration issues can arise when setting up storage for the Vertex AR system. Understanding these issues and their solutions can help prevent deployment problems and ensure smooth operation.

One common issue is incorrect MinIO endpoint URLs. The `MINIO_ENDPOINT` should include only the hostname and port (e.g., `localhost:9000` or `storage.example.com:9000`) without the `http://` or `https://` prefix. Including the protocol prefix can cause connection failures. Additionally, when using `MINIO_SECURE=true`, the endpoint should not include the protocol, as the secure flag determines whether to use HTTPS.

Permission problems with secret keys are another frequent issue. The `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` must have the appropriate permissions to read, write, and create buckets in the MinIO server. Insufficient permissions will result in authentication errors or operation failures. It's recommended to create dedicated service accounts with the minimum required permissions for the Vertex AR application.

Bucket access errors can occur when the specified bucket does not exist or the credentials don't have access to it. The system attempts to create the bucket automatically, but this requires the `s3:CreateBucket` permission. If automatic creation fails, the bucket must be created manually through the MinIO console or CLI.

Other common issues include:
- Network connectivity problems between the application server and MinIO server
- Firewall rules blocking the MinIO port (typically 9000)
- DNS resolution issues with the MinIO endpoint hostname
- SSL/TLS certificate validation errors when using secure connections
- Storage quota limits being exceeded on the MinIO server

**Section sources**
- [config.py](file://vertex-ar/app/config.py#L66-L70)
- [storage.py](file://vertex-ar/storage.py#L22-L35)
- [storage_manager.py](file://vertex-ar/storage_manager.py#L57-L62)

## Troubleshooting Guide

When encountering storage connectivity issues in the Vertex AR system, a systematic troubleshooting approach can help identify and resolve the problem quickly.

For connection issues, first verify the basic configuration by checking the `STORAGE_TYPE` environment variable and the corresponding MinIO settings. Ensure that `MINIO_ENDPOINT` is correctly formatted without protocol prefixes and that the port number is correct.

To test connectivity, you can use the storage test API endpoint available in the admin interface. This endpoint attempts to establish a connection to the configured storage backend and reports success or failure with detailed error messages. For MinIO, this test attempts to list buckets to verify authentication and permissions.

If connection tests fail, check network connectivity between the application server and MinIO server using tools like `ping` and `telnet`. For example:
```bash
telnet storage.example.com 9000
```

For authentication issues, verify that the `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` are correct and have the necessary permissions. You can test these credentials using the MinIO client (mc):
```bash
mc alias set myminio http://storage.example.com:9000 ACCESS_KEY SECRET_KEY
mc ls myminio
```

When experiencing bucket access errors, ensure that the bucket specified in `MINIO_BUCKET` exists and that the credentials have appropriate permissions. You can create the bucket manually if automatic creation fails:
```bash
mc mb myminio/vertex-ar-production
```

For performance issues, check the network bandwidth between the application and storage servers, as well as the disk I/O performance of the storage backend. Large file uploads may time out if the network is slow or congested.

Enable detailed logging to capture more information about storage operations. The system logs storage-related activities, including connection attempts, file operations, and error messages, which can provide valuable insights into the root cause of issues.

**Section sources**
- [storage.py](file://vertex-ar/storage.py#L46-L56)
- [storage_manager.py](file://vertex-ar/storage_manager.py#L257-L288)
- [storage_management.py](file://vertex-ar/app/api/storage_management.py#L149-L291)

## Performance Optimization

Optimizing storage performance in the Vertex AR system involves several strategies that depend on the chosen storage backend and deployment scenario.

For local storage, performance optimization focuses on the underlying filesystem and disk I/O. Using fast storage media (SSDs), ensuring adequate free disk space, and configuring appropriate filesystem mount options can significantly improve performance. Regular maintenance tasks like defragmentation (for HDDs) and TRIM (for SSDs) help maintain optimal performance over time.

When using MinIO/S3 storage, network performance becomes a critical factor. Deploying the application server in the same data center or cloud region as the MinIO server minimizes network latency and maximizes bandwidth. Using dedicated network connections or VLANs can further improve performance and reliability.

For high-throughput scenarios, consider the following optimizations:
- Enable `MINIO_SECURE=false` for internal network connections to reduce TLS overhead
- Use larger multipart upload thresholds for big files to reduce the number of requests
- Implement client-side caching for frequently accessed assets
- Use connection pooling to reuse established connections
- Enable compression for text-based assets when appropriate

The system's architecture supports horizontal scaling by allowing different content types to use different storage backends. For example, frequently accessed portraits could be stored in a high-performance MinIO cluster, while less frequently accessed videos could be stored in a more cost-effective solution.

Monitoring storage performance metrics such as request latency, throughput, and error rates can help identify bottlenecks and guide optimization efforts. The system provides monitoring endpoints that expose storage-related metrics for integration with monitoring tools.

**Section sources**
- [config.py](file://vertex-ar/app/config.py#L210-L221)
- [storage_manager.py](file://vertex-ar/storage_manager.py#L74-L85)
- [storage.py](file://vertex-ar/storage.py#L66-L75)