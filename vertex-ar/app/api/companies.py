"""
Company management endpoints for Vertex AR API.
"""
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.database import Database
from app.models import (
    CompanyCreate,
    CompanyUpdate,
    CompanyListItem,
    CompanyResponse,
    PaginatedCompaniesResponse,
    MessageResponse,
    YandexFolderUpdate,
    CompanyStorageTypeUpdate,
    CompanyStorageFolderUpdate,
    CompanyStorageInfoResponse,
)
from app.models_categories import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    PaginatedCategoriesResponse,
)
from app.storage_utils import is_local_storage
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
    if not is_local_storage(company.storage_type) and company.storage_connection_id:
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
    elif not is_local_storage(company.storage_type) and not company.storage_connection_id:
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
            company.storage_folder_path,
            company.backup_provider,
            company.backup_remote_path,
            company.email,
            company.description,
            company.city,
            company.phone,
            company.website,
            company.social_links,
            company.manager_name,
            company.manager_phone,
            company.manager_email
        )
        created_company = database.get_company(company_id)

        # Automatically provision default folder structure for the new company
        # Only for local storage types
        from app.storage_utils import is_local_storage
        if is_local_storage(created_company.get("storage_type", "local")):
            try:
                # Get storage manager
                from storage_manager import get_storage_manager
                storage_manager = get_storage_manager()

                # Provision default categories (portraits, certificates, diplomas)
                category_slugs = ["portraits", "certificates", "diplomas"]
                provision_result = await storage_manager.provision_company_storage(company_id, category_slugs)

                if not provision_result.get("success", False):
                    logger.error(
                        "Failed to provision folder structure for new company",
                        company_id=company_id,
                        error=provision_result.get("error")
                    )
                    # Rollback company creation if folder provisioning fails
                    database.delete_company(company_id)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to provision folder structure for company"
                    )

                logger.info(
                    "Successfully provisioned folder structure for new company",
                    company_id=company_id,
                    result=provision_result
                )
            except Exception as provision_exc:
                logger.error(
                    "Error provisioning folder structure for new company",
                    company_id=company_id,
                    error=str(provision_exc)
                )
                # Rollback company creation if folder provisioning fails
                database.delete_company(company_id)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to provision folder structure: {str(provision_exc)}"
                )

        return CompanyResponse(
            id=created_company["id"],
            name=created_company["name"],
            storage_type=created_company["storage_type"],
            storage_connection_id=created_company.get("storage_connection_id"),
            yandex_disk_folder_id=created_company.get("yandex_disk_folder_id"),
            content_types=created_company.get("content_types"),
            storage_folder_path=created_company.get("storage_folder_path"),
            backup_provider=created_company.get("backup_provider"),
            backup_remote_path=created_company.get("backup_remote_path"),
            email=created_company.get("email"),
            description=created_company.get("description"),
            city=created_company.get("city"),
            phone=created_company.get("phone"),
            website=created_company.get("website"),
            social_links=created_company.get("social_links"),
            manager_name=created_company.get("manager_name"),
            manager_phone=created_company.get("manager_phone"),
            manager_email=created_company.get("manager_email"),
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
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    storage_type: Optional[str] = None,
) -> PaginatedCompaniesResponse:
    """
    Get list of companies with pagination and filtering.

    Query parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 50, max: 200)
    - search: Search query for company name
    - storage_type: Filter by storage type (local, local_disk, minio, yandex_disk)
    """
    username = _get_admin_user(request)
    database = get_database()

    # Validate pagination params
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 200:
        page_size = 50

    offset = (page - 1) * page_size

    try:
        # Get paginated companies
        companies = database.list_companies_paginated(
            limit=page_size,
            offset=offset,
            search=search,
            storage_type=storage_type
        )

        # Get total count for pagination
        total = database.count_companies_filtered(search=search, storage_type=storage_type)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        items = [
            CompanyListItem(
                id=c["id"],
                name=c["name"],
                storage_type=c.get("storage_type", "local"),
                storage_connection_id=c.get("storage_connection_id"),
                yandex_disk_folder_id=c.get("yandex_disk_folder_id"),
                content_types=c.get("content_types"),
                storage_folder_path=c.get("storage_folder_path"),
                backup_provider=c.get("backup_provider"),
                backup_remote_path=c.get("backup_remote_path"),
                email=c.get("email"),
                description=c.get("description"),
                city=c.get("city"),
                phone=c.get("phone"),
                website=c.get("website"),
                social_links=c.get("social_links"),
                manager_name=c.get("manager_name"),
                manager_phone=c.get("manager_phone"),
                manager_email=c.get("manager_email"),
                created_at=c["created_at"],
                client_count=c.get("client_count", 0),
            )
            for c in companies
        ]

        return PaginatedCompaniesResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
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
        storage_folder_path=company.get("storage_folder_path"),
        backup_provider=company.get("backup_provider"),
        backup_remote_path=company.get("backup_remote_path"),
        email=company.get("email"),
        description=company.get("description"),
        city=company.get("city"),
        phone=company.get("phone"),
        website=company.get("website"),
        social_links=company.get("social_links"),
        manager_name=company.get("manager_name"),
        manager_phone=company.get("manager_phone"),
        manager_email=company.get("manager_email"),
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


