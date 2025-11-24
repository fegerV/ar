#!/usr/bin/env python3
"""
Comprehensive test script for Notification Center functionality.
Tests both backend API and database operations.
"""
import sys
import os
from pathlib import Path

# Add vertex-ar to path
sys.path.insert(0, str(Path(__file__).parent / "vertex-ar"))

from notifications import (
    get_db,
    create_notification,
    get_notifications,
    get_notification,
    update_notification,
    delete_notification,
    mark_all_as_read,
    get_user_unread_count,
    NotificationCreate,
    NotificationUpdate,
)


def print_test_header(test_name: str):
    """Print formatted test header"""
    print("\n" + "=" * 70)
    print(f"🧪 {test_name}")
    print("=" * 70)


def print_result(test_name: str, passed: bool, details: str = ""):
    """Print test result"""
    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"{status}: {test_name}")
    if details:
        print(f"   📝 {details}")


def test_create_notifications():
    """Test creating notifications of different types"""
    print_test_header("Test 1: Creating Notifications")
    
    db = next(get_db())
    try:
        # Test data for different notification types
        test_notifications = [
            {
                "title": "Тестовое информационное уведомление",
                "message": "Это информационное сообщение для проверки системы уведомлений",
                "notification_type": "info"
            },
            {
                "title": "Успешная операция",
                "message": "Бэкап успешно создан в 10:30:45",
                "notification_type": "success"
            },
            {
                "title": "Предупреждение о нагрузке",
                "message": "Использование CPU достигло 85%. Рекомендуется проверить активные процессы",
                "notification_type": "warning"
            },
            {
                "title": "Критическая ошибка",
                "message": "Не удалось подключиться к базе данных. Проверьте настройки соединения",
                "notification_type": "error"
            },
            {
                "title": "Персональное уведомление",
                "message": "У вас новый запрос от клиента ID: 12345",
                "user_id": "admin@vertex-ar.com",
                "notification_type": "info"
            },
        ]
        
        created_ids = []
        all_passed = True
        
        for i, notification_data in enumerate(test_notifications, 1):
            try:
                notification_create = NotificationCreate(**notification_data)
                notification = create_notification(db, notification_create)
                created_ids.append(notification.id)
                
                print_result(
                    f"Create notification #{i} ({notification_data['notification_type']})",
                    True,
                    f"ID: {notification.id}, Title: {notification.title}"
                )
            except Exception as e:
                print_result(
                    f"Create notification #{i}",
                    False,
                    f"Error: {str(e)}"
                )
                all_passed = False
        
        return all_passed, created_ids
    
    except Exception as e:
        print_result("Create notifications batch", False, f"Unexpected error: {str(e)}")
        return False, []
    finally:
        db.close()


def test_get_notifications():
    """Test retrieving notifications with filters"""
    print_test_header("Test 2: Retrieving Notifications")
    
    db = next(get_db())
    try:
        all_passed = True
        
        # Test 1: Get all notifications
        all_notifications = get_notifications(db, limit=100)
        print_result(
            "Get all notifications",
            len(all_notifications) > 0,
            f"Found {len(all_notifications)} notifications"
        )
        
        # Test 2: Get unread only
        unread_notifications = get_notifications(db, unread_only=True, limit=100)
        print_result(
            "Get unread notifications only",
            True,
            f"Found {len(unread_notifications)} unread notifications"
        )
        
        # Test 3: Get by user_id
        user_notifications = get_notifications(db, user_id="admin@vertex-ar.com", limit=100)
        print_result(
            "Get user-specific notifications",
            True,
            f"Found {len(user_notifications)} notifications for admin@vertex-ar.com"
        )
        
        # Test 4: Get with limit
        limited_notifications = get_notifications(db, limit=3)
        passed = len(limited_notifications) <= 3
        print_result(
            "Get notifications with limit=3",
            passed,
            f"Retrieved {len(limited_notifications)} notifications"
        )
        all_passed = all_passed and passed
        
        return all_passed
    
    except Exception as e:
        print_result("Get notifications", False, f"Error: {str(e)}")
        return False
    finally:
        db.close()


