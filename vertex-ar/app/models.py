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
    
    @field_validator('name')
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        return validate_name(v)


class CompanyResponse(BaseModel):
    id: str
    name: str
    created_at: str


class CompanyListItem(CompanyResponse):
    client_count: int = 0


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
    view_count: int
    created_at: str


# Video models
class VideoResponse(BaseModel):
    id: str
    portrait_id: str
    video_path: str
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