"""
Client management endpoints for Vertex AR API.
"""
import csv
import uuid
from datetime import datetime
from io import BytesIO, StringIO
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.auth import get_current_user, require_admin
from app.database import Database
from app.models import (
    BulkIdsRequest,
    ClientCreate,
    ClientListItem,
    ClientResponse,
    ClientUpdate,
    MessageResponse,
    PaginatedClientsResponse,
)
from logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter()


def get_database() -> Database:
    """Get database instance."""
    from app.main import get_current_app
    app = get_current_app()
    if not hasattr(app.state, 'database'):
        from pathlib import Path
        BASE_DIR = app.state.config["BASE_DIR"]
        DB_PATH = BASE_DIR / "app_data.db"
        from app.database import Database, ensure_default_admin_user
        app.state.database = Database(DB_PATH)
        ensure_default_admin_user(app.state.database)
    return app.state.database


def _client_to_response(
    client: Dict[str, Any],
    with_portrait_count: bool = False,
    portrait_count: Optional[int] = None,
) -> Union[Dict[str, Any], ClientResponse]:
    """Convert database record to API response."""
    response_dict = {
        "id": client["id"],
        "phone": client["phone"],
        "name": client["name"],
        "created_at": client["created_at"],
    }

    if with_portrait_count:
        count = portrait_count
        if count is None:
            database = get_database()
            portraits = database.list_portraits(client["id"])
            count = len(portraits)
        response_dict["portraits_count"] = count or 0
        return response_dict

    return ClientResponse(**response_dict)


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    client: ClientCreate,
    username: str = Depends(get_current_user)
) -> ClientResponse:
    """Create a new client."""
    database = get_database()
    
    logger.info(
        "client_creation_attempt",
        phone=client.phone,
        name=client.name,
        username=username,
    )
    
    # Check if client with this phone already exists
    existing_client = database.get_client_by_phone(client.phone)
    if existing_client:
        logger.warning(
            "client_creation_failed_duplicate_phone",
            phone=client.phone,
            username=username,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Client with this phone number already exists"
        )
    
    client_id = str(uuid.uuid4())
    db_client = database.create_client(client_id, client.phone, client.name)
    
    logger.info(
        "client_created_successfully",
        client_id=client_id,
        phone=client.phone,
        name=client.name,
        username=username,
    )
    
    return _client_to_response(db_client)


@router.get("/", response_model=List[ClientResponse])
async def list_clients(username: str = Depends(get_current_user)) -> List[ClientResponse]:
    """Get list of all clients."""
    database = get_database()
    
    logger.info("clients_list_request", username=username)
    
    clients = database.list_clients()
    
    logger.info("clients_list_retrieved", count=len(clients), username=username)
    
    return [_client_to_response(client) for client in clients]


@router.get("/list", response_model=PaginatedClientsResponse)
async def list_clients_admin(
    page: int = 1,
    page_size: int = 25,
    search: Optional[str] = None,
    _: str = Depends(require_admin),
) -> PaginatedClientsResponse:
    """List clients with pagination and optional search (admin only)."""
    database = get_database()

    page = max(page, 1)
    page_size = max(1, min(page_size, 100))

    total = database.count_clients(search=search)
    if total == 0:
        logger.info("clients_list_empty", search=search)
        return PaginatedClientsResponse(
            items=[],
            total=0,
            page=1,
            page_size=page_size,
            total_pages=0,
        )

    total_pages = (total + page_size - 1) // page_size
    if page > total_pages:
        page = total_pages

    offset = (page - 1) * page_size
    clients = database.list_clients(search=search, limit=page_size, offset=offset)
    client_ids = [client["id"] for client in clients]
    portrait_counts = database.get_portrait_counts(client_ids)

    items = [
        ClientListItem(
            id=client["id"],
            phone=client["phone"],
            name=client["name"],
            created_at=client["created_at"],
            portraits_count=portrait_counts.get(client["id"], 0),
        )
        for client in clients
    ]

    logger.info(
        "clients_list_paginated",
        total=total,
        page=page,
        page_size=page_size,
        returned=len(items),
        search=search,
    )

    return PaginatedClientsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/bulk-delete", response_model=MessageResponse)
async def bulk_delete_clients(
    payload: BulkIdsRequest,
    admin_user: str = Depends(require_admin),
) -> MessageResponse:
    """Bulk delete clients (admin only)."""
    database = get_database()
    unique_ids = [client_id for client_id in dict.fromkeys(payload.ids) if client_id]
    if not unique_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No client IDs provided")

    deleted = database.delete_clients_bulk(unique_ids)
    logger.info(
        "clients_bulk_delete",
        requested=len(unique_ids),
        deleted=deleted,
        admin=admin_user,
    )

    if deleted == 0:
        return MessageResponse(message="Клиенты не найдены или уже удалены")

    return MessageResponse(message=f"Удалено клиентов: {deleted}")


