"""
Enhanced Pydantic models with comprehensive validation for Vertex AR application.
"""
import re
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator, root_validator

from validation_utils import EnhancedValidator, ValidationError


class EnhancedUserCreate(BaseModel):
    """Enhanced user creation model with comprehensive validation."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=8, max_length=256, description="Secure password")
    email: Optional[str] = Field(None, max_length=255, description="Email address")
    full_name: Optional[str] = Field(None, max_length=150, description="Full name")
    
    @validator('username')
    def validate_username(cls, v):
        try:
            return EnhancedValidator.validate_username(v)
        except ValidationError as e:
            raise ValueError(e.message)
    
    @validator('email')
    def validate_email(cls, v):
        if v is None:
            return v
        try:
            return EnhancedValidator.validate_email(v)
        except ValidationError as e:
            raise ValueError(e.message)
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        # Check for at least one digit
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain at least one special character")
        
        return v
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if v is None:
            return v
        return EnhancedValidator.sanitize_string(v, max_length=150)


class EnhancedUserLogin(BaseModel):
    """Enhanced user login model with validation."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    
    @validator('username')
    def sanitize_username(cls, v):
        return EnhancedValidator.sanitize_string(v, max_length=50)


class EnhancedUserUpdate(BaseModel):
    """Enhanced user update model with validation."""
    email: Optional[str] = Field(None, max_length=255)
    full_name: Optional[str] = Field(None, max_length=150)
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    
    @validator('email')
    def validate_email(cls, v):
        if v is None:
            return v
        try:
            return EnhancedValidator.validate_email(v)
        except ValidationError as e:
            raise ValueError(e.message)
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if v is None:
            return v
        return EnhancedValidator.sanitize_string(v, max_length=150)


