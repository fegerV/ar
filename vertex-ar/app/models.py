"""
Pydantic models for Vertex AR application.
Contains request/response models for API endpoints.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Authentication models
class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=1, max_length=256)


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# AR Content models
class ARContentResponse(BaseModel):
    id: str
    ar_url: str
    qr_code_base64: Optional[str]
    image_path: str
    video_path: str
    created_at: str


# Client models
class ClientCreate(BaseModel):
    phone: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=150)


class ClientUpdate(BaseModel):
    phone: Optional[str] = Field(None, min_length=1, max_length=20)
    name: Optional[str] = Field(None, min_length=1, max_length=150)


class ClientResponse(BaseModel):
    id: str
    phone: str
    name: str
    created_at: str


# Order models
class OrderCreate(BaseModel):
    phone: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=150)


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