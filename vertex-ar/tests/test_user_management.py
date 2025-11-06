"""
Tests for user management system.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add the parent directory to the path so we can import the app
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.auth import _hash_password
from app.database import Database
from app.main import create_app


@pytest.fixture
def app():
    """Create test app with temporary database."""
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    db_path = Path(temp_db.name)

    # Override environment for testing
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["RUNNING_TESTS"] = "1"
    os.environ["RATE_LIMIT_ENABLED"] = "false"

    app = create_app()

    # Initialize database
    database = Database(db_path)
    app.state.database = database

    yield app

    # Cleanup
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    """Create admin user and get auth token."""
    # Register admin user
    register_response = client.post(
        "/auth/register",
        json={"username": "admin", "password": "admin123456", "email": "admin@example.com", "full_name": "Admin User"},
    )
    assert register_response.status_code == 201

    # Login to get token
    login_response = client.post("/auth/login", json={"username": "admin", "password": "admin123456"})
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


@pytest.fixture
def user_token(client):
    """Create regular user and get auth token."""
    # First create admin to authorize user creation
    admin_response = client.post(
        "/auth/register",
        json={"username": "admin2", "password": "admin123456", "email": "admin2@example.com", "full_name": "Admin User 2"},
    )
    assert admin_response.status_code == 201

    admin_login = client.post("/auth/login", json={"username": "admin2", "password": "admin123456"})
    admin_token = admin_login.json()["access_token"]

    # Create regular user through admin API
    create_response = client.post(
        "/users/users",
        json={"username": "testuser", "password": "test123456", "email": "test@example.com", "full_name": "Test User"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 200

    # Login as regular user
    login_response = client.post("/auth/login", json={"username": "testuser", "password": "test123456"})
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


class TestUserRegistration:
    """Test user registration."""

    def test_register_first_user_as_admin(self, client):
        """Test that first user becomes admin."""
        response = client.post(
            "/auth/register",
            json={"username": "firstuser", "password": "password123", "email": "first@example.com", "full_name": "First User"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "firstuser"
        assert data["is_admin"] is True
        assert "Admin user created" in data["message"]

    def test_register_subsequent_user_as_regular(self, client, admin_token):
        """Test that subsequent users become regular users."""
        response = client.post(
            "/auth/register",
            json={
                "username": "regularuser",
                "password": "password123",
                "email": "regular@example.com",
                "full_name": "Regular User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "regularuser"
        assert data["is_admin"] is False
        assert "User created" in data["message"]

    def test_register_duplicate_user(self, client):
        """Test registering duplicate username fails."""
        # Register first user
        client.post(
            "/auth/register",
            json={
                "username": "duplicate",
                "password": "password123",
                "email": "dup1@example.com",
                "full_name": "Duplicate User 1",
            },
        )

        # Try to register same username
        response = client.post(
            "/auth/register",
            json={
                "username": "duplicate",
                "password": "password456",
                "email": "dup2@example.com",
                "full_name": "Duplicate User 2",
            },
        )

        assert response.status_code == 409
        assert "User already exists" in response.json()["detail"]

    def test_register_validation(self, client):
        """Test registration validation."""
        # Test short username
        response = client.post(
            "/auth/register",
            json={"username": "ab", "password": "password123", "email": "test@example.com", "full_name": "Test User"},
        )
        assert response.status_code == 422

        # Test short password
        response = client.post(
            "/auth/register",
            json={"username": "validuser", "password": "123", "email": "test@example.com", "full_name": "Test User"},
        )
        assert response.status_code == 422


class TestUserAuthentication:
    """Test user authentication."""

    def test_login_success(self, client, admin_token):
        """Test successful login."""
        response = client.post("/auth/login", json={"username": "admin", "password": "admin123456"})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post("/auth/login", json={"username": "nonexistent", "password": "wrongpassword"})

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_logout(self, client, admin_token):
        """Test user logout."""
        response = client.post("/auth/logout", headers={"Authorization": f"Bearer {admin_token}"})

        assert response.status_code == 204

        # Token should no longer work
        response = client.get("/users/profile", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 401


class TestUserProfile:
    """Test user profile management."""

    def test_get_profile(self, client, user_token):
        """Test getting user profile."""
        response = client.get("/users/profile", headers={"Authorization": f"Bearer {user_token}"})

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert "created_at" in data

    def test_update_profile(self, client, user_token):
        """Test updating user profile."""
        response = client.put(
            "/users/profile",
            json={"email": "updated@example.com", "full_name": "Updated Name"},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 200
        assert "Profile updated successfully" in response.json()["message"]

        # Verify changes
        profile_response = client.get("/users/profile", headers={"Authorization": f"Bearer {user_token}"})
        data = profile_response.json()
        assert data["email"] == "updated@example.com"
        assert data["full_name"] == "Updated Name"

    def test_change_password(self, client, user_token):
        """Test changing password."""
        response = client.post(
            "/users/change-password",
            json={"current_password": "test123456", "new_password": "newpassword123"},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 200
        assert "Password changed successfully" in response.json()["message"]

        # Should be able to login with new password
        login_response = client.post("/auth/login", json={"username": "testuser", "password": "newpassword123"})
        assert login_response.status_code == 200

        # Old password should not work
        old_login_response = client.post("/auth/login", json={"username": "testuser", "password": "test123456"})
        assert old_login_response.status_code == 401

    def test_change_password_wrong_current(self, client, user_token):
        """Test changing password with wrong current password."""
        response = client.post(
            "/users/change-password",
            json={"current_password": "wrongpassword", "new_password": "newpassword123"},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 401
        assert "Current password is incorrect" in response.json()["detail"]


class TestUserManagement:
    """Test admin user management."""

    def test_list_users(self, client, admin_token):
        """Test listing users as admin."""
        response = client.get("/users/users", headers={"Authorization": f"Bearer {admin_token}"})

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least the admin user

    def test_create_user(self, client, admin_token):
        """Test creating a user as admin."""
        response = client.post(
            "/users/users",
            json={"username": "newuser", "password": "password123", "email": "newuser@example.com", "full_name": "New User"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        assert "User newuser created successfully" in response.json()["message"]

    def test_update_user(self, client, admin_token):
        """Test updating a user as admin."""
        # First create a user
        client.post(
            "/users/users",
            json={
                "username": "updateme",
                "password": "password123",
                "email": "before@example.com",
                "full_name": "Before Update",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Update the user
        response = client.put(
            "/users/users/updateme",
            json={"email": "after@example.com", "full_name": "After Update", "is_admin": True},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        assert "User updateme updated successfully" in response.json()["message"]

    def test_delete_user(self, client, admin_token):
        """Test deleting a user as admin."""
        # First create a user
        client.post(
            "/users/users",
            json={"username": "deleteme", "password": "password123", "email": "delete@example.com", "full_name": "Delete Me"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Delete the user
        response = client.delete("/users/users/deleteme", headers={"Authorization": f"Bearer {admin_token}"})

        assert response.status_code == 200
        assert "User deleteme deactivated successfully" in response.json()["message"]

    def test_search_users(self, client, admin_token):
        """Test searching users as admin."""
        # Create some users
        client.post(
            "/users/users",
            json={"username": "search1", "password": "password123", "email": "search1@example.com", "full_name": "Search One"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        client.post(
            "/users/users",
            json={"username": "search2", "password": "password123", "email": "search2@example.com", "full_name": "Search Two"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Search by username
        response = client.get("/users/users/search?query=search", headers={"Authorization": f"Bearer {admin_token}"})

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_get_user_stats(self, client, admin_token):
        """Test getting user statistics as admin."""
        response = client.get("/users/stats", headers={"Authorization": f"Bearer {admin_token}"})

        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "active_users" in data
        assert "admin_users" in data
        assert "recent_logins" in data
        assert data["total_users"] >= 1


class TestAuthorization:
    """Test authorization controls."""

    def test_regular_user_cannot_access_admin_endpoints(self, client, user_token):
        """Test that regular users cannot access admin endpoints."""
        # Try to list users
        response = client.get("/users/users", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 403

        # Try to create user
        response = client.post(
            "/users/users",
            json={
                "username": "shouldfail",
                "password": "password123",
                "email": "fail@example.com",
                "full_name": "Should Fail",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

        # Try to get stats
        response = client.get("/users/stats", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 403

    def test_unauthorized_access(self, client):
        """Test that unauthorized access is rejected."""
        response = client.get("/users/profile")
        assert response.status_code == 401

        response = client.get("/users/users")
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
