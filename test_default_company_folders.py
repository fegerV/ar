#!/usr/bin/env python3
"""Test that ensure_default_company creates folder hierarchy"""
import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add vertex-ar to path
sys.path.insert(0, str(Path(__file__).parent / "vertex-ar"))

# Set environment BEFORE importing app modules
storage_dir = Path('/tmp/test_folders')
if storage_dir.exists():
    shutil.rmtree(storage_dir)
storage_dir.mkdir(parents=True, exist_ok=True)

db_path = Path('/tmp/test_folders.db')
if db_path.exists():
    db_path.unlink()

os.environ['DB_PATH'] = str(db_path)
os.environ['STORAGE_ROOT'] = str(storage_dir)

from app.database import Database, ensure_default_company

print("Testing ensure_default_company folder creation...")
print(f"Storage root: {storage_dir}")

# Create database and call ensure_default_company
db = Database(db_path)
ensure_default_company(db)

# Check if folders were created
expected_base = storage_dir / "vertex_ar_content" / "vertex-ar-default" / "portraits"
print(f"\nChecking for folder: {expected_base}")

if expected_base.exists():
    print("✓ Base folder created successfully")
    for subfolder in ["Image", "QR", "nft_markers", "nft_cache"]:
        subfolder_path = expected_base / subfolder
        if subfolder_path.exists():
            print(f"✓ Subfolder exists: {subfolder}")
        else:
            print(f"✗ Subfolder missing: {subfolder}")
else:
    print("✗ Base folder not created")
    print(f"  Contents of {storage_dir}:")
    for item in storage_dir.rglob("*"):
        print(f"    {item}")

# Cleanup
if db_path.exists():
    db_path.unlink()
if storage_dir.exists():
    shutil.rmtree(storage_dir)

print("\n✓ Test complete")
