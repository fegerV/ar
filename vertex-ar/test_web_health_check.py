#!/usr/bin/env python3
"""
Test script to reproduce and verify the web_server health check issue.

This script demonstrates:
1. The issue when BASE_URL points to an external domain (with TLS/host mismatch)
2. The solution with fallback to localhost and detailed diagnostics
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.monitoring import system_monitor


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def main():
    print_section("Web Server Health Check - Issue Reproduction & Fix Verification")
    
    # Display current configuration
    print_section("Current Configuration")
    print(f"BASE_URL:              {settings.BASE_URL}")
    print(f"INTERNAL_HEALTH_URL:   {settings.INTERNAL_HEALTH_URL or '(not set - will use localhost fallback)'}")
    print(f"APP_HOST:              {settings.APP_HOST}")
    print(f"APP_PORT:              {settings.APP_PORT}")
    
    # Test the web server health check
    print_section("Testing Web Server Health Check")
    print("Calling system_monitor.get_service_health()...")
    
    try:
        service_health = system_monitor.get_service_health()
        web_server_status = service_health.get("web_server", {})
        
        print("\n" + "-" * 70)
        print("WEB SERVER STATUS REPORT")
        print("-" * 70)
        
        # Overall status
        print(f"\nHealth Status:  {'✅ HEALTHY' if web_server_status.get('healthy') else '❌ FAILED'}")
        print(f"Status:         {web_server_status.get('status', 'unknown').upper()}")
        
        if web_server_status.get('response_time_ms'):
            print(f"Response Time:  {web_server_status['response_time_ms']} ms")
        
        # Show which URL succeeded (if any)
        if web_server_status.get('successful_url'):
            print(f"\n✅ Successful Connection:")
            print(f"   Type: {web_server_status.get('successful_url_type', 'unknown')}")
            print(f"   URL:  {web_server_status['successful_url']}")
        
        # Show all attempts
        attempts = web_server_status.get('attempts', [])
        if attempts:
            print(f"\n📋 Connection Attempts ({len(attempts)} total):")
            for i, attempt in enumerate(attempts, 1):
                status_icon = "✅" if attempt['success'] else "❌"
                print(f"\n   {i}. {status_icon} {attempt['type'].upper()}")
                print(f"      URL:      {attempt['url']}")
                print(f"      Success:  {attempt['success']}")
                if attempt.get('status_code'):
                    print(f"      HTTP:     {attempt['status_code']}")
                if attempt.get('response_time_ms'):
                    print(f"      Time:     {attempt['response_time_ms']} ms")
                if attempt.get('error'):
                    print(f"      Error:    {attempt['error']}")
        
        # Show process diagnostics
        process_info = web_server_status.get('process_info', {})
        if process_info:
            print(f"\n🔧 Process Diagnostics:")
            print(f"   Running:      {process_info.get('running', False)}")
            if process_info.get('pid'):
                print(f"   PID:          {process_info['pid']}")
                print(f"   Name:         {process_info.get('name', 'unknown')}")
                if process_info.get('cpu_percent'):
                    print(f"   CPU:          {process_info['cpu_percent']}%")
                if process_info.get('memory_mb'):
                    print(f"   Memory:       {process_info['memory_mb']:.1f} MB")
            elif process_info.get('error'):
                print(f"   Error:        {process_info['error']}")
        
        # Show port diagnostics
        port_info = web_server_status.get('port_info', {})
        if port_info:
            print(f"\n🔌 Port Diagnostics:")
            print(f"   Port:         {port_info.get('port', settings.APP_PORT)}")
            print(f"   Status:       {port_info.get('status', 'unknown').upper()}")
            print(f"   Accepting:    {port_info.get('accepting_connections', False)}")
            if port_info.get('error'):
                print(f"   Error:        {port_info['error']}")
        
        # Status message
        if web_server_status.get('status_message'):
            print(f"\n💬 Status Message:")
            print(f"   {web_server_status['status_message']}")
        
        print("\n" + "-" * 70)
        
        # Interpretation
        print_section("Interpretation")
        
        if web_server_status.get('healthy'):
            print("✅ SUCCESS: Web server is healthy and responding to health checks.")
            if web_server_status.get('successful_url_type') == 'localhost':
                print("\n⚠️  NOTE: Health check succeeded via localhost fallback.")
                print("   This means BASE_URL is not directly accessible (TLS/host mismatch)")
                print("   but the service is running locally and healthy.")
        else:
            if web_server_status.get('status') == 'degraded':
                print("⚠️  DEGRADED: HTTP health check failed, but process/port diagnostics")
                print("   indicate the service is running. Possible causes:")
                print("   - Health endpoint is not responding")
                print("   - Rate limiting blocking requests")
                print("   - Application startup still in progress")
            else:
                print("❌ FAILED: Web server health check failed.")
                print("   The service appears to be down or unreachable.")
        
        # Recommendations
        print_section("Recommendations")
        
        if not web_server_status.get('healthy'):
            print("To fix the issue:")
            print("1. Check if the application is running")
            print("2. Verify the /health endpoint is accessible")
            print("3. Check firewall/network settings")
            print("4. Review application logs for errors")
        elif web_server_status.get('successful_url_type') == 'localhost':
            print("To optimize:")
            print("1. Set INTERNAL_HEALTH_URL in .env to skip external URL attempts:")
            print("   INTERNAL_HEALTH_URL=http://localhost:8000")
            print("2. Or ensure BASE_URL is accessible from the server itself")
        else:
            print("✅ No action needed - health check working optimally!")
        
        # Raw JSON output
        print_section("Raw JSON Output (for debugging)")
        print(json.dumps(web_server_status, indent=2, default=str))
        
    except Exception as e:
        print(f"\n❌ ERROR: Failed to get service health: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 70)
    print("Test completed successfully!")
    print("=" * 70 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