def test_notification_operations(notification_ids):
    """Test operations on specific notifications"""
    print_test_header("Test 3: Notification Operations")
    
    if not notification_ids:
        print_result("Notification operations", False, "No notification IDs provided")
        return False
    
    db = next(get_db())
    try:
        all_passed = True
        test_id = notification_ids[0]
        
        # Test 1: Get single notification
        notification = get_notification(db, test_id)
        passed = notification is not None
        print_result(
            f"Get notification by ID ({test_id})",
            passed,
            f"Title: {notification.title if notification else 'Not found'}"
        )
        all_passed = all_passed and passed
        
        # Test 2: Mark as read
        if notification:
            update_data = NotificationUpdate(is_read=True)
            updated = update_notification(db, test_id, update_data)
            passed = updated is not None and updated.is_read == True
            print_result(
                "Mark notification as read",
                passed,
                f"is_read: {updated.is_read if updated else 'Failed'}"
            )
            all_passed = all_passed and passed
        
        # Test 3: Mark as unread
        if notification:
            update_data = NotificationUpdate(is_read=False)
            updated = update_notification(db, test_id, update_data)
            passed = updated is not None and updated.is_read == False
            print_result(
                "Mark notification as unread",
                passed,
                f"is_read: {updated.is_read if updated else 'Failed'}"
            )
            all_passed = all_passed and passed
        
        return all_passed
    
    except Exception as e:
        print_result("Notification operations", False, f"Error: {str(e)}")
        return False
    finally:
        db.close()


def test_bulk_operations():
    """Test bulk operations on notifications"""
    print_test_header("Test 4: Bulk Operations")
    
    db = next(get_db())
    try:
        all_passed = True
        
        # Test 1: Get unread count before
        unread_before = get_notifications(db, unread_only=True, limit=500)
        count_before = len(unread_before)
        print_result(
            "Count unread notifications before mark all",
            True,
            f"{count_before} unread notifications"
        )
        
        # Test 2: Mark all as read
        mark_all_as_read(db)
        unread_after = get_notifications(db, unread_only=True, limit=500)
        count_after = len(unread_after)
        passed = count_after == 0
        print_result(
            "Mark all notifications as read",
            passed,
            f"Unread count: {count_before} → {count_after}"
        )
        all_passed = all_passed and passed
        
        # Test 3: Get user unread count
        user_unread = get_user_unread_count(db, "admin@vertex-ar.com")
        print_result(
            "Get user unread count",
            True,
            f"User has {user_unread} unread notifications"
        )
        
        return all_passed
    
    except Exception as e:
        print_result("Bulk operations", False, f"Error: {str(e)}")
        return False
    finally:
        db.close()


def test_delete_operations(notification_ids):
    """Test deletion of notifications"""
    print_test_header("Test 5: Delete Operations")
    
    if not notification_ids or len(notification_ids) < 2:
        print_result("Delete operations", False, "Not enough notification IDs")
        return False
    
    db = next(get_db())
    try:
        all_passed = True
        delete_id = notification_ids[-1]  # Delete last one
        
        # Test 1: Delete notification
        deleted = delete_notification(db, delete_id)
        passed = deleted is not None
        print_result(
            f"Delete notification (ID: {delete_id})",
            passed,
            f"Deleted: {deleted.title if deleted else 'Not found'}"
        )
        all_passed = all_passed and passed
        
        # Test 2: Verify deletion
        should_be_none = get_notification(db, delete_id)
        passed = should_be_none is None
        print_result(
            "Verify notification was deleted",
            passed,
            "Notification no longer exists" if passed else "Notification still exists"
        )
        all_passed = all_passed and passed
        
        return all_passed
    
    except Exception as e:
        print_result("Delete operations", False, f"Error: {str(e)}")
        return False
    finally:
        db.close()


def test_notification_types():
    """Test that all notification types are properly handled"""
    print_test_header("Test 6: Notification Type Validation")
    
    db = next(get_db())
    try:
        all_passed = True
        valid_types = ["info", "success", "warning", "error"]
        
        for ntype in valid_types:
            notification_data = NotificationCreate(
                title=f"Test {ntype.upper()}",
                message=f"Testing notification type: {ntype}",
                notification_type=ntype
            )
            notification = create_notification(db, notification_data)
            passed = notification.notification_type == ntype
            print_result(
                f"Create {ntype} notification",
                passed,
                f"Type: {notification.notification_type}"
            )
            all_passed = all_passed and passed
        
        return all_passed
    
    except Exception as e:
        print_result("Notification type validation", False, f"Error: {str(e)}")
        return False
    finally:
        db.close()