@router.put("/companies/{company_id}", response_model=CompanyResponse)
@router.patch("/companies/{company_id}", response_model=CompanyResponse)
async def update_company(
    request: Request,
    company_id: str,
    company_update: CompanyUpdate,
) -> CompanyResponse:
    """
    Update company fields (PUT for full replacement, PATCH for partial update).

    Can update: name, storage_type, storage_connection_id, yandex_disk_folder_id,
    content_types, storage_folder_path, backup_provider, backup_remote_path,
    email, description, city, phone, website, social_links,
    manager_name, manager_phone, manager_email
    """
    username = _get_admin_user(request)
    database = get_database()

    # Prevent updating default company name
    company = database.get_company(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    if company_id == "vertex-ar-default" and company_update.name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot rename default company 'Vertex AR'"
        )

    # Prevent updating default company storage settings
    if company_id == "vertex-ar-default":
        if (company_update.storage_type is not None and company_update.storage_type != "local_disk") or \
           (company_update.storage_folder_path is not None and company_update.storage_folder_path != "vertex_ar_content"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot change storage settings for default company 'Vertex AR'. It must use local_disk with vertex_ar_content folder."
            )

    # Validate storage configuration if being updated
    if company_update.storage_type and not is_local_storage(company_update.storage_type):
        # If changing to remote storage, ensure connection_id is provided
        connection_id = company_update.storage_connection_id or company.get("storage_connection_id")
        if not connection_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Storage connection ID is required for remote storage types"
            )

        # Validate connection exists and is active
        connection = database.get_storage_connection(connection_id)
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

    # Build update dict from provided fields
    update_fields = {}
    if company_update.name is not None:
        update_fields['name'] = company_update.name
    if company_update.storage_type is not None:
        update_fields['storage_type'] = company_update.storage_type
    if company_update.storage_connection_id is not None:
        update_fields['storage_connection_id'] = company_update.storage_connection_id
    if company_update.yandex_disk_folder_id is not None:
        update_fields['yandex_disk_folder_id'] = company_update.yandex_disk_folder_id
    if company_update.content_types is not None:
        update_fields['content_types'] = company_update.content_types
    if company_update.storage_folder_path is not None:
        update_fields['storage_folder_path'] = company_update.storage_folder_path
    if company_update.backup_provider is not None:
        update_fields['backup_provider'] = company_update.backup_provider
    if company_update.backup_remote_path is not None:
        update_fields['backup_remote_path'] = company_update.backup_remote_path
    if company_update.email is not None:
        update_fields['email'] = company_update.email
    if company_update.description is not None:
        update_fields['description'] = company_update.description
    if company_update.city is not None:
        update_fields['city'] = company_update.city
    if company_update.phone is not None:
        update_fields['phone'] = company_update.phone
    if company_update.website is not None:
        update_fields['website'] = company_update.website
    if company_update.social_links is not None:
        update_fields['social_links'] = company_update.social_links
    if company_update.manager_name is not None:
        update_fields['manager_name'] = company_update.manager_name
    if company_update.manager_phone is not None:
        update_fields['manager_phone'] = company_update.manager_phone
    if company_update.manager_email is not None:
        update_fields['manager_email'] = company_update.manager_email

    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    try:
        success = database.update_company(company_id, **update_fields)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update company"
            )

        # Clear storage adapter cache if storage config changed
        if any(k in update_fields for k in ['storage_type', 'storage_connection_id', 'yandex_disk_folder_id', 'storage_folder_path']):
            try:
                from storage_manager import get_storage_manager
                storage_manager = get_storage_manager()
                storage_manager.clear_company_cache(company_id)
            except Exception as cache_exc:
                logger.warning(f"Failed to clear storage cache: {cache_exc}")

        # Return updated company
        updated_company = database.get_company(company_id)
        return CompanyResponse(
            id=updated_company["id"],
            name=updated_company["name"],
            storage_type=updated_company.get("storage_type", "local"),
            storage_connection_id=updated_company.get("storage_connection_id"),
            yandex_disk_folder_id=updated_company.get("yandex_disk_folder_id"),
            content_types=updated_company.get("content_types"),
            storage_folder_path=updated_company.get("storage_folder_path"),
            backup_provider=updated_company.get("backup_provider"),
            backup_remote_path=updated_company.get("backup_remote_path"),
            email=updated_company.get("email"),
            description=updated_company.get("description"),
            city=updated_company.get("city"),
            phone=updated_company.get("phone"),
            website=updated_company.get("website"),
            social_links=updated_company.get("social_links"),
            manager_name=updated_company.get("manager_name"),
            manager_phone=updated_company.get("manager_phone"),
            manager_email=updated_company.get("manager_email"),
            created_at=updated_company["created_at"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error updating company: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update company"
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

    if is_local_storage(storage_type):
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

    # Prevent updating default company storage type
    if company_id == "vertex-ar-default" and storage_update.storage_type != "local_disk":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change storage type for default company 'Vertex AR'. It must use local_disk."
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

    # Accept both 'local' and 'local_disk' as local storage types
    from app.storage_utils import is_local_storage
    if not is_local_storage(company.get("storage_type", "")):
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

    # Prevent updating default company storage folder path to anything other than 'vertex_ar_content'
    if company_id == "vertex-ar-default" and folder_update.folder_path != "vertex_ar_content":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change storage folder for default company 'Vertex AR'. It must use 'vertex_ar_content'."
        )

    try:
        from pathlib import Path
        from app.config import settings

        folder_path = folder_update.folder_path

        # For default company, always use vertex_ar_content directory
        if company_id == "vertex-ar-default":
            base_path = Path(settings.STORAGE_ROOT) / "vertex_ar_content"
        else:
            base_path = Path(settings.STORAGE_ROOT) / folder_path
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


# Category endpoints (wrapping projects table)


@router.post("/companies/{company_id}/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    request: Request,
    company_id: str,
    category: CategoryCreate,
) -> CategoryResponse:
    """
    Create a new category for a company.

    Categories are organizational units within a company that can contain portraits/folders.
    Each category has a storage-friendly slug for folder/URL naming.
    """
    username = _get_admin_user(request)
    database = get_database()

    # Verify company exists
    company = database.get_company(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    # Check if slug already exists for this company
    existing = database.get_category_by_slug(company_id, category.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category with slug '{category.slug}' already exists"
        )

    try:
        category_id = f"cat-{uuid4().hex[:8]}"
        created_category = database.create_category(
            category_id=category_id,
            company_id=company_id,
            name=category.name,
            slug=category.slug,
            description=category.description
        )

        # Get folder and portrait counts
        folder_count = database.get_project_folder_count(category_id)
        portrait_count = database.get_project_portrait_count(category_id)

        logger.info(
            "Created category",
            category_id=category_id,
            company_id=company_id,
            name=category.name,
            slug=category.slug,
            user=username
        )

        return CategoryResponse(
            id=created_category["id"],
            company_id=created_category["company_id"],
            name=created_category["name"],
            slug=created_category.get("slug"),
            description=created_category.get("description"),
            created_at=created_category["created_at"],
            folder_count=folder_count,
            portrait_count=portrait_count,
        )
    except ValueError as ve:
        if "already_exists" in str(ve):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Category '{category.name}' already exists"
            )
        raise
    except Exception as exc:
        logger.error(f"Error creating category: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create category"
        )


@router.get("/companies/{company_id}/categories", response_model=PaginatedCategoriesResponse)
async def list_categories(
    request: Request,
    company_id: str,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedCategoriesResponse:
    """
    List all categories for a company with pagination.

    Returns categories with folder and portrait counts.
    """
    username = _get_admin_user(request)
    database = get_database()

    # Verify company exists
    company = database.get_company(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    # Validate pagination params
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 200:
        page_size = 50

    offset = (page - 1) * page_size

    try:
        categories = database.list_categories(
            company_id=company_id,
            limit=page_size,
            offset=offset
        )
        total = database.count_categories(company_id=company_id)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        items = []
        for cat in categories:
            folder_count = database.get_project_folder_count(cat["id"])
            portrait_count = database.get_project_portrait_count(cat["id"])

            items.append(CategoryResponse(
                id=cat["id"],
                company_id=cat["company_id"],
                name=cat["name"],
                slug=cat.get("slug"),
                description=cat.get("description"),
                created_at=cat["created_at"],
                folder_count=folder_count,
                portrait_count=portrait_count,
            ))

        return PaginatedCategoriesResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as exc:
        logger.error(f"Error listing categories: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list categories"
        )


@router.get("/companies/{company_id}/categories/{category_id}", response_model=CategoryResponse)
async def get_category(
    request: Request,
    company_id: str,
    category_id: str,
) -> CategoryResponse:
    """Get a specific category by ID."""
    username = _get_admin_user(request)
    database = get_database()

    category = database.get_project(category_id)
    if not category or category.get("company_id") != company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    folder_count = database.get_project_folder_count(category_id)
    portrait_count = database.get_project_portrait_count(category_id)

    return CategoryResponse(
        id=category["id"],
        company_id=category["company_id"],
        name=category["name"],
        slug=category.get("slug"),
        description=category.get("description"),
        created_at=category["created_at"],
        folder_count=folder_count,
        portrait_count=portrait_count,
    )


@router.put("/companies/{company_id}/categories/{category_id}", response_model=CategoryResponse)
@router.patch("/companies/{company_id}/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    request: Request,
    company_id: str,
    category_id: str,
    category_update: CategoryUpdate,
) -> CategoryResponse:
    """
    Update category name, slug, or description.

    Validates that new slug doesn't conflict with existing categories.
    """
    username = _get_admin_user(request)
    database = get_database()

    # Verify category exists and belongs to company
    category = database.get_project(category_id)
    if not category or category.get("company_id") != company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Check for slug conflict if slug is being updated
    if category_update.slug and category_update.slug != category.get("slug"):
        existing = database.get_category_by_slug(company_id, category_update.slug)
        if existing and existing["id"] != category_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Category with slug '{category_update.slug}' already exists"
            )

    try:
        success = database.rename_category(
            category_id=category_id,
            new_name=category_update.name or category["name"],
            new_slug=category_update.slug
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update category"
            )

        # Update description separately if provided
        if category_update.description is not None:
            database.update_project(category_id, description=category_update.description)

        # Get updated category
        updated_category = database.get_project(category_id)
        folder_count = database.get_project_folder_count(category_id)
        portrait_count = database.get_project_portrait_count(category_id)

        logger.info(
            "Updated category",
            category_id=category_id,
            company_id=company_id,
            user=username
        )

        return CategoryResponse(
            id=updated_category["id"],
            company_id=updated_category["company_id"],
            name=updated_category["name"],
            slug=updated_category.get("slug"),
            description=updated_category.get("description"),
            created_at=updated_category["created_at"],
            folder_count=folder_count,
            portrait_count=portrait_count,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error updating category: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update category"
        )


@router.delete("/companies/{company_id}/categories/{category_id}", response_model=MessageResponse)
async def delete_category(
    request: Request,
    company_id: str,
    category_id: str,
) -> MessageResponse:
    """
    Delete a category.

    This will cascade delete all folders and portraits within the category.
    """
    username = _get_admin_user(request)
    database = get_database()

    # Verify category exists and belongs to company
    category = database.get_project(category_id)
    if not category or category.get("company_id") != company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    try:
        success = database.delete_category(category_id)
        if success:
            logger.info(
                "Deleted category",
                category_id=category_id,
                company_id=company_id,
                name=category["name"],
                user=username
            )
            return MessageResponse(
                message=f"Category '{category['name']}' deleted successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete category"
            )
    except Exception as exc:
        logger.error(f"Error deleting category: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete category"
        )


# Storage workflow endpoints


@router.get("/companies/workflow/storage-options", response_model=List[dict])
async def get_storage_workflow_options(
    request: Request,
) -> List[dict]:
    """
    Get available storage options for company creation workflow.

    Returns list of storage types with connection details:
    - Local storage (always available)
    - Tested remote storage connections (MinIO, Yandex Disk)
    """
    username = _get_admin_user(request)
    database = get_database()

    try:
        options = database.get_available_storage_options()
        logger.info(
            "Retrieved storage workflow options",
            count=len(options),
            user=username
        )
        return options
    except Exception as exc:
        logger.error(f"Error getting storage options: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get storage options"
        )
