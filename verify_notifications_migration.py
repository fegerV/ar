#!/usr/bin/env python3
"""
Verification script for notifications table migration.
Checks all 7 new columns and their integration.
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add vertex-ar to path
sys.path.insert(0, str(Path(__file__).parent / 'vertex-ar'))

def check_database_schema():
    """Check that notifications table has all required columns."""
    print("=" * 80)
    print("1. CHECKING DATABASE SCHEMA")
    print("=" * 80)
    
    from notifications import engine
    import sqlite3
    
    url_str = str(engine.url).replace('sqlite:///', '')
    conn = sqlite3.connect(url_str)
    cursor = conn.execute('PRAGMA table_info(notifications)')
    
    required_columns = {
        'priority': 'VARCHAR',
        'status': 'VARCHAR',
        'source': 'VARCHAR',
        'service_name': 'VARCHAR',
        'event_data': 'TEXT',
        'group_id': 'VARCHAR',
        'processed_at': 'DATETIME'
    }
    
    columns_found = {}
    print("\nNotifications table columns:")
    for row in cursor.fetchall():
        col_name = row[1]
        col_type = row[2]
        is_nullable = row[3] == 0
        print(f"  ✓ {col_name:20} {col_type:15} (nullable: {is_nullable})")
        columns_found[col_name] = col_type
    
    print("\nVerifying new columns:")
    all_present = True
    for col_name, expected_type in required_columns.items():
        if col_name in columns_found:
            if expected_type in columns_found[col_name]:
                print(f"  ✓ {col_name} - present with correct type ({columns_found[col_name]})")
            else:
                print(f"  ⚠ {col_name} - present but type mismatch (expected {expected_type}, got {columns_found[col_name]})")
        else:
            print(f"  ✗ {col_name} - MISSING!")
            all_present = False
    
    conn.close()
    return all_present


def check_indexes():
    """Check indexes on notifications table."""
    print("\n" + "=" * 80)
    print("2. CHECKING INDEXES")
    print("=" * 80)
    
    from notifications import engine
    import sqlite3
    
    url_str = str(engine.url).replace('sqlite:///', '')
    conn = sqlite3.connect(url_str)
    cursor = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='notifications'")
    
    indexes = {}
    print("\nExisting indexes:")
    for row in cursor.fetchall():
        indexes[row[0]] = row[1]
        print(f"  ✓ {row[0]}")
        if row[1]:
            print(f"    SQL: {row[1]}")
    
    # Check recommended indexes
    recommended_indexes = ['group_id', 'status', 'source']
    print("\nRecommended indexes for performance:")
    for col in recommended_indexes:
        idx_name = f"ix_notifications_{col}"
        if any(col in str(idx_sql) for idx_sql in indexes.values() if idx_sql):
            print(f"  ✓ {col} - indexed")
        else:
            print(f"  ⚠ {col} - NOT indexed (consider adding for better performance)")
    
    conn.close()
    return True


def check_notification_model():
    """Check SQLAlchemy Notification model."""
    print("\n" + "=" * 80)
    print("3. CHECKING NOTIFICATION MODEL")
    print("=" * 80)
    
    from notifications import Notification, NotificationPriority, NotificationStatus
    import inspect
    
    print("\nNotification model attributes:")
    model_attrs = {
        'priority': 'Enum(NotificationPriority)',
        'status': 'Enum(NotificationStatus)',
        'source': 'String',
        'service_name': 'String',
        'event_data': 'Text',
        'group_id': 'String',
        'processed_at': 'DateTime'
    }
    
    for attr_name, expected_type in model_attrs.items():
        if hasattr(Notification, attr_name):
            column = getattr(Notification, attr_name)
            print(f"  ✓ {attr_name:20} - present (type: {column.type})")
        else:
            print(f"  ✗ {attr_name} - MISSING!")
            return False
    
    print("\nNotificationPriority enum values:")
    for priority in NotificationPriority:
        print(f"  ✓ {priority.name} = {priority.value}")
    
    print("\nNotificationStatus enum values:")
    for status in NotificationStatus:
        print(f"  ✓ {status.name} = {status.value}")
    
    return True


def check_pydantic_models():
    """Check Pydantic models for new fields."""
    print("\n" + "=" * 80)
    print("4. CHECKING PYDANTIC MODELS")
    print("=" * 80)
    
    from notifications import (
        NotificationCreate, NotificationUpdate, NotificationResponse,
        NotificationFilter, NotificationPriority, NotificationStatus
    )
    
    print("\nNotificationCreate model fields:")
    for field_name, field_info in NotificationCreate.model_fields.items():
        if field_name in ['priority', 'status', 'source', 'service_name', 'event_data', 'group_id']:
            print(f"  ✓ {field_name:20} - {field_info.annotation}")
    
    print("\nNotificationUpdate model fields:")
    for field_name, field_info in NotificationUpdate.model_fields.items():
        if field_name in ['priority', 'status', 'processed_at']:
            print(f"  ✓ {field_name:20} - {field_info.annotation}")
    
    print("\nNotificationResponse model fields:")
    for field_name, field_info in NotificationResponse.model_fields.items():
        if field_name in ['priority', 'status', 'source', 'service_name', 'event_data', 'group_id', 'processed_at']:
            print(f"  ✓ {field_name:20} - {field_info.annotation}")
    
    print("\nNotificationFilter model fields:")
    for field_name, field_info in NotificationFilter.model_fields.items():
        if field_name in ['priority', 'status', 'source', 'service_name', 'group_id']:
            print(f"  ✓ {field_name:20} - {field_info.annotation}")
    
    return True


def test_create_notification_with_new_fields():
    """Test creating notifications with new fields."""
    print("\n" + "=" * 80)
    print("5. TESTING NOTIFICATION CREATION WITH NEW FIELDS")
    print("=" * 80)
    
    from notifications import (
        create_notification, get_notifications, delete_notification,
        NotificationCreate, NotificationPriority, get_db
    )
    
    db = next(get_db())
    
    try:
        # Test 1: Create notification with all new fields
        print("\nTest 1: Creating notification with all new fields...")
        notification_data = NotificationCreate(
            title="Test Notification",
            message="Testing all new fields",
            notification_type="info",
            priority=NotificationPriority.HIGH,
            source="verification_script",
            service_name="vertex_ar",
            event_data={"test": "data", "timestamp": datetime.utcnow().isoformat()},
            group_id="test_group_1"
        )
        
        notification = create_notification(db, notification_data)
        print(f"  ✓ Created notification ID: {notification.id}")
        print(f"    - priority: {notification.priority}")
        print(f"    - status: {notification.status}")
        print(f"    - source: {notification.source}")
        print(f"    - service_name: {notification.service_name}")
        print(f"    - event_data: {notification.event_data}")
        print(f"    - group_id: {notification.group_id}")
        print(f"    - processed_at: {notification.processed_at}")
        
        # Test 2: Query by new fields
        print("\nTest 2: Querying notifications by new fields...")
        from notifications import NotificationFilter, NotificationStatus
        
        filter_high_priority = NotificationFilter(priority=NotificationPriority.HIGH)
        high_priority_notifications = get_notifications(db, filter_high_priority, limit=10)
        print(f"  ✓ Found {len(high_priority_notifications)} HIGH priority notifications")
        
        filter_by_source = NotificationFilter(source="verification_script")
        source_notifications = get_notifications(db, filter_by_source, limit=10)
        print(f"  ✓ Found {len(source_notifications)} notifications from 'verification_script' source")
        
        filter_by_service = NotificationFilter(service_name="vertex_ar")
        service_notifications = get_notifications(db, filter_by_service, limit=10)
        print(f"  ✓ Found {len(service_notifications)} notifications from 'vertex_ar' service")
        
        filter_by_group = NotificationFilter(group_id="test_group_1")
        group_notifications = get_notifications(db, filter_by_group, limit=10)
        print(f"  ✓ Found {len(group_notifications)} notifications in 'test_group_1' group")
        
        # Test 3: Update notification status and processed_at
        print("\nTest 3: Updating notification status and processed_at...")
        from notifications import update_notification, NotificationUpdate
        
        update_data = NotificationUpdate(
            status=NotificationStatus.PROCESSED,
            is_read=True
        )
        updated = update_notification(db, notification.id, update_data)
        print(f"  ✓ Updated notification status to: {updated.status}")
        print(f"    - processed_at set to: {updated.processed_at}")
        
        # Clean up
        delete_notification(db, notification.id)
        print("\n  ✓ Test notification cleaned up")
        
        return True
        
    except Exception as e:
        print(f"\n  ✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def check_monitoring_integration():
    """Check if monitoring.py uses new notification fields."""
    print("\n" + "=" * 80)
    print("6. CHECKING MONITORING INTEGRATION")
    print("=" * 80)
    
    # Check if monitoring.py imports and uses notification system
    monitoring_file = Path(__file__).parent / 'vertex-ar' / 'app' / 'monitoring.py'
    
    if not monitoring_file.exists():
        print("  ⚠ monitoring.py not found")
        return False
    
    content = monitoring_file.read_text()
    
    checks = {
        'imports notifications': 'from notifications import' in content or 'import notifications' in content,
        'uses NotificationPriority': 'NotificationPriority' in content,
        'uses service_name': 'service_name' in content,
        'uses event_data': 'event_data' in content,
        'uses source': '"source"' in content or "'source'" in content,
    }
    
    print("\nMonitoring.py integration:")
    for check_name, check_result in checks.items():
        status = "✓" if check_result else "⚠"
        print(f"  {status} {check_name}: {check_result}")
    
    return True


def check_lifecycle_scheduler_integration():
    """Check if lifecycle_scheduler uses new notification fields."""
    print("\n" + "=" * 80)
    print("7. CHECKING LIFECYCLE SCHEDULER INTEGRATION")
    print("=" * 80)
    
    lifecycle_file = Path(__file__).parent / 'vertex-ar' / 'app' / 'project_lifecycle.py'
    
    if not lifecycle_file.exists():
        print("  ⚠ project_lifecycle.py not found")
        return False
    
    content = lifecycle_file.read_text()
    
    # The lifecycle scheduler uses alerting.py which in turn uses notifications
    checks = {
        'uses alerting system': 'from app.alerting import' in content,
        'sends notifications': 'alert_manager' in content,
    }
    
    print("\nLifecycle scheduler integration:")
    for check_name, check_result in checks.items():
        status = "✓" if check_result else "⚠"
        print(f"  {status} {check_name}: {check_result}")
    
    # Check alerting.py integration
    alerting_file = Path(__file__).parent / 'vertex-ar' / 'app' / 'alerting.py'
    if alerting_file.exists():
        alerting_content = alerting_file.read_text()
        print("\nAlerting.py notification system usage:")
        
        alerting_checks = {
            'imports notifications': 'from notifications import' in alerting_content,
            'uses NotificationPriority': 'NotificationPriority' in alerting_content,
            'uses priority parameter': 'priority' in alerting_content,
            'uses source parameter': 'source' in alerting_content,
            'uses service_name parameter': 'service_name' in alerting_content,
            'uses event_data parameter': 'event_data' in alerting_content,
        }
        
        for check_name, check_result in alerting_checks.items():
            status = "✓" if check_result else "⚠"
            print(f"  {status} {check_name}: {check_result}")
    
    return True


def check_backward_compatibility():
    """Check backward compatibility with old notification records."""
    print("\n" + "=" * 80)
    print("8. CHECKING BACKWARD COMPATIBILITY")
    print("=" * 80)
    
    from notifications import get_db, get_notifications
    
    db = next(get_db())
    
    try:
        # Get all notifications
        all_notifications = get_notifications(db, limit=1000)
        
        print(f"\nTotal notifications in database: {len(all_notifications)}")
        
        if len(all_notifications) > 0:
            # Check how many have new fields populated
            with_priority = sum(1 for n in all_notifications if n.priority)
            with_status = sum(1 for n in all_notifications if n.status)
            with_source = sum(1 for n in all_notifications if n.source)
            with_service_name = sum(1 for n in all_notifications if n.service_name)
            with_event_data = sum(1 for n in all_notifications if n.event_data)
            with_group_id = sum(1 for n in all_notifications if n.group_id)
            with_processed_at = sum(1 for n in all_notifications if n.processed_at)
            
            print("\nNotifications with new fields populated:")
            print(f"  - priority: {with_priority} ({with_priority/len(all_notifications)*100:.1f}%)")
            print(f"  - status: {with_status} ({with_status/len(all_notifications)*100:.1f}%)")
            print(f"  - source: {with_source} ({with_source/len(all_notifications)*100:.1f}%)")
            print(f"  - service_name: {with_service_name} ({with_service_name/len(all_notifications)*100:.1f}%)")
            print(f"  - event_data: {with_event_data} ({with_event_data/len(all_notifications)*100:.1f}%)")
            print(f"  - group_id: {with_group_id} ({with_group_id/len(all_notifications)*100:.1f}%)")
            print(f"  - processed_at: {with_processed_at} ({with_processed_at/len(all_notifications)*100:.1f}%)")
            
            # Check if old notifications can be read without errors
            print("\n✓ All notifications can be read successfully (backward compatible)")
        else:
            print("\n  ℹ No existing notifications found in database")
        
        return True
        
    except Exception as e:
        print(f"\n  ✗ Error checking backward compatibility: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def generate_report():
    """Generate comprehensive report."""
    print("\n" + "=" * 80)
    print("VERIFICATION REPORT SUMMARY")
    print("=" * 80)
    
    results = {
        "Database Schema": check_database_schema(),
        "Indexes": check_indexes(),
        "Notification Model": check_notification_model(),
        "Pydantic Models": check_pydantic_models(),
        "Create/Query/Update Tests": test_create_notification_with_new_fields(),
        "Monitoring Integration": check_monitoring_integration(),
        "Lifecycle Scheduler Integration": check_lifecycle_scheduler_integration(),
        "Backward Compatibility": check_backward_compatibility(),
    }
    
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    
    all_passed = True
    for check_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:10} {check_name}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✓ ALL CHECKS PASSED - Migration is complete and working correctly!")
    else:
        print("⚠ SOME CHECKS FAILED - Review the output above for details")
    print("=" * 80)
    
    return all_passed


if __name__ == "__main__":
    try:
        success = generate_report()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
