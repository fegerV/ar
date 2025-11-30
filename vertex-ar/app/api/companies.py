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
    YandexFolderUpdate,
    CompanyContentTypesUpdate,
    ContentTypeItem,
    CompanyStorageTypeUpdate,
    CompanyStorageFolderUpdate,
    CompanyStorageInfoResponse,
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
            company.content_types,
            company.storage_folder_path
        )
        created_company = database.get_company(company_id)
        
        return CompanyResponse(
            id=created_company["id"],
            name=created_company["name"],
            storage_type=created_company["storage_type"],
            storage_connection_id=created_company.get("storage_connection_id"),
            yandex_disk_folder_id=created_company.get("yandex_disk_folder_id"),
            content_types=created_company.get("content_types"),
            storage_folder_path=created_company.get("storage_folder_path"),
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
                storage_folder_path=c.get("storage_folder_path"),
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


@router.post("/companies/{company_id}/yandex-disk-folder", response_model=CompanyResponse)
async def set_company_yandex_folder(
    request: Request,
    company_id: str,
    folder_update: YandexFolderUpdate,
) -> CompanyResponse:
    """
    Set Yandex Disk folder for a company.
    
    Validates that the company uses Yandex Disk storage,
    verifies the folder exists on Yandex Disk,
    and persists the selection to the database.
    """
    username = _get_admin_user(request)
    database = get_database()
    
    # Get company
    company = database.get_company(company_id)
    if not company:
        logger.error(
            "Company not found",
            company_id=company_id,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Validate company uses Yandex Disk storage
    if company.get('storage_type') != 'yandex_disk':
        logger.error(
            "Company does not use Yandex Disk storage",
            company_id=company_id,
            storage_type=company.get('storage_type'),
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company must use Yandex Disk storage type"
        )
    
    storage_connection_id = company.get('storage_connection_id')
    if not storage_connection_id:
        logger.error(
            "Company has no storage connection",
            company_id=company_id,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company has no storage connection configured"
        )
    
    # Get storage connection
    connection = database.get_storage_connection(storage_connection_id)
    if not connection:
        logger.error(
            "Storage connection not found",
            company_id=company_id,
            storage_connection_id=storage_connection_id,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storage connection not found"
        )
    
    if not connection.get('is_active'):
        logger.error(
            "Storage connection is inactive",
            company_id=company_id,
            storage_connection_id=storage_connection_id,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Storage connection is inactive"
        )
    
    # Get OAuth token from connection
    config = connection.get('config', {})
    oauth_token = config.get('oauth_token')
    if not oauth_token:
        logger.error(
            "No OAuth token in storage connection",
            company_id=company_id,
            storage_connection_id=storage_connection_id,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Storage connection has no OAuth token configured"
        )
    
    # Verify folder exists on Yandex Disk
    try:
        from app.storage_yandex import YandexDiskStorageAdapter
        
        # Create adapter with empty base_path to check absolute path
        adapter = YandexDiskStorageAdapter(oauth_token=oauth_token, base_path="")
        
        # Check if folder exists
        folder_exists = await adapter.file_exists(folder_update.folder_path)
        if not folder_exists:
            logger.error(
                "Yandex Disk folder not found",
                company_id=company_id,
                folder_path=folder_update.folder_path,
                user=username
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Folder not found on Yandex Disk: {folder_update.folder_path}"
            )
        
        logger.info(
            "Verified Yandex Disk folder exists",
            company_id=company_id,
            folder_path=folder_update.folder_path,
            user=username
        )
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to verify Yandex Disk folder",
            error=str(exc),
            company_id=company_id,
            folder_path=folder_update.folder_path,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify folder: {str(exc)}"
        )
    
    # Save folder path to database
    try:
        success = database.set_company_yandex_folder(company_id, folder_update.folder_path)
        if not success:
            logger.error(
                "Failed to update company Yandex folder in database",
                company_id=company_id,
                folder_path=folder_update.folder_path,
                user=username
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update company folder"
            )
        
        logger.info(
            "Set company Yandex Disk folder",
            company_id=company_id,
            folder_path=folder_update.folder_path,
            user=username
        )
        
        # Clear company storage adapter cache
        from storage_manager import get_storage_manager
        storage_manager = get_storage_manager()
        storage_manager.clear_company_cache(company_id)
        
        # Return updated company
        updated_company = database.get_company(company_id)
        return CompanyResponse(
            id=updated_company["id"],
            name=updated_company["name"],
            storage_type=updated_company.get("storage_type", "local"),
            storage_connection_id=updated_company.get("storage_connection_id"),
            yandex_disk_folder_id=updated_company.get("yandex_disk_folder_id"),
            content_types=updated_company.get("content_types"),
            created_at=updated_company["created_at"],
        )
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to set company Yandex folder",
            error=str(exc),
            company_id=company_id,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update company"
        )


