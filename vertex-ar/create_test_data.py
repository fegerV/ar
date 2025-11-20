#!/usr/bin/env python3
"""
Create test data for video lightbox testing.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from pathlib import Path
from app.database import Database
from app.auth import _hash_password
import uuid
import shutil

# Initialize database
DB_PATH = Path("app_data.db")
db = Database(DB_PATH)

# Create a test client
client_id = str(uuid.uuid4())
db.create_client(
    client_id=client_id,
    name="Test Client",
    phone=f"+123456789{uuid.uuid4().int % 10}"
)

# Create a test portrait
portrait_id = str(uuid.uuid4())
permanent_link = f"test-portrait-{portrait_id[:8]}"

# Create a dummy image file
storage_root = Path("storage")
portrait_storage = storage_root / "portraits" / client_id / portrait_id
portrait_storage.mkdir(parents=True, exist_ok=True)

# Create a simple test image (just a text file for testing)
test_image_path = portrait_storage / f"{portrait_id}.jpg"
with open(test_image_path, "wb") as f:
    # Write a minimal JPEG header (just for testing)
    f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9')

# Create a dummy video file (just a text file for testing)
test_video_path = portrait_storage / f"{uuid.uuid4()}.mp4"
with open(test_video_path, "wb") as f:
    f.write(b"dummy video content for testing")

# Create a dummy preview image
test_preview_path = portrait_storage / f"{uuid.uuid4()}_preview.jpg"
with open(test_preview_path, "wb") as f:
    # Write a minimal JPEG header
    f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9')

# Create portrait in database
db.create_portrait(
    portrait_id=portrait_id,
    client_id=client_id,
    permanent_link=permanent_link,
    image_path=str(test_image_path),
    marker_fset="",
    marker_fset3="",
    marker_iset="",
    qr_code=None,
    image_preview_path=None
)

# Create video in database
video_id = str(uuid.uuid4())
db.create_video(
    video_id=video_id,
    portrait_id=portrait_id,
    video_path=str(test_video_path),
    is_active=True,
    video_preview_path=str(test_preview_path),
    description="Test video for lightbox testing"
)

print(f"Created test data:")
print(f"  Client ID: {client_id}")
print(f"  Portrait ID: {portrait_id}")
print(f"  Permanent Link: {permanent_link}")
print(f"  Video ID: {video_id}")
print(f"  Admin URL: http://localhost:8000/admin/order/{portrait_id}")

# Create admin user if not exists (using ensure_admin_user pattern)
admin_username = "admin"
admin_password = "admin123"
hashed_password = _hash_password(admin_password)

try:
    db.ensure_admin_user(
        username=admin_username,
        hashed_password=hashed_password,
        email="admin@example.com",
        full_name="Test Admin"
    )
    print(f"Created admin user: {admin_username} / {admin_password}")
except:
    print(f"Admin user already exists: {admin_username} / {admin_password}")

print("\nYou can now test the video lightbox by:")
print("1. Going to http://localhost:8000/admin")
print("2. Logging in with admin/admin123")
print("3. Clicking on any order to see the video lightbox")