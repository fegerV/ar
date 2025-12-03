# Core Features

<cite>
**Referenced Files in This Document**   
- [multicompany.md](file://docs/features/multicompany.md)
- [storage-implementation.md](file://docs/features/storage-implementation.md)
- [video-scheduler.md](file://docs/features/video-scheduler.md)
- [lifecycle-management.md](file://docs/features/lifecycle-management.md)
- [remote-backups.md](file://docs/features/remote-backups.md)
- [EMAIL_QUEUE.md](file://docs/EMAIL_QUEUE.md)
- [storage-scaling.md](file://docs/features/storage-scaling.md)
- [storage-summary.md](file://docs/features/storage-summary.md)
- [vertex-ar/app/storage.py](file://vertex-ar/app/storage.py)
- [vertex-ar/app/storage_yandex.py](file://vertex-ar/app/storage_yandex.py)
- [vertex-ar/app/storage_minio.py](file://vertex-ar/app/storage_minio.py)
- [vertex-ar/app/storage_local.py](file://vertex-ar/app/storage_local.py)
- [vertex-ar/app/video_animation_scheduler.py](file://vertex-ar/app/video_animation_scheduler.py)
- [vertex-ar/app/project_lifecycle.py](file://vertex-ar/app/project_lifecycle.py)
</cite>

## Table of Contents
1. [AR Content Management](#ar-content-management)
2. [Multi-Company Tenancy](#multi-company-tenancy)
3. [Storage Orchestration](#storage-orchestration)
4. [Automated Backups](#automated-backups)
5. [Video Scheduling](#video-scheduling)
6. [Lifecycle Management](#lifecycle-management)
7. [Email Processing](#email-processing)

## AR Content Management

AR Content Management provides the foundational framework for organizing and managing augmented reality assets within the Vertex AR platform. This feature enables administrators to structure digital content through a hierarchical system of companies, categories, and projects, ensuring logical organization and efficient retrieval of AR materials.

The system implements a category-based organizational model where each company can define custom categories such as "portraits," "diplomas," or "certificates." These categories serve as organizational containers for AR content and are managed through the projects table with storage-friendly slugs. The file organization follows a structured hierarchy: `{storage_root}/{folder_path}/{company_slug}/{category_slug}/{order_id}/`, ensuring consistent and predictable content placement across different storage backends.

Content management operations are exposed through a comprehensive API that supports CRUD operations for all content types. The system automatically generates public URLs for content access, with URL generation adapting to the specific storage backend in use. This abstraction allows the AR application to function seamlessly regardless of whether content is stored locally or in cloud storage.

Administrators can manage content through an intuitive admin interface that provides visual feedback, status indicators, and bulk operations. The system supports real-time validation and connection testing for all storage configurations, ensuring reliability and immediate feedback during setup and maintenance.

**Section sources**
- [storage-implementation.md](file://docs/features/storage-implementation.md#category-based-organization)
- [storage-summary.md](file://docs/features/storage-summary.md#multi-storage-support)
- [vertex-ar/app/storage.py](file://vertex-ar/app/storage.py)

## Multi-Company Tenancy

Multi-Company Tenancy enables the Vertex AR platform to support multiple independent organizations within a single application instance. This feature is essential for service providers who manage AR content for various clients or for enterprises with distinct business units requiring isolated data environments.

The implementation centers around a dedicated `companies` table in the database that stores company records with unique identifiers, names, and creation timestamps. Each company operates as an isolated tenant, with its own clients, portraits, videos, and associated metadata. The database schema enforces data isolation through foreign key relationships, where entities like clients contain a `company_id` field that references their parent company.

When creating a new client, the system requires specifying the company ID, ensuring proper data segregation. Similarly, when retrieving clients or other content, queries must include the company ID to filter results appropriately. This design prevents cross-company data leakage while allowing efficient queries within a company's dataset.

The admin interface includes a company management dashboard that displays the current company name prominently and provides controls for switching between companies. Administrators can create new companies through a simple form, view company statistics including client counts, and delete companies (except the default "Vertex AR" company). Company deletion triggers cascading deletion of all associated data, maintaining referential integrity.

Security is enforced through authentication and authorization mechanisms. All company-related operations require administrator privileges and are authenticated via session cookies. The system logs all company management operations for audit purposes and implements CORS protection for API endpoints.

**Section sources**
- [multicompany.md](file://docs/features/multicompany.md)
- [vertex-ar/app/api/companies.py](file://vertex-ar/app/api/companies.py)

## Storage Orchestration

Storage Orchestration provides a flexible and extensible framework for managing AR content across multiple storage backends. This feature enables organizations to choose the most appropriate storage solution for their needs, whether local disk, MinIO, or Yandex Disk, and to configure storage independently for different content types.

The architecture is built around a pluggable storage adapter pattern, with a base `StorageAdapter` class defining the contract for all storage implementations. Currently supported adapters include `LocalStorageAdapter` for local filesystem storage, `MinioStorageAdapter` for S3-compatible object storage, and `YandexDiskStorageAdapter` for cloud storage integration. Each adapter implements the same interface, allowing the system to route operations transparently to the appropriate backend.

The `StorageManager` component acts as a facade that routes file operations to the correct storage adapter based on per-company configuration. When an order is created, the system determines the storage backend from the company's `storage_type` field, then uses the corresponding adapter to handle file uploads, downloads, and deletions. This abstraction enables seamless migration between storage types without changing application code.

Configuration is managed through a centralized interface that allows administrators to select storage types for different content categories, test connections, and monitor storage usage. The system supports category-based organization through projects, with files organized according to a hierarchical path structure that incorporates company and category identifiers.

For cloud storage providers like Yandex Disk, the system implements advanced features including OAuth token authentication, public link generation, and quota monitoring. The Yandex Disk adapter includes connection pooling, request retry logic, and directory existence caching to optimize performance and reliability.

**Section sources**
- [storage-implementation.md](file://docs/features/storage-implementation.md)
- [storage-scaling.md](file://docs/features/storage-scaling.md)
- [vertex-ar/app/storage.py](file://vertex-ar/app/storage.py)
- [vertex-ar/app/storage_yandex.py](file://vertex-ar/app/storage_yandex.py)
- [vertex-ar/app/storage_minio.py](file://vertex-ar/app/storage_minio.py)
- [vertex-ar/app/storage_local.py](file://vertex-ar/app/storage_local.py)

## Automated Backups

Automated Backups provide a comprehensive data protection solution that ensures the durability and recoverability of AR content and application data. This feature combines local backup capabilities with cloud synchronization to create a robust disaster recovery strategy.

The backup system supports configurable chunking for large backup files, automatically splitting them into manageable segments based on size thresholds. Administrators can configure the maximum backup size (default: 500MB) and chunk size (default: 100MB) through environment variables or the admin interface. This chunking enables reliable transfers over unstable connections and simplifies storage management.

Backup creation is automated through scheduled tasks that can be configured via cron jobs or systemd timers. The system includes a backup manager that handles the creation, compression, and verification of backup files. For enhanced reliability, the system supports incremental backups and automatic cleanup of old backup files based on retention policies.

Cloud integration extends the backup capabilities by enabling automatic synchronization to remote storage providers. The system supports Yandex Disk and Google Drive, with configuration managed through a JSON file containing OAuth tokens and provider settings. The remote storage manager handles connection testing, file listing, upload/download operations, and quota monitoring.

The admin interface provides a comprehensive backup management dashboard that displays backup status, storage usage, and synchronization statistics. Administrators can manually trigger backups, restore from backups, and monitor the progress of backup operations. The system logs all backup activities for audit and troubleshooting purposes.

**Section sources**
- [remote-backups.md](file://docs/features/remote-backups.md)
- [storage-implementation.md](file://docs/features/storage-implementation.md#chunked-backup-support)
- [vertex-ar/backup_manager.py](file://vertex-ar/backup_manager.py)
- [vertex-ar/app/api/backups.py](file://vertex-ar/app/api/backups.py)

## Video Scheduling

Video Scheduling enables automated management of AR video content activation and deactivation based on predefined schedules. This feature allows organizations to plan content campaigns, manage temporary promotions, and implement video rotation strategies without manual intervention.

The system extends the videos database table with scheduling fields including `start_datetime` and `end_datetime` for activation periods, `rotation_type` for defining rotation behavior, and `status` for tracking video state. Videos can be configured with three rotation types: "none" for manual control, "sequential" for chronological activation, and "cyclic" for continuous rotation.

A background scheduler task runs at configurable intervals (default: every 5 minutes) to check for videos that should be activated or deactivated based on their schedule. When a video's start time is reached, it is automatically activated; when the end time expires, it is deactivated. The system supports automatic archiving of expired videos after a configurable grace period (default: 1 week).

The admin interface includes a video scheduling dashboard that displays the scheduler status, last check time, and a list of all videos with their scheduling parameters. Administrators can filter videos by status, view scheduling history, and perform bulk operations. The interface provides visual indicators for active, inactive, and archived videos.

Integration with the notification system ensures that stakeholders are informed of scheduling events. The system automatically sends notifications when videos are activated, deactivated, or rotated, with alerts delivered via Telegram and email. Prometheus metrics track scheduler performance, including the number of processed events and execution times.

**Section sources**
- [video-scheduler.md](file://docs/features/video-scheduler.md)
- [vertex-ar/app/video_animation_scheduler.py](file://vertex-ar/app/video_animation_scheduler.py)
- [vertex-ar/app/api/videos.py](file://vertex-ar/app/api/videos.py)

## Lifecycle Management

Lifecycle Management provides automated tracking and notification capabilities for AR content subscriptions. This feature helps organizations manage content expiration, renewals, and archival processes through a combination of status tracking and automated alerts.

The system introduces lifecycle statuses for portraits: "active" for valid subscriptions, "expiring" for subscriptions with 30 days or less remaining, and "archived" for expired content. These statuses are calculated dynamically based on the `subscription_end` timestamp stored in the database. The admin interface displays these statuses with color-coded indicators and provides filtering capabilities to identify content requiring attention.

A background scheduler runs at regular intervals to check subscription deadlines and update statuses accordingly. When a subscription enters the "expiring" state, the system can send automated notifications to both administrators and clients. The notification system supports multiple channels including email and Telegram, with templates available in multiple languages.

The admin dashboard includes a status legend that shows counts for each lifecycle state, allowing operators to quickly assess the health of their content portfolio. Clicking on status indicators filters the content list to show only items in that state, facilitating targeted management actions. The system also tracks notification history to prevent duplicate alerts.

Integration with the database ensures that lifecycle information is persisted and can be queried efficiently. The system includes API endpoints for retrieving status counts and filtering content by lifecycle state, enabling external systems to integrate with the lifecycle management functionality.

**Section sources**
- [lifecycle-management.md](file://docs/features/lifecycle-management.md)
- [vertex-ar/app/project_lifecycle.py](file://vertex-ar/app/project_lifecycle.py)
- [vertex-ar/app/api/admin.py](file://vertex-ar/app/api/admin.py)

## Email Processing

Email Processing implements a durable, asynchronous email queue that ensures reliable message delivery without blocking application workflows. This feature decouples email sending from request processing, improving application responsiveness and ensuring message persistence across restarts.

The system uses a database-persistent queue to store email jobs, with a dedicated `email_queue` table that tracks job status, retry attempts, and error information. Email jobs progress through a lifecycle from "pending" to "sending" to either "sent" or "failed" state. Failed jobs are automatically retried up to three times with exponential backoff before being marked as permanently failed.

A configurable worker pool processes queued emails concurrently, with the number of workers controlled by an environment variable. The system integrates with the existing email service, routing non-urgent emails to the persistent queue while providing an "urgent" flag to bypass queuing for time-sensitive messages. This hybrid approach ensures both reliability for routine communications and immediacy for critical alerts.

The implementation includes comprehensive monitoring and management capabilities. Administrators can view queue statistics, list failed jobs, retry failed deliveries, and clean up old jobs through both API endpoints and a command-line interface. Prometheus metrics expose queue depth, send duration, and failure rates for integration with monitoring systems.

Security considerations include secure storage of SMTP credentials, connection encryption via TLS, and rate limiting to prevent abuse. The system automatically falls back to an in-memory queue if the persistent queue is unavailable, ensuring graceful degradation. All email operations are logged for audit and troubleshooting purposes.

**Section sources**
- [EMAIL_QUEUE.md](file://docs/EMAIL_QUEUE.md)
- [vertex-ar/app/services/email_queue.py](file://vertex-ar/app/services/email_queue.py)
- [vertex-ar/app/email_service.py](file://vertex-ar/app/email_service.py)
- [scripts/process_email_queue.py](file://scripts/process_email_queue.py)