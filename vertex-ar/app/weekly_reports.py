"""
Weekly reports system for Vertex AR - generates and sends comprehensive server reports.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

from app.config import settings
from app.alerting import alert_manager
from app.monitoring import system_monitor
from logging_setup import get_logger

logger = get_logger(__name__)


class WeeklyReportGenerator:
    """Generates and sends weekly reports about server performance and usage."""
    
    def __init__(self):
        self.enabled = settings.ALERTING_ENABLED
        self.report_day = settings.WEEKLY_REPORT_DAY.lower()
        self.report_time = settings.WEEKLY_REPORT_TIME
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics for the report."""
        try:
            from app.database import Database
            
            db = Database(settings.DB_PATH)
            stats = {}
            
            # Get company count
            stats["companies_count"] = len(db.list_companies())
            
            # Get client count
            stats["clients_count"] = len(db.list_clients())
            
            # Get portrait count
            stats["portraits_count"] = db.count_portraits()
            
            # Get video count
            stats["videos_count"] = db.count_videos()
            
            # Get order count
            stats["orders_count"] = 0  # Orders not implemented in current schema
            
            # Get backup count
            try:
                from app.backup_manager import BackupManager
                backup_manager = BackupManager(settings.STORAGE_ROOT)
                stats["backups_count"] = len(backup_manager.list_backups())
            except Exception:
                stats["backups_count"] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for the past week."""
        try:
            from app.database import Database
            
            db = Database(settings.DB_PATH)
            stats = {}
            
            # Get portraits created in the last week
            one_week_ago = datetime.utcnow() - timedelta(days=7)
            all_portraits = db.list_portraits()
            
            new_portraits = [
                p for p in all_portraits 
                if datetime.fromisoformat(p["created_at"]) >= one_week_ago
            ]
            stats["new_portraits_this_week"] = len(new_portraits)
            
            # Calculate total views
            total_views = sum(p.get("view_count", 0) for p in all_portraits)
            stats["total_views"] = total_views
            
            # Get top viewed portraits
            sorted_portraits = sorted(all_portraits, key=lambda x: x.get("view_count", 0), reverse=True)
            stats["top_portraits"] = [
                {
                    "id": p["id"],
                    "client_name": p.get("client_name", "Unknown"),
                    "views": p.get("view_count", 0)
                }
                for p in sorted_portraits[:5]
            ]
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return {}
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics."""
        try:
            stats = {}
            
            # CPU and Memory
            stats["cpu_usage"] = system_monitor.get_cpu_usage()
            stats["memory"] = system_monitor.get_memory_usage()
            stats["disk"] = system_monitor.get_disk_usage()
            
            # Service health
            stats["service_health"] = system_monitor.get_service_health()
            
            # Process info
            stats["process"] = system_monitor.get_process_info()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {}
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alerts from the past week."""
        try:
            recent_alerts = system_monitor.get_recent_alerts(hours=24 * 7)
            
            summary = {
                "total_alerts": len(recent_alerts),
                "unread_alerts": len([a for a in recent_alerts if not a["is_read"]]),
                "alerts_by_type": {},
                "alerts_by_severity": {"error": 0, "warning": 0, "info": 0}
            }
            
            for alert in recent_alerts:
                # Count by type (from title)
                alert_type = "unknown"
                if "cpu" in alert["title"].lower():
                    alert_type = "cpu"
                elif "memory" in alert["title"].lower():
                    alert_type = "memory"
                elif "disk" in alert["title"].lower():
                    alert_type = "disk"
                elif "service" in alert["title"].lower():
                    alert_type = "service"
                
                summary["alerts_by_type"][alert_type] = summary["alerts_by_type"].get(alert_type, 0) + 1
                
                # Count by severity
                severity = alert["type"]
                if severity in summary["alerts_by_severity"]:
                    summary["alerts_by_severity"][severity] += 1
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting alert summary: {e}")
            return {}
    
    def generate_report_text(self) -> str:
        """Generate the weekly report text."""
        now = datetime.utcnow()
        report_date = now.strftime("%Y-%m-%d")
        week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        
        # Collect all statistics
        db_stats = self.get_database_stats()
        usage_stats = self.get_usage_stats()
        system_stats = self.get_system_stats()
        alert_summary = self.get_alert_summary()
        
        report = f"""
📊 VERTEX AR WEEKLY REPORT
{'='*50}

📅 Period: {week_start} to {report_date}
🕐 Generated: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC
🌐 Server: {settings.BASE_URL}

📈 DATABASE STATISTICS
{'-'*30}
• Companies: {db_stats.get('companies_count', 0)}
• Clients: {db_stats.get('clients_count', 0)}
• Portraits: {db_stats.get('portraits_count', 0)}
• Videos: {db_stats.get('videos_count', 0)}
• Orders: {db_stats.get('orders_count', 0)}
• Backups: {db_stats.get('backups_count', 0)}

🎯 USAGE STATISTICS
{'-'*30}
• New portraits this week: {usage_stats.get('new_portraits_this_week', 0)}
• Total portrait views: {usage_stats.get('total_views', 0)}

Top Portraits (by views):
"""
        
        for i, portrait in enumerate(usage_stats.get("top_portraits", []), 1):
            report += f"  {i}. {portrait['client_name']}: {portrait['views']} views\n"
        
        report += f"""