@router.post("/companies/{company_id}/content-types", response_model=dict)
async def update_company_content_types(
    request: Request,
    company_id: str,
    content_types_update: CompanyContentTypesUpdate,
) -> dict:
    """
    Update content types for a company.
    
    Accepts a list of content types with labels (and optional slugs).
    Slugs are auto-generated from labels if not provided.
    At least one content type with a unique slug is required.
    Returns the normalized list for immediate UI feedback.
    """
    username = _get_admin_user(request)
    database = get_database()
    
    # Get company
    company = database.get_company(company_id)
    if not company:
        logger.error(
            "Company not found",
            company_id=company_id,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Build comma-separated content types string
    # Format: slug1:label1,slug2:label2
    content_types_parts = []
    normalized_list = []
    
    for item in content_types_update.content_types:
        content_types_parts.append(f"{item.slug}:{item.label}")
        normalized_list.append({
            "slug": item.slug,
            "label": item.label
        })
    
    content_types_str = ",".join(content_types_parts)
    
    # Save to database
    try:
        success = database.update_company_content_types(company_id, content_types_str)
        if not success:
            logger.error(
                "Failed to update company content types in database",
                company_id=company_id,
                content_types=content_types_str,
                user=username
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update content types"
            )
        
        logger.info(
            "Updated company content types",
            company_id=company_id,
            content_types=content_types_str,
            user=username
        )
        
        return {
            "success": True,
            "content_types": normalized_list,
            "content_types_str": content_types_str
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to update company content types",
            error=str(exc),
            company_id=company_id,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update content types"
        )


@router.get("/companies/{company_id}/storage-info", response_model=CompanyStorageInfoResponse)
async def get_company_storage_info(
    request: Request,
    company_id: str,
) -> CompanyStorageInfoResponse:
    """
    Get storage configuration information for a company.
    
    Returns current storage type, folder path, and configuration status.
    """
    username = _get_admin_user(request)
    database = get_database()
    
    company = database.get_company(company_id)
    if not company:
        logger.error(
            "Company not found",
            company_id=company_id,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    storage_type = company.get("storage_type", "local")
    storage_folder_path = company.get("storage_folder_path")
    yandex_disk_folder_id = company.get("yandex_disk_folder_id")
    storage_connection_id = company.get("storage_connection_id")
    
    is_configured = False
    status_message = ""
    
    if storage_type == "local":
        if storage_folder_path:
            is_configured = True
            status_message = f"✅ Настроено (папка: {storage_folder_path})"
        else:
            status_message = "⚠️ Требуется настройка папки"
    elif storage_type == "yandex_disk":
        if yandex_disk_folder_id and storage_connection_id:
            is_configured = True
            status_message = f"✅ Настроено (Яндекс Диск: {yandex_disk_folder_id})"
        else:
            status_message = "⚠️ Требуется выбор папки на Яндекс Диске"
    else:
        if storage_connection_id:
            is_configured = True
            status_message = "✅ Настроено"
        else:
            status_message = "⚠️ Требуется подключение к хранилищу"
    
    logger.info(
        "Retrieved company storage info",
        company_id=company_id,
        storage_type=storage_type,
        is_configured=is_configured,
        user=username
    )
    
    return CompanyStorageInfoResponse(
        company_id=company["id"],
        company_name=company["name"],
        storage_type=storage_type,
        storage_folder_path=storage_folder_path,
        yandex_disk_folder_id=yandex_disk_folder_id,
        storage_connection_id=storage_connection_id,
        is_configured=is_configured,
        status_message=status_message,
    )


@router.put("/companies/{company_id}/storage-type", response_model=CompanyResponse)
async def update_company_storage_type(
    request: Request,
    company_id: str,
    storage_update: CompanyStorageTypeUpdate,
) -> CompanyResponse:
    """
    Update the storage type for a company.
    
    Valid storage types: local, minio, yandex_disk
    """
    username = _get_admin_user(request)
    database = get_database()
    
    company = database.get_company(company_id)
    if not company:
        logger.error(
            "Company not found",
            company_id=company_id,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    try:
        success = database.update_company(
            company_id,
            storage_type=storage_update.storage_type
        )
        
        if not success:
            logger.error(
                "Failed to update company storage type",
                company_id=company_id,
                storage_type=storage_update.storage_type,
                user=username
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update storage type"
            )
        
        logger.info(
            "Updated company storage type",
            company_id=company_id,
            old_type=company.get("storage_type"),
            new_type=storage_update.storage_type,
            user=username
        )
        
        updated_company = database.get_company(company_id)
        return CompanyResponse(
            id=updated_company["id"],
            name=updated_company["name"],
            storage_type=updated_company["storage_type"],
            storage_connection_id=updated_company.get("storage_connection_id"),
            yandex_disk_folder_id=updated_company.get("yandex_disk_folder_id"),
            content_types=updated_company.get("content_types"),
            storage_folder_path=updated_company.get("storage_folder_path"),
            created_at=updated_company["created_at"],
        )
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to update company storage type",
            error=str(exc),
            company_id=company_id,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update storage type"
        )


@router.post("/companies/{company_id}/storage-folder", response_model=CompanyResponse)
async def create_or_update_company_storage_folder(
    request: Request,
    company_id: str,
    folder_update: CompanyStorageFolderUpdate,
) -> CompanyResponse:
    """
    Create or update storage folder for a company (for local storage).
    
    Validates folder name and creates the folder on disk.
    """
    username = _get_admin_user(request)
    database = get_database()
    
    company = database.get_company(company_id)
    if not company:
        logger.error(
            "Company not found",
            company_id=company_id,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    if company.get("storage_type") != "local":
        logger.error(
            "Company does not use local storage",
            company_id=company_id,
            storage_type=company.get("storage_type"),
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Storage folder is only applicable for local storage type"
        )
    
    try:
        from pathlib import Path
        
        folder_path = folder_update.folder_path
        
        base_path = Path("app_data") / folder_path
        base_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "Created storage folder",
            company_id=company_id,
            folder_path=folder_path,
            full_path=str(base_path),
            user=username
        )
        
        success = database.update_company(
            company_id,
            storage_folder_path=folder_path
        )
        
        if not success:
            logger.error(
                "Failed to update company storage folder in database",
                company_id=company_id,
                folder_path=folder_path,
                user=username
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update storage folder"
            )
        
        updated_company = database.get_company(company_id)
        return CompanyResponse(
            id=updated_company["id"],
            name=updated_company["name"],
            storage_type=updated_company["storage_type"],
            storage_connection_id=updated_company.get("storage_connection_id"),
            yandex_disk_folder_id=updated_company.get("yandex_disk_folder_id"),
            content_types=updated_company.get("content_types"),
            storage_folder_path=updated_company.get("storage_folder_path"),
            created_at=updated_company["created_at"],
        )
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to create/update storage folder",
            error=str(exc),
            company_id=company_id,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create/update storage folder: {str(exc)}"
        )
