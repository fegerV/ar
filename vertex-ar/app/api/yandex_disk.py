"""
Yandex Disk file access API endpoints.
"""
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from urllib.parse import unquote

from app.storage_yandex import YandexDiskStorageAdapter
from app.models import YandexDiskFoldersResponse, YandexDiskFolder
from storage_config import get_storage_config
from logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/yandex-disk", tags=["yandex_disk"])


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
        
        database = app.state.database
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


@router.get("/folders", response_model=YandexDiskFoldersResponse)
async def list_yandex_disk_folders(
    request: Request,
    company_id: Optional[str] = Query(None, description="Company ID to get storage connection from"),
    storage_connection_id: Optional[str] = Query(None, description="Storage connection ID"),
    path: str = Query("", description="Path to list folders from (relative to base)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
) -> YandexDiskFoldersResponse:
    """
    List folders from Yandex Disk.
    
    Admin authentication required. Provide either company_id or storage_connection_id
    to determine which OAuth token to use.
    """
    username = _get_admin_user(request)
    
    try:
        from app.main import get_current_app
        app = get_current_app()
        database = app.state.database
        
        oauth_token = None
        base_path = "vertex-ar"
        
        # Determine OAuth token from company_id or storage_connection_id
        if storage_connection_id:
            connection = database.get_storage_connection(storage_connection_id)
            if not connection:
                logger.error(
                    "Storage connection not found",
                    storage_connection_id=storage_connection_id,
                    user=username
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Storage connection not found"
                )
            
            if connection.get('type') != 'yandex_disk':
                logger.error(
                    "Storage connection is not Yandex Disk type",
                    storage_connection_id=storage_connection_id,
                    type=connection.get('type'),
                    user=username
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Storage connection must be Yandex Disk type"
                )
            
            if not connection.get('is_active'):
                logger.error(
                    "Storage connection is inactive",
                    storage_connection_id=storage_connection_id,
                    user=username
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Storage connection is inactive"
                )
            
            config = connection.get('config', {})
            oauth_token = config.get('oauth_token')
            if config.get('base_path'):
                base_path = config.get('base_path')
        
        elif company_id:
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
            
            if company.get('storage_type') != 'yandex_disk':
                logger.error(
                    "Company storage is not Yandex Disk",
                    company_id=company_id,
                    storage_type=company.get('storage_type'),
                    user=username
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Company must use Yandex Disk storage"
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
            
            connection = database.get_storage_connection(storage_connection_id)
            if not connection:
                logger.error(
                    "Storage connection not found for company",
                    company_id=company_id,
                    storage_connection_id=storage_connection_id,
                    user=username
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Storage connection not found"
                )
            
            config = connection.get('config', {})
            oauth_token = config.get('oauth_token')
            
            # Use company's folder_id as base if available
            if company.get('yandex_disk_folder_id'):
                base_path = company.get('yandex_disk_folder_id')
            elif config.get('base_path'):
                base_path = config.get('base_path')
        
        else:
            logger.error(
                "No company_id or storage_connection_id provided",
                user=username
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either company_id or storage_connection_id must be provided"
            )
        
        # Check if we have an OAuth token
        if not oauth_token:
            logger.error(
                "No OAuth token available",
                company_id=company_id,
                storage_connection_id=storage_connection_id,
                user=username
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Yandex Disk OAuth token configured"
            )
        
        # Create adapter and list directories
        adapter = YandexDiskStorageAdapter(oauth_token=oauth_token, base_path=base_path)
        
        try:
            result = adapter.list_directories(path=path, limit=limit, offset=offset)
            
            folders = [
                YandexDiskFolder(
                    path=item['path'],
                    name=item['name']
                )
                for item in result['items']
            ]
            
            logger.info(
                "Listed Yandex Disk folders",
                user=username,
                company_id=company_id,
                storage_connection_id=storage_connection_id,
                path=path,
                count=len(folders)
            )
            
            return YandexDiskFoldersResponse(
                items=folders,
                total=result['total'],
                has_more=result['has_more']
            )
        
        except Exception as e:
            logger.error(
                "Failed to list Yandex Disk folders",
                error=str(e),
                user=username,
                company_id=company_id,
                storage_connection_id=storage_connection_id,
                path=path
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list folders: {str(e)}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error listing Yandex Disk folders",
            error=str(e),
            user=username
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/file/{encoded_path:path}")
async def get_yandex_disk_file(encoded_path: str) -> Response:
    """
    Get file from Yandex Disk by encoded path.
    
    This endpoint serves as a proxy for Yandex Disk files.
    """
    try:
        # Decode the path
        file_path = unquote(encoded_path)
        
        # Get Yandex Disk configuration
        config = get_storage_config()
        if not config.is_yandex_enabled():
            raise HTTPException(status_code=404, detail="Yandex Disk not configured")
        
        # Create adapter
        adapter = YandexDiskStorageAdapter(config.get_yandex_token())
        
        # Get file data
        file_data = await adapter.get_file(file_path)
        
        # Determine content type
        content_type = "application/octet-stream"
        if file_path.lower().endswith(('.jpg', '.jpeg')):
            content_type = "image/jpeg"
        elif file_path.lower().endswith('.png'):
            content_type = "image/png"
        elif file_path.lower().endswith('.webp'):
            content_type = "image/webp"
        elif file_path.lower().endswith('.mp4'):
            content_type = "video/mp4"
        elif file_path.lower().endswith('.webm'):
            content_type = "video/webm"
        
        return Response(
            content=file_data,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to serve Yandex Disk file",
            error=str(e),
            file_path=file_path if 'file_path' in locals() else encoded_path
        )
        raise HTTPException(status_code=404, detail="File not found")


@router.get("/download/{encoded_path:path}")
async def download_yandex_disk_file(encoded_path: str) -> Response:
    """
    Download file from Yandex Disk by encoded path.
    
    This endpoint provides direct download for Yandex Disk files.
    """
    try:
        # Decode the path
        file_path = unquote(encoded_path)
        
        # Get Yandex Disk configuration
        config = get_storage_config()
        if not config.is_yandex_enabled():
            raise HTTPException(status_code=404, detail="Yandex Disk not configured")
        
        # Create adapter
        adapter = YandexDiskStorageAdapter(config.get_yandex_token())
        
        # Get direct download URL
        download_url = adapter.get_download_url(file_path)
        
        # Get file data
        file_data = await adapter.get_file(file_path)
        
        # Extract filename from path
        filename = Path(file_path).name
        
        return Response(
            content=file_data,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"",
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to download Yandex Disk file",
            error=str(e),
            file_path=file_path if 'file_path' in locals() else encoded_path
        )
        raise HTTPException(status_code=404, detail="File not found")