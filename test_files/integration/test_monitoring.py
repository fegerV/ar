#!/usr/bin/env python3
"""
Test script for Vertex AR monitoring and alerting system.
"""
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/home/engine/project/vertex-ar')

from app.config import settings
from app.alerting import alert_manager
from app.monitoring import system_monitor
from app.weekly_reports import weekly_report_generator


async def test_monitoring_system():
    """Test the complete monitoring and alerting system."""
    print("🧪 Testing Vertex AR Monitoring System")
    print("=" * 50)
    
    # Test 1: Configuration
    print("\n1. Testing Configuration...")
    print(f"   Alerting enabled: {settings.ALERTING_ENABLED}")
    print(f"   CPU threshold: {settings.CPU_THRESHOLD}%")
    print(f"   Memory threshold: {settings.MEMORY_THRESHOLD}%")
    print(f"   Disk threshold: {settings.DISK_THRESHOLD}%")
    print(f"   Health check interval: {settings.HEALTH_CHECK_INTERVAL}s")
    print(f"   Telegram configured: {bool(settings.TELEGRAM_BOT_TOKEN)}")
    print(f"   Email configured: {bool(settings.SMTP_USERNAME and settings.ADMIN_EMAILS)}")
    
    # Test 2: System Metrics
    print("\n2. Testing System Metrics...")
    try:
        cpu_usage = system_monitor.get_cpu_usage()
        print(f"   CPU usage: {cpu_usage:.1f}%")
        
        memory_info = system_monitor.get_memory_usage()
        print(f"   Memory usage: {memory_info['percent']:.1f}% ({memory_info['used_gb']:.1f}GB/{memory_info['total_gb']:.1f}GB)")
        
        disk_info = system_monitor.get_disk_usage()
        print(f"   Disk usage: {disk_info['percent']:.1f}% ({disk_info['used_gb']:.1f}GB/{disk_info['total_gb']:.1f}GB)")
        
        service_health = system_monitor.get_service_health()
        print(f"   Service health: {service_health}")
        
    except Exception as e:
        print(f"   ❌ Error getting metrics: {e}")
    
    # Test 3: Health Check
    print("\n3. Testing Health Check...")
    try:
        health_result = await system_monitor.check_system_health()
        print(f"   Health status: {health_result['status']}")
        if health_result.get('alerts'):
            print(f"   Active alerts: {len(health_result['alerts'])}")
        else:
            print("   ✅ No active alerts")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
    
    # Test 4: Alert Channels
    print("\n4. Testing Alert Channels...")
    try:
        test_results = await alert_manager.test_alert_system()
        for channel, success in test_results.items():
            status = "✅" if success else "❌"
            print(f"   {status} {channel}: {'Success' if success else 'Failed'}")
    except Exception as e:
        print(f"   ❌ Alert test failed: {e}")
    
    # Test 5: Weekly Report Generation
    print("\n5. Testing Weekly Report Generation...")
    try:
        report_text = weekly_report_generator.generate_report_text()
        print(f"   ✅ Report generated ({len(report_text)} characters)")
        print("   Report preview:")
        print("   " + "\n   ".join(report_text.split('\n')[:10]))
        print("   ...")
    except Exception as e:
        print(f"   ❌ Report generation failed: {e}")
    
    # Test 6: Database Stats
    print("\n6. Testing Database Statistics...")
    try:
        db_stats = weekly_report_generator.get_database_stats()
        print(f"   Companies: {db_stats.get('companies_count', 0)}")
        print(f"   Clients: {db_stats.get('clients_count', 0)}")
        print(f"   Portraits: {db_stats.get('portraits_count', 0)}")
        print(f"   Videos: {db_stats.get('videos_count', 0)}")
        print(f"   Orders: {db_stats.get('orders_count', 0)}")
    except Exception as e:
        print(f"   ❌ Database stats failed: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Monitoring system test completed!")
    print("\nNext steps:")
    print("1. Configure SMTP/Telegram settings in .env")
    print("2. Set ALERTING_ENABLED=true")
    print("3. Restart the application")
    print("4. Check admin dashboard monitoring section")


if __name__ == "__main__":
    asyncio.run(test_monitoring_system())
