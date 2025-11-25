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
    storage_type: str = Field(default="local", description="Storage type")
    storage_connection_id: Optional[str] = Field(default=None, description="Storage connection ID for remote storage")
    
    @field_validator('name')
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        return validate_name(v)
    
    @field_validator('storage_type')
    @classmethod
    def validate_storage_type(cls, v: str) -> str:
        if v not in ['local', 'minio', 'yandex_disk']:
            raise ValueError('storage_type must be one of: local, minio, yandex_disk')
        return v


class CompanyResponse(BaseModel):
    id: str
    name: str
    storage_type: str
    storage_connection_id: Optional[str] = None
    created_at: str


class CompanyListItem(CompanyResponse):
    client_count: int = 0


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    storage_type: Optional[str] = Field(None, description="Storage type")
    storage_connection_id: Optional[str] = Field(None, description="Storage connection ID for remote storage")
    
    @field_validator('name')
    @classmethod
    def validate_company_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_name(v)
        return v
    
    @field_validator('storage_type')
    @classmethod
    def validate_storage_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ['local', 'minio', 'yandex_disk']:
            raise ValueError('storage_type must be one of: local, minio, yandex_disk')
        return v


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
    
    @field_validator('storage_type')
    @classmethod
    def validate_storage_type(cls, v: str) -> str:
        if v not in ['local', 'minio', 'yandex_disk']:
            raise ValueError('storage_type must be one of: local, minio, yandex_disk')
        return v


class PaginatedCompaniesResponse(BaseModel):
    items: List[CompanyListItem]
    total: int


# Client models
class ClientCreate(BaseModel):
    phone: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=150)
    company_id: str = Field(..., description="Company ID")
    
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


class ClientUpdate(BaseModel):
    phone: Optional[str] = Field(None, min_length=1, max_length=20)
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    
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


class ClientResponse(BaseModel):
    id: str
    phone: str
    name: str
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
    ids: List[str] = Field(..., min_items=1, description="List of IDs to process")


# Order models
class OrderCreate(BaseModel):
    phone: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=150)
    
    @field_validator('phone')
    @classmethod
    def validate_phone_field(cls, v: str) -> str:
        return validate_phone(v)
    
    @field_validator('name')
    @classmethod
    def validate_name_field(cls, v: str) -> str:
        return validate_name(v)


# Portrait models
class PortraitResponse(BaseModel):
    id: str
    client_id: str
    permanent_link: str
    qr_code_base64: Optional[str]
    image_path: str
    image_url: Optional[str] = None  # Public URL for image
    preview_url: Optional[str] = None  # Public URL for preview
    view_count: int
    created_at: str


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