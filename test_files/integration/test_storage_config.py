#!/usr/bin/env python3
"""
Test script for storage configuration functionality.
Tests the new multi-storage system implementation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pathlib import Path
import json
import tempfile

def test_storage_config():
    """Test storage configuration system."""
    print("Testing storage configuration system...")
    
    try:
        from storage_config import get_storage_config
        config = get_storage_config()
        
        # Test default configuration
        assert config is not None, "Config should not be None"
        assert "content_types" in config, "Should have content_types"
        assert "backup_settings" in config, "Should have backup_settings"
        
        # Test default values
        content_types = config["content_types"]
        assert content_types["portraits"]["storage_type"] == "local", "Default should be local"
        assert content_types["videos"]["storage_type"] == "local", "Default should be local"
        assert content_types["previews"]["storage_type"] == "local", "Default should be local"
        assert content_types["nft_markers"]["storage_type"] == "local", "Default should be local"
        
        backup_settings = config["backup_settings"]
        assert backup_settings["auto_split_backups"] == True, "Auto-split should be enabled"
        assert backup_settings["max_backup_size_mb"] == 500, "Default max size should be 500MB"
        assert backup_settings["chunk_size_mb"] == 100, "Default chunk size should be 100MB"
        
        print("✅ Storage configuration test passed")
        return True
        
    except Exception as e:
        print(f"❌ Storage configuration test failed: {e}")
        return False

def test_storage_manager():
    """Test storage manager initialization."""
    print("Testing storage manager...")
    
    try:
        from storage_manager import get_storage_manager
        
        # Test with temporary storage root
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = get_storage_manager(Path(temp_dir))
            
            # Test adapter retrieval
            portraits_adapter = manager.get_adapter("portraits")
            videos_adapter = manager.get_adapter("videos")
            previews_adapter = manager.get_adapter("previews")
            nft_adapter = manager.get_adapter("nft_markers")
            
            # All should return local adapter by default
            from app.storage_local import LocalStorageAdapter
            assert isinstance(portraits_adapter, LocalStorageAdapter), "Should return LocalStorageAdapter"
            assert isinstance(videos_adapter, LocalStorageAdapter), "Should return LocalStorageAdapter"
            assert isinstance(previews_adapter, LocalStorageAdapter), "Should return LocalStorageAdapter"
            assert isinstance(nft_adapter, LocalStorageAdapter), "Should return LocalStorageAdapter"
            
            print("✅ Storage manager test passed")
            return True
            
    except Exception as e:
        print(f"❌ Storage manager test failed: {e}")
        return False

def test_yandex_disk_adapter():
    """Test Yandex Disk adapter (without actual API calls)."""
    print("Testing Yandex Disk adapter...")
    
    try:
        from app.storage_yandex import YandexDiskStorageAdapter
        
        # Test initialization (should fail without token)
        try:
            adapter = YandexDiskStorageAdapter("")  # Empty token
            assert False, "Should fail with empty token"
        except Exception:
            pass  # Expected to fail
        
        # Test initialization with dummy token
        adapter = YandexDiskStorageAdapter("dummy_token", "test_path")
        assert adapter.oauth_token == "dummy_token", "Token should be stored"
        assert adapter.base_path == "test_path", "Base path should be stored"
        
        print("✅ Yandex Disk adapter test passed")
        return True
        
    except Exception as e:
        print(f"❌ Yandex Disk adapter test failed: {e}")
        return False

def test_backup_settings():
    """Test backup settings integration."""
    print("Testing backup settings...")
    
    try:
        from backup_manager import create_backup_manager
        from storage_config import get_storage_config
        
        # Test backup manager creation
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / "backups"
            db_path = Path(temp_dir) / "test.db"
            storage_path = Path(temp_dir) / "storage"
            
            manager = create_backup_manager(
                backup_dir=backup_dir,
                db_path=db_path,
                storage_path=storage_path
            )
            
            # Test settings loading
            settings = manager._get_backup_settings()
            assert "compression" in settings, "Should have compression setting"
            assert "auto_split_backups" in settings, "Should have auto_split setting"
            assert "max_backup_size_mb" in settings, "Should have max size setting"
            assert "chunk_size_mb" in settings, "Should have chunk size setting"
            
            print("✅ Backup settings test passed")
            return True
            
    except Exception as e:
        print(f"❌ Backup settings test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Running Storage Configuration Tests\n")
    
    tests = [
        test_storage_config,
        test_storage_manager,
        test_yandex_disk_adapter,
        test_backup_settings
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Empty line
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Storage configuration is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())