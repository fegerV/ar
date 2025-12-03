#!/usr/bin/env python3
"""Simple test for folder service"""
import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add vertex-ar to path
sys.path.insert(0, str(Path(__file__).parent / "vertex-ar"))

# Use a proper temporary directory for Windows
storage_dir = Path(tempfile.mkdtemp())
print(f"Storage root: {storage_dir}")

from app.services.folder_service import FolderService

# Test folder service directly
folder_service = FolderService(storage_dir)

# Create a simple directory structure
test_path = storage_dir / "test_directory"
print(f"Creating directory: {test_path}")
test_path.mkdir(parents=True, exist_ok=True)

if test_path.exists():
    print("✓ Directory created successfully")
else:
    print("✗ Directory not created")

# List contents
print(f"Contents of {storage_dir}:")
for item in storage_dir.iterdir():
    print(f"  {item.name}")

# Cleanup
try:
    if storage_dir.exists():
        shutil.rmtree(storage_dir)
except Exception as e:
    print(f"Warning: Failed to cleanup test files: {e}")

print("\n✓ Simple test complete")