def test_ui_template():
    """Test notification center UI template"""
    print_test_header("Test 7: UI Template Validation")
    
    template_path = Path("vertex-ar/templates/admin_notifications.html")
    
    if not template_path.exists():
        print_result("UI template exists", False, "Template file not found")
        return False
    
    content = template_path.read_text()
    all_passed = True
    
    ui_checks = {
        "Has notification feed": "notificationFeed" in content,
        "Has filter controls": "notificationTypeFilter" in content,
        "Has search functionality": "notificationSearch" in content,
        "Has unread filter": "unreadOnlyFilter" in content,
        "Has time range filter": "timeRangeFilter" in content,
        "Has refresh button": "refreshNotificationsBtn" in content,
        "Has mark all read button": "markAllNotificationsBtn" in content,
        "Has notification stats": "totalNotifications" in content,
        "Has notification types": "notification-type-badge" in content,
        "Has dark mode support": 'data-theme="dark"' in content,
        "Has loading overlay": "loadingOverlay" in content,
        "Has toast notifications": "showToast" in content,
        "Has delete functionality": "deleteNotification" in content,
        "Has toggle read functionality": "toggleNotificationRead" in content,
        "Has responsive design": "@media" in content,
    }
    
    for check_name, result in ui_checks.items():
        print_result(check_name, result)
        all_passed = all_passed and result
    
    return all_passed


def test_api_endpoints():
    """Test API endpoint definitions"""
    print_test_header("Test 8: API Endpoint Validation")
    
    api_path = Path("vertex-ar/app/api/notifications.py")
    
    if not api_path.exists():
        print_result("API file exists", False, "API file not found")
        return False
    
    content = api_path.read_text()
    all_passed = True
    
    api_checks = {
        "Has list endpoint": "@router.get" in content and "list_notifications" in content,
        "Has create endpoint": "@router.post" in content and "create_notification_endpoint" in content,
        "Has get single endpoint": 'get("/{notification_id}"' in content,
        "Has update endpoint": "@router.put" in content and "update_notification_endpoint" in content,
        "Has delete endpoint": "@router.delete" in content and "delete_notification_endpoint" in content,
        "Has mark all read endpoint": "mark-all-read" in content,
        "Has admin authentication": "require_admin" in content,
        "Has proper response models": "NotificationResponse" in content,
        "Has error handling": "HTTPException" in content,
        "Has proper status codes": "status.HTTP_201_CREATED" in content,
    }
    
    for check_name, result in api_checks.items():
        print_result(check_name, result)
        all_passed = all_passed and result
    
    return all_passed


def cleanup_test_notifications():
    """Clean up test notifications (optional)"""
    print_test_header("Cleanup: Remove Test Notifications")
    
    db = next(get_db())
    try:
        # Get all test notifications
        notifications = get_notifications(db, limit=500)
        test_keywords = ["Тест", "Test", "тестовое"]
        
        deleted_count = 0
        for notification in notifications:
            title_lower = notification.title.lower()
            if any(keyword.lower() in title_lower for keyword in test_keywords):
                delete_notification(db, notification.id)
                deleted_count += 1
        
        print_result(
            "Cleanup test notifications",
            True,
            f"Removed {deleted_count} test notifications"
        )
        return True
    
    except Exception as e:
        print_result("Cleanup", False, f"Error: {str(e)}")
        return False
    finally:
        db.close()


def run_all_tests():
    """Run all notification center tests"""
    print("\n" + "🚀" * 35)
    print("   NOTIFICATION CENTER COMPREHENSIVE TEST SUITE")
    print("🚀" * 35)
    
    results = {}
    notification_ids = []
    
    # Run tests
    results["Create Notifications"], notification_ids = test_create_notifications()
    results["Get Notifications"] = test_get_notifications()
    results["Notification Operations"] = test_notification_operations(notification_ids)
    results["Bulk Operations"] = test_bulk_operations()
    results["Delete Operations"] = test_delete_operations(notification_ids)
    results["Notification Types"] = test_notification_types()
    results["UI Template"] = test_ui_template()
    results["API Endpoints"] = test_api_endpoints()
    
    # Summary
    print_test_header("TEST SUMMARY")
    
    passed_count = sum(1 for result in results.values() if result)
    total_count = len(results)
    
    for test_name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}")
    
    print("\n" + "=" * 70)
    success_rate = (passed_count / total_count) * 100 if total_count > 0 else 0
    print(f"📊 Results: {passed_count}/{total_count} tests passed ({success_rate:.1f}%)")
    
    if passed_count == total_count:
        print("🎉 ALL TESTS PASSED! Notification Center is working correctly!")
        print("\n🧹 Cleaning up test notifications...")
        cleanup_test_notifications()
        return True
    else:
        print("⚠️  Some tests failed. Please review the results above.")
        return False


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
