"""
Client management endpoints for Vertex AR API.
"""

import uuid
from typing import List

from app.api.auth import get_current_user
from app.database import Database
from app.models import ClientCreate, ClientResponse, ClientUpdate
from fastapi import APIRouter, Depends, HTTPException, status
from logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter()


def get_database() -> Database:
    """Get database instance."""
    from app.main import get_current_app

    app = get_current_app()
    if not hasattr(app.state, "database"):
        from pathlib import Path

        BASE_DIR = app.state.config["BASE_DIR"]
        DB_PATH = BASE_DIR / "app_data.db"
        from app.database import Database

        app.state.database = Database(DB_PATH)
    return app.state.database


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(client: ClientCreate, username: str = Depends(get_current_user)) -> ClientResponse:
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
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client with this phone number already exists")

    client_id = str(uuid.uuid4())
    db_client = database.create_client(client_id, client.phone, client.name)

    logger.info(
        "client_created_successfully",
        client_id=client_id,
        phone=client.phone,
        name=client.name,
        username=username,
    )

    return ClientResponse(
        id=db_client["id"], phone=db_client["phone"], name=db_client["name"], created_at=db_client["created_at"]
    )


@router.get("/", response_model=List[ClientResponse])
async def list_clients(username: str = Depends(get_current_user)) -> List[ClientResponse]:
    """Get list of all clients."""
    database = get_database()

    logger.info("clients_list_request", username=username)

    clients = database.list_clients()

    logger.info("clients_list_retrieved", count=len(clients), username=username)

    return [
        ClientResponse(id=client["id"], phone=client["phone"], name=client["name"], created_at=client["created_at"])
        for client in clients
    ]


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(client_id: str, username: str = Depends(get_current_user)) -> ClientResponse:
    """Get client by ID."""
    database = get_database()

    logger.info("client_fetch_attempt", client_id=client_id, username=username)

    client = database.get_client(client_id)

    if not client:
        logger.warning("client_fetch_failed_not_found", client_id=client_id, username=username)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    logger.info("client_fetched_successfully", client_id=client_id, username=username)

    return ClientResponse(id=client["id"], phone=client["phone"], name=client["name"], created_at=client["created_at"])


@router.get("/phone/{phone}", response_model=ClientResponse)
async def get_client_by_phone(phone: str, username: str = Depends(get_current_user)) -> ClientResponse:
    """Get client by phone number."""
    database = get_database()
    client = database.get_client_by_phone(phone)

    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    return ClientResponse(id=client["id"], phone=client["phone"], name=client["name"], created_at=client["created_at"])


@router.get("/search/{phone}", response_model=List[ClientResponse])
async def search_clients(phone: str, username: str = Depends(get_current_user)) -> List[ClientResponse]:
    """Search clients by phone (partial match)."""
    database = get_database()
    clients = database.search_clients(phone)

    return [
        ClientResponse(id=client["id"], phone=client["phone"], name=client["name"], created_at=client["created_at"])
        for client in clients
    ]


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: str, client_update: ClientUpdate, username: str = Depends(get_current_user)
) -> ClientResponse:
    """Update client data."""
    database = get_database()

    logger.info("client_update_attempt", client_id=client_id, username=username)

    # Check if client exists
    existing_client = database.get_client(client_id)
    if not existing_client:
        logger.warning("client_update_failed_not_found", client_id=client_id, username=username)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

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
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client with this phone number already exists")

    # Update client
    updated = database.update_client(client_id, phone=client_update.phone, name=client_update.name)

    if not updated:
        logger.warning("client_update_failed_no_fields", client_id=client_id, username=username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update")

    # Return updated client
    updated_client = database.get_client(client_id)

    logger.info(
        "client_updated_successfully",
        client_id=client_id,
        username=username,
    )

    return ClientResponse(
        id=updated_client["id"],
        phone=updated_client["phone"],
        name=updated_client["name"],
        created_at=updated_client["created_at"],
    )


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(client_id: str, username: str = Depends(get_current_user)):
    """Delete client."""
    database = get_database()

    logger.info("client_deletion_attempt", client_id=client_id, username=username)

    # Check if client exists
    existing_client = database.get_client(client_id)
    if not existing_client:
        logger.warning("client_deletion_failed_not_found", client_id=client_id, username=username)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    # Delete client
    deleted = database.delete_client(client_id)
    if not deleted:
        logger.error("client_deletion_failed_database_error", client_id=client_id, username=username)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete client")

    logger.info("client_deleted_successfully", client_id=client_id, username=username)
