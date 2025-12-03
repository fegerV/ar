# Configuration Management

<cite>
**Referenced Files in This Document**   
- [.env.example](file://.env.example)
- [.env.production.example](file://.env.production.example)
- [vertex-ar/config/storage_config.json](file://vertex-ar/config/storage_config.json)
- [vertex-ar/config/remote_storage.example.json](file://vertex-ar/config/remote_storage.example.json)
- [vertex-ar/app/config.py](file://vertex-ar/app/config.py)
- [vertex-ar/storage_config.py](file://vertex-ar/storage_config.py)
- [vertex-ar/app/notification_config.py](file://vertex-ar/app/notification_config.py)
- [vertex-ar/app/email_service.py](file://vertex-ar/app/email_service.py)
- [vertex-ar/storage.py](file://vertex-ar/storage.py)
- [vertex-ar/storage_manager.py](file://vertex-ar/storage_manager.py)
- [vertex-ar/app/database.py](file://vertex-ar/app/database.py)
- [vertex-ar/app/main.py](file://vertex-ar/app/main.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Configuration Hierarchy and Loading Mechanism](#configuration-hierarchy-and-loading-mechanism)
3. [Environment Variables](#environment-variables)
4. [JSON Configuration Files](#json-configuration-files)
5. [Runtime Configuration Loading](#runtime-configuration-loading)
6. [Database Connection Configuration](#database-connection-configuration)
7. [Storage Settings](#storage-settings)
8. [Email Service Configuration](#email-service-configuration)
9. [Feature Toggles and System Settings](#feature-toggles-and-system-settings)
10. [Configuration Validation and Error Handling](#configuration-validation-and-error-handling)
11. [Secure Storage of Sensitive Credentials](#secure-storage-of-sensitive-credentials)
12. [Environment-Specific Configuration](#environment-specific-configuration)
13. [Configuration Management Architecture](#configuration-management-architecture)

## Introduction
The Vertex AR application implements a comprehensive configuration management system that combines environment variables, JSON configuration files, and runtime configuration loading to provide flexibility across different deployment scenarios. The system is designed to support development, staging, and production environments with appropriate security measures, particularly for sensitive credentials like SMTP settings. Configuration is hierarchical, with environment variables taking precedence over default values, and certain settings stored securely in the database with encryption. This documentation details the complete configuration system, including all configurable parameters, their default values, override mechanisms, and best practices for managing configuration across different environments.

**Section sources**
- [.env.example](file://.env.example)
- [.env.production.example](file://.env.production.example)
- [vertex-ar/app/config.py](file://vertex-ar/app/config.py)

## Configuration Hierarchy and Loading Mechanism
The configuration system follows a hierarchical approach where different sources have varying levels of precedence. Environment variables have the highest priority and can override default values and JSON configuration settings. The system loads configuration from multiple sources in a specific order: first, default values are established within the code, then JSON configuration files are loaded (if present), and finally, environment variables are applied to override any previous settings. This allows for flexible configuration management where base settings can be defined in JSON files while environment-specific overrides are handled through environment variables. The Settings class in config.py orchestrates this loading process, reading from environment variables using os.getenv() with default fallback values. For storage configuration, the system first attempts to load from the storage_config.json file, creating a default configuration if the file is not found. This hierarchical approach enables a clear separation between default settings, persistent configuration, and environment-specific overrides.

```mermaid
flowchart TD
Start([Configuration Loading]) --> DefaultValues["Set Default Values in Code"]
DefaultValues --> CheckJSON["Check for JSON Config Files"]
CheckJSON --> JSONExists{"JSON Files Exist?"}
JSONExists --> |Yes| LoadJSON["Load JSON Configuration"]
JSONExists --> |No| UseDefaults["Use Default Values"]
LoadJSON --> LoadEnv["Load Environment Variables"]
UseDefaults --> LoadEnv
LoadEnv --> ApplyOverrides["Apply Environment Variable Overrides"]
ApplyOverrides --> FinalConfig["Final Runtime Configuration"]
FinalConfig --> End([Configuration Ready])
style Start fill:#4CAF50,stroke:#388E3C
style End fill:#4CAF50,stroke:#388E3C
style JSONExists fill:#FFC107,stroke:#FFA000
```

**Diagram sources **
- [vertex-ar/app/config.py](file://vertex-ar/app/config.py#L15-L244)
- [vertex-ar/storage_config.py](file://vertex-ar/storage_config.py#L18-L44)

**Section sources**
- [vertex-ar/app/config.py](file://vertex-ar/app/config.py#L15-L244)
- [vertex-ar/storage_config.py](file://vertex-ar/storage_config.py#L18-L44)

## Environment Variables
Environment variables form the primary mechanism for configuring the Vertex AR application across different deployment environments. The system uses a comprehensive set of environment variables organized into logical groups including application settings, database configuration, storage settings, file upload limits, logging, security, rate limiting, notifications, monitoring, backup schedules, and development settings. The .env.example file provides a complete template with all available variables and their default values, serving as the authoritative reference for configuration options. Critical settings such as DEBUG, SECRET_KEY, DATABASE_URL, STORAGE_TYPE, and BASE_URL can be overridden through environment variables to customize behavior for specific environments. Security-related variables like CORS_ORIGINS and BCRYPT_ROUNDS allow for environment-specific security policies. Notification services are configured through variables like TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SMTP_HOST, and SMTP_PORT. Monitoring and alerting thresholds are controlled by CPU_THRESHOLD, MEMORY_THRESHOLD, and DISK_THRESHOLD. The system is designed to read these variables at startup, with environment variables taking precedence over default values defined in code.

**Section sources**
- [.env.example](file://.env.example)
- [.env.production.example](file://.env.production.example)
- [vertex-ar/app/config.py](file://vertex-ar/app/config.py#L15-L244)

## JSON Configuration Files
The application utilizes JSON configuration files for persistent storage of settings that may change during runtime or require more complex data structures than simple key-value pairs. The primary configuration file is storage_config.json located in the config directory, which defines storage settings for different content types (portraits, videos, previews, nft_markers) and includes backup settings, Yandex Disk configuration, and MinIO settings. This file follows a structured schema with nested objects for different configuration aspects. The system automatically creates a default configuration file if it doesn't exist, using the _get_default_config method in the StorageConfig class. The remote_storage.example.json file provides a template for configuring remote storage providers like Yandex Disk and Google Drive. These JSON files are loaded at application startup and can be modified during runtime through the application's API, with changes persisted back to the file system. The configuration system validates the structure of these files and provides fallback defaults if the files are missing or corrupted, ensuring the application can start even with incomplete configuration.

```mermaid
erDiagram
STORAGE_CONFIG ||--o{ CONTENT_TYPES : contains
STORAGE_CONFIG ||--o{ BACKUP_SETTINGS : contains
STORAGE_CONFIG ||--o{ YANDEX_DISK : contains
STORAGE_CONFIG ||--o{ MINIO : contains
CONTENT_TYPES {
string portraits_storage_type
boolean portraits_yandex_enabled
string portraits_yandex_base_path
string videos_storage_type
boolean videos_yandex_enabled
string videos_yandex_base_path
string previews_storage_type
boolean previews_yandex_enabled
string previews_yandex_base_path
string nft_markers_storage_type
boolean nft_markers_yandex_enabled
string nft_markers_yandex_base_path
}
BACKUP_SETTINGS {
boolean auto_split_backups
integer max_backup_size_mb
integer chunk_size_mb
string compression
}
YANDEX_DISK {
string oauth_token
boolean enabled
}
MINIO {
boolean enabled
string endpoint
string access_key
string secret_key
string bucket
}
STORAGE_CONFIG {
json content_types
json backup_settings
json yandex_disk
json minio
}
```

**Diagram sources **
- [vertex-ar/config/storage_config.json](file://vertex-ar/config/storage_config.json)
- [vertex-ar/storage_config.py](file://vertex-ar/storage_config.py#L58-L107)

**Section sources**
- [vertex-ar/config/storage_config.json](file://vertex-ar/config/storage_config.json)
- [vertex-ar/config/remote_storage.example.json](file://vertex-ar/config/remote_storage.example.json)
- [vertex-ar/storage_config.py](file://vertex-ar/storage_config.py#L18-L203)

## Runtime Configuration Loading
The configuration system implements dynamic loading of settings at runtime, allowing the application to adapt to changing conditions without requiring restarts. The Settings class in config.py loads environment variables during initialization and provides a singleton instance accessible throughout the application. The StorageConfig class monitors the storage configuration file and can reload it when changes are detected. The NotificationConfig class dynamically loads notification settings from the database, checking for updates when requested. This runtime loading is implemented through getter methods that can refresh configuration from their source when needed. For example, the get_smtp_config method in NotificationConfig checks the database for current SMTP settings each time it's called, ensuring that configuration changes made through the admin UI are immediately available. The system also implements caching for frequently accessed configuration to improve performance while maintaining the ability to refresh when needed. This approach balances the need for up-to-date configuration with performance considerations, allowing the application to respond to configuration changes without requiring restarts.

**Section sources**
- [vertex-ar/app/config.py](file://vertex-ar/app/config.py#L15-L244)
- [vertex-ar/app/notification_config.py](file://vertex-ar/app/notification_config.py#L47-L82)
- [vertex-ar/storage_config.py](file://vertex-ar/storage_config.py#L28-L43)

## Database Connection Configuration
Database connections are configured primarily through the DATABASE_URL environment variable, which specifies the database type and connection parameters. The application supports SQLite as the default database, with the path specified relative to the application directory (e.g., sqlite:///./app_data.db). For production deployments, PostgreSQL is recommended, with the connection URL following the format postgresql://user:password@localhost:5432/vertex_ar. The system automatically creates the database directory if it doesn't exist, ensuring the application can start even on a fresh installation. Database configuration is handled by the Database class in database.py, which initializes the connection and creates necessary tables if they don't exist. The configuration system provides sensible defaults while allowing complete customization of the database connection. Connection pooling and other advanced database settings are managed internally by the application, with configuration options exposed through environment variables like UVICORN_WORKERS for controlling the number of database connections in a production environment.

**Section sources**
- [.env.example](file://.env.example)
- [vertex-ar/app/config.py](file://vertex-ar/app/config.py#L32-L36)
- [vertex-ar/app/database.py](file://vertex-ar/app/database.py#L37-L46)

## Storage Settings
Storage configuration is a multi-layered system that supports different storage backends for different content types. The primary storage type is controlled by the STORAGE_TYPE environment variable, which can be set to "local" for file system storage or "minio" for S3-compatible object storage. Local storage uses the STORAGE_PATH environment variable to specify the directory path, defaulting to ./storage relative to the application directory. For MinIO/S3 storage, the system requires configuration of MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET, and MINIO_SECURE. The storage_config.json file provides granular control over storage settings for specific content types (portraits, videos, previews, nft_markers), allowing different storage backends to be used for different types of content. Yandex Disk integration is also supported through OAuth token authentication, with configuration options for base paths and enabling/disabling per content type. The system automatically creates necessary directories and buckets when initializing storage adapters, ensuring the application can start with minimal configuration.

```mermaid
classDiagram
class StorageManager {
+storage_root Path
+config StorageConfig
+adapters Dict[str, StorageAdapter]
+get_adapter(content_type) StorageAdapter
+get_company_adapter(company_id, content_type) StorageAdapter
+reinitialize_adapters()
+save_file(file_data, file_path, content_type) str
+get_file(file_path, content_type) bytes
+delete_file(file_path, content_type) bool
}
class StorageConfig {
+config_path Path
+config Dict[str, Any]
+get_storage_type(content_type) str
+set_storage_type(content_type, storage_type)
+get_yandex_config(content_type) Dict[str, Any]
+set_yandex_config(content_type, enabled, base_path)
+get_backup_settings() Dict[str, Any]
+get_yandex_token() str
+set_yandex_token(token)
+is_yandex_enabled() bool
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
+provision_hierarchy(company_slug, category_slugs, subfolders) Dict[str, Any]
+directory_exists(path) bool
+clear_directory_cache()
}
StorageManager --> StorageConfig : "uses"
StorageManager --> StorageAdapter : "manages"
StorageAdapter <|-- LocalStorageAdapter
StorageAdapter <|-- MinioStorageAdapter
StorageAdapter <|-- YandexDiskStorageAdapter
```

**Diagram sources **
- [vertex-ar/storage_manager.py](file://vertex-ar/storage_manager.py#L19-L582)
- [vertex-ar/storage_config.py](file://vertex-ar/storage_config.py#L15-L203)
- [vertex-ar/app/storage_local.py](file://vertex-ar/app/storage_local.py)
- [vertex-ar/app/storage_minio.py](file://vertex-ar/app/storage_minio.py)
- [vertex-ar/app/storage_yandex.py](file://vertex-ar/app/storage_yandex.py)

**Section sources**
- [.env.example](file://.env.example)
- [vertex-ar/config/storage_config.json](file://vertex-ar/config/storage_config.json)
- [vertex-ar/storage_config.py](file://vertex-ar/storage_config.py#L15-L203)
- [vertex-ar/storage_manager.py](file://vertex-ar/storage_manager.py#L19-L582)

## Email Service Configuration
Email service configuration follows a security-first approach, with sensitive credentials stored securely in the database rather than in environment variables. The system previously supported SMTP configuration through environment variables (SMTP_USERNAME, SMTP_PASSWORD), but this has been deprecated due to security concerns. The .env.example file explicitly warns that these environment variables are deprecated and should not be used in production. Instead, SMTP credentials are configured through the admin UI at /admin/notification-settings, where they are encrypted before being stored in the database. The NotificationConfig class retrieves these encrypted credentials and decrypts them when needed for sending emails. Non-sensitive SMTP settings like SMTP_HOST, SMTP_PORT, and SMTP_USE_TLS are still configured through environment variables. The email service implements retry logic with exponential backoff, configurable through EMAIL_RETRY_MAX_ATTEMPTS and EMAIL_RETRY_DELAYS. Email queue workers are configured through EMAIL_QUEUE_WORKERS. The system validates SMTP configuration at startup and refuses to start in production if credentials are detected in environment variables, preventing accidental exposure of sensitive information.

```mermaid
sequenceDiagram
participant Admin as "Admin UI"
participant DB as "Database"
participant Config as "NotificationConfig"
participant EmailService as "EmailService"
participant SMTP as "SMTP Server"
Admin->>DB : Configure SMTP credentials (encrypted)
DB-->>Admin : Confirmation
Note over Admin,DB : Credentials encrypted in database
EmailService->>Config : get_smtp_config(actor="email_service")
Config->>DB : Retrieve encrypted credentials
DB-->>Config : Encrypted credentials
Config->>Config : Decrypt credentials
Config-->>EmailService : SMTP configuration
EmailService->>SMTP : Send email with credentials
SMTP-->>EmailService : Delivery confirmation
EmailService->>Config : Log access attempt
Note over Config : Security guardrail : Rejects env-based credentials in production
```

**Diagram sources **
- [vertex-ar/app/notification_config.py](file://vertex-ar/app/notification_config.py#L83-L145)
- [vertex-ar/app/email_service.py](file://vertex-ar/app/email_service.py#L370-L415)
- [.env.example](file://.env.example)
- [docs/EMAIL_MIGRATION.md](file://docs/EMAIL_MIGRATION.md)

**Section sources**
- [.env.example](file://.env.example)
- [vertex-ar/app/notification_config.py](file://vertex-ar/app/notification_config.py#L40-L221)
- [vertex-ar/app/email_service.py](file://vertex-ar/app/email_service.py#L16-L627)
- [docs/EMAIL_MIGRATION.md](file://docs/EMAIL_MIGRATION.md)

## Feature Toggles and System Settings
The application implements numerous feature toggles and system settings that control various aspects of functionality and behavior. These are primarily configured through environment variables, allowing operators to enable or disable features without code changes. Key feature toggles include DEBUG (enables debug mode), RATE_LIMIT_ENABLED (controls rate limiting), ALERTING_ENABLED (enables system monitoring and alerting), VIDEO_SCHEDULER_ENABLED (controls video animation scheduler), and LIFECYCLE_SCHEDULER_ENABLED (controls lifecycle scheduler). Backup features are controlled by BACKUP_DATABASE_ENABLED, BACKUP_STORAGE_ENABLED, and BACKUP_FULL_ENABLED. Monitoring features are toggled with ANALYTICS_ENABLED. The system also includes numerous threshold settings that act as feature controls, such as CPU_THRESHOLD, MEMORY_THRESHOLD, and DISK_THRESHOLD for monitoring alerts. File upload limits are controlled by MAX_IMAGE_SIZE_MB, MAX_VIDEO_SIZE_MB, and related variables. NFT marker generation is configured with NFT_FEATURE_DENSITY, NFT_PYRAMID_LEVELS, and NFT_TARGET_DPI. These feature toggles allow for fine-grained control over application behavior, enabling operators to customize the system for their specific needs and constraints.

**Section sources**
- [.env.example](file://.env.example)
- [.env.production.example](file://.env.production.example)
- [vertex-ar/app/config.py](file://vertex-ar/app/config.py#L49-L244)

## Configuration Validation and Error Handling
The configuration system includes comprehensive validation and error handling to ensure the application can start and operate correctly even with incomplete or incorrect configuration. When loading the storage configuration from storage_config.json, the system checks if the file exists and creates a default configuration if it doesn't. If the file exists but cannot be parsed, the system logs an error and falls back to default values. Environment variables are validated with appropriate types (string, integer, float, boolean) using conversion functions like int() and float(), with error handling to prevent crashes if invalid values are provided. The email service configuration includes a critical security check that validates whether SMTP credentials are configured through the secure database storage rather than environment variables, refusing to start in production if credentials are detected in environment variables. The system logs detailed error messages when configuration issues are detected, helping operators diagnose and fix problems. Default values are provided for all configuration options, ensuring the application can start even with minimal configuration. The configuration loading process is designed to be resilient, with multiple fallback mechanisms to prevent startup failures due to configuration issues.

**Section sources**
- [vertex-ar/storage_config.py](file://vertex-ar/storage_config.py#L30-L43)
- [vertex-ar/app/config.py](file://vertex-ar/app/config.py#L15-L244)
- [vertex-ar/app/email_service.py](file://vertex-ar/app/email_service.py#L81-L108)
- [docs/SMTP_SECURITY_ENHANCEMENT_SUMMARY.md](file://docs/SMTP_SECURITY_ENHANCEMENT_SUMMARY.md)

## Secure Storage of Sensitive Credentials
The application implements a robust system for the secure storage of sensitive credentials, particularly for email and storage services. Sensitive credentials like SMTP passwords and Telegram bot tokens are never stored in plain text in environment variables or configuration files. Instead, they are encrypted and stored in the database, with encryption managed by the encryption_manager from app.encryption. The NotificationConfig class handles the decryption of these credentials when they are needed for sending notifications. The system includes a security guardrail that checks for the presence of SMTP credentials in environment variables at startup, logging a critical warning and refusing to start in production if such credentials are detected. This prevents accidental exposure of sensitive information in production environments. The encryption system uses secure cryptographic algorithms to protect credentials at rest. Access to sensitive configuration is logged for audit purposes, with the get_smtp_config method logging access attempts including the actor requesting the configuration. This multi-layered approach to credential security ensures that sensitive information is protected while still allowing necessary functionality.

**Section sources**
- [vertex-ar/app/notification_config.py](file://vertex-ar/app/notification_config.py#L57-L69)
- [vertex-ar/app/email_service.py](file://vertex-ar/app/email_service.py#L81-L108)
- [docs/SMTP_SECURITY_ENHANCEMENT_SUMMARY.md](file://docs/SMTP_SECURITY_ENHANCEMENT_SUMMARY.md)
- [vertex-ar/app/encryption.py](file://vertex-ar/app/encryption.py)

## Environment-Specific Configuration
The application provides templates for environment-specific configuration through example files that demonstrate best practices for different deployment scenarios. The .env.example file serves as a comprehensive template for development environments, with debug mode enabled, CORS set to allow all origins, and detailed error messages shown. The .env.production.example file provides a template for production deployments, with debug mode disabled, specific CORS origins configured, HTTPS enabled for MinIO, and production-appropriate logging settings. These templates guide operators in configuring the application appropriately for different environments, highlighting critical security settings that must be changed before production deployment (such as SECRET_KEY and MINIO credentials). The system supports environment-specific configuration through the ENVIRONMENT variable, which influences behavior such as whether to start with environment-based SMTP credentials (allowed in development but not production). This approach enables consistent configuration management across the development lifecycle while ensuring appropriate security and performance settings for each environment.

**Section sources**
- [.env.example](file://.env.example)
- [.env.production.example](file://.env.production.example)
- [vertex-ar/app/config.py](file://vertex-ar/app/config.py#L104-L107)

## Configuration Management Architecture
The configuration management system is architected as a layered approach that combines multiple configuration sources with appropriate security and flexibility considerations. At the foundation are default values hardcoded in the application, providing sensible defaults that allow the application to run with minimal configuration. On top of this layer are JSON configuration files that provide persistent storage for settings that may change during runtime, particularly storage configuration. The highest layer consists of environment variables, which provide deployment-specific overrides and are the primary mechanism for configuring the application in different environments. Sensitive credentials are stored separately in the database with encryption, accessed through a secure configuration interface. The system uses singleton pattern for configuration objects, ensuring consistent access to configuration throughout the application. Configuration loading is centralized in the Settings and StorageConfig classes, with clear separation of concerns between different aspects of configuration. This architecture provides a balance between flexibility, security, and ease of use, allowing operators to configure the application appropriately for their needs while protecting sensitive information and ensuring reliable operation.

```mermaid
graph TD
A[Default Values in Code] --> B[JSON Configuration Files]
B --> C[Environment Variables]
C --> D[Database with Encrypted Credentials]
D --> E[Runtime Configuration Object]
E --> F[Application Components]
subgraph "Configuration Sources"
A
B
C
D
end
subgraph "Runtime"
E
F
end
style A fill:#E8F5E8,stroke:#4CAF50
style B fill:#E8F5E8,stroke:#4CAF50
style C fill:#E8F5E8,stroke:#4CAF50
style D fill:#E8F5E8,stroke:#4CAF50
style E fill:#BBDEFB,stroke:#2196F3
style F fill:#FFECB3,stroke:#FF9800
click A "vertex-ar/app/config.py" "Default Values"
click B "vertex-ar/config/storage_config.json" "JSON Configuration"
click C ".env.example" "Environment Variables"
click D "vertex-ar/app/database.py" "Encrypted Credentials"
click E "vertex-ar/app/config.py" "Runtime Configuration"
click F "vertex-ar/app/main.py" "Application Components"
```

**Diagram sources **
- [vertex-ar/app/config.py](file://vertex-ar/app/config.py)
- [vertex-ar/storage_config.py](file://vertex-ar/storage_config.py)
- [vertex-ar/app/notification_config.py](file://vertex-ar/app/notification_config.py)
- [vertex-ar/app/main.py](file://vertex-ar/app/main.py)

**Section sources**
- [vertex-ar/app/config.py](file://vertex-ar/app/config.py)
- [vertex-ar/storage_config.py](file://vertex-ar/storage_config.py)
- [vertex-ar/app/notification_config.py](file://vertex-ar/app/notification_config.py)
- [vertex-ar/app/main.py](file://vertex-ar/app/main.py)