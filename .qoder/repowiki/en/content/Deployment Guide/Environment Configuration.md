# Environment Configuration

<cite>
**Referenced Files in This Document**   
- [.env.example](file://.env.example)
- [.env.production.example](file://.env.production.example)
- [vertex-ar/config/storage_config.json](file://vertex-ar/config/storage_config.json)
- [vertex-ar/config/remote_storage.example.json](file://vertex-ar/config/remote_storage.example.json)
- [vertex-ar/app/config.py](file://vertex-ar/app/config.py)
- [vertex-ar/storage_config.py](file://vertex-ar/storage_config.py)
- [vertex-ar/app/email_service.py](file://vertex-ar/app/email_service.py)
- [vertex-ar/app/notification_config.py](file://vertex-ar/app/notification_config.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Core Configuration Files](#core-configuration-files)
3. [Critical Environment Variables](#critical-environment-variables)
4. [Configuration Loading and Validation](#configuration-loading-and-validation)
5. [Development vs Production Configurations](#development-vs-production-configurations)
6. [Securing Sensitive Data](#securing-sensitive-data)
7. [Managing Multiple Environments](#managing-multiple-environments)
8. [Configuration Validation](#configuration-validation)
9. [Storage Configuration System](#storage-configuration-system)
10. [Email Service Configuration](#email-service-configuration)

## Introduction
The AR application uses a comprehensive environment configuration system that combines environment variables with JSON configuration files to manage settings across different environments. The system is designed to provide flexibility for development while ensuring security and reliability in production. Configuration is managed through `.env` files for environment-specific settings and JSON files for complex storage configurations. The application implements robust validation and security measures, particularly for sensitive data like database credentials and email service configurations.

## Core Configuration Files
The application utilizes several key configuration files to manage settings across different environments and use cases. These files serve as templates that should be copied and customized for specific deployments.

```mermaid
flowchart TD
A[".env.example"] --> B["Development Configuration"]
C[".env.production.example"] --> D["Production Configuration"]
E["storage_config.json"] --> F["Storage Configuration"]
G["remote_storage.example.json"] --> H["Remote Storage Template"]
```

**Diagram sources**
- [.env.example](file://.env.example)
- [.env.production.example](file://.env.production.example)
- [vertex-ar/config/storage_config.json](file://vertex-ar/config/storage_config.json)
- [vertex-ar/config/remote_storage.example.json](file://vertex-ar/config/remote_storage.example.json)

**Section sources**
- [.env.example](file://.env.example)
- [.env.production.example](file://.env.production.example)
- [vertex-ar/config/storage_config.json](file://vertex-ar/config/storage_config.json)
- [vertex-ar/config/remote_storage.example.json](file://vertex-ar/config/remote_storage.example.json)

## Critical Environment Variables
The application relies on numerous environment variables grouped into logical categories for different aspects of the system.

### Application Settings
The core application settings define basic behavior and connectivity:

- **DEBUG**: Enables debug mode (set to `False` in production)
- **SECRET_KEY**: Secret key for JWT tokens (must be a secure random key in production)
- **APP_HOST**: Application host (typically `0.0.0.0`)
- **APP_PORT**: Application port (typically `8000`)
- **BASE_URL**: Base URL for generating AR URLs and QR codes
- **INTERNAL_HEALTH_URL**: Internal health check URL (optional, for monitoring)

### Database Configuration
Database settings determine how the application connects to its data store:

- **DATABASE_URL**: Database connection URL (supports SQLite and PostgreSQL)
- **SQLite**: `sqlite:///./app_data.db` (default for development)
- **PostgreSQL**: `postgresql://user:password@localhost:5432/vertex_ar` (recommended for production)

### Storage Settings
Storage configuration controls where media files are stored:

- **STORAGE_TYPE**: Storage type (`local` or `minio`)
- **STORAGE_PATH**: Local storage path (relative to application directory)
- **MINIO_ENDPOINT**: MinIO endpoint (without http://)
- **MINIO_ACCESS_KEY**: MinIO access key
- **MINIO_SECRET_KEY**: MinIO secret key
- **MINIO_BUCKET**: MinIO bucket name
- **MINIO_SECURE**: Use secure connection (HTTPS)
- **MINIO_PUBLIC_URL**: Public URL for accessing files (optional)

### Security and Authentication
Security-related variables control access and authentication:

- **CORS_ORIGINS**: CORS allowed origins (comma-separated)
- **TOKEN_EXPIRATION_HOURS**: Token expiration time in hours
- **BCRYPT_ROUNDS**: Bcrypt password hashing rounds
- **DEFAULT_ADMIN_USERNAME**: Default admin username
- **DEFAULT_ADMIN_PASSWORD**: Default admin password
- **DEFAULT_ADMIN_EMAIL**: Default admin email

### Email Service Configuration
Email settings configure notification delivery:

- **SMTP_HOST**: SMTP server host
- **SMTP_PORT**: SMTP server port
- **SMTP_USE_TLS**: Use TLS for SMTP connection
- **EMAIL_FROM**: Default sender email address
- **ADMIN_EMAILS**: Admin notification emails (comma-separated)
- **EMAIL_RETRY_MAX_ATTEMPTS**: Maximum number of send attempts
- **EMAIL_RETRY_DELAYS**: Retry delays in seconds (comma-separated)

### Monitoring and Alerting
System monitoring variables control alert thresholds and behavior:

- **ALERTING_ENABLED**: Enable system monitoring and alerting
- **CPU_THRESHOLD**: CPU usage threshold (percentage)
- **MEMORY_THRESHOLD**: Memory usage threshold (percentage)
- **DISK_THRESHOLD**: Disk usage threshold (percentage)
- **HEALTH_CHECK_INTERVAL**: Health check interval in seconds
- **SENTRY_DSN**: Sentry DSN for error tracking
- **GA_TRACKING_ID**: Google Analytics ID

### Backup and Scheduling
Backup configuration controls automated backup operations:

- **BACKUP_DATABASE_ENABLED**: Enable database backup schedule
- **BACKUP_DATABASE_SCHEDULE**: Database backup schedule (cron format)
- **BACKUP_STORAGE_ENABLED**: Enable storage backup schedule
- **BACKUP_STORAGE_SCHEDULE**: Storage backup schedule
- **BACKUP_FULL_ENABLED**: Enable full backup schedule
- **BACKUP_FULL_SCHEDULE**: Full backup schedule
- **BACKUP_ROTATION_ENABLED**: Enable backup rotation schedule
- **BACKUP_ROTATION_SCHEDULE**: Backup rotation schedule
- **MAX_BACKUPS**: Maximum number of backups to keep

**Section sources**
- [.env.example](file://.env.example)
- [.env.production.example](file://.env.production.example)

## Configuration Loading and Validation
The application loads and validates configuration through a well-defined process that ensures settings are properly initialized and secure.

### Configuration Loading Process
The configuration system follows a hierarchical approach to load settings from multiple sources:

```mermaid
flowchart TD
A["Application Startup"] --> B["Load Environment Variables"]
B --> C["Initialize Settings Object"]
C --> D["Validate Required Variables"]
D --> E["Check Security Constraints"]
E --> F["Initialize Storage Configuration"]
F --> G["Load JSON Configuration Files"]
G --> H["Final Configuration Validation"]
H --> I["Application Ready"]
```

**Diagram sources**
- [vertex-ar/app/config.py](file://vertex-ar/app/config.py)
- [vertex-ar/storage_config.py](file://vertex-ar/storage_config.py)

The configuration loading process begins with environment variables, which are loaded into a `Settings` object defined in `app/config.py`. Default values are provided for optional settings, while critical variables without defaults will cause the application to fail if not provided.

### Security Validation
The system implements strict security validation, particularly for sensitive configurations:

- **SMTP Credentials**: The application checks for deprecated environment-based SMTP credentials and issues warnings
- **Production Security**: In production mode, the application refuses to start if SMTP credentials are configured via environment variables
- **Secure Defaults**: Default values are chosen with security in mind (e.g., debug mode disabled in production)
- **Input Validation**: All configuration values are validated for appropriate types and ranges

The security validation is particularly strict for email service configuration. If SMTP credentials are detected in environment variables, the system logs a critical warning and, in production mode, refuses to start. This forces operators to use the secure encrypted storage in the database instead.

### Configuration Object Model
The application uses a class-based configuration model with the `Settings` class in `app/config.py`. This class encapsulates all configuration values and provides methods for loading and validating settings. The configuration is accessible as a global instance, making it available throughout the application.

**Section sources**
- [vertex-ar/app/config.py](file://vertex-ar/app/config.py)
- [vertex-ar/app/email_service.py](file://vertex-ar/app/email_service.py)

## Development vs Production Configurations
The application provides distinct configuration templates for development and production environments, reflecting the different requirements and security considerations for each.

### Development Configuration
The development configuration, defined in `.env.example`, is designed for ease of use and rapid development:

- **Debug Mode**: Enabled (`DEBUG=True`)
- **Security**: CORS origins set to `*` for easy API access
- **Database**: SQLite database for simplicity
- **Storage**: Local storage for easy file access
- **Email**: SMTP settings configured for Gmail
- **Monitoring**: Analytics disabled
- **Reloading**: Code reloading enabled for development

The development configuration prioritizes developer convenience, allowing for rapid iteration and testing without complex setup requirements.

### Production Configuration
The production configuration, defined in `.env.production.example`, emphasizes security, reliability, and performance:

- **Debug Mode**: Disabled (`DEBUG=False`)
- **Security**: Specific CORS origins, secure connections
- **Database**: PostgreSQL recommended for production
- **Storage**: MinIO or other S3-compatible storage
- **Email**: Secure configuration via admin UI
- **Monitoring**: Analytics and error tracking enabled
- **Logging**: Log file configured for persistent logging

The production configuration implements several security best practices:
- HTTPS connections for MinIO storage
- Specific CORS origins instead of wildcard
- Persistent logging to a file
- Error tracking with Sentry
- Rate limiting enabled

```mermaid
flowchart LR
A["Development Configuration"] --> |Less Secure| B["Developer Convenience"]
C["Production Configuration"] --> |More Secure| D["Production Reliability"]
B --> E["Rapid Development"]
D --> F["System Stability"]
```

**Diagram sources**
- [.env.example](file://.env.example)
- [.env.production.example](file://.env.production.example)

**Section sources**
- [.env.example](file://.env.example)
- [.env.production.example](file://.env.production.example)

## Securing Sensitive Data
The application implements a multi-layered approach to securing sensitive configuration data, particularly credentials and API keys.

### Email Credentials Security
The system has a sophisticated security model for email service credentials:

- **Deprecated Environment Variables**: SMTP credentials in environment variables are deprecated and insecure
- **Encrypted Database Storage**: SMTP credentials are stored encrypted in the database via the admin UI
- **Runtime Validation**: The application checks for environment-based credentials and issues warnings
- **Production Enforcement**: In production, the application refuses to start with environment-based SMTP credentials

This security model is documented in the code with clear warnings and instructions for migration. The system provides a clear path for operators to transition from the insecure environment variable approach to the secure encrypted database storage.

### Encryption Implementation
Sensitive data is encrypted using industry-standard practices:

- **PBKDF2-derived AES-256**: Encryption at rest using strong cryptographic algorithms
- **Masked Display**: Credentials are never shown in full in API responses or UI
- **Secure Testing**: Connection tests use decrypted credentials but don't expose them in responses
- **Audit Logging**: All changes to sensitive configurations are logged with username and timestamp

The encryption is managed by the `encryption_manager` in the application, which handles the encryption and decryption of sensitive fields in the database.

### Security Best Practices
The configuration system follows several security best practices:

- **Environment Isolation**: Development and production configurations are kept separate
- **Principle of Least Privilege**: Services use the minimum required permissions
- **Regular Rotation**: Credentials should be rotated regularly
- **Access Control**: Configuration changes require administrative privileges
- **Audit Trails**: Configuration changes are logged for accountability

**Section sources**
- [vertex-ar/app/config.py](file://vertex-ar/app/config.py)
- [vertex-ar/app/email_service.py](file://vertex-ar/app/email_service.py)
- [vertex-ar/app/notification_config.py](file://vertex-ar/app/notification_config.py)

## Managing Multiple Environments
The application supports multiple environments through a combination of configuration files and environment variables.

### Environment-Specific Configuration
The system uses different configuration files for different environments:

- **Development**: `.env` (based on `.env.example`)
- **Production**: `.env` (based on `.env.production.example`)
- **Testing**: Environment variables set during test execution

The application determines the current environment based on the presence and values of environment variables, particularly `DEBUG` and `ENVIRONMENT`.

### Configuration Inheritance
The configuration system implements a form of inheritance where:

- **Base Settings**: Defined in the code with sensible defaults
- **Environment Overrides**: Environment variables override defaults
- **Runtime Configuration**: Some settings can be modified at runtime through the admin UI

This allows for a flexible configuration model where defaults provide a working system, environment variables customize for specific deployments, and runtime configuration allows for dynamic changes.

### Deployment Considerations
When managing multiple environments, several considerations are important:

- **Consistent Naming**: Use consistent naming conventions for environment variables
- **Secure Transmission**: Ensure secure transmission of configuration data
- **Version Control**: Keep configuration templates in version control, but not actual credentials
- **Backup and Recovery**: Include configuration in backup and recovery procedures
- **Documentation**: Maintain up-to-date documentation for configuration requirements

**Section sources**
- [.env.example](file://.env.example)
- [.env.production.example](file://.env.production.example)
- [vertex-ar/app/config.py](file://vertex-ar/app/config.py)

## Configuration Validation
The application performs comprehensive validation of configuration settings to ensure system stability and security.

### Runtime Validation
The system validates configuration at runtime through several mechanisms:

- **Required Variables**: Checks for presence of required environment variables
- **Type Validation**: Ensures variables are of the correct type (string, integer, boolean)
- **Range Validation**: Validates numeric values are within acceptable ranges
- **Security Checks**: Verifies security-related settings meet requirements
- **Dependency Validation**: Ensures related settings are consistent

The validation occurs during application startup, preventing the application from running with invalid or insecure configurations.

### Pre-Deployment Validation
Before deployment, operators should validate configuration using several methods:

- **Template Comparison**: Compare current `.env` file with the latest template
- **Security Audit**: Check for any sensitive data in configuration files
- **Connectivity Testing**: Test connections to external services (database, storage, email)
- **Performance Testing**: Validate configuration under expected load
- **Backup Verification**: Test backup and restore procedures

### Validation Error Handling
When configuration validation fails, the application provides clear error messages and guidance:

- **Descriptive Errors**: Error messages describe what went wrong and how to fix it
- **Security Warnings**: Critical security issues are highlighted with urgent warnings
- **Graceful Degradation**: Where possible, the application uses safe defaults
- **Startup Prevention**: In critical cases, the application refuses to start

The email service configuration provides a particularly robust example of validation error handling, with detailed warnings and specific instructions for resolving security issues.

**Section sources**
- [vertex-ar/app/config.py](file://vertex-ar/app/config.py)
- [vertex-ar/app/email_service.py](file://vertex-ar/app/email_service.py)

## Storage Configuration System
The application uses a sophisticated storage configuration system that supports multiple storage backends and content types.

### JSON Configuration Files
The storage configuration is managed through JSON files in the `config/` directory:

- **storage_config.json**: Main storage configuration with content type mappings
- **remote_storage.example.json**: Template for remote storage configuration

The `storage_config.json` file defines storage settings for different content types (portraits, videos, previews, NFT markers) and includes backup settings and remote storage configurations.

### Content-Type Specific Storage
The system allows different content types to use different storage backends:

- **Portraits**: Can be stored locally or on Yandex Disk
- **Videos**: Can be stored locally or on Yandex Disk
- **Previews**: Can be stored locally or on Yandex Disk
- **NFT Markers**: Can be stored locally or on Yandex Disk

This flexibility allows operators to optimize storage based on content type characteristics and access patterns.

### Remote Storage Integration
The application supports integration with remote storage services:

- **Yandex Disk**: Configured through OAuth token
- **Google Drive**: Configured through access token
- **MinIO/S3**: Configured through access key and secret

The remote storage configuration is designed to be extensible, allowing for additional storage providers to be added in the future.

```mermaid
classDiagram
class StorageConfig {
+content_types : Dict
+backup_settings : Dict
+yandex_disk : Dict
+minio : Dict
+get_storage_type(content_type)
+set_storage_type(content_type, storage_type)
+get_yandex_config(content_type)
+set_yandex_config(content_type, enabled, base_path)
+get_backup_settings()
+set_backup_settings(settings)
+get_yandex_token()
+set_yandex_token(token)
+is_yandex_enabled()
+get_minio_config()
+set_minio_config(config)
}
class StorageAdapter {
<<abstract>>
+save_file(file_data, file_path)
+get_file(file_path)
+delete_file(file_path)
+file_exists(file_path)
+get_public_url(file_path)
+create_directory(dir_path)
+directory_exists(dir_path)
+list_directories(base_path)
+provision_hierarchy(company_slug, category_slugs, subfolders)
}
StorageConfig --> StorageAdapter : "uses"
StorageAdapter <|-- LocalStorageAdapter : "implements"
StorageAdapter <|-- MinioStorageAdapter : "implements"
StorageAdapter <|-- YandexDiskStorageAdapter : "implements"
```

**Diagram sources**
- [vertex-ar/config/storage_config.json](file://vertex-ar/config/storage_config.json)
- [vertex-ar/storage_config.py](file://vertex-ar/storage_config.py)
- [vertex-ar/app/storage.py](file://vertex-ar/app/storage.py)
- [vertex-ar/app/storage_local.py](file://vertex-ar/app/storage_local.py)
- [vertex-ar/app/storage_minio.py](file://vertex-ar/app/storage_minio.py)
- [vertex-ar/app/storage_yandex.py](file://vertex-ar/app/storage_yandex.py)

**Section sources**
- [vertex-ar/config/storage_config.json](file://vertex-ar/config/storage_config.json)
- [vertex-ar/storage_config.py](file://vertex-ar/storage_config.py)

## Email Service Configuration
The email service configuration is a critical component of the application's notification system, with a focus on reliability and security.

### Secure Configuration Model
The email service uses a secure configuration model that prevents credentials from being exposed:

- **Database Storage**: SMTP credentials are stored encrypted in the database
- **Admin UI Configuration**: Credentials are configured through a secure admin interface
- **Runtime Retrieval**: Credentials are retrieved at runtime when needed
- **Access Logging**: All access to SMTP configuration is logged

This model ensures that sensitive credentials are never exposed in environment variables or configuration files.

### Configuration Flow
The email service configuration follows a specific flow:

```mermaid
flowchart TD
A["Admin UI"] --> |Encrypted Storage| B["Database"]
B --> C["NotificationConfig"]
C --> |Decryption| D["SMTP Credentials"]
D --> E["EmailService"]
E --> F["SMTP Server"]
G["Environment Variables"] --> |Deprecated| H["Security Warning"]
H --> |Production| I["Application Refusal"]
```

**Diagram sources**
- [vertex-ar/app/email_service.py](file://vertex-ar/app/email_service.py)
- [vertex-ar/app/notification_config.py](file://vertex-ar/app/notification_config.py)

The configuration flow begins with the admin UI, where operators enter SMTP credentials. These credentials are encrypted and stored in the database. At runtime, the `NotificationConfig` class retrieves and decrypts the credentials when needed by the `EmailService`.

### Migration from Legacy Configuration
The system provides a clear migration path from the legacy environment variable configuration:

1. **Configure in Admin UI**: Enter SMTP credentials through the admin UI at `/admin/notification-settings`
2. **Remove Environment Variables**: Remove `SMTP_USERNAME` and `SMTP_PASSWORD` from the `.env` file and environment
3. **Test Configuration**: Test email functionality to ensure the new configuration works
4. **Deploy**: Deploy the updated configuration to production

The application assists with this migration by providing clear warnings and instructions when legacy configuration is detected.

**Section sources**
- [vertex-ar/app/email_service.py](file://vertex-ar/app/email_service.py)
- [vertex-ar/app/notification_config.py](file://vertex-ar/app/notification_config.py)