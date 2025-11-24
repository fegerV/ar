#!/usr/bin/env python3
"""
Integration test for notification center web interface.
Tests API routes and ensures proper integration with FastAPI app.
"""
import sys
from pathlib import Path

# Add vertex-ar to path
sys.path.insert(0, str(Path(__file__).parent / "vertex-ar"))

from fastapi.testclient import TestClient
from app.main import app
from notifications import (
    get_db,
    create_notification,
    NotificationCreate,
)


def print_header(text: str):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"🧪 {text}")
    print("=" * 70)


def print_result(name: str, passed: bool, details: str = ""):
    """Print test result"""
    status = "✅" if passed else "❌"
    print(f"{status} {name}")
    if details:
        print(f"   📝 {details}")


def setup_test_data():
    """Create test notifications for integration testing"""
    db = next(get_db())
    try:
        notifications = [
            NotificationCreate(
                title="Integration Test Info",
                message="Test info notification for integration tests",
                notification_type="info"
            ),
            NotificationCreate(
                title="Integration Test Success",
                message="Test success notification",
                notification_type="success"
            ),
            NotificationCreate(
                title="Integration Test Warning",
                message="Test warning notification",
                notification_type="warning"
            ),
        ]
        
        created_ids = []
        for notification_data in notifications:
            notification = create_notification(db, notification_data)
            created_ids.append(notification.id)
        
        return created_ids
    finally:
        db.close()


def test_api_routes():
    """Test notification API routes through FastAPI"""
    print_header("API Routes Integration Test")
    
    client = TestClient(app)
    all_passed = True
    
    # Setup test data
    print("📋 Setting up test data...")
    notification_ids = setup_test_data()
    print(f"   Created {len(notification_ids)} test notifications")
    
    # Test 1: List notifications endpoint
    try:
        # Note: These endpoints require admin authentication
        # We'll test without auth to verify routes exist and return proper errors
        response = client.get("/notifications")
        # Should return 401 or redirect without auth
        passed = response.status_code in [401, 403, 307]
        print_result(
            "GET /notifications (requires auth)",
            passed,
            f"Status: {response.status_code} (auth required as expected)"
        )
        all_passed = all_passed and passed
    except Exception as e:
        print_result("GET /notifications", False, f"Error: {str(e)}")
        all_passed = False
    
    # Test 2: Create notification endpoint
    try:
        response = client.post(
            "/notifications",
            json={
                "title": "API Test",
                "message": "Test message",
                "notification_type": "info"
            }
        )
        passed = response.status_code in [401, 403, 307]
        print_result(
            "POST /notifications (requires auth)",
            passed,
            f"Status: {response.status_code} (auth required as expected)"
        )
        all_passed = all_passed and passed
    except Exception as e:
        print_result("POST /notifications", False, f"Error: {str(e)}")
        all_passed = False
    
    # Test 3: Get single notification endpoint
    try:
        response = client.get(f"/notifications/{notification_ids[0]}")
        passed = response.status_code in [401, 403, 307]
        print_result(
            "GET /notifications/{id} (requires auth)",
            passed,
            f"Status: {response.status_code} (auth required as expected)"
        )
        all_passed = all_passed and passed
    except Exception as e:
        print_result("GET /notifications/{id}", False, f"Error: {str(e)}")
        all_passed = False
    
    # Test 4: Update notification endpoint
    try:
        response = client.put(
            f"/notifications/{notification_ids[0]}",
            json={"is_read": True}
        )
        passed = response.status_code in [401, 403, 307]
        print_result(
            "PUT /notifications/{id} (requires auth)",
            passed,
            f"Status: {response.status_code} (auth required as expected)"
        )
        all_passed = all_passed and passed
    except Exception as e:
        print_result("PUT /notifications/{id}", False, f"Error: {str(e)}")
        all_passed = False
    
    # Test 5: Delete notification endpoint
    try:
        response = client.delete(f"/notifications/{notification_ids[0]}")
        passed = response.status_code in [401, 403, 307]
        print_result(
            "DELETE /notifications/{id} (requires auth)",
            passed,
            f"Status: {response.status_code} (auth required as expected)"
        )
        all_passed = all_passed and passed
    except Exception as e:
        print_result("DELETE /notifications/{id}", False, f"Error: {str(e)}")
        all_passed = False
    
    # Test 6: Mark all as read endpoint
    try:
        response = client.put("/notifications/mark-all-read")
        passed = response.status_code in [401, 403, 307]
        print_result(
            "PUT /notifications/mark-all-read (requires auth)",
            passed,
            f"Status: {response.status_code} (auth required as expected)"
        )
        all_passed = all_passed and passed
    except Exception as e:
        print_result("PUT /notifications/mark-all-read", False, f"Error: {str(e)}")
        all_passed = False
    
    return all_passed


