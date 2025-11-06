#!/usr/bin/env python3
"""
Manual test script for user management system.
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_user_management():
    """Test user management functionality."""
    print("Testing User Management System")
    print("=" * 50)
    
    # Test 1: Register first user (should become admin)
    print("\n1. Registering first user (should become admin)...")
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": "admin",
        "password": "admin123456",
        "email": "admin@example.com",
        "full_name": "Admin User"
    })
    
    if response.status_code == 201:
        data = response.json()
        print(f"✓ Admin user created: {data['username']}, is_admin: {data['is_admin']}")
    else:
        print(f"✗ Failed to create admin user: {response.status_code} - {response.text}")
        return
    
    # Test 2: Login as admin
    print("\n2. Logging in as admin...")
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "admin",
        "password": "admin123456"
    })
    
    if response.status_code == 200:
        token_data = response.json()
        admin_token = token_data["access_token"]
        print("✓ Admin login successful")
    else:
        print(f"✗ Admin login failed: {response.status_code} - {response.text}")
        return
    
    # Test 3: Get admin profile
    print("\n3. Getting admin profile...")
    response = requests.get(f"{BASE_URL}/users/profile", headers={
        "Authorization": f"Bearer {admin_token}"
    })
    
    if response.status_code == 200:
        profile = response.json()
        print(f"✓ Profile retrieved: {profile['username']}, email: {profile['email']}")
    else:
        print(f"✗ Failed to get profile: {response.status_code} - {response.text}")
    
    # Test 4: Create regular user as admin
    print("\n4. Creating regular user as admin...")
    response = requests.post(f"{BASE_URL}/users/users", json={
        "username": "testuser",
        "password": "test123456",
        "email": "test@example.com",
        "full_name": "Test User"
    }, headers={
        "Authorization": f"Bearer {admin_token}"
    })
    
    if response.status_code == 200:
        print("✓ Regular user created successfully")
    else:
        print(f"✗ Failed to create user: {response.status_code} - {response.text}")
    
    # Test 5: Login as regular user
    print("\n5. Logging in as regular user...")
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "testuser",
        "password": "test123456"
    })
    
    if response.status_code == 200:
        token_data = response.json()
        user_token = token_data["access_token"]
        print("✓ Regular user login successful")
    else:
        print(f"✗ Regular user login failed: {response.status_code} - {response.text}")
        return
    
    # Test 6: Update regular user profile
    print("\n6. Updating regular user profile...")
    response = requests.put(f"{BASE_URL}/users/profile", json={
        "email": "updated@example.com",
        "full_name": "Updated User Name"
    }, headers={
        "Authorization": f"Bearer {user_token}"
    })
    
    if response.status_code == 200:
        print("✓ Profile updated successfully")
    else:
        print(f"✗ Failed to update profile: {response.status_code} - {response.text}")
    
    # Test 7: List users as admin
    print("\n7. Listing users as admin...")
    response = requests.get(f"{BASE_URL}/users/users", headers={
        "Authorization": f"Bearer {admin_token}"
    })
    
    if response.status_code == 200:
        users = response.json()
        print(f"✓ Retrieved {len(users)} users:")
        for user in users:
            print(f"  - {user['username']} (admin: {user['is_admin']}, active: {user['is_active']})")
    else:
        print(f"✗ Failed to list users: {response.status_code} - {response.text}")
    
    # Test 8: Get user statistics as admin
    print("\n8. Getting user statistics as admin...")
    response = requests.get(f"{BASE_URL}/users/stats", headers={
        "Authorization": f"Bearer {admin_token}"
    })
    
    if response.status_code == 200:
        stats = response.json()
        print("✓ User statistics:")
        print(f"  - Total users: {stats['total_users']}")
        print(f"  - Active users: {stats['active_users']}")
        print(f"  - Admin users: {stats['admin_users']}")
        print(f"  - Recent logins: {stats['recent_logins']}")
    else:
        print(f"✗ Failed to get stats: {response.status_code} - {response.text}")
    
    # Test 9: Search users as admin
    print("\n9. Searching users as admin...")
    response = requests.get(f"{BASE_URL}/users/users/search?query=test", headers={
        "Authorization": f"Bearer {admin_token}"
    })
    
    if response.status_code == 200:
        users = response.json()
        print(f"✓ Found {len(users)} users matching 'test':")
        for user in users:
            print(f"  - {user['username']}: {user['full_name']}")
    else:
        print(f"✗ Failed to search users: {response.status_code} - {response.text}")
    
    # Test 10: Test authorization (regular user trying admin endpoint)
    print("\n10. Testing authorization (regular user trying admin endpoint)...")
    response = requests.get(f"{BASE_URL}/users/users", headers={
        "Authorization": f"Bearer {user_token}"
    })
    
    if response.status_code == 403:
        print("✓ Authorization correctly blocked regular user")
    else:
        print(f"✗ Authorization failed: {response.status_code} - {response.text}")
    
    # Test 11: Change password
    print("\n11. Changing password...")
    response = requests.post(f"{BASE_URL}/users/change-password", json={
        "current_password": "test123456",
        "new_password": "newpassword123"
    }, headers={
        "Authorization": f"Bearer {user_token}"
    })
    
    if response.status_code == 200:
        print("✓ Password changed successfully")
        
        # Test login with new password
        response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": "testuser",
            "password": "newpassword123"
        })
        
        if response.status_code == 200:
            print("✓ Login with new password successful")
        else:
            print(f"✗ Login with new password failed: {response.status_code} - {response.text}")
    else:
        print(f"✗ Failed to change password: {response.status_code} - {response.text}")
    
    # Test 12: Logout
    print("\n12. Testing logout...")
    response = requests.post(f"{BASE_URL}/auth/logout", headers={
        "Authorization": f"Bearer {user_token}"
    })
    
    if response.status_code == 204:
        print("✓ Logout successful")
        
        # Test that token no longer works
        response = requests.get(f"{BASE_URL}/users/profile", headers={
            "Authorization": f"Bearer {user_token}"
        })
        
        if response.status_code == 401:
            print("✓ Token correctly invalidated after logout")
        else:
            print(f"✗ Token still works after logout: {response.status_code}")
    else:
        print(f"✗ Logout failed: {response.status_code} - {response.text}")
    
    print("\n" + "=" * 50)
    print("User Management System Test Complete!")
    print("✓ All tests passed!")


if __name__ == "__main__":
    try:
        test_user_management()
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server. Make sure the application is running on http://localhost:8000")
    except Exception as e:
        print(f"✗ Test failed with error: {e}")