#!/usr/bin/env python3
"""
Simple test for basic functionality without external dependencies.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_basic_imports():
    """Test basic imports."""
    print("Testing basic imports...")
    
    try:
        from app.config import settings
        print("✅ config module imported")
    except Exception as e:
        print(f"❌ config import failed: {e}")
        return False
    
    try:
        from app.database import Database
        print("✅ database module imported")
    except Exception as e:
        print(f"❌ database import failed: {e}")
        return False
    
    try:
        from app.models import PortraitResponse, VideoResponse
        print("✅ models module imported")
    except Exception as e:
        print(f"❌ models import failed: {e}")
        return False
    
    try:
        from app.storage import StorageAdapter
        print("✅ storage module imported")
    except Exception as e:
        print(f"❌ storage import failed: {e}")
        return False
    
    try:
        from app.storage_local import LocalStorageAdapter
        print("✅ storage_local module imported")
    except Exception as e:
        print(f"❌ storage_local import failed: {e}")
        return False
    
    try:
        from app.storage_minio import MinioStorageAdapter
        print("✅ storage_minio module imported")
    except Exception as e:
        print(f"❌ storage_minio import failed: {e}")
        return False
    
    return True

def test_new_files():
    """Test that new files exist."""
    print("Testing new files...")
    
    new_files = [
        "storage_config.py",
        "storage_manager.py",
        "app/storage_yandex.py",
        "app/api/storage_config.py",
        "app/api/yandex_disk.py"
    ]
    
    for file_path in new_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            return False
    
    return True

def test_config_directory():
    """Test config directory."""
    print("Testing config directory...")
    
    config_dir = "config"
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
        print(f"✅ Created {config_dir} directory")
    
    gitkeep = os.path.join(config_dir, ".gitkeep")
    if os.path.exists(gitkeep):
        print(f"✅ {gitkeep} exists")
    else:
        print(f"❌ {gitkeep} missing")
        return False
    
    return True

def main():
    """Run basic tests."""
    print("🧪 Running Basic Functionality Tests\n")
    
    tests = [
        test_basic_imports,
        test_new_files,
        test_config_directory
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Empty line
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic tests passed! System is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())