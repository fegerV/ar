#!/usr/bin/env python3
"""Debug test for company bootstrap"""
import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add vertex-ar to path
sys.path.insert(0, str(Path(__file__).parent / "vertex-ar"))

# Use a proper temporary directory for Windows
storage_dir = Path(tempfile.mkdtemp())
db_path = storage_dir / "test_folders.db"

# Set environment BEFORE importing app modules
os.environ['DB_PATH'] = str(db_path)
os.environ['STORAGE_ROOT'] = str(storage_dir)

from app.database import Database
from app.services.folder_service import FolderService
from app.services.company_bootstrap import CompanyBootstrap

print("Testing CompanyBootstrap directly...")
print(f"Storage root: {storage_dir}")

# Create database
db = Database(db_path)

# Test CompanyBootstrap directly
bootstrap = CompanyBootstrap(db, storage_dir)

# Test ensure_default_company
print("\n=== Testing ensure_default_company ===")
company = bootstrap.ensure_default_company()
print(f"Company: {company}")

# Test seed_default_categories
print("\n=== Testing seed_default_categories ===")
categories = bootstrap.seed_default_categories(company["id"])
print(f"Categories: {len(categories)}")

# Test seed_default_folders
print("\n=== Testing seed_default_folders ===")
folders = bootstrap.seed_default_folders(company["id"])
print(f"Folders: {len(folders)}")

# Test create_filesystem_hierarchy
print("\n=== Testing create_filesystem_hierarchy ===")
fs_result = bootstrap.create_filesystem_hierarchy(company, categories)
print(f"Filesystem result: {fs_result}")

# Check what was actually created
print(f"\n=== Checking created directories ===")
print(f"Contents of {storage_dir}:")
if storage_dir.exists():
    for root, dirs, files in os.walk(storage_dir):
        level = root.replace(str(storage_dir), '').count(os.sep)
        indent = ' ' * 2 * level
        print(f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f'{subindent}{file}')

# Cleanup
try:
    if db_path.exists():
        db_path.unlink()
    if storage_dir.exists():
        shutil.rmtree(storage_dir)
except Exception as e:
    print(f"Warning: Failed to cleanup test files: {e}")

print("\n✓ Debug test complete")
