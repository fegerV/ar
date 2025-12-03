#!/usr/bin/env python3
"""Test that ensure_default_company creates folder hierarchy and database records"""
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

# Set environment variables
os.environ['DB_PATH'] = str(db_path)
os.environ['STORAGE_ROOT'] = str(storage_dir)

# Import modules after setting environment variables
from app.database import Database, ensure_default_company
from app.services.folder_service import FolderService

# Directly update the settings instance to use our storage root
from app.config import settings
settings.STORAGE_ROOT = storage_dir

print("Testing ensure_default_company complete bootstrap...")
print(f"Storage root: {storage_dir}")

# Create database and call ensure_default_company
db = Database(db_path)
ensure_default_company(db)

# Check if company was created
print("\n=== Database Verification ===")
company = db.get_company("vertex-ar-default")
if company:
    print("✓ Default company created successfully")
    print(f"  ID: {company['id']}")
    print(f"  Name: {company['name']}")
    print(f"  Storage Type: {company.get('storage_type', 'N/A')}")
    print(f"  Storage Folder Path: {company.get('storage_folder_path', 'N/A')}")
else:
    print("✗ Default company not found")
    sys.exit(1)

# Check categories
categories = db.list_categories(company_id="vertex-ar-default")
print(f"\nCategories found: {len(categories)}")
for category in categories:
    print(f"  - {category['name']} (slug: {category.get('slug', 'N/A')})")

    # Check folders for this category
    folders = db.list_folders(project_id=category["id"])
    print(f"    Folders: {len(folders)}")
    for folder in folders:
        print(f"      - {folder['name']}")

# Check if folders were created on filesystem
print("\n=== Filesystem Verification ===")
# Use the test storage directory
folder_service = FolderService(storage_dir)
expected_base = storage_dir / "vertex_ar_content"

print(f"Checking for base directory: {expected_base}")
if expected_base.exists():
    print("✓ Base storage directory created successfully")
    print(f"  Path: {expected_base}")

    # Check company folder (using slugified company ID)
    company_folder = expected_base / "vertex_ar_default"  # Use slugified version
    print(f"Checking for company folder: {company_folder}")
    if company_folder.exists():
        print("✓ Company folder created successfully")
        print(f"  Path: {company_folder}")

        # Check category folders
        category_slugs = [cat["slug"] for cat in categories]
        print(f"Verifying hierarchy for categories: {category_slugs}")
        verification_result = folder_service.verify_hierarchy(company, category_slugs)

        print(f"Verification result: {verification_result}")
        if verification_result["all_exist"]:
            print("✓ All category folder hierarchies created successfully")
            for slug, details in verification_result["categories"].items():
                if details["exists"]:
                    print(f"  - Category '{slug}': ✓")
                    for subfolder, sf_details in details["subfolders"].items():
                        if sf_details["exists"]:
                            print(f"    - {subfolder}: ✓")
                        else:
                            print(f"    - {subfolder}: ✗")
                else:
                    print(f"  - Category '{slug}': ✗")
        else:
            print("⚠ Some category folder hierarchies missing")
            for slug, details in verification_result["categories"].items():
                status = "✓" if details["exists"] else "✗"
                print(f"  - Category '{slug}': {status}")
                if details["exists"]:
                    print(f"    Base path: {details['base_path']}")
                    # Check what's actually in the directory
                    base_path = Path(details["base_path"])
                    if base_path.exists():
                        print(f"    Contents:")
                        for item in base_path.iterdir():
                            print(f"      {item.name}")
    else:
        print("✗ Company folder not created")
        print(f"  Expected: {company_folder}")
        # List contents of base directory
        print(f"  Contents of {expected_base}:")
        if expected_base.exists():
            for item in expected_base.iterdir():
                print(f"    {item.name}")
else:
    print("✗ Base storage directory not created")
    print(f"  Expected: {expected_base}")
    print(f"  Contents of {storage_dir}:")
    if storage_dir.exists():
        for item in storage_dir.iterdir():
            print(f"    {item.name}")

# Let's also check what directories were actually created
print(f"\nRecursive contents of {storage_dir}:")
if storage_dir.exists():
    for root, dirs, files in os.walk(storage_dir):
        level = root.replace(str(storage_dir), '').count(os.sep)
        indent = ' ' * 2 * level
        print(f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f'{subindent}{file}')

# Additional verification of specific paths
print("\n=== Detailed Path Verification ===")
required_paths = [
    "vertex_ar_content/vertex_ar_default/portraits",  # Use slugified company ID
    "vertex_ar_content/vertex_ar_default/diplomas",   # Use slugified company ID
    "vertex_ar_content/vertex_ar_default/certificates"  # Use slugified company ID
]

for rel_path in required_paths:
    full_path = storage_dir / rel_path.replace("/", os.sep)  # Handle Windows path separator
    print(f"Checking path: {full_path}")
    if full_path.exists():
        print(f"✓ {rel_path}")

        # Check standard subfolders
        for subfolder in ["Image", "QR", "nft_markers", "nft_cache"]:
            subfolder_path = full_path / subfolder
            if subfolder_path.exists():
                print(f"  ✓ {subfolder}")
            else:
                print(f"  ✗ {subfolder}")
    else:
        print(f"✗ {rel_path}")
        # Show what's actually there
        parent_dir = full_path.parent
        if parent_dir.exists():
            print(f"    Contents of {parent_dir}:")
            for item in parent_dir.iterdir():
                print(f"      {item.name}")

# Cleanup
try:
    if db_path.exists():
        db_path.unlink()
    if storage_dir.exists():
        shutil.rmtree(storage_dir)
except Exception as e:
    print(f"Warning: Failed to cleanup test files: {e}")

print("\n✓ Test complete")
