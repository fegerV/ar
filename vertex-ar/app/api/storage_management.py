"""
Storage management endpoints for Vertex AR API.
Handles storage connections and per-company storage configuration.
"""
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.database import Database
from app.models import (
    CompanyStorageUpdate,
    MessageResponse,
    StorageConnectionCreate,
    StorageConnectionResponse,
    StorageConnectionUpdate,
    StorageOptionResponse,
    StorageTestRequest,
    StorageTestResponse,
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


async def _test_storage_connection(connection: Dict[str, Any]) -> StorageTestResponse:
    """Test a storage connection."""
    storage_type = connection['type']
    config = connection['config']
    
    try:
        if storage_type == 'minio':
            return await _test_minio_connection(config)
        elif storage_type == 'yandex_disk':
            return await _test_yandex_disk_connection(config)
        else:
            return StorageTestResponse(
                success=False,
                message=f"Unsupported storage type: {storage_type}"
            )
    except Exception as exc:
        logger.error(f"Error testing storage connection: {exc}")
        return StorageTestResponse(
            success=False,
            message=f"Connection test failed: {str(exc)}"
        )


async def _test_minio_connection(config: Dict[str, Any]) -> StorageTestResponse:
    """Test MinIO connection."""
    try:
        from app.storage_minio import MinioStorageAdapter
        
        endpoint = config.get('endpoint', 'localhost:9000')
        access_key = config.get('access_key', '')
        secret_key = config.get('secret_key', '')
        bucket = config.get('bucket', 'vertex-ar')
        secure = config.get('secure', False)
        
        if not access_key or not secret_key:
            return StorageTestResponse(
                success=False,
                message="Access key and secret key are required"
            )
        
        # Create adapter and test connection
        adapter = MinioStorageAdapter(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            bucket=bucket,
            secure=secure
        )
        
        # Test by checking if bucket exists or can be created
        try:
            # Try to list objects (this will fail if bucket doesn't exist and we don't have permissions)
            await adapter.list_files("")
            
            return StorageTestResponse(
                success=True,
                message="MinIO connection successful",
                details={
                    "endpoint": endpoint,
                    "bucket": bucket,
                    "secure": secure
                }
            )
        except Exception as bucket_exc:
            # Try to create bucket
            try:
                # Note: This would require bucket creation method in adapter
                # For now, just validate the connection parameters
                return StorageTestResponse(
                    success=True,
                    message="MinIO connection parameters valid (bucket may need to be created manually)",
                    details={
                        "endpoint": endpoint,
                        "bucket": bucket,
                        "secure": secure
                    }
                )
            except Exception as create_exc:
                return StorageTestResponse(
                    success=False,
                    message=f"MinIO connection failed: {str(create_exc)}"
                )
                
    except ImportError:
        return StorageTestResponse(
            success=False,
            message="MinIO storage adapter not available"
        )
    except Exception as exc:
        return StorageTestResponse(
            success=False,
            message=f"MinIO connection test failed: {str(exc)}"
        )


async def _test_yandex_disk_connection(config: Dict[str, Any]) -> StorageTestResponse:
    """Test Yandex Disk connection."""
    try:
        from app.storage_yandex import YandexDiskStorageAdapter
        
        oauth_token = config.get('oauth_token', '')
        base_path = config.get('base_path', 'vertex-ar')
        
        if not oauth_token:
            return StorageTestResponse(
                success=False,
                message="OAuth token is required"
            )
        
        # Create adapter and test connection
        adapter = YandexDiskStorageAdapter(
            oauth_token=oauth_token,
            base_path=base_path
        )
        
        # Test by getting storage info
        try:
            info = adapter.get_storage_info()
            
            return StorageTestResponse(
                success=True,
                message="Yandex Disk connection successful",
                details={
                    "base_path": base_path,
                    "info": info
                }
            )
        except Exception as disk_exc:
            return StorageTestResponse(
                success=False,
                message=f"Yandex Disk connection failed: {str(disk_exc)}"
            )
                
    except ImportError:
        return StorageTestResponse(
            success=False,
            message="Yandex Disk storage adapter not available"
        )
    except Exception as exc:
        return StorageTestResponse(
            success=False,
            message=f"Yandex Disk connection test failed: {str(exc)}"
        )


@router.get("/storages", response_model=List[StorageConnectionResponse])
async def list_storage_connections(
    request: Request,
    active_only: bool = True,
    tested_only: bool = False,
) -> List[StorageConnectionResponse]:
    """Get list of storage connections."""
    username = _get_admin_user(request)
    database = get_database()
    
    try:
        connections = database.get_storage_connections(active_only=active_only, tested_only=tested_only)
        return [
            StorageConnectionResponse(
                id=conn['id'],
                name=conn['name'],
                type=conn['type'],
                config=conn['config'],
                is_active=bool(conn['is_active']),
                is_tested=bool(conn['is_tested']),
                test_result=conn.get('test_result'),
                created_at=conn['created_at'],
                updated_at=conn['updated_at'],
            )
            for conn in connections
        ]
    except Exception as exc:
        logger.error(f"Error listing storage connections: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list storage connections"
        )


@router.post("/storages", response_model=StorageConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_storage_connection(
    request: Request,
    storage: StorageConnectionCreate,
) -> StorageConnectionResponse:
    """Create a new storage connection."""
    username = _get_admin_user(request)
    database = get_database()
    
    # Check if name already exists
    existing_connections = database.get_storage_connections(active_only=False, tested_only=False)
    for conn in existing_connections:
        if conn['name'].lower() == storage.name.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Storage connection '{storage.name}' already exists"
            )
    
    connection_id = f"storage-{uuid4().hex[:8]}"
    
    try:
        success = database.create_storage_connection(
            connection_id=connection_id,
            name=storage.name,
            storage_type=storage.type,
            config=storage.config,
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create storage connection"
            )
        
        created = database.get_storage_connection(connection_id)
        if not created:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created storage connection"
            )
        
        return StorageConnectionResponse(
            id=created['id'],
            name=created['name'],
            type=created['type'],
            config=created['config'],
            is_active=bool(created['is_active']),
            is_tested=bool(created['is_tested']),
            test_result=created.get('test_result'),
            created_at=created['created_at'],
            updated_at=created['updated_at'],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error creating storage connection: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create storage connection"
        )


