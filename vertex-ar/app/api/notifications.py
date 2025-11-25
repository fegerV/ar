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
    NotificationFilter,
    NotificationGroup,
    NotificationPriority,
    NotificationStatus,
    create_notification,
    delete_all_notifications,
    delete_notification,
    get_db,
    get_notification,
    get_notifications,
    get_notifications_filtered,
    get_notification_groups,
    get_group_notifications,
    export_notifications_to_csv,
    export_notifications_to_json,
    update_notification,
    update_notification_priority,
    bulk_update_notifications_status,
    get_notification_statistics,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _to_response(notification) -> NotificationResponse:
    """Convert SQLAlchemy model to Pydantic response."""
    response_data = {
        'id': notification.id,
        'title': notification.title,
        'message': notification.message,
        'user_id': notification.user_id,
        'notification_type': notification.notification_type,
        'priority': notification.priority,
        'status': notification.status,
        'is_read': notification.is_read,
        'source': notification.source,
        'service_name': notification.service_name,
        'event_data': notification.event_data,
        'group_id': notification.group_id,
        'created_at': notification.created_at,
        'expires_at': notification.expires_at,
        'processed_at': notification.processed_at
    }
    
    # Parse event_data if it's a JSON string
    if notification.event_data:
        try:
            import json
            response_data['event_data'] = json.loads(notification.event_data)
        except:
            pass
    
    return NotificationResponse.model_validate(response_data)


@router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    user_id: Optional[str] = None,
    notification_type: Optional[str] = None,
    priority: Optional[NotificationPriority] = None,
    status: Optional[NotificationStatus] = None,
    source: Optional[str] = None,
    service_name: Optional[str] = None,
    group_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
) -> List[NotificationResponse]:
    """List notifications with advanced filtering."""
    limit = max(1, min(limit, 500))
    
    # Build filters
    filters = NotificationFilter(
        user_id=user_id,
        notification_type=notification_type,
        priority=priority,
        status=status if not unread_only else NotificationStatus.NEW,
        source=source,
        service_name=service_name,
        group_id=group_id,
        search=search
    )
    
    # Parse dates
    if date_from:
        try:
            from datetime import datetime
            filters.date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    if date_to:
        try:
            from datetime import datetime
            filters.date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    notifications_list = get_notifications(
        db,
        filters=filters,
        limit=limit,
        offset=offset,
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
    # Get all notifications to update
    filters = NotificationFilter(user_id=user_id, status=NotificationStatus.NEW)
    notifications = get_notifications(db, filters, limit=10000)
    
    if notifications:
        notification_ids = [n.id for n in notifications]
        bulk_update_notifications_status(db, notification_ids, NotificationStatus.READ)


@router.get("/groups", response_model=List[NotificationGroup])
async def list_notification_groups(
    user_id: Optional[str] = None,
    notification_type: Optional[str] = None,
    priority: Optional[NotificationPriority] = None,
    source: Optional[str] = None,
    service_name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
) -> List[NotificationGroup]:
    """Get grouped notifications with aggregation."""
    filters = NotificationFilter(
        user_id=user_id,
        notification_type=notification_type,
        priority=priority,
        source=source,
        service_name=service_name
    )
    
    # Parse dates
    if date_from:
        try:
            from datetime import datetime
            filters.date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    if date_to:
        try:
            from datetime import datetime
            filters.date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    groups = get_notification_groups(db, filters, limit)
    return groups


@router.get("/groups/{group_id}", response_model=List[NotificationResponse])
async def get_group_notifications_endpoint(
    group_id: str,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
) -> List[NotificationResponse]:
    """Get all notifications in a specific group."""
    notifications = get_group_notifications(db, group_id, limit)
    return [_to_response(notification) for notification in notifications]


@router.get("/export/csv")
async def export_notifications_csv(
    user_id: Optional[str] = None,
    notification_type: Optional[str] = None,
    priority: Optional[NotificationPriority] = None,
    status: Optional[NotificationStatus] = None,
    source: Optional[str] = None,
    service_name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 1000,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Export notifications to CSV format."""
    from fastapi.responses import Response
    
    filters = NotificationFilter(
        user_id=user_id,
        notification_type=notification_type,
        priority=priority,
        status=status,
        source=source,
        service_name=service_name,
        search=search
    )
    
    # Parse dates
    if date_from:
        try:
            from datetime import datetime
            filters.date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    if date_to:
        try:
            from datetime import datetime
            filters.date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    csv_data = export_notifications_to_csv(db, filters, limit)
    
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=notifications.csv"}
    )


@router.get("/export/json")
async def export_notifications_json(
    user_id: Optional[str] = None,
    notification_type: Optional[str] = None,
    priority: Optional[NotificationPriority] = None,
    status: Optional[NotificationStatus] = None,
    source: Optional[str] = None,
    service_name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 1000,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Export notifications to JSON format."""
    from fastapi.responses import Response
    
    filters = NotificationFilter(
        user_id=user_id,
        notification_type=notification_type,
        priority=priority,
        status=status,
        source=source,
        service_name=service_name,
        search=search
    )
    
    # Parse dates
    if date_from:
        try:
            from datetime import datetime
            filters.date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    if date_to:
        try:
            from datetime import datetime
            filters.date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    json_data = export_notifications_to_json(db, filters, limit)
    
    return Response(
        content=json_data,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=notifications.json"}
    )


@router.get("/statistics")
async def get_notifications_stats(
    user_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
) -> dict:
    """Get notification statistics."""
    filters = NotificationFilter(user_id=user_id)
    
    # Parse dates
    if date_from:
        try:
            from datetime import datetime
            filters.date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    if date_to:
        try:
            from datetime import datetime
            filters.date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    return get_notification_statistics(db, filters)


@router.put("/{notification_id}/priority")
async def update_notification_priority_endpoint(
    notification_id: int,
    priority: NotificationPriority,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
) -> NotificationResponse:
    """Update notification priority."""
    notification = update_notification_priority(db, notification_id, priority)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return _to_response(notification)


@router.put("/bulk-status")
async def bulk_update_status(
    notification_ids: List[int],
    status: NotificationStatus,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
) -> dict:
    """Bulk update notification status."""
    updated_count = bulk_update_notifications_status(db, notification_ids, status)
    return {"updated_count": updated_count}
