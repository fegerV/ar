"""
Notification management API endpoints for Vertex AR.
Provides endpoints for managing integrations, sync, and advanced features.
"""
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import require_admin
from notifications import get_db
from notification_integrations import (
    notification_integrator,
    notification_scheduler,
    WebhookEvent
)
from notification_sync import (
    notification_sync_manager,
    notification_aggregator
)

router = APIRouter(prefix="/notifications-management", tags=["notifications-management"])


@router.get("/integrations/status")
async def get_integrations_status(
    _: str = Depends(require_admin),
) -> Dict[str, Any]:
    """Get status of all notification integrations."""
    try:
        webhook_stats = notification_integrator.get_webhook_stats()
        
        return {
            "webhook_stats": webhook_stats,
            "scheduler_running": notification_scheduler.running,
            "registered_handlers": list(notification_integrator.integration_handlers.keys()),
            "scheduled_tasks_count": len(notification_scheduler.scheduled_tasks)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting integrations status: {str(e)}"
        )


@router.post("/webhooks/test")
async def test_webhook(
    url: str,
    payload: Optional[Dict[str, Any]] = None,
    _: str = Depends(require_admin),
) -> Dict[str, Any]:
    """Test webhook delivery."""
    try:
        if payload is None:
            payload = {
                "test": True,
                "message": "Test webhook from Vertex AR",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        
        success = await notification_integrator.send_webhook(url, payload)
        
        return {
            "success": success,
            "url": url,
            "payload": payload,
            "webhook_stats": notification_integrator.get_webhook_stats()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error testing webhook: {str(e)}"
        )


@router.get("/sync/status")
async def get_sync_status(
    _: str = Depends(require_admin),
) -> Dict[str, Any]:
    """Get notification sync manager status."""
    try:
        return notification_sync_manager.get_status()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting sync status: {str(e)}"
        )


@router.post("/sync/trigger-cleanup")
async def trigger_cleanup(
    _: str = Depends(require_admin),
) -> Dict[str, Any]:
    """Trigger manual cleanup of notifications."""
    try:
        import asyncio
        await notification_sync_manager._perform_cleanup()
        
        return {
            "success": True,
            "message": "Cleanup triggered successfully",
            "cleanup_stats": notification_sync_manager.cleanup_stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering cleanup: {str(e)}"
        )


@router.get("/aggregation/rules")
async def get_aggregation_rules(
    _: str = Depends(require_admin),
) -> Dict[str, Any]:
    """Get notification aggregation rules."""
    try:
        return notification_aggregator.get_aggregation_stats()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting aggregation rules: {str(e)}"
        )


@router.post("/aggregation/rules")
async def add_aggregation_rule(
    name: str,
    pattern: str,
    max_count: int = 10,
    time_window: int = 3600,
    _: str = Depends(require_admin),
) -> Dict[str, Any]:
    """Add a new notification aggregation rule."""
    try:
        notification_aggregator.add_aggregation_rule(
            name=name,
            pattern=pattern,
            max_count=max_count,
            time_window=time_window
        )
        
        return {
            "success": True,
            "message": f"Aggregation rule '{name}' added successfully",
            "rules": notification_aggregator.get_aggregation_stats()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding aggregation rule: {str(e)}"
        )


@router.delete("/aggregation/rules/{rule_name}")
async def delete_aggregation_rule(
    rule_name: str,
    _: str = Depends(require_admin),
) -> Dict[str, Any]:
    """Delete a notification aggregation rule."""
    try:
        if rule_name in notification_aggregator.aggregation_rules:
            del notification_aggregator.aggregation_rules[rule_name]
            
            return {
                "success": True,
                "message": f"Aggregation rule '{rule_name}' deleted successfully",
                "rules": notification_aggregator.get_aggregation_stats()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Aggregation rule '{rule_name}' not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting aggregation rule: {str(e)}"
        )


