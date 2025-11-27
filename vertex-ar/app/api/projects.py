"""
API endpoints for project management.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import get_current_user
from app.database import Database
from app.models import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListItem,
    PaginatedProjectsResponse,
    MessageResponse,
)
from logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


def get_database() -> Database:
    from app.main import get_current_app
    return get_current_app().state.database


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_data: ProjectCreate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_database),
) -> ProjectResponse:
    """Create a new project."""
    logger.info(f"Creating project: {project_data.name} in company {project_data.company_id}")
    
    # Check if company exists
    company = db.get_company(project_data.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check if project with same name already exists in company
    existing = db.get_project_by_name(project_data.company_id, project_data.name)
    if existing:
        raise HTTPException(status_code=409, detail="Project with this name already exists in company")
    
    project_id = str(uuid.uuid4())
    try:
        project = db.create_project(
            project_id=project_id,
            company_id=project_data.company_id,
            name=project_data.name,
            description=project_data.description,
            status=project_data.status or "active",
            subscription_end=project_data.subscription_end,
        )
        logger.info(f"Project created: {project_id}")
        return ProjectResponse(**project)
    except ValueError as e:
        if "project_already_exists" in str(e):
            raise HTTPException(status_code=409, detail="Project already exists")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_database),
) -> ProjectResponse:
    """Get project by ID."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(**project)


@router.get("", response_model=PaginatedProjectsResponse)
async def list_projects(
    company_id: Optional[str] = Query(None, description="Filter by company ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_database),
) -> PaginatedProjectsResponse:
    """List all projects with pagination."""
    offset = (page - 1) * page_size
    
    projects = db.list_projects(company_id=company_id, limit=page_size, offset=offset)
    total = db.count_projects(company_id=company_id)
    
    # Enrich with counts
    items = []
    for project in projects:
        folder_count = db.get_project_folder_count(project["id"])
        portrait_count = db.get_project_portrait_count(project["id"])
        items.append(
            ProjectListItem(
                **project,
                folder_count=folder_count,
                portrait_count=portrait_count,
            )
        )
    
    total_pages = (total + page_size - 1) // page_size
    
    return PaginatedProjectsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_database),
) -> ProjectResponse:
    """Update project."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if new name conflicts with existing project in same company
    if project_data.name:
        existing = db.get_project_by_name(project["company_id"], project_data.name)
        if existing and existing["id"] != project_id:
            raise HTTPException(status_code=409, detail="Project with this name already exists in company")
    
    success = db.update_project(
        project_id=project_id,
        name=project_data.name,
        description=project_data.description,
        status=project_data.status,
        subscription_end=project_data.subscription_end,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="No changes made")
    
    updated_project = db.get_project(project_id)
    logger.info(f"Project updated: {project_id}")
    return ProjectResponse(**updated_project)


@router.delete("/{project_id}", response_model=MessageResponse)
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_database),
) -> MessageResponse:
    """Delete project and all related folders (cascade)."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    success = db.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete project")
    
    logger.info(f"Project deleted: {project_id}")
    return MessageResponse(message="Project deleted successfully")
