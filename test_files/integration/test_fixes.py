#!/usr/bin/env python3
"""
Test script to verify that the notification system fixes are working.
"""
import sys
import os
sys.path.insert(0, '.')

def test_notification_functionality():
    """Test that all notification functionality works correctly."""
    print("🧪 Testing Vertex AR notification system fixes...")
    
    try:
        # Test 1: Import modules
        print("\n1. Testing imports...")
        from notifications import send_notification, NotificationPriority, get_db
        from notification_sync import notification_sync_manager
        from app.alerting import alert_manager
        import asyncio
        print("   ✓ All imports successful")
        
        # Test 2: Database connection and table structure
        print("\n2. Testing database structure...")
        from sqlalchemy import inspect
        db = next(get_db())
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        
        if 'notifications' in tables:
            columns = [col['name'] for col in inspector.get_columns('notifications')]
            if 'priority' in columns:
                print("   ✓ Notifications table exists with priority column")
            else:
                print("   ✗ Priority column missing from notifications table")
                return False
        else:
            print("   ✗ Notifications table missing")
            return False
        db.close()
        
        # Test 3: send_notification with priority parameter
        print("\n3. Testing send_notification with priority...")
        notification = send_notification(
            title='Test Notification',
            message='Test message with priority parameter',
            priority=NotificationPriority.HIGH,
            source='test_script',
            service_name='verification'
        )
        print("   ✓ send_notification works with priority parameter")
        
        # Test 4: NotificationSyncManager cleanup statistics
        print("\n4. Testing NotificationSyncManager...")
        db = next(get_db())
        cleanup_stats = asyncio.run(notification_sync_manager._get_cleanup_statistics(db))
        if 'expired_notifications' in cleanup_stats:
            print("   ✓ NotificationSyncManager._get_cleanup_statistics works")
        else:
            print("   ✗ NotificationSyncManager._get_cleanup_statistics failed")
            return False
        db.close()
        
        # Test 5: Application creation
        print("\n5. Testing application creation...")
        from app.main import create_app
        app = create_app()
        print("   ✓ FastAPI application creates successfully")
        
        print("\n🎉 All tests passed! The notification system is working correctly.")
        print("\n📋 Summary of fixes applied:")
        print("   • Updated send_notification() to accept priority and other parameters")
        print("   • Fixed NotificationSyncManager._get_cleanup_statistics() method signature")
        print("   • Updated Pydantic Config to use from_attributes instead of orm_mode")
        print("   • Enhanced cleanup statistics with meaningful data")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_notification_functionality()
    sys.exit(0 if success else 1)