@router.post("/schedule/notification")
async def schedule_notification(
    notification_data: Dict[str, Any],
    integrations: List[str],
    priority: str = "medium",
    run_at: Optional[str] = None,
    interval_minutes: Optional[int] = None,
    _: str = Depends(require_admin),
) -> Dict[str, Any]:
    """Schedule a notification task."""
    try:
        from datetime import datetime
        
        run_datetime = None
        if run_at:
            run_datetime = datetime.fromisoformat(run_at.replace('Z', '+00:00'))
        
        notification_scheduler.schedule_notification(
            notification_data=notification_data,
            integrations=integrations,
            priority=priority,
            run_at=run_datetime,
            interval_minutes=interval_minutes
        )
        
        return {
            "success": True,
            "message": "Notification scheduled successfully",
            "scheduled_tasks_count": len(notification_scheduler.scheduled_tasks)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error scheduling notification: {str(e)}"
        )


@router.get("/schedule/tasks")
async def get_scheduled_tasks(
    _: str = Depends(require_admin),
) -> Dict[str, Any]:
    """Get all scheduled notification tasks."""
    try:
        tasks = []
        for task in notification_scheduler.scheduled_tasks:
            task_data = {
                "notification_data": task["notification_data"],
                "integrations": task["integrations"],
                "priority": task["priority"],
                "next_run": task["next_run"].isoformat() if task.get("next_run") else None,
                "interval_minutes": task.get("interval_minutes"),
                "created_at": task["created_at"].isoformat() if task.get("created_at") else None
            }
            tasks.append(task_data)
        
        return {
            "tasks": tasks,
            "total_count": len(tasks),
            "scheduler_running": notification_scheduler.running
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting scheduled tasks: {str(e)}"
        )


@router.delete("/schedule/tasks")
async def clear_scheduled_tasks(
    _: str = Depends(require_admin),
) -> Dict[str, Any]:
    """Clear all scheduled notification tasks."""
    try:
        task_count = len(notification_scheduler.scheduled_tasks)
        notification_scheduler.scheduled_tasks.clear()
        
        return {
            "success": True,
            "message": f"Cleared {task_count} scheduled tasks",
            "cleared_count": task_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing scheduled tasks: {str(e)}"
        )


@router.post("/test-routing")
async def test_notification_routing(
    notification_data: Dict[str, Any],
    priority: str = "medium",
    integrations: Optional[List[str]] = None,
    _: str = Depends(require_admin),
) -> Dict[str, Any]:
    """Test notification routing through integrations."""
    try:
        if integrations is None:
            from app.config import settings
            route_map = {
                "critical": settings.CRITICAL_NOTIFICATION_ROUTES,
                "high": settings.HIGH_NOTIFICATION_ROUTES,
                "medium": settings.MEDIUM_NOTIFICATION_ROUTES,
                "low": settings.LOW_NOTIFICATION_ROUTES
            }
            integrations = route_map.get(priority, [])
        
        results = await notification_integrator.route_notification(
            notification_data, integrations, priority
        )
        
        return {
            "success": True,
            "notification_data": notification_data,
            "priority": priority,
            "integrations": integrations,
            "results": results
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error testing notification routing: {str(e)}"
        )


@router.get("/webhooks/queue")
async def get_webhook_queue(
    _: str = Depends(require_admin),
) -> Dict[str, Any]:
    """Get current webhook queue status."""
    try:
        queue_data = []
        for event in notification_integrator.webhook_queue:
            event_data = {
                "url": event.url,
                "status": event.status.value,
                "attempts": event.attempts,
                "created_at": event.created_at.isoformat(),
                "delivered_at": event.delivered_at.isoformat() if event.delivered_at else None,
                "last_error": event.last_error
            }
            queue_data.append(event_data)
        
        return {
            "queue": queue_data,
            "total_count": len(queue_data),
            "stats": notification_integrator.get_webhook_stats()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting webhook queue: {str(e)}"
        )