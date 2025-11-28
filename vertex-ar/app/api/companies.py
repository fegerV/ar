"""
Company management endpoints for Vertex AR API.
"""
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.database import Database
from app.models import (
    CompanyCreate,
    CompanyListItem,
    CompanyResponse,
    PaginatedCompaniesResponse,
    MessageResponse,
)
from logging_setup import get_logger

logger = get_logger(__name__)
router = APIRouter()


def get_database() -> Database:
    """Get database instance."""
    from app.main import get_current_app
    app = get_current_app()
    if not hasattr(app.state, 'database'):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not initialized"
        )
    return app.state.database


def _get_admin_user(request: Request) -> str:
    """Get and verify admin user from request."""
    from app.main import get_current_app
    auth_token = request.cookies.get("authToken")
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        app = get_current_app()
        tokens = app.state.tokens
        username = tokens.verify_token(auth_token)
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        database = get_database()
        user = database.get_user(username)
        if not user or not user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return username
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error verifying admin user: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


@router.post("/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    request: Request,
    company: CompanyCreate,
) -> CompanyResponse:
    """Create a new company."""
    username = _get_admin_user(request)
    database = get_database()
    
    # Check if company with this name already exists
    existing = database.get_company_by_name(company.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Company '{company.name}' already exists"
        )
    
    # Validate storage configuration
    if company.storage_type != 'local' and company.storage_connection_id:
        connection = database.get_storage_connection(company.storage_connection_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage connection not found"
            )
        
        if not connection['is_active'] or not connection['is_tested']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Storage connection must be active and tested"
            )
    elif company.storage_type != 'local' and not company.storage_connection_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Storage connection ID is required for remote storage"
        )
    
    company_id = f"company-{uuid4().hex[:8]}"
    
    try:
        database.create_company(
            company_id, 
            company.name,
            company.storage_type,
            company.storage_connection_id,
            company.yandex_disk_folder_id,
            company.content_types
        )
        created_company = database.get_company(company_id)
        
        return CompanyResponse(
            id=created_company["id"],
            name=created_company["name"],
            storage_type=created_company["storage_type"],
            storage_connection_id=created_company.get("storage_connection_id"),
            yandex_disk_folder_id=created_company.get("yandex_disk_folder_id"),
            content_types=created_company.get("content_types"),
            created_at=created_company["created_at"],
        )
    except Exception as exc:
        logger.error(f"Error creating company: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create company"
        )


@router.get("/companies", response_model=PaginatedCompaniesResponse)
async def list_companies(
    request: Request,
) -> PaginatedCompaniesResponse:
    """Get list of all companies."""
    username = _get_admin_user(request)
    database = get_database()
    
    try:
        companies = database.get_companies_with_client_count()
        
        items = [
            CompanyListItem(
                id=c["id"],
                name=c["name"],
                storage_type=c.get("storage_type", "local"),
                storage_connection_id=c.get("storage_connection_id"),
                yandex_disk_folder_id=c.get("yandex_disk_folder_id"),
                content_types=c.get("content_types"),
                created_at=c["created_at"],
                client_count=c.get("client_count", 0),
            )
            for c in companies
        ]
        
        return PaginatedCompaniesResponse(
            items=items,
            total=len(items),
        )
    except Exception as exc:
        logger.error(f"Error listing companies: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list companies"
        )


@router.get("/companies/{company_id}", response_model=CompanyResponse)
async def get_company(
    request: Request,
    company_id: str,
) -> CompanyResponse:
    """Get company by ID."""
    username = _get_admin_user(request)
    database = get_database()
    
    company = database.get_company(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    return CompanyResponse(
        id=company["id"],
        name=company["name"],
        storage_type=company.get("storage_type", "local"),
        storage_connection_id=company.get("storage_connection_id"),
        yandex_disk_folder_id=company.get("yandex_disk_folder_id"),
        content_types=company.get("content_types"),
        created_at=company["created_at"],
    )


@router.delete("/companies/{company_id}", response_model=MessageResponse)
async def delete_company(
    request: Request,
    company_id: str,
) -> MessageResponse:
    """Delete company and all related data."""
    username = _get_admin_user(request)
    database = get_database()
    
    # Prevent deletion of default company
    if company_id == "vertex-ar-default":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete default company 'Vertex AR'"
        )
    
    company = database.get_company(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    try:
        success = database.delete_company(company_id)
        if success:
            return MessageResponse(
                message=f"Company '{company['name']}' deleted successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete company"
            )
    except Exception as exc:
        logger.error(f"Error deleting company: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete company"
        )


@router.post("/companies/{company_id}/select", response_model=CompanyResponse)
async def select_company(
    request: Request,
    company_id: str,
) -> CompanyResponse:
    """Select/switch to a company."""
    username = _get_admin_user(request)
    database = get_database()
    
    company = database.get_company(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    return CompanyResponse(
        id=company["id"],
        name=company["name"],
        storage_type=company.get("storage_type", "local"),
        storage_connection_id=company.get("storage_connection_id"),
        yandex_disk_folder_id=company.get("yandex_disk_folder_id"),
        content_types=company.get("content_types"),
        created_at=company["created_at"],
    )