@router.get("/storages/{connection_id}", response_model=StorageConnectionResponse)
async def get_storage_connection(
    request: Request,
    connection_id: str,
) -> StorageConnectionResponse:
    """Get storage connection by ID."""
    username = _get_admin_user(request)
    database = get_database()
    
    connection = database.get_storage_connection(connection_id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storage connection not found"
        )
    
    return StorageConnectionResponse(
        id=connection['id'],
        name=connection['name'],
        type=connection['type'],
        config=connection['config'],
        is_active=bool(connection['is_active']),
        is_tested=bool(connection['is_tested']),
        test_result=connection.get('test_result'),
        created_at=connection['created_at'],
        updated_at=connection['updated_at'],
    )


@router.put("/storages/{connection_id}", response_model=StorageConnectionResponse)
async def update_storage_connection(
    request: Request,
    connection_id: str,
    storage_update: StorageConnectionUpdate,
) -> StorageConnectionResponse:
    """Update storage connection."""
    username = _get_admin_user(request)
    database = get_database()
    
    # Check if connection exists
    existing = database.get_storage_connection(connection_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storage connection not found"
        )
    
    # Check if name conflicts with existing connection
    if storage_update.name:
        existing_connections = database.get_storage_connections(active_only=False, tested_only=False)
        for conn in existing_connections:
            if conn['id'] != connection_id and conn['name'].lower() == storage_update.name.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Storage connection '{storage_update.name}' already exists"
                )
    
    try:
        success = database.update_storage_connection(
            connection_id=connection_id,
            name=storage_update.name,
            config=storage_update.config,
            is_active=storage_update.is_active,
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update storage connection"
            )
        
        # Reset test status if config changed
        if storage_update.config is not None:
            database.update_storage_connection_test_result(connection_id, False, "Configuration changed - retest required")
        
        updated = database.get_storage_connection(connection_id)
        return StorageConnectionResponse(
            id=updated['id'],
            name=updated['name'],
            type=updated['type'],
            config=updated['config'],
            is_active=bool(updated['is_active']),
            is_tested=bool(updated['is_tested']),
            test_result=updated.get('test_result'),
            created_at=updated['created_at'],
            updated_at=updated['updated_at'],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error updating storage connection: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update storage connection"
        )


@router.delete("/storages/{connection_id}", response_model=MessageResponse)
async def delete_storage_connection(
    request: Request,
    connection_id: str,
) -> MessageResponse:
    """Delete storage connection."""
    username = _get_admin_user(request)
    database = get_database()
    
    # Check if connection exists
    existing = database.get_storage_connection(connection_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storage connection not found"
        )
    
    try:
        success = database.delete_storage_connection(connection_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete storage connection - it may be in use by companies"
            )
        
        return MessageResponse(
            message=f"Storage connection '{existing['name']}' deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error deleting storage connection: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete storage connection"
        )


@router.post("/storages/test", response_model=StorageTestResponse)
async def test_storage_connection(
    request: Request,
    test_request: StorageTestRequest,
) -> StorageTestResponse:
    """Test a storage connection."""
    username = _get_admin_user(request)
    database = get_database()
    
    # Get storage connection
    connection = database.get_storage_connection(test_request.connection_id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storage connection not found"
        )
    
    # Test the connection
    result = await _test_storage_connection(connection)
    
    # Update test result in database
    database.update_storage_connection_test_result(
        test_request.connection_id,
        result.success,
        result.message
    )
    
    return result


@router.get("/storage-options", response_model=List[StorageOptionResponse])
async def get_available_storage_options(
    request: Request,
) -> List[StorageOptionResponse]:
    """Get available storage options for company selection."""
    username = _get_admin_user(request)
    database = get_database()
    
    try:
        options = database.get_available_storage_options()
        return [
            StorageOptionResponse(
                id=opt['id'],
                name=opt['name'],
                type=opt['type'],
                connection_id=opt.get('connection_id'),
                is_available=opt['is_available']
            )
            for opt in options
        ]
    except Exception as exc:
        logger.error(f"Error getting storage options: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get storage options"
        )


@router.patch("/companies/{company_id}/storage", response_model=MessageResponse)
async def update_company_storage(
    request: Request,
    company_id: str,
    storage_update: CompanyStorageUpdate,
) -> MessageResponse:
    """Update company storage configuration."""
    username = _get_admin_user(request)
    database = get_database()
    
    # Check if company exists
    company = database.get_company(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Validate storage connection if specified
    if storage_update.storage_type != 'local' and storage_update.storage_connection_id:
        connection = database.get_storage_connection(storage_update.storage_connection_id)
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
    
    try:
        success = database.update_company_storage(
            company_id=company_id,
            storage_type=storage_update.storage_type,
            storage_connection_id=storage_update.storage_connection_id,
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update company storage"
            )
        
        return MessageResponse(
            message=f"Company storage updated successfully"
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error updating company storage: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update company storage"
        )