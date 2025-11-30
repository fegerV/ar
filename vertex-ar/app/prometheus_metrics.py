"""
Prometheus metrics exporter for Vertex AR monitoring system.
Exports comprehensive system and application metrics in Prometheus format.
"""
import time
from typing import Dict, Any
from prometheus_client import Gauge, Counter, Histogram, CollectorRegistry, generate_latest
from prometheus_client.core import REGISTRY

from app.monitoring import system_monitor
from app.config import settings
from logging_setup import get_logger

logger = get_logger(__name__)

# Import email service metrics (registered automatically on import)
try:
    from app.email_service import email_service
except ImportError:
    logger.warning("Email service not available for metrics export")
    email_service = None

# Create a custom registry for our metrics
registry = CollectorRegistry()

# System metrics
cpu_usage_gauge = Gauge('vertex_ar_cpu_usage_percent', 'CPU usage percentage', ['core'], registry=registry)
cpu_overall_gauge = Gauge('vertex_ar_cpu_overall_percent', 'Overall CPU usage percentage', registry=registry)
cpu_load_avg_gauge = Gauge('vertex_ar_cpu_load_average', 'CPU load average', ['period'], registry=registry)
memory_usage_gauge = Gauge('vertex_ar_memory_usage_bytes', 'Memory usage in bytes', ['type'], registry=registry)
memory_percent_gauge = Gauge('vertex_ar_memory_usage_percent', 'Memory usage percentage', ['type'], registry=registry)
disk_usage_gauge = Gauge('vertex_ar_disk_usage_bytes', 'Disk usage in bytes', ['mountpoint', 'type'], registry=registry)
disk_percent_gauge = Gauge('vertex_ar_disk_usage_percent', 'Disk usage percentage', ['mountpoint'], registry=registry)
disk_io_gauge = Gauge('vertex_ar_disk_io_bytes', 'Disk I/O bytes', ['direction'], registry=registry)
disk_io_count_gauge = Gauge('vertex_ar_disk_io_count', 'Disk I/O operations count', ['direction'], registry=registry)
disk_latency_gauge = Gauge('vertex_ar_disk_latency_ms', 'Disk latency in milliseconds', ['direction'], registry=registry)

# Network metrics
network_bytes_gauge = Gauge('vertex_ar_network_bytes_total', 'Network bytes total', ['interface', 'direction'], registry=registry)
network_packets_gauge = Gauge('vertex_ar_network_packets_total', 'Network packets total', ['interface', 'direction'], registry=registry)
network_errors_gauge = Gauge('vertex_ar_network_errors_total', 'Network errors total', ['interface', 'direction'], registry=registry)
network_drops_gauge = Gauge('vertex_ar_network_drops_total', 'Network drops total', ['interface', 'direction'], registry=registry)
network_connections_gauge = Gauge('vertex_ar_network_connections', 'Network connections by status', ['status'], registry=registry)

# Service health metrics
service_health_gauge = Gauge('vertex_ar_service_health', 'Service health status (1=healthy, 0=unhealthy)', ['service'], registry=registry)
service_response_time_gauge = Gauge('vertex_ar_service_response_time_ms', 'Service response time in milliseconds', ['service'], registry=registry)

# Application metrics
process_memory_gauge = Gauge('vertex_ar_process_memory_bytes', 'Process memory usage in bytes', ['type'], registry=registry)
process_cpu_gauge = Gauge('vertex_ar_process_cpu_percent', 'Process CPU usage percentage', [], registry=registry)
process_threads_gauge = Gauge('vertex_ar_process_threads', 'Number of process threads', [], registry=registry)

# Alert metrics
alert_counter = Counter('vertex_ar_alerts_total', 'Total number of alerts triggered', ['type', 'severity'], registry=registry)
active_alerts_gauge = Gauge('vertex_ar_active_alerts', 'Number of active alerts', ['severity'], registry=registry)

# Temperature metrics (if available)
disk_temperature_gauge = Gauge('vertex_ar_disk_temperature_celsius', 'Disk temperature in Celsius', ['device'], registry=registry)

# Historical trend metrics
trend_gauge = Gauge('vertex_ar_metric_trend', 'Metric trend slope', ['metric'], registry=registry)