def test_admin_page_route():
    """Test admin notifications page route"""
    print_header("Admin Page Route Test")
    
    client = TestClient(app)
    all_passed = True
    
    # Test admin notifications page
    try:
        response = client.get("/admin/notifications", follow_redirects=False)
        # Without auth, should redirect (302/307) or require auth (401/403)
        passed = response.status_code in [200, 302, 307, 401, 403]
        print_result(
            "GET /admin/notifications (route exists)",
            passed,
            f"Status: {response.status_code} (redirects to auth as expected)"
        )
        all_passed = all_passed and passed
        
        # Check that template file exists and has correct content
        from pathlib import Path
        template_path = Path("vertex-ar/templates/admin_notifications.html")
        template_exists = template_path.exists()
        print_result(
            "Notification center template exists",
            template_exists,
            f"Path: {template_path}"
        )
        all_passed = all_passed and template_exists
        
        if template_exists:
            content = template_path.read_text()
            checks = {
                "Template has notification center title": "Центр уведомлений" in content,
                "Template has notification feed": "notificationFeed" in content,
                "Template has filters": "notificationTypeFilter" in content,
                "Template has stats": "totalNotifications" in content,
                "Template has load function": "loadNotificationCenter" in content,
            }
            
            for check_name, result in checks.items():
                print_result(check_name, result)
                all_passed = all_passed and result
    
    except Exception as e:
        print_result("Admin notifications page", False, f"Error: {str(e)}")
        all_passed = False
    
    return all_passed


def test_notification_router_registration():
    """Test that notification router is properly registered"""
    print_header("Router Registration Test")
    
    all_passed = True
    
    # Check if notifications router is included
    router_found = False
    for route in app.routes:
        if hasattr(route, 'path') and '/notifications' in route.path:
            router_found = True
            print_result(
                f"Route registered: {route.path}",
                True,
                f"Methods: {getattr(route, 'methods', 'N/A')}"
            )
    
    print_result(
        "Notification router registered",
        router_found,
        "Found notification routes in app"
    )
    all_passed = all_passed and router_found
    
    return all_passed


def cleanup_test_data():
    """Clean up test notifications"""
    print_header("Cleanup Integration Test Data")
    
    from notifications import get_notifications, delete_notification
    
    db = next(get_db())
    try:
        notifications = get_notifications(db, limit=500)
        deleted = 0
        
        for notification in notifications:
            if "Integration Test" in notification.title:
                delete_notification(db, notification.id)
                deleted += 1
        
        print_result(
            "Cleanup complete",
            True,
            f"Removed {deleted} integration test notifications"
        )
        return True
    except Exception as e:
        print_result("Cleanup", False, f"Error: {str(e)}")
        return False
    finally:
        db.close()


def run_integration_tests():
    """Run all integration tests"""
    print("\n" + "🚀" * 35)
    print("   NOTIFICATION CENTER INTEGRATION TEST SUITE")
    print("🚀" * 35)
    
    results = {}
    
    # Run tests
    results["API Routes"] = test_api_routes()
    results["Admin Page Route"] = test_admin_page_route()
    results["Router Registration"] = test_notification_router_registration()
    
    # Summary
    print_header("INTEGRATION TEST SUMMARY")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print("\n" + "=" * 70)
    success_rate = (passed / total * 100) if total > 0 else 0
    print(f"📊 Results: {passed}/{total} integration tests passed ({success_rate:.1f}%)")
    
    # Cleanup
    cleanup_test_data()
    
    if passed == total:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        return True
    else:
        print("⚠️  Some integration tests failed.")
        return False


if __name__ == "__main__":
    try:
        success = run_integration_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
