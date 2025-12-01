"""
Pydantic models for category management (wrapping projects table).
"""
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.validators import validate_name


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Display name for category")
    slug: str = Field(..., min_length=1, max_length=100, description="URL/storage-friendly identifier")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")
    
    @field_validator('name')
    @classmethod
    def validate_name_field(cls, v: str) -> str:
        return validate_name(v)
    
    @field_validator('slug')
    @classmethod
    def validate_slug_field(cls, v: str) -> str:
        import re
        if not v or not v.strip():
            raise ValueError('Slug is required')
        v = v.strip().lower()
        if not re.match(r'^[a-z0-9-_]+$', v):
            raise ValueError('Slug can only contain lowercase letters, numbers, dashes, and underscores')
        return v


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Display name")
    slug: Optional[str] = Field(None, min_length=1, max_length=100, description="URL/storage-friendly identifier")
    description: Optional[str] = Field(None, max_length=500, description="Description")
    
    @field_validator('name')
    @classmethod
    def validate_name_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_name(v)
        return v
    
    @field_validator('slug')
    @classmethod
    def validate_slug_field(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            import re
            v = v.strip().lower()
            if not re.match(r'^[a-z0-9-_]+$', v):
                raise ValueError('Slug can only contain lowercase letters, numbers, dashes, and underscores')
            return v
        return v


class CategoryResponse(BaseModel):
    id: str
    company_id: str
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    created_at: str
    folder_count: int = 0
    portrait_count: int = 0


class PaginatedCategoriesResponse(BaseModel):
    items: List[CategoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
