"""
Tests for API endpoints.
"""
import pytest
import tempfile
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import create_app


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)
    
    yield db_path
    
    # Cleanup
    db_path.unlink(missing_ok=True)


@pytest.fixture
def test_app(temp_db):
    """Create a test FastAPI app with temporary database."""
    # Mock environment variables for testing
    with patch.dict('os.environ', {
        'RUNNING_TESTS': '1',
        'RATE_LIMIT_ENABLED': 'false',
        'CORS_ORIGINS': 'http://localhost:8000'
    }):
        app = create_app()
        
        # Initialize database with temp path
        from app.database import Database
        app.state.database = Database(temp_db)
        
        # Initialize auth components
        from app.auth import TokenManager, AuthSecurityManager
        app.state.tokens = TokenManager(session_timeout_minutes=30)
        app.state.auth_security = AuthSecurityManager(max_attempts=5, lockout_minutes=15)
        
        return app


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


@pytest.fixture
def admin_token(client):
    """Create an admin user and return auth token."""
    # Register admin user
    register_response = client.post("/auth/register", json={
        "username": "admin",
        "password": "admin_password"
    })
    assert register_response.status_code == 201
    
    # Login and get token
    login_response = client.post("/auth/login", json={
        "username": "admin",
        "password": "admin_password"
    })
    assert login_response.status_code == 200
    
    return login_response.json()["access_token"]


@pytest.fixture
def auth_headers(admin_token):
    """Create authorization headers."""
    return {"Authorization": f"Bearer {admin_token}"}


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    def test_version_endpoint(self, client):
        """Test version endpoint."""
        response = client.get("/version")
        assert response.status_code == 200
        
        data = response.json()
        assert "version" in data


