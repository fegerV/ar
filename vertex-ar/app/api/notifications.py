"""
Notifications API endpoints for Vertex AR admin panel.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import require_admin
from notifications import (
    NotificationCreate,
    NotificationResponse,
    NotificationUpdate,
    create_notification,
    delete_all_notifications,
    delete_notification,
    get_db,
    get_notification,
    get_notifications,
    mark_all_as_read,
    update_notification,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _to_response(notification) -> NotificationResponse:
    """Convert SQLAlchemy model to Pydantic response."""
    return NotificationResponse.model_validate(notification, from_attributes=True)


@router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    unread_only: bool = False,
    user_id: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
) -> List[NotificationResponse]:
    """List notifications for admin dashboard."""
    limit = max(1, min(limit, 500))
    notifications_list = get_notifications(
        db,
        user_id=user_id,
        limit=limit,
        unread_only=unread_only,
    )
    return [_to_response(notification) for notification in notifications_list]


@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification_endpoint(
    payload: NotificationCreate,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
) -> NotificationResponse:
    """Create a new notification (admin only)."""
    notification = create_notification(db, payload)
    return _to_response(notification)


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification_endpoint(
    notification_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
) -> NotificationResponse:
    """Get a single notification by ID."""
    notification = get_notification(db, notification_id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return _to_response(notification)


@router.put("/{notification_id}", response_model=NotificationResponse)
async def update_notification_endpoint(
    notification_id: int,
    payload: NotificationUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
) -> NotificationResponse:
    """Update notification flags (e.g., mark as read)."""
    notification = update_notification(db, notification_id, payload)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return _to_response(notification)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_endpoint(
    notification_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
) -> None:
    """Delete notification."""
    notification = delete_notification(db, notification_id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notifications_endpoint(
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
) -> None:
    """Delete notifications in bulk for all users or a specific user."""
    delete_all_notifications(db, user_id=user_id)


@router.put("/mark-all-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
) -> None:
    """Mark notifications as read for a user or for all."""
    mark_all_as_read(db, user_id=user_id)
