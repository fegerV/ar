#!/usr/bin/env python3
"""
Test script to verify the refactored Vertex AR application works correctly.
"""
import asyncio
import sys
from pathlib import Path

# Add vertex-ar to path
sys.path.insert(0, str(Path(__file__).parent / "vertex-ar"))

from app.main import create_app
from app.config import settings


def test_app_creation():
    """Test that the app can be created successfully."""
    print("🧪 Testing application creation...")
    
    try:
        app = create_app()
        print("✅ Application created successfully")
        
        # Test configuration
        print(f"✅ Version: {app.state.config['VERSION']}")
        print(f"✅ Base URL: {app.state.config['BASE_URL']}")
        print(f"✅ Storage type: {app.state.config['STORAGE_TYPE']}")
        
        # Test routes
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        print(f"✅ Routes registered: {len(routes)}")
        
        # Test essential routes
        essential_routes = ['/health', '/version', '/auth/login', '/auth/register', '/ar/upload']
        for route in essential_routes:
            if route in routes:
                print(f"✅ Route {route} found")
            else:
                print(f"❌ Route {route} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Application creation failed: {e}")
        return False


def test_configuration():
    """Test configuration settings."""
    print("\n🧪 Testing configuration...")
    
    try:
        # Test essential settings
        assert settings.VERSION is not None
        assert settings.BASE_URL is not None
        assert settings.STORAGE_ROOT.exists()
        assert settings.STATIC_ROOT.exists()
        
        print(f"✅ Version: {settings.VERSION}")
        print(f"✅ Base URL: {settings.BASE_URL}")
        print(f"✅ Storage root: {settings.STORAGE_ROOT}")
        print(f"✅ Static root: {settings.STATIC_ROOT}")
        print(f"✅ Rate limiting enabled: {settings.RATE_LIMIT_ENABLED}")
        print(f"✅ Auth rate limit: {settings.AUTH_RATE_LIMIT}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_modules():
    """Test that all modules can be imported."""
    print("\n🧪 Testing module imports...")
    
    modules_to_test = [
        'app.config',
        'app.rate_limiter',
        'app.storage',
        'app.storage_local',
        'app.storage_minio',
        'app.auth',
        'app.database',
        'app.models',
        'app.api.auth',
        'app.api.users',
        'app.api.ar',
        'app.api.admin',
        'app.api.clients',
        'app.api.portraits',
        'app.api.videos',
        'app.api.health',
    ]
    
    success_count = 0
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✅ {module}")
            success_count += 1
        except Exception as e:
            print(f"❌ {module}: {e}")
    
    print(f"✅ {success_count}/{len(modules_to_test)} modules imported successfully")
    return success_count == len(modules_to_test)


def test_rate_limiter():
    """Test rate limiter functionality."""
    print("\n🧪 Testing rate limiter...")
    
    try:
        from app.rate_limiter import SimpleRateLimiter, parse_rate_limit, create_rate_limit_dependency
        
        # Test rate limit parsing
        limit_count, period_seconds = parse_rate_limit("5/minute")
        assert limit_count == 5
        assert period_seconds == 60
        print("✅ Rate limit parsing works")
        
        # Test rate limiter instance
        limiter = SimpleRateLimiter()
        assert limiter is not None
        print("✅ Rate limiter instance created")
        
        # Test dependency creation
        dependency = create_rate_limit_dependency("10/minute")
        assert dependency is not None
        print("✅ Rate limit dependency created")
        
        return True
        
    except Exception as e:
        print(f"❌ Rate limiter test failed: {e}")
        return False


async def test_app_startup():
    """Test application startup and basic functionality."""
    print("\n🧪 Testing application startup...")
    
    try:
        from fastapi.testclient import TestClient
        
        app = create_app()
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        print("✅ Health endpoint works")
        
        # Test version endpoint
        response = client.get("/version")
        assert response.status_code == 200
        print("✅ Version endpoint works")
        
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "Hello" in data
        print("✅ Root endpoint works")
        
        return True
        
    except Exception as e:
        print(f"❌ Application startup test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Testing Refactored Vertex AR Application")
    print("=" * 50)
    
    tests = [
        test_configuration,
        test_modules,
        test_rate_limiter,
        test_app_creation,
    ]
    
    # Run synchronous tests
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    # Run async tests
    try:
        if asyncio.run(test_app_startup()):
            passed += 1
    except Exception as e:
        print(f"❌ Async test failed: {e}")
    
    total = len(tests) + 1  # +1 for async test
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Refactoring successful.")
        return 0
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())