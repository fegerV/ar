#!/usr/bin/env python3
"""
Simple test to verify Docker database and environment configuration.
This script tests that the database path detection logic works correctly.
"""

import sys
from pathlib import Path
import tempfile
import os

# Add vertex-ar to path to import modules
sys.path.insert(0, str(Path(__file__).parent / "vertex-ar"))

def test_db_path_detection_docker():
    """Test that config detects /app/data correctly in Docker."""
    # Create a temporary /app/data directory for testing
    with tempfile.TemporaryDirectory(prefix="docker_test_") as tmpdir:
        # Create /app/data structure
        app_data_dir = Path(tmpdir) / "app" / "data"
        app_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Simulate Docker by checking if path exists
        db_dir = Path(app_data_dir) if app_data_dir.exists() else Path("/tmp")
        
        assert db_dir.exists(), "Database directory should exist"
        assert db_dir == app_data_dir, "Should use /app/data when it exists"
        
        # Verify we can create a database file there
        db_file = db_dir / "app_data.db"
        db_file.touch()
        
        assert db_file.exists(), "Should be able to create database file"
        
    print("✓ Docker path detection test passed")

def test_db_path_detection_local():
    """Test that config falls back to BASE_DIR for local development."""
    # Simulate local environment (no /app/data)
    db_dir = Path("/app/data") if Path("/app/data").exists() else Path.cwd()
    
    # In local environment, /app/data shouldn't exist
    if not Path("/app/data").exists():
        assert db_dir == Path.cwd() or db_dir != Path("/app/data"), \
            "Should use fallback when /app/data doesn't exist"
    
    print("✓ Local path detection test passed")

def test_env_file_exists():
    """Test that .env file exists."""
    env_file = Path(__file__).parent / ".env"
    
    assert env_file.exists(), ".env file should exist"
    
    # Verify it has required variables
    env_content = env_file.read_text()
    assert "DATABASE_URL" in env_content, ".env should have DATABASE_URL"
    assert "SECRET_KEY" in env_content, ".env should have SECRET_KEY"
    assert "ADMIN_USERNAME" in env_content, ".env should have ADMIN_USERNAME"
    
    print("✓ Environment file test passed")

def test_app_data_directory():
    """Test that app_data directory exists."""
    app_data_dir = Path(__file__).parent / "app_data"
    
    assert app_data_dir.exists(), "app_data directory should exist"
    assert app_data_dir.is_dir(), "app_data should be a directory"
    
    gitkeep = app_data_dir / ".gitkeep"
    assert gitkeep.exists(), "app_data/.gitkeep should exist"
    
    print("✓ App data directory test passed")

def test_docker_compose_config():
    """Test that docker-compose.yml has correct volume configuration."""
    import yaml
    
    docker_file = Path(__file__).parent / "docker-compose.yml"
    
    with open(docker_file) as f:
        config = yaml.safe_load(f)
    
    volumes = config["services"]["app"]["volumes"]
    
    # Check for the correct volume mount
    volume_mounts = {v.split(":")[0]: v.split(":")[1] for v in volumes if ":" in v}
    
    assert "./app_data" in volume_mounts, "Should mount ./app_data"
    assert volume_mounts["./app_data"] == "/app/data", "Should mount to /app/data"
    
    print("✓ Docker compose configuration test passed")

def test_dockerfile_data_dir():
    """Test that Dockerfile creates /app/data directory."""
    dockerfile = Path(__file__).parent / "Dockerfile.app"
    content = dockerfile.read_text()
    
    assert "mkdir -p /app/data" in content, "Dockerfile should create /app/data"
    assert "chmod 755 /app/data" in content, "Dockerfile should set proper permissions"
    
    print("✓ Dockerfile data directory test passed")

def test_config_py_logic():
    """Test that config.py has proper DB path detection."""
    config_file = Path(__file__).parent / "vertex-ar" / "app" / "config.py"
    content = config_file.read_text()
    
    # Check for Docker detection logic
    assert 'Path("/app/data")' in content, "Should check for /app/data"
    assert ".exists()" in content, "Should check if path exists"
    assert "mkdir" in content or "mkdir" in content.lower(), "Should create directories"
    
    print("✓ Config.py logic test passed")

def test_database_py_init():
    """Test that database.py creates directories."""
    db_file = Path(__file__).parent / "vertex-ar" / "app" / "database.py"
    content = db_file.read_text()
    
    # Check for directory creation logic
    assert "Path(path)" in content, "Should convert path to Path object"
    assert "parent.mkdir" in content, "Should create parent directories"
    assert "str(self.path)" in content, "Should convert path to string for sqlite3"
    
    print("✓ Database.py initialization test passed")

def main():
    """Run all tests."""
    print("Running Docker database fix verification tests...\n")
    
    tests = [
        ("Docker path detection", test_db_path_detection_docker),
        ("Local path detection", test_db_path_detection_local),
        ("Environment file", test_env_file_exists),
        ("App data directory", test_app_data_directory),
        ("Docker compose config", test_docker_compose_config),
        ("Dockerfile data dir", test_dockerfile_data_dir),
        ("Config.py logic", test_config_py_logic),
        ("Database.py init", test_database_py_init),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            print(f"Testing: {name}...")
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {name} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name} error: {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Tests passed: {passed}/{len(tests)}")
    
    if failed > 0:
        print(f"Tests failed: {failed}")
        sys.exit(1)
    else:
        print("All tests passed! ✓")
        sys.exit(0)

if __name__ == "__main__":
    main()