class TestAuthEndpoints:
    """Test authentication endpoints."""
    
    def test_register_user(self, client):
        """Test user registration."""
        response = client.post("/auth/register", json={
            "username": "testuser",
            "password": "test_password"
        })
        assert response.status_code == 201
        
        data = response.json()
        assert data["username"] == "testuser"
    
    def test_register_duplicate_user(self, client):
        """Test registering duplicate user."""
        # Register first user
        client.post("/auth/register", json={
            "username": "testuser",
            "password": "test_password"
        })
        
        # Try to register same user again
        response = client.post("/auth/register", json={
            "username": "testuser",
            "password": "another_password"
        })
        assert response.status_code == 409
    
    def test_login_valid_credentials(self, client):
        """Test login with valid credentials."""
        # Register user first
        client.post("/auth/register", json={
            "username": "testuser",
            "password": "test_password"
        })
        
        # Login
        response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "test_password"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post("/auth/login", json={
            "username": "nonexistent",
            "password": "wrong_password"
        })
        assert response.status_code == 401
    
    def test_logout_valid_token(self, client, admin_token):
        """Test logout with valid token."""
        response = client.post("/auth/logout", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 204
    
    def test_logout_invalid_token(self, client):
        """Test logout with invalid token."""
        response = client.post("/auth/logout", headers={
            "Authorization": "Bearer invalid_token"
        })
        assert response.status_code == 401


class TestClientEndpoints:
    """Test client management endpoints."""
    
    def test_create_client(self, client, auth_headers):
        """Test creating a client."""
        response = client.post("/clients/", json={
            "phone": "+1234567890",
            "name": "John Doe"
        }, headers=auth_headers)
        assert response.status_code == 201
        
        data = response.json()
        assert data["phone"] == "+1234567890"
        assert data["name"] == "John Doe"
        assert "id" in data
        assert "created_at" in data
    
    def test_create_duplicate_client(self, client, auth_headers):
        """Test creating client with duplicate phone."""
        # Create first client
        client.post("/clients/", json={
            "phone": "+1234567890",
            "name": "John Doe"
        }, headers=auth_headers)
        
        # Try to create duplicate
        response = client.post("/clients/", json={
            "phone": "+1234567890",
            "name": "Jane Doe"
        }, headers=auth_headers)
        assert response.status_code == 409
    
    def test_list_clients(self, client, auth_headers):
        """Test listing clients."""
        # Create a client first
        client.post("/clients/", json={
            "phone": "+1234567890",
            "name": "John Doe"
        }, headers=auth_headers)
        
        response = client.get("/clients/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 1
        assert data[0]["phone"] == "+1234567890"
        assert data[0]["name"] == "John Doe"
    
    def test_get_client(self, client, auth_headers):
        """Test getting a specific client."""
        # Create a client first
        create_response = client.post("/clients/", json={
            "phone": "+1234567890",
            "name": "John Doe"
        }, headers=auth_headers)
        client_id = create_response.json()["id"]
        
        response = client.get(f"/clients/{client_id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == client_id
        assert data["phone"] == "+1234567890"
        assert data["name"] == "John Doe"
    
    def test_get_client_by_phone(self, client, auth_headers):
        """Test getting client by phone number."""
        # Create a client first
        client.post("/clients/", json={
            "phone": "+1234567890",
            "name": "John Doe"
        }, headers=auth_headers)
        
        response = client.get("/clients/phone/+1234567890", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["phone"] == "+1234567890"
        assert data["name"] == "John Doe"
    
    def test_search_clients(self, client, auth_headers):
        """Test searching clients."""
        # Create multiple clients
        client.post("/clients/", json={
            "phone": "+1234567890",
            "name": "John Doe"
        }, headers=auth_headers)
        
        client.post("/clients/", json={
            "phone": "+1234567891",
            "name": "Jane Doe"
        }, headers=auth_headers)
        
        response = client.get("/clients/search/123", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 2
    
    def test_update_client(self, client, auth_headers):
        """Test updating a client."""
        # Create a client first
        create_response = client.post("/clients/", json={
            "phone": "+1234567890",
            "name": "John Doe"
        }, headers=auth_headers)
        client_id = create_response.json()["id"]
        
        # Update client
        response = client.put(f"/clients/{client_id}", json={
            "name": "John Smith"
        }, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "John Smith"
        assert data["phone"] == "+1234567890"  # unchanged
    
    def test_delete_client(self, client, auth_headers):
        """Test deleting a client."""
        # Create a client first
        create_response = client.post("/clients/", json={
            "phone": "+1234567890",
            "name": "John Doe"
        }, headers=auth_headers)
        client_id = create_response.json()["id"]
        
        response = client.delete(f"/clients/{client_id}", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify deletion
        get_response = client.get(f"/clients/{client_id}", headers=auth_headers)
        assert get_response.status_code == 404


class TestPortraitEndpoints:
    """Test portrait management endpoints."""
    
    def test_create_portrait(self, client, auth_headers):
        """Test creating a portrait."""
        # First create a client
        client_response = client.post("/clients/", json={
            "phone": "+1234567890",
            "name": "John Doe"
        }, headers=auth_headers)
        client_id = client_response.json()["id"]
        
        # Mock file upload and NFT generation
        with patch('app.api.portraits.PreviewGenerator') as mock_preview, \
             patch('app.api.portraits.NFTMarkerGenerator') as mock_nft, \
             patch('app.api.portraits.qrcode') as mock_qrcode:
            
            # Setup mocks
            mock_preview.generate_image_preview.return_value = b"fake_preview"
            mock_nft.return_value.generate_marker.return_value = Mock(
                fset_path="fset",
                fset3_path="fset3",
                iset_path="iset"
            )
            mock_qrcode.make.return_value = Mock()
            mock_qrcode.make.return_value.save = Mock()
            
            # Mock the BytesIO operations
            with patch('app.api.portraits.BytesIO') as mock_bytesio, \
                 patch('builtins.open', create=True) as mock_open, \
                 patch('app.api.portraits.base64.b64encode') as mock_b64:
                
                mock_bytesio.return_value = Mock()
                mock_b64.return_value.decode.return_value = "fake_qr"
                
                # Create portrait with mock image
                response = client.post(
                    f"/portraits/?client_id={client_id}",
                    files={"image": ("test.jpg", b"fake_image_content", "image/jpeg")},
                    headers=auth_headers
                )
                
                # Should succeed despite mocking
                assert response.status_code in [201, 200]  # May vary based on mocking
    
    def test_list_portraits(self, client, auth_headers):
        """Test listing portraits."""
        response = client.get("/portraits/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)


class TestVideoEndpoints:
    """Test video management endpoints."""
    
    def test_list_videos_for_portrait(self, client, auth_headers):
        """Test listing videos for a portrait."""
        # This will likely return 404 since portrait doesn't exist
        response = client.get("/videos/portrait/fake_portrait_id", headers=auth_headers)
        assert response.status_code in [200, 404]  # May vary


class TestUnauthenticatedAccess:
    """Test that unauthenticated access is properly blocked."""
    
    def test_unauthenticated_client_create(self, client):
        """Test creating client without authentication."""
        response = client.post("/clients/", json={
            "phone": "+1234567890",
            "name": "John Doe"
        })
        assert response.status_code == 401
    
    def test_unauthenticated_client_list(self, client):
        """Test listing clients without authentication."""
        response = client.get("/clients/")
        assert response.status_code == 401