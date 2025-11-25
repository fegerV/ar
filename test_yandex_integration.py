#!/usr/bin/env python3
"""
Test script for Yandex Disk integration and backup splitting functionality.
"""

import os
import sys
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
vertex_ar_path = project_root / "vertex-ar"
sys.path.insert(0, str(vertex_ar_path))

def test_imports():
    """Test that all required modules can be imported."""
    try:
        from vertex_ar.backup_manager import BackupManager, create_backup_manager
        from vertex_ar.remote_storage import YandexDiskStorage, get_remote_storage_manager
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_backup_manager_creation():
    """Test BackupManager creation and basic functionality."""
    try:
        manager = create_backup_manager()
        print("✅ BackupManager created successfully")
        
        # Test backup settings loading
        settings = manager._get_backup_settings()
        print(f"✅ Backup settings loaded: {settings}")
        
        # Test file splitting method exists
        if hasattr(manager, '_split_large_file'):
            print("✅ File splitting method available")
        else:
            print("❌ File splitting method missing")
            return False
            
        return True
    except Exception as e:
        print(f"❌ BackupManager test failed: {e}")
        return False

def test_yandex_disk_class():
    """Test YandexDiskStorage class initialization."""
    try:
        # Test with dummy token
        storage = YandexDiskStorage("dummy_token")
        print("✅ YandexDiskStorage class initializes correctly")
        
        # Test required methods exist
        required_methods = ['test_connection', 'upload_file', 'download_file', 'get_storage_info']
        for method in required_methods:
            if hasattr(storage, method):
                print(f"✅ Method {method} exists")
            else:
                print(f"❌ Method {method} missing")
                return False
        
        return True
    except Exception as e:
        print(f"❌ YandexDiskStorage test failed: {e}")
        return False

def test_settings_file():
    """Test backup settings file creation."""
    try:
        settings_dir = Path("app_data")
        settings_file = settings_dir / "backup_settings.json"
        
        # Create test settings
        test_settings = {
            "compression": "gz",
            "max_backups": 7,
            "auto_split_backups": True,
            "max_backup_size_mb": 500
        }
        
        settings_dir.mkdir(exist_ok=True)
        
        with open(settings_file, 'w') as f:
            json.dump(test_settings, f, indent=2)
        
        print("✅ Test settings file created")
        
        # Verify file can be read
        with open(settings_file, 'r') as f:
            loaded_settings = json.load(f)
        
        if loaded_settings == test_settings:
            print("✅ Settings file read/write works correctly")
            return True
        else:
            print("❌ Settings file corruption")
            return False
            
    except Exception as e:
        print(f"❌ Settings file test failed: {e}")
        return False

def test_template_exists():
    """Test that admin settings template exists."""
    template_path = Path("vertex-ar/templates/admin_settings.html")
    if template_path.exists():
        print("✅ Admin settings template exists")
        return True
    else:
        print("❌ Admin settings template missing")
        return False

def test_api_routes():
    """Test that API routes are properly defined."""
    try:
        from vertex_ar.app.api.admin import router
        from vertex_ar.app.api.backups import router as backups_router
        
        # Check if routes exist
        admin_routes = [route.path for route in router.routes]
        backup_routes = [route.path for route in backups_router.routes]
        
        if "/settings" in admin_routes:
            print("✅ Admin settings route exists")
        else:
            print("❌ Admin settings route missing")
            return False
        
        # Check backup create endpoint
        backup_create_exists = any("create" in route for route in backup_routes)
        if backup_create_exists:
            print("✅ Backup create endpoint exists")
        else:
            print("❌ Backup create endpoint missing")
            return False
        
        return True
    except Exception as e:
        print(f"❌ API routes test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Yandex Disk Integration Implementation\n")
    
    tests = [
        ("Import Test", test_imports),
        ("BackupManager Test", test_backup_manager_creation),
        ("YandexDiskStorage Test", test_yandex_disk_class),
        ("Settings File Test", test_settings_file),
        ("Template Test", test_template_exists),
        ("API Routes Test", test_api_routes),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Implementation is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)