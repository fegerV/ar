"""
Monitoring and alerting API endpoints for Vertex AR admin panel.
"""
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel

# Import at runtime to avoid circular imports
def get_require_admin():
    from app.api.auth import require_admin
    return require_admin
from app.alerting import alert_manager
from app.monitoring import system_monitor
from app.weekly_reports import weekly_report_generator
from app.config import settings
from logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


class AlertTestRequest(BaseModel):
    """Request model for testing alerts."""
    message: Optional[str] = "This is a test alert from Vertex AR monitoring system"
    severity: Optional[str] = "medium"


class ThresholdUpdateRequest(BaseModel):
    """Request model for updating alert thresholds."""
    cpu_threshold: Optional[float] = None
    memory_threshold: Optional[float] = None
    disk_threshold: Optional[float] = None


class MonitoringStatusResponse(BaseModel):
    """Response model for monitoring status."""
    enabled: bool
    check_interval: int
    last_check: Optional[str] = None
    thresholds: Dict[str, float]
    alert_channels: Dict[str, bool]


@router.get("/status", response_model=MonitoringStatusResponse)
async def get_monitoring_status(
    _: str = Depends(get_require_admin()),
) -> MonitoringStatusResponse:
    """Get current monitoring system status."""
    return MonitoringStatusResponse(
        enabled=settings.ALERTING_ENABLED,
        check_interval=settings.HEALTH_CHECK_INTERVAL,
        thresholds={
            "cpu": settings.CPU_THRESHOLD,
            "memory": settings.MEMORY_THRESHOLD,
            "disk": settings.DISK_THRESHOLD
        },
        alert_channels={
            "telegram": bool(settings.TELEGRAM_BOT_TOKEN),
            "email": bool(settings.SMTP_USERNAME and settings.ADMIN_EMAILS)
        }
    )


@router.post("/health-check")
async def trigger_health_check(
    _: str = Depends(get_require_admin()),
) -> Dict[str, Any]:
    """Trigger an immediate system health check."""
    try:
        health_result = await system_monitor.check_system_health()
        return {
            "success": True,
            "data": health_result,
            "message": "Health check completed successfully"
        }
    except Exception as e:
        logger.error(f"Manual health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/metrics")
async def get_system_metrics(
    _: str = Depends(get_require_admin()),
) -> Dict[str, Any]:
    """Get current system metrics."""
    try:
        metrics = {
            "cpu": system_monitor.get_cpu_usage(),
            "memory": system_monitor.get_memory_usage(),
            "disk": system_monitor.get_disk_usage(),
            "network": system_monitor.get_network_stats(),
            "process": system_monitor.get_process_info(),
            "services": system_monitor.get_service_health()
        }
        return {
            "success": True,
            "data": metrics,
            "timestamp": system_monitor.last_checks.get("system", "").isoformat() if system_monitor.last_checks.get("system") else None
        }
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


@router.post("/test-alert")
async def test_alert_system(
    request: AlertTestRequest,
    _: str = Depends(get_require_admin()),
) -> Dict[str, Any]:
    """Test the alert system by sending a test alert."""
    try:
        results = await alert_manager.test_alert_system()
        
        # Also send a real test alert
        await alert_manager.send_alert(
            "test",
            "Test Alert",
            request.message,
            request.severity
        )
        
        return {
            "success": True,
            "channels_tested": results,
            "message": "Test alert sent successfully"
        }
    except Exception as e:
        logger.error(f"Test alert failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test alert failed: {str(e)}"
        )


@router.get("/alerts")
async def get_recent_alerts(
    hours: int = 24,
    _: str = Depends(get_require_admin()),
) -> Dict[str, Any]:
    """Get recent alerts from the system."""
    try:
        alerts = system_monitor.get_recent_alerts(hours=hours)
        return {
            "success": True,
            "data": alerts,
            "count": len(alerts),
            "hours": hours
        }
    except Exception as e:
        logger.error(f"Error getting recent alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alerts: {str(e)}"
        )


@router.post("/send-report")
async def send_weekly_report_now(
    background_tasks: BackgroundTasks,
    _: str = Depends(get_require_admin()),
) -> Dict[str, Any]:
    """Send the weekly report immediately."""
    try:
        # Run in background to avoid timeout
        background_tasks.add_task(weekly_report_generator.send_weekly_report)
        
        return {
            "success": True,
            "message": "Weekly report is being generated and sent"
        }
    except Exception as e:
        logger.error(f"Error sending weekly report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send weekly report: {str(e)}"
        )


@router.get("/report-preview")
async def get_weekly_report_preview(
    _: str = Depends(get_require_admin()),
) -> Dict[str, Any]:
    """Get a preview of the weekly report without sending it."""
    try:
        report_text = weekly_report_generator.generate_report_text()
        
        return {
            "success": True,
            "data": {
                "report": report_text,
                "generated_at": weekly_report_generator.report_day,
                "schedule": f"{weekly_report_generator.report_day} at {weekly_report_generator.report_time}"
            }
        }
    except Exception as e:
        logger.error(f"Error generating report preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report preview: {str(e)}"
        )


@router.put("/thresholds")
async def update_alert_thresholds(
    request: ThresholdUpdateRequest,
    _: str = Depends(get_require_admin()),
) -> Dict[str, Any]:
    """Update alert thresholds (runtime only, not persisted)."""
    try:
        updated = []
        
        if request.cpu_threshold is not None:
            if 0 <= request.cpu_threshold <= 100:
                system_monitor.alert_thresholds["cpu"] = request.cpu_threshold
                updated.append(f"CPU: {request.cpu_threshold}%")
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CPU threshold must be between 0 and 100"
                )
        
        if request.memory_threshold is not None:
            if 0 <= request.memory_threshold <= 100:
                system_monitor.alert_thresholds["memory"] = request.memory_threshold
                updated.append(f"Memory: {request.memory_threshold}%")
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Memory threshold must be between 0 and 100"
                )
        
        if request.disk_threshold is not None:
            if 0 <= request.disk_threshold <= 100:
                system_monitor.alert_thresholds["disk"] = request.disk_threshold
                updated.append(f"Disk: {request.disk_threshold}%")
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Disk threshold must be between 0 and 100"
                )
        
        return {
            "success": True,
            "message": f"Thresholds updated: {', '.join(updated)}",
            "current_thresholds": system_monitor.alert_thresholds
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating thresholds: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update thresholds: {str(e)}"
        )


@router.get("/stats")
async def get_monitoring_stats(
    _: str = Depends(get_require_admin()),
) -> Dict[str, Any]:
    """Get comprehensive monitoring statistics."""
    try:
        # Database stats
        db_stats = weekly_report_generator.get_database_stats()
        
        # Usage stats
        usage_stats = weekly_report_generator.get_usage_stats()
        
        # Alert summary
        alert_summary = weekly_report_generator.get_alert_summary()
        
        # System info
        system_info = {
            "uptime_seconds": system_monitor.get_process_info().get("create_time"),
            "monitoring_enabled": settings.ALERTING_ENABLED,
            "check_interval": settings.HEALTH_CHECK_INTERVAL,
            "last_alerts": system_monitor.last_alerts
        }
        
        return {
            "success": True,
            "data": {
                "database": db_stats,
                "usage": usage_stats,
                "alerts": alert_summary,
                "system": system_info
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting monitoring stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monitoring stats: {str(e)}"
        )
