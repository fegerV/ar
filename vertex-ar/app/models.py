"""
Pydantic models for Vertex AR application.
Contains request/response models for API endpoints.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.validators import (
    validate_email,
    validate_phone,
    validate_username,
    validate_password_strength,
    validate_name,
    validate_url,
    validate_social_links,
)


# Authentication models
class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# User profile models (for admin self-management)
class UserUpdate(BaseModel):
    email: Optional[str] = Field(None, max_length=255)
    full_name: Optional[str] = Field(None, max_length=150)
    
    @field_validator('email')
    @classmethod
    def validate_email_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_email(v)
        return v
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_name(v)
        return v


class UserProfile(BaseModel):
    username: str
    email: Optional[str]
    full_name: Optional[str]
    created_at: str
    last_login: Optional[str]


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=256)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password_field(cls, v: str) -> str:
        return validate_password_strength(v)


# AR Content models
class ARContentResponse(BaseModel):
    id: str
    ar_url: str
    qr_code_base64: Optional[str]
    image_path: str
    video_path: str
    created_at: str


# Company models
class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    storage_type: str = Field(default="local_disk", description="Storage type")
    storage_connection_id: Optional[str] = Field(default=None, description="Storage connection ID for remote storage")
    yandex_disk_folder_id: Optional[str] = Field(default=None, description="Yandex Disk folder ID for storing orders")
    storage_folder_path: Optional[str] = Field(default="vertex_ar_content", description="Storage folder path for local storage")
    backup_provider: Optional[str] = Field(default=None, description="Remote backup provider (e.g., yandex_disk, google_drive)")
    backup_remote_path: Optional[str] = Field(default=None, description="Remote path for backups")
    email: Optional[str] = Field(default=None, max_length=255, description="Company email address")
    description: Optional[str] = Field(default=None, description="Company description")
    city: Optional[str] = Field(default=None, max_length=150, description="Company city/location")
    phone: Optional[str] = Field(default=None, max_length=50, description="Company phone number")
    website: Optional[str] = Field(default=None, max_length=2048, description="Company website URL")
    social_links: Optional[str] = Field(default=None, description="Social media links as JSON string")
    manager_name: Optional[str] = Field(default=None, max_length=150, description="Manager/contact person name")
    manager_phone: Optional[str] = Field(default=None, max_length=50, description="Manager phone number")
    manager_email: Optional[str] = Field(default=None, max_length=255, description="Manager email address")
    
    @field_validator('name')
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        return validate_name(v)
    
    @field_validator('storage_type')
    @classmethod
    def validate_storage_type(cls, v: str) -> str:
        if v not in ['local', 'local_disk', 'minio', 'yandex_disk']:
            raise ValueError('storage_type must be one of: local, local_disk, minio, yandex_disk')
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_email(v)
        return v
    
    @field_validator('phone')
    @classmethod
    def validate_phone_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_phone(v)
        return v
    
    @field_validator('website')
    @classmethod
    def validate_website_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_url(v)
        return v
    
    @field_validator('social_links')
    @classmethod
    def validate_social_links_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_social_links(v)
        return v
    
    @field_validator('manager_name', 'city')
    @classmethod
    def validate_name_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_name(v)
        return v
    
    @field_validator('manager_phone')
    @classmethod
    def validate_manager_phone_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_phone(v)
        return v
    
    @field_validator('manager_email')
    @classmethod
    def validate_manager_email_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_email(v)
        return v


class CompanyResponse(BaseModel):
    id: str
    name: str
    storage_type: str
    storage_connection_id: Optional[str] = None
    yandex_disk_folder_id: Optional[str] = None
    storage_folder_path: Optional[str] = None
    backup_provider: Optional[str] = None
    backup_remote_path: Optional[str] = None
    email: Optional[str] = None
    description: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    social_links: Optional[str] = None
    manager_name: Optional[str] = None
    manager_phone: Optional[str] = None
    manager_email: Optional[str] = None
    created_at: str


class CompanyListItem(CompanyResponse):
    client_count: int = 0


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    storage_type: Optional[str] = Field(None, description="Storage type")
    storage_connection_id: Optional[str] = Field(None, description="Storage connection ID for remote storage")
    yandex_disk_folder_id: Optional[str] = Field(None, description="Yandex Disk folder ID for storing orders")
    storage_folder_path: Optional[str] = Field(None, description="Storage folder path for local storage")
    backup_provider: Optional[str] = Field(None, description="Remote backup provider")
    backup_remote_path: Optional[str] = Field(None, description="Remote path for backups")
    email: Optional[str] = Field(None, max_length=255, description="Company email address")
    description: Optional[str] = Field(None, description="Company description")
    city: Optional[str] = Field(None, max_length=150, description="Company city/location")
    phone: Optional[str] = Field(None, max_length=50, description="Company phone number")
    website: Optional[str] = Field(None, max_length=2048, description="Company website URL")
    social_links: Optional[str] = Field(None, description="Social media links as JSON string")
    manager_name: Optional[str] = Field(None, max_length=150, description="Manager/contact person name")
    manager_phone: Optional[str] = Field(None, max_length=50, description="Manager phone number")
    manager_email: Optional[str] = Field(None, max_length=255, description="Manager email address")
    
    @field_validator('name')
    @classmethod
    def validate_company_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_name(v)
        return v
    
    @field_validator('storage_type')
    @classmethod
    def validate_storage_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ['local', 'local_disk', 'minio', 'yandex_disk']:
            raise ValueError('storage_type must be one of: local, local_disk, minio, yandex_disk')
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_email(v)
        return v
    
    @field_validator('phone')
    @classmethod
    def validate_phone_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_phone(v)
        return v
    
    @field_validator('website')
    @classmethod
    def validate_website_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_url(v)
        return v
    
    @field_validator('social_links')
    @classmethod
    def validate_social_links_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_social_links(v)
        return v
    
    @field_validator('manager_name', 'city')
    @classmethod
    def validate_name_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_name(v)
        return v
    
    @field_validator('manager_phone')
    @classmethod
    def validate_manager_phone_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_phone(v)
        return v
    
    @field_validator('manager_email')
    @classmethod
    def validate_manager_email_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_email(v)
        return v


# Company backup configuration models
class CompanyBackupConfig(BaseModel):
    """Model for setting company backup configuration."""
    backup_provider: Optional[str] = Field(None, description="Provider name (e.g., yandex_disk, google_drive)")
    backup_remote_path: Optional[str] = Field(None, description="Remote directory path for backups")
    
    @field_validator('backup_provider')
    @classmethod
    def validate_provider(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ['yandex_disk', 'google_drive', 'local']:
            raise ValueError('backup_provider must be one of: yandex_disk, google_drive, local')
        return v


class CompanyBackupConfigResponse(BaseModel):
    """Response model for company backup configuration."""
    company_id: str
    company_name: str
    backup_provider: Optional[str] = None
    backup_remote_path: Optional[str] = None


# Storage connection models
class StorageConnectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., description="Storage type: minio, yandex_disk")
    config: Dict[str, Any] = Field(..., description="Storage configuration")
    
    @field_validator('name')
    @classmethod
    def validate_connection_name(cls, v: str) -> str:
        return validate_name(v)
    
    @field_validator('type')
    @classmethod
    def validate_storage_type(cls, v: str) -> str:
        if v not in ['minio', 'yandex_disk']:
            raise ValueError('type must be one of: minio, yandex_disk')
        return v


class StorageConnectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    
    @field_validator('name')
    @classmethod
    def validate_connection_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_name(v)
        return v


class StorageConnectionResponse(BaseModel):
    id: str
    name: str
    type: str
    config: Dict[str, Any]
    is_active: bool
    is_tested: bool
    test_result: Optional[str] = None
    created_at: str
    updated_at: str


class StorageTestRequest(BaseModel):
    connection_id: str


class StorageTestResponse(BaseModel):
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class StorageOptionResponse(BaseModel):
    id: str
    name: str
    type: str
    connection_id: Optional[str] = None
    is_available: bool


class CompanyStorageUpdate(BaseModel):
    storage_type: str
    storage_connection_id: Optional[str] = None
    yandex_disk_folder_id: Optional[str] = None
    
    @field_validator('storage_type')
    @classmethod
    def validate_storage_type(cls, v: str) -> str:
        if v not in ['local', 'local_disk', 'minio', 'yandex_disk']:
            raise ValueError('storage_type must be one of: local, local_disk, minio, yandex_disk')
        return v



class CompanyStorageTypeUpdate(BaseModel):
    storage_type: str = Field(..., description="Storage type: local, local_disk, minio, or yandex_disk")
    
    @field_validator('storage_type')
    @classmethod
    def validate_storage_type(cls, v: str) -> str:
        if v not in ['local', 'local_disk', 'minio', 'yandex_disk']:
            raise ValueError('storage_type must be one of: local, local_disk, minio, yandex_disk')
        return v


class CompanyStorageFolderUpdate(BaseModel):
    folder_path: str = Field(..., min_length=1, max_length=255, description="Storage folder path")
    
    @field_validator('folder_path')
    @classmethod
    def validate_folder_path(cls, v: str) -> str:
        import re
        if not v or not v.strip():
            raise ValueError('Folder path is required')
        v = v.strip()
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Folder path can only contain letters, numbers, dashes, and underscores')
        return v


class CompanyStorageInfoResponse(BaseModel):
    company_id: str
    company_name: str
    storage_type: str
    storage_folder_path: Optional[str] = None
    yandex_disk_folder_id: Optional[str] = None
    storage_connection_id: Optional[str] = None
    is_configured: bool
    status_message: str


class YandexFolderUpdate(BaseModel):
    folder_path: str = Field(..., min_length=1, description="Yandex Disk folder path to assign to company")
    
    @field_validator('folder_path')
    @classmethod
    def validate_folder_path(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Folder path is required')
        return v.strip()


class CompanyYandexFolderUpdate(BaseModel):
    """Alias for YandexFolderUpdate to match naming convention."""
    yandex_disk_folder_id: str = Field(..., min_length=1, description="Yandex Disk folder ID/path")
    
    @field_validator('yandex_disk_folder_id')
    @classmethod
    def validate_folder_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Yandex Disk folder ID is required')
        return v.strip()


class CompanyContentType(BaseModel):
    """Response model for a single content type."""
    slug: str = Field(..., description="URL-safe slug")
    label: str = Field(..., description="Human-readable label")


class YandexDiskFolder(BaseModel):
    path: str = Field(..., description="Full path on Yandex Disk")
    name: str = Field(..., description="Folder name")


class YandexDiskFoldersResponse(BaseModel):
    items: List[YandexDiskFolder]
    total: int
    has_more: bool


class PaginatedCompaniesResponse(BaseModel):
    items: List[CompanyListItem]
    total: int
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=50, description="Items per page")
    total_pages: int = Field(default=1, description="Total number of pages")


# Client models
class ClientCreate(BaseModel):
    phone: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=150)
    company_id: str = Field(..., description="Company ID")
    email: Optional[str] = Field(None, max_length=255, description="Client email address")
    
    @field_validator('phone')
    @classmethod
    def validate_phone_field(cls, v: str) -> str:
        return validate_phone(v)
    
    @field_validator('name')
    @classmethod
    def validate_name_field(cls, v: str) -> str:
        return validate_name(v)
    
    @field_validator('company_id')
    @classmethod
    def validate_company_id_field(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Company ID is required')
        return v.strip()
    
    @field_validator('email')
    @classmethod
    def validate_email_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_email(v)
        return v


class ClientUpdate(BaseModel):
    phone: Optional[str] = Field(None, min_length=1, max_length=20)
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    email: Optional[str] = Field(None, max_length=255, description="Client email address")
    
    @field_validator('phone')
    @classmethod
    def validate_phone_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_phone(v)
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_name(v)
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_email(v)
        return v


class ClientResponse(BaseModel):
    id: str
    phone: str
    name: str
    email: Optional[str] = None
    created_at: str


class ClientListItem(ClientResponse):
    portraits_count: int = 0
    latest_portrait_preview: Optional[str] = None  # Base64 encoded preview of latest portrait
    company_id: Optional[str] = None


class PaginatedClientsResponse(BaseModel):
    items: List[ClientListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class BulkIdsRequest(BaseModel):
    ids: List[str] = Field(..., min_length=1, description="List of IDs to process")


# Project models
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    company_id: str = Field(..., description="Company ID")
    status: Optional[str] = Field(default="active", description="Lifecycle status")
    subscription_end: Optional[str] = Field(None, description="Subscription end date (ISO format)")
    
    @field_validator('name')
    @classmethod
    def validate_name_field(cls, v: str) -> str:
        return validate_name(v)
    
    @field_validator('company_id')
    @classmethod
    def validate_company_id_field(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Company ID is required')
        return v.strip()
    
    @field_validator('status')
    @classmethod
    def validate_status_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ['active', 'expiring', 'archived']:
            raise ValueError('status must be one of: active, expiring, archived')
        return v
    
    @field_validator('subscription_end')
    @classmethod
    def validate_subscription_end_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            from datetime import datetime
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                raise ValueError('subscription_end must be a valid ISO format date')
        return v


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[str] = Field(None, description="Lifecycle status")
    subscription_end: Optional[str] = Field(None, description="Subscription end date (ISO format)")
    
    @field_validator('name')
    @classmethod
    def validate_name_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_name(v)
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ['active', 'expiring', 'archived']:
            raise ValueError('status must be one of: active, expiring, archived')
        return v
    
    @field_validator('subscription_end')
    @classmethod
    def validate_subscription_end_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            from datetime import datetime
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                raise ValueError('subscription_end must be a valid ISO format date')
        return v


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    company_id: str
    created_at: str
    status: Optional[str] = "active"
    subscription_end: Optional[str] = None
    last_status_change: Optional[str] = None


class ProjectListItem(ProjectResponse):
    folder_count: int = 0
    portrait_count: int = 0


class PaginatedProjectsResponse(BaseModel):
    items: List[ProjectListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# Folder models
class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    project_id: str = Field(..., description="Project ID")
    
    @field_validator('name')
    @classmethod
    def validate_name_field(cls, v: str) -> str:
        return validate_name(v)
    
    @field_validator('project_id')
    @classmethod
    def validate_project_id_field(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Project ID is required')
        return v.strip()


class FolderUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    
    @field_validator('name')
    @classmethod
    def validate_name_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_name(v)
        return v


class FolderResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    project_id: str
    created_at: str


class FolderListItem(FolderResponse):
    portrait_count: int = 0


class PaginatedFoldersResponse(BaseModel):
    items: List[FolderListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# Order models
class OrderCreate(BaseModel):
    phone: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=150)
    email: Optional[str] = Field(None, max_length=255, description="Client email address")
    subscription_end: Optional[str] = Field(None, description="Subscription end date (ISO format)")
    
    @field_validator('phone')
    @classmethod
    def validate_phone_field(cls, v: str) -> str:
        return validate_phone(v)
    
    @field_validator('name')
    @classmethod
    def validate_name_field(cls, v: str) -> str:
        return validate_name(v)
    
    @field_validator('email')
    @classmethod
    def validate_email_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return validate_email(v)
        return v
    
    @field_validator('subscription_end')
    @classmethod
    def validate_subscription_end_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            from datetime import datetime
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                raise ValueError('subscription_end must be a valid ISO format date')
        return v


# Portrait models
class PortraitResponse(BaseModel):
    id: str
    client_id: str
    folder_id: Optional[str] = None  # New: folder association
    permanent_link: str
    qr_code_base64: Optional[str]
    image_path: str
    image_url: Optional[str] = None  # Public URL for image
    preview_url: Optional[str] = None  # Public URL for preview
    view_count: int
    created_at: str
    subscription_end: Optional[str] = None
    lifecycle_status: Optional[str] = "active"
    last_status_change: Optional[str] = None


# Video models
class VideoResponse(BaseModel):
    id: str
    portrait_id: str
    video_path: str
    video_url: Optional[str] = None  # Public URL for video
    preview_url: Optional[str] = None  # Public URL for preview
    is_active: bool
    created_at: str
    file_size_mb: Optional[int] = None
    # New scheduling fields
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    rotation_type: Optional[str] = None
    status: Optional[str] = None


class VideoScheduleUpdate(BaseModel):
    start_datetime: Optional[str] = Field(None, description="Start datetime in ISO format")
    end_datetime: Optional[str] = Field(None, description="End datetime in ISO format")
    rotation_type: Optional[str] = Field(None, description="Rotation type: none, sequential, cyclic")
    status: Optional[str] = Field(None, description="Status: active, inactive, archived")
    
    @field_validator('rotation_type')
    @classmethod
    def validate_rotation_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ['none', 'sequential', 'cyclic']:
            raise ValueError('rotation_type must be one of: none, sequential, cyclic')
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ['active', 'inactive', 'archived']:
            raise ValueError('status must be one of: active, inactive, archived')
        return v


class VideoScheduleHistory(BaseModel):
    id: str
    video_id: str
    old_status: Optional[str]
    new_status: str
    change_reason: str
    changed_at: str
    changed_by: Optional[str]


class VideoScheduleSummary(BaseModel):
    status_counts: Dict[str, int]
    pending_activation: int
    pending_deactivation: int


class VideoRotationRequest(BaseModel):
    portrait_id: str
    rotation_type: str = Field(..., description="Rotation type: sequential, cyclic")
    
    @field_validator('rotation_type')
    @classmethod
    def validate_rotation_type(cls, v: str) -> str:
        if v not in ['sequential', 'cyclic']:
            raise ValueError('rotation_type must be one of: sequential, cyclic')
        return v


class OrderResponse(BaseModel):
    client: ClientResponse
    portrait: PortraitResponse
    video: VideoResponse


# Generic response models
class HealthResponse(BaseModel):
    status: str
    version: str


class MessageResponse(BaseModel):
    message: str


class CountResponse(BaseModel):
    count: int


# Notification settings models
class NotificationSettingsUpdate(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = Field(None, ge=1, le=65535)
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None  # Will be encrypted before storage
    smtp_from_email: Optional[str] = None
    smtp_use_tls: Optional[bool] = None
    smtp_use_ssl: Optional[bool] = None
    telegram_bot_token: Optional[str] = None  # Will be encrypted before storage
    telegram_chat_ids: Optional[str] = None  # Comma-separated list
    event_log_errors: Optional[bool] = None
    event_db_issues: Optional[bool] = None
    event_disk_space: Optional[bool] = None
    event_resource_monitoring: Optional[bool] = None
    event_backup_success: Optional[bool] = None
    event_info_notifications: Optional[bool] = None
    disk_threshold_percent: Optional[int] = Field(None, ge=1, le=100)
    cpu_threshold_percent: Optional[int] = Field(None, ge=1, le=100)
    memory_threshold_percent: Optional[int] = Field(None, ge=1, le=100)
    is_active: Optional[bool] = None
    
    @field_validator('smtp_from_email')
    @classmethod
    def validate_smtp_from_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_email(v)
        return v


class NotificationSettingsResponse(BaseModel):
    id: str
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password_masked: Optional[str] = None  # Masked password
    smtp_from_email: Optional[str] = None
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    telegram_bot_token_masked: Optional[str] = None  # Masked token
    telegram_chat_ids: Optional[str] = None
    event_log_errors: bool = True
    event_db_issues: bool = True
    event_disk_space: bool = True
    event_resource_monitoring: bool = True
    event_backup_success: bool = True
    event_info_notifications: bool = True
    disk_threshold_percent: int = 90
    cpu_threshold_percent: int = 80
    memory_threshold_percent: int = 85
    is_active: bool = True
    created_at: str
    updated_at: str


class NotificationTestRequest(BaseModel):
    test_type: str = Field(..., description="Type of test: email, telegram, or both")
    
    @field_validator('test_type')
    @classmethod
    def validate_test_type(cls, v: str) -> str:
        if v not in ['email', 'telegram', 'both']:
            raise ValueError('test_type must be one of: email, telegram, both')
        return v


class NotificationTestResponse(BaseModel):
    success: bool
    results: Dict[str, Any]
    message: str


class NotificationHistoryItem(BaseModel):
    id: str
    notification_type: str
    recipient: str
    subject: Optional[str] = None
    message: str
    status: str
    error_message: Optional[str] = None
    sent_at: str


class PaginatedNotificationHistoryResponse(BaseModel):
    items: List[NotificationHistoryItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# Email Template models
class EmailTemplateCreate(BaseModel):
    template_type: str = Field(..., description="Template type: subscription_end, system_error, admin_report")
    subject: str = Field(..., min_length=1, max_length=200, description="Email subject")
    html_content: str = Field(..., min_length=10, description="HTML content of the email")
    variables_used: Optional[str] = Field(None, description="JSON array of variable names used in template")
    is_active: bool = Field(True, description="Whether template is active")
    
    @field_validator('template_type')
    @classmethod
    def validate_template_type(cls, v: str) -> str:
        valid_types = ['subscription_end', 'system_error', 'admin_report']
        if v not in valid_types:
            raise ValueError(f'template_type must be one of: {", ".join(valid_types)}')
        return v
    
    @field_validator('html_content')
    @classmethod
    def validate_html_content(cls, v: str) -> str:
        dangerous_tags = ['<script', '<iframe', 'javascript:', 'onerror=', 'onload=']
        v_lower = v.lower()
        for tag in dangerous_tags:
            if tag in v_lower:
                raise ValueError(f'HTML content contains potentially dangerous tag or attribute: {tag}')
        return v


class EmailTemplateUpdate(BaseModel):
    subject: Optional[str] = Field(None, min_length=1, max_length=200, description="Email subject")
    html_content: Optional[str] = Field(None, min_length=10, description="HTML content of the email")
    variables_used: Optional[str] = Field(None, description="JSON array of variable names used in template")
    is_active: Optional[bool] = Field(None, description="Whether template is active")
    
    @field_validator('html_content')
    @classmethod
    def validate_html_content(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        dangerous_tags = ['<script', '<iframe', 'javascript:', 'onerror=', 'onload=']
        v_lower = v.lower()
        for tag in dangerous_tags:
            if tag in v_lower:
                raise ValueError(f'HTML content contains potentially dangerous tag or attribute: {tag}')
        return v


class EmailTemplateResponse(BaseModel):
    id: str
    template_type: str
    subject: str
    html_content: str
    variables_used: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str


class EmailTemplatePreviewRequest(BaseModel):
    variables: Dict[str, str] = Field(..., description="Variable values to substitute in template")


class EmailTemplatePreviewResponse(BaseModel):
    subject: str
    html_content: str