class EnhancedPasswordChange(BaseModel):
    """Enhanced password change model with validation."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=256, description="New secure password")
    
    @validator('new_password')
    def validate_new_password_strength(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters long")
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', v):
            raise ValueError("New password must contain at least one uppercase letter")
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', v):
            raise ValueError("New password must contain at least one lowercase letter")
        
        # Check for at least one digit
        if not re.search(r'\d', v):
            raise ValueError("New password must contain at least one digit")
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("New password must contain at least one special character")
        
        return v


class EnhancedClientCreate(BaseModel):
    """Enhanced client creation model with phone validation."""
    phone: str = Field(..., min_length=10, max_length=20, description="Phone number")
    name: str = Field(..., min_length=1, max_length=150, description="Client name")
    email: Optional[str] = Field(None, max_length=255, description="Email address")
    
    @validator('phone')
    def validate_phone(cls, v):
        try:
            return EnhancedValidator.validate_phone_number(v, region='international')
        except ValidationError as e:
            raise ValueError(e.message)
    
    @validator('name')
    def validate_name(cls, v):
        return EnhancedValidator.sanitize_string(v, max_length=150)
    
    @validator('email')
    def validate_email(cls, v):
        if v is None:
            return v
        try:
            return EnhancedValidator.validate_email(v)
        except ValidationError as e:
            raise ValueError(e.message)


class EnhancedClientUpdate(BaseModel):
    """Enhanced client update model with validation."""
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    email: Optional[str] = Field(None, max_length=255)
    
    @validator('phone')
    def validate_phone(cls, v):
        if v is None:
            return v
        try:
            return EnhancedValidator.validate_phone_number(v, region='international')
        except ValidationError as e:
            raise ValueError(e.message)
    
    @validator('name')
    def validate_name(cls, v):
        if v is None:
            return v
        return EnhancedValidator.sanitize_string(v, max_length=150)
    
    @validator('email')
    def validate_email(cls, v):
        if v is None:
            return v
        try:
            return EnhancedValidator.validate_email(v)
        except ValidationError as e:
            raise ValueError(e.message)


class EnhancedOrderCreate(BaseModel):
    """Enhanced order creation model with validation."""
    phone: str = Field(..., min_length=10, max_length=20, description="Client phone number")
    name: str = Field(..., min_length=1, max_length=150, description="Client name")
    email: Optional[str] = Field(None, max_length=255, description="Client email")
    notes: Optional[str] = Field(None, max_length=1000, description="Order notes")
    
    @validator('phone')
    def validate_phone(cls, v):
        try:
            return EnhancedValidator.validate_phone_number(v, region='international')
        except ValidationError as e:
            raise ValueError(e.message)
    
    @validator('name')
    def validate_name(cls, v):
        return EnhancedValidator.sanitize_string(v, max_length=150)
    
    @validator('email')
    def validate_email(cls, v):
        if v is None:
            return v
        try:
            return EnhancedValidator.validate_email(v)
        except ValidationError as e:
            raise ValueError(e.message)
    
    @validator('notes')
    def validate_notes(cls, v):
        if v is None:
            return v
        return EnhancedValidator.sanitize_string(v, max_length=1000)


class EnhancedUserSearch(BaseModel):
    """Enhanced user search model with validation."""
    query: Optional[str] = Field(None, max_length=100)
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)
    
    @validator('query')
    def sanitize_query(cls, v):
        if v is None:
            return v
        return EnhancedValidator.sanitize_string(v, max_length=100)
    
    @validator('limit')
    def validate_limit(cls, v):
        try:
            if v < 1:
                raise ValueError("Limit must be at least 1")
            if v > 100:
                raise ValueError("Limit cannot exceed 100")
            return v
        except Exception as e:
            raise ValueError(str(e))
    
    @validator('offset')
    def validate_offset(cls, v):
        try:
            if v < 0:
                raise ValueError("Offset cannot be negative")
            return v
        except Exception as e:
            raise ValueError(str(e))
    
    @root_validator(skip_on_failure=True)
    def validate_pagination_params(cls, values):
        limit = values.get('limit', 50)
        offset = values.get('offset', 0)
        try:
            EnhancedValidator.validate_pagination_params(limit, offset)
        except ValidationError as e:
            raise ValueError(e.message)
        return values


class EnhancedPortraitCreate(BaseModel):
    """Enhanced portrait creation model with validation."""
    client_id: str = Field(..., description="Client ID")
    title: Optional[str] = Field(None, max_length=200, description="Portrait title")
    description: Optional[str] = Field(None, max_length=1000, description="Portrait description")
    
    @validator('client_id')
    def validate_client_id(cls, v):
        try:
            return EnhancedValidator.validate_uuid(v, 'client_id')
        except ValidationError as e:
            raise ValueError(e.message)
    
    @validator('title')
    def validate_title(cls, v):
        if v is None:
            return v
        return EnhancedValidator.sanitize_string(v, max_length=200)
    
    @validator('description')
    def validate_description(cls, v):
        if v is None:
            return v
        return EnhancedValidator.sanitize_string(v, max_length=1000)


class EnhancedVideoUpload(BaseModel):
    """Enhanced video upload model with validation."""
    portrait_id: str = Field(..., description="Portrait ID")
    title: Optional[str] = Field(None, max_length=200, description="Video title")
    description: Optional[str] = Field(None, max_length=1000, description="Video description")
    duration_seconds: Optional[int] = Field(None, ge=1, le=3600, description="Video duration in seconds")
    
    @validator('portrait_id')
    def validate_portrait_id(cls, v):
        try:
            return EnhancedValidator.validate_uuid(v, 'portrait_id')
        except ValidationError as e:
            raise ValueError(e.message)
    
    @validator('title')
    def validate_title(cls, v):
        if v is None:
            return v
        return EnhancedValidator.sanitize_string(v, max_length=200)
    
    @validator('description')
    def validate_description(cls, v):
        if v is None:
            return v
        return EnhancedValidator.sanitize_string(v, max_length=1000)


class EnhancedARContentCreate(BaseModel):
    """Enhanced AR content creation model with validation."""
    title: Optional[str] = Field(None, max_length=200, description="AR content title")
    description: Optional[str] = Field(None, max_length=1000, description="AR content description")
    is_public: bool = Field(False, description="Whether content is publicly accessible")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    
    @validator('title')
    def validate_title(cls, v):
        if v is None:
            return v
        return EnhancedValidator.sanitize_string(v, max_length=200)
    
    @validator('description')
    def validate_description(cls, v):
        if v is None:
            return v
        return EnhancedValidator.sanitize_string(v, max_length=1000)
    
    @validator('tags')
    def validate_tags(cls, v):
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("Maximum 10 tags allowed")
        
        sanitized_tags = []
        for tag in v:
            if len(tag) > 50:
                raise ValueError("Each tag must be 50 characters or less")
            sanitized_tag = EnhancedValidator.sanitize_string(tag, max_length=50)
            if sanitized_tag:
                sanitized_tags.append(sanitized_tag)
        
        return sanitized_tags


class EnhancedFileUpload(BaseModel):
    """Enhanced file upload metadata model with validation."""
    filename: str = Field(..., max_length=255, description="Original filename")
    content_type: str = Field(..., max_length=100, description="MIME content type")
    size_bytes: int = Field(..., ge=1, description="File size in bytes")
    description: Optional[str] = Field(None, max_length=500, description="File description")
    
    @validator('filename')
    def validate_filename(cls, v):
        # Remove path traversal attempts
        sanitized = v.replace('../', '').replace('..\\', '')
        return EnhancedValidator.sanitize_string(sanitized, max_length=255)
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = [
            'image/jpeg', 'image/png', 'image/webp',
            'video/mp4', 'video/webm',
            'application/pdf'
        ]
        if v not in allowed_types:
            raise ValueError(f"Content type {v} is not allowed")
        return v
    
    @validator('description')
    def validate_description(cls, v):
        if v is None:
            return v
        return EnhancedValidator.sanitize_string(v, max_length=500)


# Response models remain the same but with enhanced documentation
class EnhancedUserResponse(BaseModel):
    """Enhanced user response model with comprehensive fields."""
    username: str
    email: Optional[str]
    full_name: Optional[str]
    is_admin: bool
    is_active: bool
    created_at: str
    last_login: Optional[str]
    login_count: Optional[int] = None
    profile_image_url: Optional[str] = None


class EnhancedClientResponse(BaseModel):
    """Enhanced client response model with additional fields."""
    id: str
    phone: str
    name: str
    email: Optional[str]
    created_at: str
    updated_at: Optional[str] = None
    portrait_count: Optional[int] = 0
    total_orders: Optional[int] = 0


class EnhancedPortraitResponse(BaseModel):
    """Enhanced portrait response model with comprehensive data."""
    id: str
    client_id: str
    title: Optional[str]
    description: Optional[str]
    permanent_link: str
    qr_code_base64: Optional[str]
    image_path: str
    view_count: int
    created_at: str
    updated_at: Optional[str] = None
    is_active: bool = True
    video_count: Optional[int] = 0
    active_video_id: Optional[str] = None


class EnhancedVideoResponse(BaseModel):
    """Enhanced video response model with metadata."""
    id: str
    portrait_id: str
    title: Optional[str]
    description: Optional[str]
    video_path: str
    is_active: bool
    duration_seconds: Optional[int]
    size_bytes: Optional[int]
    created_at: str
    view_count: Optional[int] = 0


class EnhancedOrderResponse(BaseModel):
    """Enhanced order response model with full details."""
    id: str
    client: EnhancedClientResponse
    portrait: EnhancedPortraitResponse
    video: Optional[EnhancedVideoResponse]
    created_at: str
    status: str = "completed"
    notes: Optional[str] = None


# Enhanced search and filter models
class EnhancedSearchFilter(BaseModel):
    """Enhanced search filter model with validation."""
    query: Optional[str] = Field(None, max_length=100)
    date_from: Optional[str] = Field(None, description="ISO date string (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="ISO date string (YYYY-MM-DD)")
    status: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = Field(None)
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)
    sort_by: str = Field("created_at", max_length=50)
    sort_order: str = Field("desc", pattern="^(asc|desc)$")
    
    @validator('query')
    def sanitize_query(cls, v):
        if v is None:
            return v
        return EnhancedValidator.sanitize_string(v, max_length=100)
    
    @validator('tags')
    def validate_tags(cls, v):
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("Maximum 10 tags allowed")
        return [EnhancedValidator.sanitize_string(tag, max_length=50) for tag in v]
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        allowed_fields = [
            'created_at', 'updated_at', 'name', 'title', 'view_count', 
            'phone', 'email', 'status', 'duration'
        ]
        if v not in allowed_fields:
            raise ValueError(f"Sort field must be one of: {', '.join(allowed_fields)}")
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_dates(cls, values):
        date_from = values.get('date_from')
        date_to = values.get('date_to')
        
        if date_from:
            try:
                datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError("date_from must be a valid ISO date string")
        
        if date_to:
            try:
                datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError("date_to must be a valid ISO date string")
        
        return values