class PrometheusExporter:
    """Exports monitoring metrics in Prometheus format."""
    
    def __init__(self):
        self.last_update = 0
        self.update_interval = 30  # Update every 30 seconds
        
    def update_metrics(self):
        """Update all Prometheus metrics with current system data."""
        try:
            current_time = time.time()
            if current_time - self.last_update < self.update_interval:
                return generate_latest(registry)
            
            # Get current system metrics
            cpu_metrics = system_monitor.get_cpu_usage()
            memory_metrics = system_monitor.get_memory_usage()
            disk_metrics = system_monitor.get_disk_usage()
            network_metrics = system_monitor.get_network_stats()
            service_health = system_monitor.get_service_health()
            process_info = system_monitor.get_process_info()
            
            # Update CPU metrics
            cpu_overall_gauge.set(cpu_metrics["percent"])
            
            # Load averages
            cpu_load_avg_gauge.labels(period='1min').set(cpu_metrics["load_average"]["1min"])
            cpu_load_avg_gauge.labels(period='5min').set(cpu_metrics["load_average"]["5min"])
            cpu_load_avg_gauge.labels(period='15min').set(cpu_metrics["load_average"]["15min"])
            
            # Per-core CPU usage
            for i, core_usage in enumerate(cpu_metrics["per_core"]):
                cpu_usage_gauge.labels(core=f'core_{i}').set(core_usage)
            
            # Memory metrics
            memory_usage_gauge.labels(type='used').set(memory_metrics["virtual"]["used_gb"] * 1024**3)
            memory_usage_gauge.labels(type='available').set(memory_metrics["virtual"]["available_gb"] * 1024**3)
            memory_usage_gauge.labels(type='total').set(memory_metrics["virtual"]["total_gb"] * 1024**3)
            memory_usage_gauge.labels(type='swap_used').set(memory_metrics["swap"]["used_gb"] * 1024**3)
            memory_usage_gauge.labels(type='swap_total').set(memory_metrics["swap"]["total_gb"] * 1024**3)
            
            memory_percent_gauge.labels(type='virtual').set(memory_metrics["virtual"]["percent"])
            memory_percent_gauge.labels(type='swap').set(memory_metrics["swap"]["percent"])
            
            # Disk metrics
            disk_usage_gauge.labels(mountpoint='storage', type='used').set(disk_metrics["storage"]["used_gb"] * 1024**3)
            disk_usage_gauge.labels(mountpoint='storage', type='free').set(disk_metrics["storage"]["free_gb"] * 1024**3)
            disk_usage_gauge.labels(mountpoint='storage', type='total').set(disk_metrics["storage"]["total_gb"] * 1024**3)
            disk_percent_gauge.labels(mountpoint='storage').set(disk_metrics["storage"]["percent"])
            
            # All partitions
            for partition in disk_metrics["partitions"]:
                mountpoint = partition["mountpoint"].replace("/", "_")
                if mountpoint == "":
                    mountpoint = "root"
                disk_usage_gauge.labels(mountpoint=mountpoint, type='used').set(partition["used_gb"] * 1024**3)
                disk_usage_gauge.labels(mountpoint=mountpoint, type='free').set(partition["free_gb"] * 1024**3)
                disk_percent_gauge.labels(mountpoint=mountpoint).set(partition["percent"])
            
            # Disk I/O metrics
            if "io_stats" in disk_metrics and disk_metrics["io_stats"]:
                io_stats = disk_metrics["io_stats"]
                disk_io_gauge.labels(direction='read').set(io_stats.get("read_bytes", 0))
                disk_io_gauge.labels(direction='write').set(io_stats.get("write_bytes", 0))
                disk_io_count_gauge.labels(direction='read').set(io_stats.get("read_count", 0))
                disk_io_count_gauge.labels(direction='write').set(io_stats.get("write_count", 0))
                disk_latency_gauge.labels(direction='read').set(io_stats.get("avg_read_latency_ms", 0))
                disk_latency_gauge.labels(direction='write').set(io_stats.get("avg_write_latency_ms", 0))
            
            # Disk temperature
            for device, temp in disk_metrics.get("temperature", {}).items():
                disk_temperature_gauge.labels(device=device).set(temp)
            
            # Network metrics
            if "total" in network_metrics:
                total = network_metrics["total"]
                network_bytes_gauge.labels(interface='all', direction='sent').set(total.get("bytes_sent", 0))
                network_bytes_gauge.labels(interface='all', direction='recv').set(total.get("bytes_recv", 0))
                network_packets_gauge.labels(interface='all', direction='sent').set(total.get("packets_sent", 0))
                network_packets_gauge.labels(interface='all', direction='recv').set(total.get("packets_recv", 0))
                network_errors_gauge.labels(interface='all', direction='in').set(total.get("errin", 0))
                network_errors_gauge.labels(interface='all', direction='out').set(total.get("errout", 0))
                network_drops_gauge.labels(interface='all', direction='in').set(total.get("dropin", 0))
                network_drops_gauge.labels(interface='all', direction='out').set(total.get("dropout", 0))
            
            # Per-interface network metrics
            for interface_name, interface_data in network_metrics.get("interfaces", {}).items():
                safe_name = interface_name.replace(".", "_").replace("-", "_")
                network_bytes_gauge.labels(interface=safe_name, direction='sent').set(interface_data.get("bytes_sent", 0))
                network_bytes_gauge.labels(interface=safe_name, direction='recv').set(interface_data.get("bytes_recv", 0))
                network_packets_gauge.labels(interface=safe_name, direction='sent').set(interface_data.get("packets_sent", 0))
                network_packets_gauge.labels(interface=safe_name, direction='recv').set(interface_data.get("packets_recv", 0))
                network_errors_gauge.labels(interface=safe_name, direction='in').set(interface_data.get("errin", 0))
                network_errors_gauge.labels(interface=safe_name, direction='out').set(interface_data.get("errout", 0))
                network_drops_gauge.labels(interface=safe_name, direction='in').set(interface_data.get("dropin", 0))
                network_drops_gauge.labels(interface=safe_name, direction='out').set(interface_data.get("dropout", 0))
            
            # Network connections
            if "connections" in network_metrics:
                connections = network_metrics["connections"]
                for status, count in connections.get("status_breakdown", {}).items():
                    safe_status = status.replace(" ", "_").lower()
                    network_connections_gauge.labels(status=safe_status).set(count)
            
            # Service health metrics
            core_services = ["database", "storage", "minio", "web_server"]
            for service_name in core_services:
                if service_name in service_health:
                    service_data = service_health[service_name]
                    health_value = 1 if service_data.get("healthy", False) else 0
                    service_health_gauge.labels(service=service_name).set(health_value)
                    
                    response_time = service_data.get("response_time_ms")
                    if response_time is not None:
                        service_response_time_gauge.labels(service=service_name).set(response_time)
            
            # External services
            if "external_services" in service_health:
                for service_name, service_data in service_health["external_services"].items():
                    health_value = 1 if service_data.get("healthy", False) else 0
                    service_health_gauge.labels(service=f"external_{service_name}").set(health_value)
                    
                    response_time = service_data.get("response_time_ms")
                    if response_time is not None:
                        service_response_time_gauge.labels(service=f"external_{service_name}").set(response_time)
            
            # Process metrics
            if process_info:
                process_memory_gauge.labels(type='rss').set(process_info.get("memory_mb", 0) * 1024**2)
                process_cpu_gauge.set(process_info.get("cpu_percent", 0))
                process_threads_gauge.set(process_info.get("num_threads", 0))
            
            # Update trend metrics
            try:
                trends = system_monitor.get_historical_trends(hours=1)
                for metric_name, trend_data in trends.get("trends", {}).items():
                    if isinstance(trend_data, dict) and "slope" in trend_data:
                        trend_gauge.labels(metric=metric_name).set(trend_data["slope"])
            except Exception as e:
                logger.debug(f"Could not update trend metrics: {e}")
            
            self.last_update = current_time
            logger.debug("Prometheus metrics updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating Prometheus metrics: {e}")
        
        return generate_latest(registry)
    
    def get_metrics(self) -> str:
        """Get current metrics in Prometheus format."""
        return self.update_metrics()


# Global exporter instance
prometheus_exporter = PrometheusExporter()