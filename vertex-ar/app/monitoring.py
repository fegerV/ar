"""
Server monitoring system for Vertex AR - tracks system health and performance.
"""

import asyncio
import os
import time
import subprocess
import json
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
            "disk": settings.DISK_THRESHOLD,
        }
        # Store historical data for trend analysis (keep last 100 data points)
        self.historical_data: Dict[str, List[Dict[str, Any]]] = {"cpu": [], "memory": [], "disk": [], "network": []}
        # Track consecutive failures per service/metric for alert deduplication
        self.last_alerts: Dict[str, datetime] = {}
        # Track failure counts per metric/service key
        self.failure_counts: Dict[str, int] = {}
        # Consecutive failures required before escalating to alert
        self.consecutive_failure_threshold = getattr(settings, 'MONITORING_CONSECUTIVE_FAILURES', 3)
        # Deduplication window in seconds
        self.dedup_window = getattr(settings, 'MONITORING_DEDUP_WINDOW', settings.NOTIFICATION_DEDUP_WINDOW)

    def _should_escalate_alert(self, alert_key: str) -> bool:
        """
        Check if an alert should be escalated based on consecutive failures.
        
        Args:
            alert_key: Unique key for the alert (e.g., "cpu_high", "service_database")
            
        Returns:
            True if alert should be escalated, False otherwise
        """
        # Increment failure count
        self.failure_counts[alert_key] = self.failure_counts.get(alert_key, 0) + 1
        
        # Check if we've reached the consecutive failure threshold
        if self.failure_counts[alert_key] >= self.consecutive_failure_threshold:
            # Check deduplication window
            if alert_key in self.last_alerts:
                time_since_last = (datetime.utcnow() - self.last_alerts[alert_key]).total_seconds()
                if time_since_last < self.dedup_window:
                    logger.debug(f"Alert {alert_key} within dedup window ({time_since_last:.1f}s < {self.dedup_window}s)")
                    return False
            
            # Update last alert time
            self.last_alerts[alert_key] = datetime.utcnow()
            logger.info(f"Escalating alert {alert_key} after {self.failure_counts[alert_key]} consecutive failures")
            return True
        else:
            logger.debug(f"Alert {alert_key} not escalated: {self.failure_counts[alert_key]}/{self.consecutive_failure_threshold} failures")
            return False
    
    def _reset_failure_count(self, alert_key: str) -> None:
        """
        Reset the failure count for a metric/service that has recovered.
        
        Args:
            alert_key: Unique key for the alert
        """
        if alert_key in self.failure_counts and self.failure_counts[alert_key] > 0:
            logger.debug(f"Resetting failure count for {alert_key} (was {self.failure_counts[alert_key]})")
            self.failure_counts[alert_key] = 0
    
    def _determine_severity(self, metric_type: str, value: float, threshold: float) -> str:
        """
        Determine alert severity based on how much a metric exceeds its threshold.
        
        Args:
            metric_type: Type of metric (cpu, memory, disk)
            value: Current value
            threshold: Alert threshold
            
        Returns:
            Severity level: "warning", "medium", or "high"
        """
        # Calculate percentage over threshold
        overshoot = ((value - threshold) / threshold) * 100
        
        # Critical level (>15% over threshold or >95% for any metric)
        if value > 95 or overshoot > 15:
            return "high"
        # Degraded level (5-15% over threshold)
        elif overshoot > 5:
            return "medium"
        # Warning level (just over threshold)
        else:
            return "warning"
    
    def get_cpu_usage(self) -> Dict[str, Any]:
        """Get comprehensive CPU usage information."""
        # Current usage percentage
        cpu_percent = psutil.cpu_percent(interval=1)

        # Load averages (1, 5, 15 minutes)
        try:
            load_avg = os.getloadavg()
        except (AttributeError, OSError):
            # Windows doesn't support getloadavg
            load_avg = [0.0, 0.0, 0.0]

        # CPU count for context
        cpu_count = psutil.cpu_count()
        cpu_count_logical = psutil.cpu_count(logical=True)

        # Per-core usage
        cpu_per_core = psutil.cpu_percent(interval=0, percpu=True)

        # Top CPU consuming processes
        top_processes = []
        try:
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                try:
                    proc_info = proc.info
                    if proc_info["cpu_percent"] > 0:  # Only include processes using CPU
                        top_processes.append(
                            {
                                "pid": proc_info["pid"],
                                "name": proc_info["name"] or "Unknown",
                                "cpu_percent": proc_info["cpu_percent"],
                                "memory_percent": proc_info["memory_percent"] or 0,
                            }
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            # Sort by CPU usage and take top 10
            top_processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
            top_processes = top_processes[:10]

        except Exception as e:
            logger.error(f"Error getting top processes: {e}")
            top_processes = []

        return {
            "percent": cpu_percent,
            "load_average": {"1min": load_avg[0], "5min": load_avg[1], "15min": load_avg[2]},
            "cpu_count": {"physical": cpu_count, "logical": cpu_count_logical},
            "per_core": cpu_per_core,
            "top_processes": top_processes,
        }

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get comprehensive memory usage information."""
        # Virtual memory
        memory = psutil.virtual_memory()

        # Swap memory
        swap = psutil.swap_memory()

        # Memory breakdown by type
        memory_details = {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "free": memory.free,
            "active": getattr(memory, "active", 0),
            "inactive": getattr(memory, "inactive", 0),
            "buffers": getattr(memory, "buffers", 0),
            "cached": getattr(memory, "cached", 0),
            "shared": getattr(memory, "shared", 0),
            "slab": getattr(memory, "slab", 0),
        }

        # Top memory consuming processes
        top_memory_processes = []
        try:
            for proc in psutil.process_iter(["pid", "name", "memory_info", "memory_percent"]):
                try:
                    proc_info = proc.info
                    if (
                        proc_info["memory_percent"] and proc_info["memory_percent"] > 1
                    ):  # Only include processes using >1% memory
                        mem_info = proc_info["memory_info"]
                        top_memory_processes.append(
                            {
                                "pid": proc_info["pid"],
                                "name": proc_info["name"] or "Unknown",
                                "memory_percent": proc_info["memory_percent"],
                                "memory_mb": mem_info.rss / (1024**2) if mem_info else 0,
                                "memory_vms_mb": mem_info.vms / (1024**2) if mem_info else 0,
                            }
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            # Sort by memory usage and take top 10
            top_memory_processes.sort(key=lambda x: x["memory_percent"], reverse=True)
            top_memory_processes = top_memory_processes[:10]

        except Exception as e:
            logger.error(f"Error getting top memory processes: {e}")
            top_memory_processes = []

        return {
            "virtual": {
                "percent": memory.percent,
                "used_gb": memory.used / (1024**3),
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "free_gb": memory.free / (1024**3),
                "details": {k: v / (1024**3) if isinstance(v, int) and v > 1024**3 else v for k, v in memory_details.items()},
            },
            "swap": {
                "percent": swap.percent,
                "used_gb": swap.used / (1024**3),
                "total_gb": swap.total / (1024**3),
                "free_gb": swap.free / (1024**3),
                "sin_gb": swap.sin / (1024**3),  # Swap in
                "sout_gb": swap.sout / (1024**3),  # Swap out
            },
            "top_processes": top_memory_processes,
        }

    def get_disk_usage(self) -> Dict[str, Any]:
        """Get comprehensive disk usage and performance information."""
        try:
            # Basic disk usage for storage directory
            disk = psutil.disk_usage(str(settings.STORAGE_ROOT))

            # Get disk I/O statistics
            disk_io = psutil.disk_io_counters()

            # Get all disk partitions for comprehensive view
            partitions = []
            for part in psutil.disk_partitions(all=False):
                try:
                    part_usage = psutil.disk_usage(part.mountpoint)
                    partitions.append(
                        {
                            "device": part.device,
                            "mountpoint": part.mountpoint,
                            "fstype": part.fstype,
                            "percent": (part_usage.used / part_usage.total) * 100,
                            "used_gb": part_usage.used / (1024**3),
                            "total_gb": part_usage.total / (1024**3),
                            "free_gb": part_usage.free / (1024**3),
                        }
                    )
                except (PermissionError, OSError):
                    # Skip partitions we can't access
                    continue

            # Calculate I/O rates (need previous values for rate calculation)
            current_time = time.time()
            io_stats = {}
            if disk_io:
                io_stats = {
                    "read_bytes": disk_io.read_bytes,
                    "write_bytes": disk_io.write_bytes,
                    "read_count": disk_io.read_count,
                    "write_count": disk_io.write_count,
                    "read_time_ms": disk_io.read_time,
                    "write_time_ms": disk_io.write_time,
                    "read_bytes_gb": disk_io.read_bytes / (1024**3),
                    "write_bytes_gb": disk_io.write_bytes / (1024**3),
                }

                # Calculate average I/O size
                if disk_io.read_count > 0:
                    io_stats["avg_read_size_kb"] = disk_io.read_bytes / disk_io.read_count / 1024
                if disk_io.write_count > 0:
                    io_stats["avg_write_size_kb"] = disk_io.write_bytes / disk_io.write_count / 1024

                # Calculate IOPS approximation (simplified)
                io_stats["total_iops"] = disk_io.read_count + disk_io.write_count

                # Calculate latency approximation
                if disk_io.read_count > 0:
                    io_stats["avg_read_latency_ms"] = disk_io.read_time / disk_io.read_count
                if disk_io.write_count > 0:
                    io_stats["avg_write_latency_ms"] = disk_io.write_time / disk_io.write_count

            # Get disk temperature if available (Linux specific)
            temperature_info = self._get_disk_temperature()

            return {
                "storage": {
                    "percent": (disk.used / disk.total) * 100,
                    "used_gb": disk.used / (1024**3),
                    "total_gb": disk.total / (1024**3),
                    "free_gb": disk.free / (1024**3),
                },
                "partitions": partitions,
                "io_stats": io_stats,
                "temperature": temperature_info,
            }

        except Exception as e:
            logger.error(f"Error getting disk usage: {e}")
            return {
                "storage": {"percent": 0, "used_gb": 0, "total_gb": 0, "free_gb": 0},
                "partitions": [],
                "io_stats": {},
                "temperature": {},
            }

    def _get_disk_temperature(self) -> Dict[str, Any]:
        """Get disk temperature information (Linux specific)."""
        temps = {}
        try:
            # Try to read SMART temperature data from hddtemp or smartctl
            if os.path.exists("/usr/sbin/hddtemp"):
                try:
                    result = subprocess.run(
                        ["/usr/sbin/hddtemp", "/dev/sd*", "/dev/nvme*"], capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        for line in result.stdout.strip().split("\n"):
                            if ": " in line and "°C" in line:
                                parts = line.split(":")
                                if len(parts) >= 3:
                                    device = parts[0].strip()
                                    temp_str = parts[2].strip()
                                    temp_value = temp_str.replace("°C", "").strip()
                                    try:
                                        temps[device] = float(temp_value)
                                    except ValueError:
                                        continue
                except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                    pass

            # Try smartctl as fallback
            elif os.path.exists("/usr/sbin/smartctl"):
                try:
                    result = subprocess.run(["lsblk", "-d", "-o", "NAME"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        disks = result.stdout.strip().split("\n")[1:]  # Skip header
                        for disk in disks:
                            disk = disk.strip()
                            if disk and not disk.startswith("loop"):
                                try:
                                    smart_result = subprocess.run(
                                        ["/usr/sbin/smartctl", "-A", f"/dev/{disk}"],
                                        capture_output=True,
                                        text=True,
                                        timeout=10,
                                    )
                                    if smart_result.returncode == 0:
                                        for line in smart_result.stdout.split("\n"):
                                            if "Temperature_Celsius" in line or "Temperature" in line:
                                                parts = line.split()
                                                for i, part in enumerate(parts):
                                                    if part.isdigit() and 0 < int(part) < 100:
                                                        temps[f"/dev/{disk}"] = int(part)
                                                        break
                                except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                                    continue
                except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                    pass

        except Exception as e:
            logger.debug(f"Could not get disk temperature: {e}")

        return temps

    def get_network_stats(self) -> Dict[str, Any]:
        """Get comprehensive network interface statistics."""
        try:
            # Overall network I/O counters
            net_io = psutil.net_io_counters()

            # Per-interface statistics
            net_if_addrs = psutil.net_if_addrs()
            net_if_stats = psutil.net_if_stats()
            net_io_per_if = psutil.net_io_counters(pernic=True)

            # Detailed interface information
            interfaces = {}
            for interface_name, stats in net_if_stats.items():
                if interface_name in net_io_per_if:
                    io_stats = net_io_per_if[interface_name]
                    interface_info = {
                        "is_up": stats.isup,
                        "speed": stats.speed,  # Mbps
                        "mtu": stats.mtu,
                        "duplex": stats.duplex,  # 0=unknown, 1=half, 2=full
                        "bytes_sent": io_stats.bytes_sent,
                        "bytes_recv": io_stats.bytes_recv,
                        "packets_sent": io_stats.packets_sent,
                        "packets_recv": io_stats.packets_recv,
                        "errin": io_stats.errin,
                        "errout": io_stats.errout,
                        "dropin": io_stats.dropin,
                        "dropout": io_stats.dropout,
                    }

                    # Calculate rates (simplified - would need historical data for true rates)
                    interface_info["bytes_sent_mb"] = io_stats.bytes_sent / (1024**2)
                    interface_info["bytes_recv_mb"] = io_stats.bytes_recv / (1024**2)

                    # Add error rates
                    if io_stats.packets_recv > 0:
                        interface_info["error_in_rate"] = (io_stats.errin / io_stats.packets_recv) * 100
                    if io_stats.packets_sent > 0:
                        interface_info["error_out_rate"] = (io_stats.errout / io_stats.packets_sent) * 100

                    # Add drop rates
                    if io_stats.packets_recv > 0:
                        interface_info["drop_in_rate"] = (io_stats.dropin / io_stats.packets_recv) * 100
                    if io_stats.packets_sent > 0:
                        interface_info["drop_out_rate"] = (io_stats.dropout / io_stats.packets_sent) * 100

                    # Add IP addresses if available
                    if interface_name in net_if_addrs:
                        addresses = []
                        for addr in net_if_addrs[interface_name]:
                            if addr.family.name in ["AF_INET", "AF_INET6"]:
                                addresses.append(
                                    {
                                        "family": addr.family.name,
                                        "address": addr.address,
                                        "netmask": addr.netmask,
                                        "broadcast": addr.broadcast,
                                    }
                                )
                        interface_info["addresses"] = addresses

                    interfaces[interface_name] = interface_info

            # Network connections
            connections = self._get_network_connections()

            # Calculate overall rates and totals
            total_stats = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errin": net_io.errin,
                "errout": net_io.errout,
                "dropin": net_io.dropin,
                "dropout": net_io.dropout,
                "bytes_sent_gb": net_io.bytes_sent / (1024**3),
                "bytes_recv_gb": net_io.bytes_recv / (1024**3),
            }

            # Calculate overall error and drop rates
            if net_io.packets_recv > 0:
                total_stats["error_in_rate"] = (net_io.errin / net_io.packets_recv) * 100
                total_stats["drop_in_rate"] = (net_io.dropin / net_io.packets_recv) * 100
            if net_io.packets_sent > 0:
                total_stats["error_out_rate"] = (net_io.errout / net_io.packets_sent) * 100
                total_stats["drop_out_rate"] = (net_io.dropout / net_io.packets_sent) * 100

            return {"total": total_stats, "interfaces": interfaces, "connections": connections}

        except Exception as e:
            logger.error(f"Error getting network stats: {e}")
            return {"total": {}, "interfaces": {}, "connections": {}}

    def _get_network_connections(self) -> Dict[str, Any]:
        """Get network connection statistics."""
        try:
            connections = psutil.net_connections()

            # Count connections by status
            status_counts = {}
            local_ports = set()
            remote_hosts = set()

            for conn in connections:
                status = conn.status
                if status in status_counts:
                    status_counts[status] += 1
                else:
                    status_counts[status] = 1

                # Track local ports
                if conn.laddr:
                    local_ports.add(conn.laddr.port)

                # Track remote hosts
                if conn.raddr:
                    remote_hosts.add(conn.raddr.ip)

            # Get listening ports
            listening_ports = []
            for conn in connections:
                if conn.status == "LISTEN" and conn.laddr:
                    listening_ports.append({"port": conn.laddr.port, "address": conn.laddr.ip, "pid": conn.pid})

            return {
                "total_connections": len(connections),
                "status_breakdown": status_counts,
                "listening_ports": sorted(listening_ports, key=lambda x: x["port"]),
                "unique_local_ports": len(local_ports),
                "unique_remote_hosts": len(remote_hosts),
            }

        except Exception as e:
            logger.error(f"Error getting network connections: {e}")
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
                "status": process.status(),
            }
        except Exception as e:
            logger.error(f"Error getting process info: {e}")
            return {}

    def get_service_health(self) -> Dict[str, Any]:
        """Check comprehensive health of various services with response times."""
        health_status = {}

        # Check database accessibility with response time
        db_start_time = time.time()
        try:
            from app.database import Database

            db = Database(settings.DB_PATH)
            # Simple query to test connection
            db.get_company("vertex-ar-default")
            db_response_time = (time.time() - db_start_time) * 1000  # Convert to ms

            health_status["database"] = {
                "healthy": True,
                "response_time_ms": round(db_response_time, 2),
                "status": "operational",
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_status["database"] = {"healthy": False, "response_time_ms": None, "status": "failed", "error": str(e)}

        # Check storage accessibility with response time
        storage_start_time = time.time()
        try:
            test_file = settings.STORAGE_ROOT / ".health_check"
            test_file.write_text("test")
            test_file.unlink()
            storage_response_time = (time.time() - storage_start_time) * 1000

            health_status["storage"] = {
                "healthy": True,
                "response_time_ms": round(storage_response_time, 2),
                "status": "operational",
            }
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            health_status["storage"] = {"healthy": False, "response_time_ms": None, "status": "failed", "error": str(e)}

        # Check MinIO if configured
        if settings.STORAGE_TYPE == "minio":
            minio_start_time = time.time()
            try:
                from app.storage_minio import MinioStorageAdapter

                storage = MinioStorageAdapter(
                    endpoint=settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    bucket=settings.MINIO_BUCKET,
                )
                # Test connection by listing objects
                storage.list_files("")
                minio_response_time = (time.time() - minio_start_time) * 1000

                health_status["minio"] = {
                    "healthy": True,
                    "response_time_ms": round(minio_response_time, 2),
                    "status": "operational",
                }
            except Exception as e:
                logger.error(f"MinIO health check failed: {e}")
                health_status["minio"] = {"healthy": False, "response_time_ms": None, "status": "failed", "error": str(e)}
        else:
            health_status["minio"] = {
                "healthy": True,
                "response_time_ms": None,
                "status": "not_configured",
            }  # Not used, so considered healthy

        # Check web server response time (self-check)
        web_start_time = time.time()
        try:
            import requests

            response = requests.get(f"{settings.BASE_URL}/health", timeout=5)
            web_response_time = (time.time() - web_start_time) * 1000

            health_status["web_server"] = {
                "healthy": response.status_code == 200,
                "response_time_ms": round(web_response_time, 2),
                "status": "operational" if response.status_code == 200 else "degraded",
                "status_code": response.status_code,
            }
        except Exception as e:
            logger.error(f"Web server health check failed: {e}")
            health_status["web_server"] = {"healthy": False, "response_time_ms": None, "status": "failed", "error": str(e)}

        # Check external services if configured
        health_status["external_services"] = self._check_external_services()

        # Get recent error logs
        health_status["recent_errors"] = self._get_recent_errors()

        return health_status

    def _check_external_services(self) -> Dict[str, Any]:
        """Check health of external services."""
        external_services = {}

        # Check email service if configured
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            try:
                import smtplib
                import socket

                start_time = time.time()
                with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=5) as server:
                    server.starttls()
                    # Don't actually login, just check if server responds
                response_time = (time.time() - start_time) * 1000

                external_services["email"] = {
                    "healthy": True,
                    "response_time_ms": round(response_time, 2),
                    "status": "operational",
                }
            except Exception as e:
                logger.error(f"Email service health check failed: {e}")
                external_services["email"] = {"healthy": False, "response_time_ms": None, "status": "failed", "error": str(e)}
        else:
            external_services["email"] = {"healthy": True, "response_time_ms": None, "status": "not_configured"}

        # Check Telegram bot if configured
        if settings.TELEGRAM_BOT_TOKEN:
            try:
                import requests

                start_time = time.time()
                response = requests.get(f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe", timeout=5)
                response_time = (time.time() - start_time) * 1000

                external_services["telegram"] = {
                    "healthy": response.status_code == 200,
                    "response_time_ms": round(response_time, 2),
                    "status": "operational" if response.status_code == 200 else "degraded",
                    "status_code": response.status_code,
                }
            except Exception as e:
                logger.error(f"Telegram bot health check failed: {e}")
                external_services["telegram"] = {
                    "healthy": False,
                    "response_time_ms": None,
                    "status": "failed",
                    "error": str(e),
                }
        else:
            external_services["telegram"] = {"healthy": True, "response_time_ms": None, "status": "not_configured"}

        return external_services

    def _get_recent_errors(self) -> Dict[str, Any]:
        """Get recent error logs from the application."""
        try:
            # Try to read from log files if they exist
            log_files = []
            log_dir = settings.BASE_DIR / "logs"

            if log_dir.exists():
                for log_file in log_dir.glob("*.log"):
                    try:
                        recent_errors = []
                        with open(log_file, "r", encoding="utf-8") as f:
                            lines = f.readlines()[-100:]  # Get last 100 lines

                        for line in lines:
                            if any(level in line.upper() for level in ["ERROR", "CRITICAL", "FATAL"]):
                                # Extract timestamp and message
                                parts = line.strip().split(" ", 3)
                                if len(parts) >= 4:
                                    timestamp = f"{parts[0]} {parts[1]}"
                                    level = parts[2]
                                    message = parts[3]
                                    recent_errors.append(
                                        {
                                            "timestamp": timestamp,
                                            "level": level,
                                            "message": message[:200],  # Truncate long messages
                                        }
                                    )

                        log_files.append({"file": log_file.name, "recent_errors": recent_errors[-20:]})  # Last 20 errors
                    except Exception as e:
                        logger.debug(f"Could not read log file {log_file}: {e}")

            return {"log_files": log_files, "total_errors": sum(len(f["recent_errors"]) for f in log_files)}

        except Exception as e:
            logger.error(f"Error getting recent errors: {e}")
            return {"log_files": [], "total_errors": 0}

    def _store_historical_data(self, metrics: Dict[str, Any]):
        """Store current metrics for historical analysis."""
        timestamp = datetime.utcnow()

        # Store CPU data
        if "cpu" in metrics:
            self.historical_data["cpu"].append(
                {
                    "timestamp": timestamp.isoformat(),
                    "percent": metrics["cpu"]["percent"],
                    "load_1min": metrics["cpu"]["load_average"]["1min"],
                    "load_5min": metrics["cpu"]["load_average"]["5min"],
                }
            )
            if len(self.historical_data["cpu"]) > 100:
                self.historical_data["cpu"] = self.historical_data["cpu"][-100:]

        # Store memory data
        if "memory" in metrics:
            self.historical_data["memory"].append(
                {
                    "timestamp": timestamp.isoformat(),
                    "percent": metrics["memory"]["virtual"]["percent"],
                    "swap_percent": metrics["memory"]["swap"]["percent"],
                    "used_gb": metrics["memory"]["virtual"]["used_gb"],
                }
            )
            if len(self.historical_data["memory"]) > 100:
                self.historical_data["memory"] = self.historical_data["memory"][-100:]

        # Store disk data
        if "disk" in metrics:
            self.historical_data["disk"].append(
                {
                    "timestamp": timestamp.isoformat(),
                    "percent": metrics["disk"]["storage"]["percent"],
                    "used_gb": metrics["disk"]["storage"]["used_gb"],
                    "free_gb": metrics["disk"]["storage"]["free_gb"],
                }
            )
            if len(self.historical_data["disk"]) > 100:
                self.historical_data["disk"] = self.historical_data["disk"][-100:]

        # Store network data
        if "network" in metrics and "total" in metrics["network"]:
            self.historical_data["network"].append(
                {
                    "timestamp": timestamp.isoformat(),
                    "bytes_sent_gb": metrics["network"]["total"]["bytes_sent_gb"],
                    "bytes_recv_gb": metrics["network"]["total"]["bytes_recv_gb"],
                    "packets_sent": metrics["network"]["total"]["packets_sent"],
                    "packets_recv": metrics["network"]["total"]["packets_recv"],
                    "error_in_rate": metrics["network"]["total"].get("error_in_rate", 0),
                    "error_out_rate": metrics["network"]["total"].get("error_out_rate", 0),
                }
            )
            if len(self.historical_data["network"]) > 100:
                self.historical_data["network"] = self.historical_data["network"][-100:]

    def get_historical_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get historical trends and analysis."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        trends = {}
        recent_data = []

        for metric_type, data in self.historical_data.items():
            # Filter data by time
            recent_data = [point for point in data if datetime.fromisoformat(point["timestamp"]) >= cutoff_time]

            if len(recent_data) < 2:
                trends[metric_type] = {
                    "trend": "insufficient_data",
                    "data_points": len(recent_data),
                    "avg": 0,
                    "min": 0,
                    "max": 0,
                }
                continue

            # Calculate trends based on metric type
            if metric_type == "cpu":
                values = [point["percent"] for point in recent_data]
                trends[metric_type] = self._calculate_trend(values, recent_data, "percent")

            elif metric_type == "memory":
                values = [point["percent"] for point in recent_data]
                trends[metric_type] = self._calculate_trend(values, recent_data, "percent")

            elif metric_type == "disk":
                values = [point["percent"] for point in recent_data]
                trends[metric_type] = self._calculate_trend(values, recent_data, "percent")

            elif metric_type == "network":
                sent_values = [point["bytes_sent_gb"] for point in recent_data]
                recv_values = [point["bytes_recv_gb"] for point in recent_data]
                trends[metric_type] = {
                    "sent": self._calculate_trend(sent_values, recent_data, "gb"),
                    "received": self._calculate_trend(recv_values, recent_data, "gb"),
                    "error_rates": {
                        "avg_in": sum(point.get("error_in_rate", 0) for point in recent_data) / len(recent_data),
                        "avg_out": sum(point.get("error_out_rate", 0) for point in recent_data) / len(recent_data),
                    },
                }

        return {"period_hours": hours, "data_points": len(recent_data) if recent_data else 0, "trends": trends}

    def _calculate_trend(self, values: List[float], data_points: List[Dict], unit: str) -> Dict[str, Any]:
        """Calculate trend statistics for a series of values."""
        if not values:
            return {"trend": "no_data", "avg": 0, "min": 0, "max": 0}

        avg_value = sum(values) / len(values)
        min_value = min(values)
        max_value = max(values)

        # Calculate trend (simple linear regression slope)
        if len(values) >= 2:
            n = len(values)
            x_values = list(range(n))

            # Calculate slope
            x_mean = sum(x_values) / n
            y_mean = sum(values) / n

            numerator = sum((x_values[i] - x_mean) * (values[i] - y_mean) for i in range(n))
            denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

            if denominator != 0:
                slope = numerator / denominator
                # Determine trend direction
                if abs(slope) < 0.01:
                    trend_direction = "stable"
                elif slope > 0:
                    trend_direction = "increasing"
                else:
                    trend_direction = "decreasing"
            else:
                slope = 0
                trend_direction = "stable"
        else:
            slope = 0
            trend_direction = "stable"

        return {
            "trend": trend_direction,
            "slope": round(slope, 4),
            "avg": round(avg_value, 2),
            "min": round(min_value, 2),
            "max": round(max_value, 2),
            "unit": unit,
            "data_points": len(values),
        }

    async def check_system_health(self) -> Dict[str, Any]:
        """Perform comprehensive system health check."""
        if not self.enabled:
            return {"status": "disabled"}

        health_data = {"timestamp": datetime.utcnow().isoformat(), "status": "healthy", "alerts": [], "metrics": {}}

        try:
            # CPU check
            cpu_usage = self.get_cpu_usage()
            health_data["metrics"]["cpu"] = cpu_usage

            if cpu_usage["percent"] > self.alert_thresholds["cpu"]:
                alert_key = "high_cpu"
                severity = self._determine_severity("cpu", cpu_usage["percent"], self.alert_thresholds["cpu"])
                alert_msg = f"High CPU usage: {cpu_usage['percent']:.1f}% (threshold: {self.alert_thresholds['cpu']}%)"
                if cpu_usage["load_average"]["1min"] > cpu_usage["cpu_count"]["physical"]:
                    alert_msg += f", Load average: {cpu_usage['load_average']['1min']:.1f}"
                
                # Check if we should escalate this alert
                if self._should_escalate_alert(alert_key):
                    health_data["alerts"].append(
                        {"type": "cpu", "severity": severity, "message": alert_msg}
                    )
                    await alert_manager.send_alert(
                        alert_key, "High CPU Usage Detected", alert_msg, severity
                    )
                else:
                    # Add to health_data for visibility but don't send alert yet
                    health_data["alerts"].append(
                        {"type": "cpu", "severity": "warning", "message": f"Monitoring: {alert_msg} (transient)", "transient": True}
                    )
            else:
                # Reset failure count when metric is healthy
                self._reset_failure_count("high_cpu")

            # Memory check
            memory_info = self.get_memory_usage()
            health_data["metrics"]["memory"] = memory_info

            if memory_info["virtual"]["percent"] > self.alert_thresholds["memory"]:
                alert_key = "high_memory"
                severity = self._determine_severity("memory", memory_info["virtual"]["percent"], self.alert_thresholds["memory"])
                alert_msg = f"High memory usage: {memory_info['virtual']['percent']:.1f}% ({memory_info['virtual']['used_gb']:.1f}GB used)"
                if memory_info["swap"]["percent"] > 50:
                    alert_msg += f", Swap: {memory_info['swap']['percent']:.1f}%"
                
                # Check if we should escalate this alert
                if self._should_escalate_alert(alert_key):
                    health_data["alerts"].append(
                        {
                            "type": "memory",
                            "severity": severity,
                            "message": alert_msg,
                        }
                    )
                    await alert_manager.send_alert(
                        alert_key,
                        "High Memory Usage Detected",
                        alert_msg,
                        severity,
                    )
                else:
                    # Add to health_data for visibility but don't send alert yet
                    health_data["alerts"].append(
                        {"type": "memory", "severity": "warning", "message": f"Monitoring: {alert_msg} (transient)", "transient": True}
                    )
            else:
                # Reset failure count when metric is healthy
                self._reset_failure_count("high_memory")

            # Disk check
            disk_info = self.get_disk_usage()
            health_data["metrics"]["disk"] = disk_info

            if disk_info["storage"]["percent"] > self.alert_thresholds["disk"]:
                alert_key = "high_disk"
                severity = self._determine_severity("disk", disk_info["storage"]["percent"], self.alert_thresholds["disk"])
                alert_msg = (
                    f"High disk usage: {disk_info['storage']['percent']:.1f}% ({disk_info['storage']['used_gb']:.1f}GB used)"
                )
                
                # Check if we should escalate this alert
                if self._should_escalate_alert(alert_key):
                    health_data["alerts"].append(
                        {
                            "type": "disk",
                            "severity": severity,
                            "message": alert_msg,
                        }
                    )
                    await alert_manager.send_alert(
                        alert_key,
                        "High Disk Usage Detected",
                        alert_msg,
                        severity,
                    )
                else:
                    # Add to health_data for visibility but don't send alert yet
                    health_data["alerts"].append(
                        {"type": "disk", "severity": "warning", "message": f"Monitoring: {alert_msg} (transient)", "transient": True}
                    )
            else:
                # Reset failure count when metric is healthy
                self._reset_failure_count("high_disk")

            # Service health
            service_health = self.get_service_health()
            health_data["metrics"]["services"] = service_health

            # Check core services
            for service_name, service_data in service_health.items():
                if service_name in ["database", "storage", "minio", "web_server"]:
                    alert_key = f"service_{service_name}"
                    
                    if not service_data["healthy"]:
                        alert_msg = f"Service {service_name} is not responding properly"
                        if service_data.get("response_time_ms"):
                            alert_msg += f" (response time: {service_data['response_time_ms']}ms)"
                        
                        # Check if we should escalate this alert
                        if self._should_escalate_alert(alert_key):
                            health_data["alerts"].append(
                                {"type": "service", "service": service_name, "severity": "high", "message": alert_msg}
                            )
                            await alert_manager.send_alert(
                                alert_key, f"Service {service_name} Failure", alert_msg, "high"
                            )
                        else:
                            # Add to health_data for visibility but don't send alert yet
                            health_data["alerts"].append(
                                {"type": "service", "service": service_name, "severity": "warning", "message": f"Monitoring: {alert_msg} (transient)", "transient": True}
                            )
                    elif (
                        service_data.get("response_time_ms") is not None and service_data.get("response_time_ms") > 5000
                    ):  # 5 seconds - degraded but not failed
                        alert_key_slow = f"service_{service_name}_slow"
                        alert_msg = f"Service {service_name} response time is high: {service_data['response_time_ms']}ms (degraded)"
                        
                        # Check if we should escalate this alert
                        if self._should_escalate_alert(alert_key_slow):
                            health_data["alerts"].append(
                                {
                                    "type": "service_performance",
                                    "service": service_name,
                                    "severity": "warning",  # Downgraded from medium since service is still working
                                    "message": alert_msg,
                                }
                            )
                            await alert_manager.send_alert(
                                alert_key_slow, f"Service {service_name} Slow Response", alert_msg, "medium"
                            )
                        else:
                            # Add to health_data for visibility but don't send alert yet
                            health_data["alerts"].append(
                                {"type": "service_performance", "service": service_name, "severity": "warning", "message": f"Monitoring: {alert_msg} (transient)", "transient": True}
                            )
                        # Reset the main service failure count since it's responding (just slowly)
                        self._reset_failure_count(alert_key)
                    else:
                        # Service is healthy, reset failure counts
                        self._reset_failure_count(alert_key)
                        self._reset_failure_count(f"service_{service_name}_slow")

            # Check external services
            if "external_services" in service_health:
                for ext_service, ext_data in service_health["external_services"].items():
                    alert_key = f"external_{ext_service}"
                    
                    if not ext_data["healthy"]:
                        alert_msg = f"External service {ext_service} is not responding properly"
                        
                        # Check if we should escalate this alert
                        if self._should_escalate_alert(alert_key):
                            health_data["alerts"].append(
                                {"type": "external_service", "service": ext_service, "severity": "medium", "message": alert_msg}
                            )
                            await alert_manager.send_alert(
                                alert_key, f"External Service {ext_service.title()} Failure", alert_msg, "medium"
                            )
                        else:
                            # Add to health_data for visibility but don't send alert yet
                            health_data["alerts"].append(
                                {"type": "external_service", "service": ext_service, "severity": "warning", "message": f"Monitoring: {alert_msg} (transient)", "transient": True}
                            )
                    else:
                        # Reset failure count when service is healthy
                        self._reset_failure_count(alert_key)

            # Check for recent errors
            if "recent_errors" in service_health and service_health["recent_errors"]["total_errors"] > 10:
                alert_key = "high_error_count"
                alert_msg = f"High number of recent errors: {service_health['recent_errors']['total_errors']} errors found"
                
                # Check if we should escalate this alert
                if self._should_escalate_alert(alert_key):
                    health_data["alerts"].append({"type": "error_logs", "severity": "medium", "message": alert_msg})
                    await alert_manager.send_alert(alert_key, "High Error Count Detected", alert_msg, "medium")
                else:
                    # Add to health_data for visibility but don't send alert yet
                    health_data["alerts"].append(
                        {"type": "error_logs", "severity": "warning", "message": f"Monitoring: {alert_msg} (transient)", "transient": True}
                    )
            else:
                # Reset failure count when errors are below threshold
                self._reset_failure_count("high_error_count")

            # Additional metrics
            health_data["metrics"]["network"] = self.get_network_stats()
            health_data["metrics"]["process"] = self.get_process_info()

            # Store historical data
            self._store_historical_data(health_data["metrics"])

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
                "monitoring_failure", "System Monitoring Failure", f"Failed to perform health check: {str(e)}", "high"
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
                alerts = get_notifications(db, limit=100, unread_only=False)

                recent_alerts = []
                for alert in alerts:
                    if alert.created_at >= cutoff_time and alert.notification_type in ["error", "warning"]:
                        recent_alerts.append(
                            {
                                "id": alert.id,
                                "title": alert.title,
                                "message": alert.message,
                                "type": alert.notification_type,
                                "created_at": alert.created_at.isoformat(),
                                "is_read": alert.is_read,
                            }
                        )

                return recent_alerts
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error getting recent alerts: {e}")
            return []


# Global monitor instance
system_monitor = SystemMonitor()
