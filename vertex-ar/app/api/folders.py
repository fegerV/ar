"""
API endpoints for folder management.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import get_current_user
from app.database import Database
from app.models import (
    FolderCreate,
    FolderUpdate,
    FolderResponse,
    FolderListItem,
    PaginatedFoldersResponse,
    MessageResponse,
)
from logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/folders", tags=["folders"])


def get_database() -> Database:
    from app.main import get_current_app
    return get_current_app().state.database


@router.post("", response_model=FolderResponse, status_code=201)
async def create_folder(
    folder_data: FolderCreate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_database),
) -> FolderResponse:
    """Create a new folder."""
    logger.info(f"Creating folder: {folder_data.name} in project {folder_data.project_id}")

    # Check if project exists
    project = db.get_project(folder_data.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if folder with same name already exists in project
    existing = db.get_folder_by_name(folder_data.project_id, folder_data.name)
    if existing:
        raise HTTPException(status_code=409, detail="Folder with this name already exists in project")

    folder_id = str(uuid.uuid4())
    try:
        folder = db.create_folder(
            folder_id=folder_id,
            project_id=folder_data.project_id,
            name=folder_data.name,
            description=folder_data.description,
        )
        logger.info(f"Folder created: {folder_id}")
        return FolderResponse(**folder)
    except ValueError as e:
        if "folder_already_exists" in str(e):
            raise HTTPException(status_code=409, detail="Folder already exists")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{folder_id}", response_model=FolderResponse)
async def get_folder(
    folder_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_database),
) -> FolderResponse:
    """Get folder by ID."""
    folder = db.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return FolderResponse(**folder)


@router.get("", response_model=PaginatedFoldersResponse)
async def list_folders(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    company_id: Optional[str] = Query(None, description="Filter by company ID (joins through projects)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_database),
) -> PaginatedFoldersResponse:
    """List all folders with pagination."""
    offset = (page - 1) * page_size

    # Handle filtering by company_id or project_id
    folders = db.list_folders(project_id=project_id, company_id=company_id, limit=page_size, offset=offset)
    total = db.count_folders(project_id=project_id, company_id=company_id)

    # Enrich with counts
    items = []
    for folder in folders:
        portrait_count = db.get_folder_portrait_count(folder["id"])
        items.append(
            FolderListItem(
                **folder,
                portrait_count=portrait_count,
            )
        )

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1

    return PaginatedFoldersResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.put("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: str,
    folder_data: FolderUpdate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_database),
) -> FolderResponse:
    """Update folder."""
    folder = db.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Check if new name conflicts with existing folder in same project
    if folder_data.name:
        existing = db.get_folder_by_name(folder["project_id"], folder_data.name)
        if existing and existing["id"] != folder_id:
            raise HTTPException(status_code=409, detail="Folder with this name already exists in project")

    success = db.update_folder(
        folder_id=folder_id,
        name=folder_data.name,
        description=folder_data.description,
    )

    if not success:
        raise HTTPException(status_code=400, detail="No changes made")

    updated_folder = db.get_folder(folder_id)
    logger.info(f"Folder updated: {folder_id}")
    return FolderResponse(**updated_folder)


@router.delete("/{folder_id}", response_model=MessageResponse)
async def delete_folder(
    folder_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_database),
) -> MessageResponse:
    """Delete folder."""
    folder = db.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Check if folder has portraits
    portrait_count = db.get_folder_portrait_count(folder_id)
    if portrait_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete folder with {portrait_count} portraits. Please remove or reassign portraits first."
        )

    success = db.delete_folder(folder_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete folder")

    logger.info(f"Folder deleted: {folder_id}")
    return MessageResponse(message="Folder deleted successfully")
