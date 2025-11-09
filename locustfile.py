"""
Locust load testing configuration for Vertex AR
Run with: locust -f locustfile.py --host=http://localhost:8000
Web UI: http://localhost:8089
"""

from locust import HttpUser, task, between, SequentialTaskSet
import random
import json


class UserBehavior(SequentialTaskSet):
    """Sequential tasks simulating real user behavior"""
    
    def on_start(self):
        """Called when a simulated user starts"""
        self.token = None
        self.client_id = None
        self.portrait_id = None
        
        # Register and login
        self.register_user()
        self.login_user()
    
    def register_user(self):
        """Register a new user"""
        username = f"testuser_{random.randint(1000, 9999)}"
        self.username = username
        self.password = "TestPass123!"
        
        response = self.client.post("/auth/register", json={
            "username": username,
            "password": self.password,
            "email": f"{username}@example.com",
            "full_name": f"Test User {random.randint(1, 1000)}"
        })
        
        if response.status_code == 200:
            print(f"✓ User registered: {username}")
    
    def login_user(self):
        """Login user and get token"""
        response = self.client.post("/auth/login", json={
            "username": self.username,
            "password": self.password
        })
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            print(f"✓ User logged in: {self.username}")
    
    @task
    def get_profile(self):
        """Get user profile"""
        if not self.token:
            return
        
        self.client.get("/api/users/me", headers={
            "Authorization": f"Bearer {self.token}"
        })
    
    @task
    def create_client(self):
        """Create a new client"""
        if not self.token:
            return
        
        response = self.client.post("/api/clients/", 
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "name": f"Test Client {random.randint(1, 1000)}",
                "phone": f"+1{random.randint(2000000000, 9999999999)}",
                "email": f"client{random.randint(1, 1000)}@example.com"
            }
        )
        
        if response.status_code == 201:
            self.client_id = response.json().get("id")
            print(f"✓ Client created: {self.client_id}")
    
    @task
    def list_clients(self):
        """List all clients"""
        if not self.token:
            return
        
        self.client.get("/api/clients/", headers={
            "Authorization": f"Bearer {self.token}"
        })
    
    @task
    def list_portraits(self):
        """List all portraits"""
        if not self.token:
            return
        
        self.client.get("/api/portraits/", headers={
            "Authorization": f"Bearer {self.token}"
        })
    
    @task
    def health_check(self):
        """Check application health"""
        self.client.get("/health")


class AdminBehavior(SequentialTaskSet):
    """Admin user behavior pattern"""
    
    def on_start(self):
        """Login as admin"""
        self.token = None
        self.login_admin()
    
    def login_admin(self):
        """Login with admin credentials"""
        response = self.client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123"  # Default admin password
        })
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            print("✓ Admin logged in")
    
    @task(5)
    def list_all_users(self):
        """List all users (admin only)"""
        if not self.token:
            return
        
        self.client.get("/api/users/", headers={
            "Authorization": f"Bearer {self.token}"
        })
    
    @task(3)
    def list_all_clients(self):
        """List all clients"""
        if not self.token:
            return
        
        self.client.get("/api/clients/", headers={
            "Authorization": f"Bearer {self.token}"
        })
    
    @task(3)
    def list_all_portraits(self):
        """List all portraits"""
        if not self.token:
            return
        
        self.client.get("/api/portraits/", headers={
            "Authorization": f"Bearer {self.token}"
        })
    
    @task(1)
    def check_storage(self):
        """Check storage status"""
        if not self.token:
            return
        
        self.client.get("/api/admin/storage/status", headers={
            "Authorization": f"Bearer {self.token}"
        })


class ReadOnlyUser(HttpUser):
    """User that only reads data - lightweight load"""
    wait_time = between(2, 5)
    weight = 3  # 3x more read-only users than regular users
    
    def on_start(self):
        """Login at the start"""
        response = self.client.post("/auth/login", json={
            "username": "readonly",
            "password": "readonly123"
        })
        
        if response.status_code == 200:
            self.token = response.json().get("access_token")
    
    @task(5)
    def view_portraits(self):
        """View portraits"""
        if hasattr(self, 'token'):
            self.client.get("/api/portraits/", headers={
                "Authorization": f"Bearer {self.token}"
            })
    
    @task(3)
    def view_clients(self):
        """View clients"""
        if hasattr(self, 'token'):
            self.client.get("/api/clients/", headers={
                "Authorization": f"Bearer {self.token}"
            })
    
    @task(2)
    def view_profile(self):
        """View own profile"""
        if hasattr(self, 'token'):
            self.client.get("/api/users/me", headers={
                "Authorization": f"Bearer {self.token}"
            })
    
    @task(1)
    def health_check(self):
        """Check health"""
        self.client.get("/health")


class RegularUser(HttpUser):
    """Regular user with normal behavior"""
    tasks = [UserBehavior]
    wait_time = between(1, 3)
    weight = 2


class AdminUser(HttpUser):
    """Admin user with elevated privileges"""
    tasks = [AdminBehavior]
    wait_time = between(3, 7)
    weight = 1  # Less admin users


class ApiStressTest(HttpUser):
    """Stress test - rapid requests"""
    wait_time = between(0.1, 0.5)
    weight = 1
    
    @task(10)
    def rapid_health_checks(self):
        """Rapid health checks"""
        self.client.get("/health")
    
    @task(5)
    def rapid_docs_access(self):
        """Access API docs"""
        self.client.get("/docs")


# Configuration for different test scenarios
class WebsiteUser(HttpUser):
    """
    Simulates a typical website user journey:
    1. Visit homepage/docs
    2. Register
    3. Login
    4. Browse content
    5. Perform actions
    """
    wait_time = between(5, 15)  # More realistic wait time
    
    def on_start(self):
        """Initialize user session"""
        self.token = None
        self.username = f"user_{random.randint(10000, 99999)}"
        self.password = "Pass123!"
        
        # Visit homepage
        self.client.get("/")
        self.client.get("/docs")
    
    @task(1)
    def register_and_setup(self):
        """Complete registration flow"""
        # Register
        response = self.client.post("/auth/register", json={
            "username": self.username,
            "password": self.password,
            "email": f"{self.username}@test.com",
            "full_name": f"User {random.randint(1, 1000)}"
        })
        
        if response.status_code == 200:
            # Login immediately after registration
            response = self.client.post("/auth/login", json={
                "username": self.username,
                "password": self.password
            })
            
            if response.status_code == 200:
                self.token = response.json().get("access_token")
    
    @task(5)
    def browse_content(self):
        """Browse available content"""
        if not self.token:
            return
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Browse clients
        self.client.get("/api/clients/", headers=headers)
        
        # Browse portraits
        self.client.get("/api/portraits/", headers=headers)
        
        # Check profile
        self.client.get("/api/users/me", headers=headers)
    
    @task(2)
    def create_content(self):
        """Create new content"""
        if not self.token:
            return
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Create a client
        self.client.post("/api/clients/", 
            headers=headers,
            json={
                "name": f"Client {random.randint(1, 10000)}",
                "phone": f"+1{random.randint(2000000000, 9999999999)}",
                "email": f"client{random.randint(1, 10000)}@test.com"
            }
        )