💻 SYSTEM PERFORMANCE
{'-'*30}
• CPU Usage: {system_stats.get('cpu_usage', 0):.1f}%
• Memory Usage: {system_stats.get('memory', {}).get('percent', 0):.1f}% 
  ({system_stats.get('memory', {}).get('used_gb', 0):.1f}GB / {system_stats.get('memory', {}).get('total_gb', 0):.1f}GB)
• Disk Usage: {system_stats.get('disk', {}).get('percent', 0):.1f}%
  ({system_stats.get('disk', {}).get('used_gb', 0):.1f}GB / {system_stats.get('disk', {}).get('total_gb', 0):.1f}GB)

Service Health:
"""
        
        for service, is_healthy in system_stats.get('service_health', {}).items():
            status = "✅ OK" if is_healthy else "❌ FAILED"
            report += f"  • {service.title()}: {status}\n"
        
        report += f"""
🚨 ALERT SUMMARY (Last 7 Days)
{'-'*30}
• Total Alerts: {alert_summary.get('total_alerts', 0)}
• Unread Alerts: {alert_summary.get('unread_alerts', 0)}

By Type:
"""
        
        for alert_type, count in alert_summary.get('alerts_by_type', {}).items():
            report += f"  • {alert_type.title()}: {count}\n"
        
        report += "\nBy Severity:\n"
        for severity, count in alert_summary.get('alerts_by_severity', {}).items():
            if count > 0:
                emoji = {"error": "🔴", "warning": "🟡", "info": "🟢"}.get(severity, "⚪")
                report += f"  • {emoji} {severity.title()}: {count}\n"
        
        report += f"""

📋 RECOMMENDATIONS
{'-'*30}
"""
        
        # Add recommendations based on stats
        if system_stats.get('cpu_usage', 0) > 70:
            report += "• Consider optimizing CPU-intensive tasks or scaling resources\n"
        
        if system_stats.get('memory', {}).get('percent', 0) > 80:
            report += "• Memory usage is high, consider adding more RAM or optimizing memory usage\n"
        
        if system_stats.get('disk', {}).get('percent', 0) > 85:
            report += "• Disk space is running low, consider cleanup or storage expansion\n"
        
        if alert_summary.get('total_alerts', 0) > 10:
            report += "• High number of alerts detected, review system stability\n"
        
        if usage_stats.get('new_portraits_this_week', 0) == 0:
            report += "• No new portraits created this week, consider marketing efforts\n"
        
        report += """
---
This is an automated weekly report from Vertex AR system.
For questions or support, please contact your system administrator.
        """
        
        return report.strip()
    
    async def send_weekly_report(self) -> bool:
        """Generate and send the weekly report."""
        if not self.enabled:
            logger.debug("Weekly reports disabled")
            return False
        
        try:
            report_text = self.generate_report_text()
            subject = f"Vertex AR Weekly Report - {datetime.utcnow().strftime('%Y-%m-%d')}"
            
            success = True
            
            # Send via Telegram
            if settings.TELEGRAM_BOT_TOKEN:
                # Split long messages for Telegram
                messages = [report_text[i:i+4000] for i in range(0, len(report_text), 4000)]
                for i, message in enumerate(messages):
                    prefix = f"📊 **WEEKLY REPORT ({i+1}/{len(messages)})**\n\n" if len(messages) > 1 else "📊 **WEEKLY REPORT**\n\n"
                    telegram_success = await alert_manager.send_telegram_alert(prefix + message)
                    success = success and telegram_success
            
            # Send via Email
            if settings.SMTP_USERNAME and settings.ADMIN_EMAILS:
                email_success = await alert_manager.send_email_alert(subject, report_text)
                success = success and email_success
            
            if success:
                logger.info("Weekly report sent successfully")
            else:
                logger.warning("Some weekly report delivery channels failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending weekly report: {e}")
            return False
    
    def should_send_report_now(self) -> bool:
        """Check if it's time to send the weekly report."""
        now = datetime.utcnow()
        
        # Check if it's the right day
        if now.strftime('%A').lower() != self.report_day:
            return False
        
        # Parse the report time
        try:
            hour, minute = map(int, self.report_time.split(':'))
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Check if we're within 1 hour of the target time
            time_diff = abs((now - target_time).total_seconds())
            return time_diff < 3600  # Within 1 hour
            
        except ValueError:
            logger.error(f"Invalid WEEKLY_REPORT_TIME format: {self.report_time}")
            return False
    
    async def start_weekly_report_scheduler(self):
        """Start the background task for scheduling weekly reports."""
        if not self.enabled:
            logger.info("Weekly reports disabled")
            return
        
        logger.info(f"Starting weekly report scheduler - {self.report_day} at {self.report_time}")
        
        while True:
            try:
                if self.should_send_report_now():
                    await self.send_weekly_report()
                    # Sleep for 2 hours to avoid sending multiple times
                    await asyncio.sleep(7200)
                else:
                    # Check every hour
                    await asyncio.sleep(3600)
                    
            except Exception as e:
                logger.error(f"Error in weekly report scheduler: {e}")
                await asyncio.sleep(3600)


# Global report generator instance
weekly_report_generator = WeeklyReportGenerator()
