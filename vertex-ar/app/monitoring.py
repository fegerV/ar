"""
Server monitoring system for Vertex AR - tracks system health and performance.
"""
import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import psutil

from app.config import settings
from app.alerting import alert_manager
from logging_setup import get_logger

logger = get_logger(__name__)


class SystemMonitor:
    """Monitors system health and performance metrics."""
    
    def __init__(self):
        self.enabled = settings.ALERTING_ENABLED
        self.check_interval = settings.HEALTH_CHECK_INTERVAL
        self.last_checks: Dict[str, datetime] = {}
        self.alert_thresholds = {
            "cpu": settings.CPU_THRESHOLD,
            "memory": settings.MEMORY_THRESHOLD,
            "disk": settings.DISK_THRESHOLD
        }
        
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        return psutil.cpu_percent(interval=1)
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get memory usage information."""
        memory = psutil.virtual_memory()
        return {
            "percent": memory.percent,
            "used_gb": memory.used / (1024**3),
            "total_gb": memory.total / (1024**3),
            "available_gb": memory.available / (1024**3)
        }
    
    def get_disk_usage(self) -> Dict[str, float]:
        """Get disk usage information for storage directory."""
        try:
            disk = psutil.disk_usage(str(settings.STORAGE_ROOT))
            return {
                "percent": (disk.used / disk.total) * 100,
                "used_gb": disk.used / (1024**3),
                "total_gb": disk.total / (1024**3),
                "free_gb": disk.free / (1024**3)
            }
        except Exception as e:
            logger.error(f"Error getting disk usage: {e}")
            return {"percent": 0, "used_gb": 0, "total_gb": 0, "free_gb": 0}
    
    def get_network_stats(self) -> Dict[str, Any]:
        """Get network interface statistics."""
        try:
            net_io = psutil.net_io_counters()
            return {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        except Exception as e:
            logger.error(f"Error getting network stats: {e}")
            return {}
    
    def get_process_info(self) -> Dict[str, Any]:
        """Get information about the current process."""
        try:
            process = psutil.Process()
            return {
                "pid": process.pid,
                "cpu_percent": process.cpu_percent(),
                "memory_mb": process.memory_info().rss / (1024**2),
                "num_threads": process.num_threads(),
                "create_time": datetime.fromtimestamp(process.create_time()).isoformat(),
                "status": process.status()
            }
        except Exception as e:
            logger.error(f"Error getting process info: {e}")
            return {}
    
    def get_service_health(self) -> Dict[str, bool]:
        """Check health of various services."""
        health_status = {}
        
        # Check database accessibility
        try:
            from app.database import Database
            db = Database(settings.DB_PATH)
            # Simple query to test connection
            db.get_company("vertex-ar-default")
            health_status["database"] = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_status["database"] = False
        
        # Check storage accessibility
        try:
            test_file = settings.STORAGE_ROOT / ".health_check"
            test_file.write_text("test")
            test_file.unlink()
            health_status["storage"] = True
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            health_status["storage"] = False
        
        # Check MinIO if configured
        if settings.STORAGE_TYPE == "minio":
            try:
                from app.storage_minio import MinioStorageAdapter
                storage = MinioStorageAdapter(
                    endpoint=settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    bucket=settings.MINIO_BUCKET
                )
                # Test connection by listing objects
                storage.list_files("")
                health_status["minio"] = True
            except Exception as e:
                logger.error(f"MinIO health check failed: {e}")
                health_status["minio"] = False
        else:
            health_status["minio"] = True  # Not used, so considered healthy
        
        return health_status
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Perform comprehensive system health check."""
        if not self.enabled:
            return {"status": "disabled"}
        
        health_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "alerts": [],
            "metrics": {}
        }
        
        try:
            # CPU check
            cpu_usage = self.get_cpu_usage()
            health_data["metrics"]["cpu"] = cpu_usage
            
            if cpu_usage > self.alert_thresholds["cpu"]:
                alert_msg = f"High CPU usage: {cpu_usage:.1f}% (threshold: {self.alert_thresholds['cpu']}%)"
                health_data["alerts"].append({
                    "type": "cpu",
                    "severity": "high" if cpu_usage > 90 else "medium",
                    "message": alert_msg
                })
                await alert_manager.send_alert(
                    "high_cpu",
                    "High CPU Usage Detected",
                    alert_msg,
                    "high" if cpu_usage > 90 else "medium"
                )
            
            # Memory check
            memory_info = self.get_memory_usage()
            health_data["metrics"]["memory"] = memory_info
            
            if memory_info["percent"] > self.alert_thresholds["memory"]:
                alert_msg = f"High memory usage: {memory_info['percent']:.1f}% ({memory_info['used_gb']:.1f}GB used)"
                health_data["alerts"].append({
                    "type": "memory",
                    "severity": "high" if memory_info["percent"] > 95 else "medium",
                    "message": alert_msg
                })
                await alert_manager.send_alert(
                    "high_memory",
                    "High Memory Usage Detected",
                    alert_msg,
                    "high" if memory_info["percent"] > 95 else "medium"
                )
            
            # Disk check
            disk_info = self.get_disk_usage()
            health_data["metrics"]["disk"] = disk_info
            
            if disk_info["percent"] > self.alert_thresholds["disk"]:
                alert_msg = f"High disk usage: {disk_info['percent']:.1f}% ({disk_info['used_gb']:.1f}GB used)"
                health_data["alerts"].append({
                    "type": "disk",
                    "severity": "high" if disk_info["percent"] > 95 else "medium",
                    "message": alert_msg
                })
                await alert_manager.send_alert(
                    "high_disk",
                    "High Disk Usage Detected",
                    alert_msg,
                    "high" if disk_info["percent"] > 95 else "medium"
                )
            
            # Service health
            service_health = self.get_service_health()
            health_data["metrics"]["services"] = service_health
            
            for service, is_healthy in service_health.items():
                if not is_healthy:
                    alert_msg = f"Service {service} is not responding properly"
                    health_data["alerts"].append({
                        "type": "service",
                        "service": service,
                        "severity": "high",
                        "message": alert_msg
                    })
                    await alert_manager.send_alert(
                        f"service_{service}",
                        f"Service {service} Failure",
                        alert_msg,
                        "high"
                    )
            
            # Additional metrics
            health_data["metrics"]["network"] = self.get_network_stats()
            health_data["metrics"]["process"] = self.get_process_info()
            
            # Determine overall status
            if health_data["alerts"]:
                high_severity = any(alert["severity"] == "high" for alert in health_data["alerts"])
                health_data["status"] = "critical" if high_severity else "warning"
            
            logger.info(f"System health check completed: {health_data['status']}")
            
        except Exception as e:
            logger.error(f"Error during system health check: {e}")
            health_data["status"] = "error"
            health_data["error"] = str(e)
            
            # Send alert about monitoring failure
            await alert_manager.send_alert(
                "monitoring_failure",
                "System Monitoring Failure",
                f"Failed to perform health check: {str(e)}",
                "high"
            )
        
        return health_data
    
    async def start_monitoring(self):
        """Start continuous background monitoring."""
        if not self.enabled:
            logger.info("System monitoring is disabled")
            return
        
        logger.info(f"Starting system monitoring with {self.check_interval}s interval")
        
        while True:
            try:
                await self.check_system_health()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent alerts from notification system."""
        try:
            from notifications import get_notifications, get_db
            
            db = next(get_db())
            try:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                alerts = get_notifications(
                    db,
                    limit=100,
                    unread_only=False
                )
                
                recent_alerts = []
                for alert in alerts:
                    if alert.created_at >= cutoff_time and alert.notification_type in ["error", "warning"]:
                        recent_alerts.append({
                            "id": alert.id,
                            "title": alert.title,
                            "message": alert.message,
                            "type": alert.notification_type,
                            "created_at": alert.created_at.isoformat(),
                            "is_read": alert.is_read
                        })
                
                return recent_alerts
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error getting recent alerts: {e}")
            return []


# Global monitor instance
system_monitor = SystemMonitor()
