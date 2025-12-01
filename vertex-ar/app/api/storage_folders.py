"""
Storage folders management endpoints for Vertex AR API.
Handles CRUD operations for local storage folder structure.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.database import Database
from app.models import (
    CompanyStorageStatusResponse,
    MessageResponse,
    StorageFolderCreateRequest,
    StorageFolderDeleteRequest,
    StorageFolderItem,
    StorageFolderOperationResponse,
    StorageFoldersListResponse,
)
from app.services import get_storage_folders_service
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


@router.get("/companies/{company_id}/storage", response_model=CompanyStorageStatusResponse)
async def get_company_storage_status(
    request: Request,
    company_id: str,
) -> CompanyStorageStatusResponse:
    """
    Get storage configuration and status for a company.
    
    Returns current storage type, paths, permissions, and configuration status.
    """
    username = _get_admin_user(request)
    database = get_database()
    service = get_storage_folders_service()
    
    # Get company from database
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
        # Get storage status from service
        storage_status = service.get_storage_status(company_id)
        
        # Determine configuration status
        storage_type = company.get("storage_type", "local")
        storage_folder_path = company.get("storage_folder_path")
        yandex_disk_folder_id = company.get("yandex_disk_folder_id")
        storage_connection_id = company.get("storage_connection_id")
        
        is_configured = False
        status_message = ""
        
        if storage_type == "local":
            if storage_status["is_ready"]:
                is_configured = True
                status_message = f"✅ Ready (path: {storage_status['company_path']})"
            else:
                status_message = "⚠️ Storage folder not accessible - check permissions"
        elif storage_type == "yandex_disk":
            if yandex_disk_folder_id and storage_connection_id:
                is_configured = True
                status_message = f"✅ Configured (Yandex Disk: {yandex_disk_folder_id})"
            else:
                status_message = "⚠️ Requires Yandex Disk folder selection"
        else:
            if storage_connection_id:
                is_configured = True
                status_message = "✅ Configured"
            else:
                status_message = "⚠️ Requires storage connection"
        
        logger.info(
            "Retrieved company storage status",
            company_id=company_id,
            storage_type=storage_type,
            is_configured=is_configured,
            is_ready=storage_status["is_ready"],
            user=username
        )
        
        return CompanyStorageStatusResponse(
            company_id=company["id"],
            company_name=company["name"],
            storage_type=storage_type,
            storage_root=storage_status["storage_root"],
            company_path=storage_status["company_path"],
            permissions=storage_status["permissions"],
            content_types=storage_status["content_types"],
            is_ready=storage_status["is_ready"],
            is_configured=is_configured,
            status_message=status_message,
        )
        
    except Exception as exc:
        logger.error(
            "Failed to get company storage status",
            error=str(exc),
            company_id=company_id,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get storage status: {str(exc)}"
        )


@router.get("/storage/folders/list", response_model=StorageFoldersListResponse)
async def list_storage_folders(
    request: Request,
    company_id: str = Query(..., description="Company identifier"),
    content_type: Optional[str] = Query(None, description="Optional content type filter"),
) -> StorageFoldersListResponse:
    """
    List existing order folders for a company.
    
    Can be filtered by content type (e.g., 'portraits', 'diplomas').
    """
    username = _get_admin_user(request)
    database = get_database()
    service = get_storage_folders_service()
    
    # Verify company exists
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
        # List folders using service
        folders = service.list_order_folders(company_id, content_type)
        
        logger.info(
            "Listed storage folders",
            company_id=company_id,
            content_type=content_type,
            folder_count=len(folders),
            user=username
        )
        
        # Convert to Pydantic models
        folder_items = [
            StorageFolderItem(**folder)
            for folder in folders
        ]
        
        return StorageFoldersListResponse(
            company_id=company_id,
            folders=folder_items,
            total=len(folder_items),
        )
        
    except Exception as exc:
        logger.error(
            "Failed to list storage folders",
            error=str(exc),
            company_id=company_id,
            content_type=content_type,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list folders: {str(exc)}"
        )


@router.post("/storage/folders/create", response_model=StorageFolderOperationResponse)
async def create_storage_folder(
    request: Request,
    folder_request: StorageFolderCreateRequest,
) -> StorageFolderOperationResponse:
    """
    Create a new order folder with required subdirectory structure.
    
    Creates folder with subdirectories: Image, QR, nft_markers, nft_cache
    Enforces uniqueness and permission checks.
    """
    username = _get_admin_user(request)
    database = get_database()
    service = get_storage_folders_service()
    
    # Verify company exists
    company = database.get_company(folder_request.company_id)
    if not company:
        logger.error(
            "Company not found",
            company_id=folder_request.company_id,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    try:
        # Create folder using service
        success, message, folder_path = service.create_order_folder(
            company_id=folder_request.company_id,
            content_type=folder_request.content_type,
            folder_name=folder_request.folder_name
        )
        
        if not success:
            logger.warning(
                "Failed to create storage folder",
                company_id=folder_request.company_id,
                content_type=folder_request.content_type,
                folder_name=folder_request.folder_name,
                reason=message,
                user=username
            )
            return StorageFolderOperationResponse(
                success=False,
                message=message,
                folder_path=None
            )
        
        logger.info(
            "Created storage folder",
            company_id=folder_request.company_id,
            content_type=folder_request.content_type,
            folder_name=folder_request.folder_name,
            folder_path=str(folder_path) if folder_path else None,
            user=username
        )
        
        return StorageFolderOperationResponse(
            success=True,
            message=message,
            folder_path=str(folder_path) if folder_path else None
        )
        
    except Exception as exc:
        logger.error(
            "Exception creating storage folder",
            error=str(exc),
            company_id=folder_request.company_id,
            content_type=folder_request.content_type,
            folder_name=folder_request.folder_name,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create folder: {str(exc)}"
        )


@router.post("/storage/folders/delete", response_model=StorageFolderOperationResponse)
async def delete_storage_folder(
    request: Request,
    folder_request: StorageFolderDeleteRequest,
) -> StorageFolderOperationResponse:
    """
    Delete an order folder.
    
    Only allows deletion of empty folders unless force=True is specified.
    """
    username = _get_admin_user(request)
    database = get_database()
    service = get_storage_folders_service()
    
    # Verify company exists
    company = database.get_company(folder_request.company_id)
    if not company:
        logger.error(
            "Company not found",
            company_id=folder_request.company_id,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    try:
        # Delete folder using service
        success, message = service.delete_order_folder(
            company_id=folder_request.company_id,
            content_type=folder_request.content_type,
            folder_name=folder_request.folder_name,
            force=folder_request.force
        )
        
        if not success:
            logger.warning(
                "Failed to delete storage folder",
                company_id=folder_request.company_id,
                content_type=folder_request.content_type,
                folder_name=folder_request.folder_name,
                reason=message,
                user=username
            )
            return StorageFolderOperationResponse(
                success=False,
                message=message,
                folder_path=None
            )
        
        logger.info(
            "Deleted storage folder",
            company_id=folder_request.company_id,
            content_type=folder_request.content_type,
            folder_name=folder_request.folder_name,
            force=folder_request.force,
            user=username
        )
        
        return StorageFolderOperationResponse(
            success=True,
            message=message,
            folder_path=None
        )
        
    except Exception as exc:
        logger.error(
            "Exception deleting storage folder",
            error=str(exc),
            company_id=folder_request.company_id,
            content_type=folder_request.content_type,
            folder_name=folder_request.folder_name,
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete folder: {str(exc)}"
        )