@router.get("/export")
async def export_clients(
    format: str = "csv",
    search: Optional[str] = None,
    ids: Optional[str] = None,
    _: str = Depends(require_admin),
):
    """Export clients list in CSV or Excel format."""
    database = get_database()

    selected_ids: List[str] = []
    if ids:
        selected_ids = [client_id.strip() for client_id in ids.split(",") if client_id.strip()]

    if selected_ids:
        clients = database.get_clients_by_ids(selected_ids)
    else:
        clients = database.list_clients(search=search)

    client_ids = [client["id"] for client in clients]
    portrait_counts = database.get_portrait_counts(client_ids)

    export_rows = [
        (
            client["id"],
            client["name"],
            client["phone"],
            portrait_counts.get(client["id"], 0),
            client.get("created_at"),
        )
        for client in clients
    ]

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    format_lower = format.lower()

    if format_lower == "csv":
        text_buffer = StringIO()
        text_buffer.write("\ufeff")
        writer = csv.writer(text_buffer, delimiter=";")
        writer.writerow(["ID", "Имя", "Телефон", "Портретов", "Создано"])
        for row in export_rows:
            writer.writerow(row)
        byte_buffer = BytesIO(text_buffer.getvalue().encode("utf-8"))
        byte_buffer.seek(0)
        filename = f"clients_{timestamp}.csv"
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        logger.info(
            "clients_export_csv",
            total=len(export_rows),
            search=search,
            ids=len(selected_ids) if selected_ids else None,
        )
        return StreamingResponse(byte_buffer, media_type="text/csv; charset=utf-8", headers=headers)

    if format_lower in {"xlsx", "excel"}:
        try:
            from openpyxl import Workbook
        except ImportError as exc:
            logger.error("openpyxl_not_installed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Excel export is not available",
            ) from exc

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Clients"
        sheet.append(["ID", "Имя", "Телефон", "Портретов", "Создано"])
        for row in export_rows:
            sheet.append(row)
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        filename = f"clients_{timestamp}.xlsx"
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        logger.info(
            "clients_export_excel",
            total=len(export_rows),
            search=search,
            ids=len(selected_ids) if selected_ids else None,
        )
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported export format")


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: str,
    username: str = Depends(get_current_user)
) -> ClientResponse:
    """Get client by ID."""
    database = get_database()
    
    logger.info("client_fetch_attempt", client_id=client_id, username=username)
    
    client = database.get_client(client_id)
    
    if not client:
        logger.warning("client_fetch_failed_not_found", client_id=client_id, username=username)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    logger.info("client_fetched_successfully", client_id=client_id, username=username)
    
    return _client_to_response(client)


@router.get("/phone/{phone}", response_model=ClientResponse)
async def get_client_by_phone(
    phone: str,
    username: str = Depends(get_current_user)
) -> ClientResponse:
    """Get client by phone number."""
    database = get_database()
    client = database.get_client_by_phone(phone)
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    return _client_to_response(client)


@router.get("/search/{phone}", response_model=List[ClientResponse])
async def search_clients(
    phone: str,
    username: str = Depends(get_current_user)
) -> List[ClientResponse]:
    """Search clients by phone (partial match)."""
    database = get_database()
    clients = database.search_clients(phone)
    
    return [_client_to_response(client) for client in clients]


@router.get("/search", response_model=List[Dict[str, Any]])
async def search_clients_query(
    phone: str,
    _: str = Depends(require_admin)
) -> List[Dict[str, Any]]:
    """Legacy endpoint: search clients via query parameter with portrait counts."""
    database = get_database()
    clients = database.search_clients(phone)
    return [_client_to_response(client, with_portrait_count=True) for client in clients]


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: str,
    client_update: ClientUpdate,
    username: str = Depends(get_current_user)
) -> ClientResponse:
    """Update client data."""
    database = get_database()
    
    logger.info("client_update_attempt", client_id=client_id, username=username)
    
    # Check if client exists
    existing_client = database.get_client(client_id)
    if not existing_client:
        logger.warning("client_update_failed_not_found", client_id=client_id, username=username)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # If updating phone, check for duplicates
    if client_update.phone:
        phone_client = database.get_client_by_phone(client_update.phone)
        if phone_client and phone_client["id"] != client_id:
            logger.warning(
                "client_update_failed_duplicate_phone",
                client_id=client_id,
                phone=client_update.phone,
                username=username,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Client with this phone number already exists"
            )
    
    # Update client
    updated = database.update_client(
        client_id,
        phone=client_update.phone,
        name=client_update.name
    )
    
    if not updated:
        logger.warning("client_update_failed_no_fields", client_id=client_id, username=username)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update"
        )
    
    # Return updated client
    updated_client = database.get_client(client_id)
    
    logger.info(
        "client_updated_successfully",
        client_id=client_id,
        username=username,
    )
    
    return _client_to_response(updated_client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: str,
    username: str = Depends(get_current_user)
):
    """Delete client."""
    database = get_database()
    
    logger.info("client_deletion_attempt", client_id=client_id, username=username)
    
    # Check if client exists
    existing_client = database.get_client(client_id)
    if not existing_client:
        logger.warning("client_deletion_failed_not_found", client_id=client_id, username=username)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Delete client
    deleted = database.delete_client(client_id)
    if not deleted:
        logger.error("client_deletion_failed_database_error", client_id=client_id, username=username)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete client"
        )
    
    logger.info("client_deleted_successfully", client_id=client_id, username=username)