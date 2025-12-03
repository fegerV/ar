#!/usr/bin/env python3
"""
Test script to verify the new path structure for the default company.
This script demonstrates that the vertex-ar-default company now uses a simplified path structure
without the redundant company slug and with shortened folder name.
"""

import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.settings import settings
except ImportError:
    # Mock settings if not available
    class MockSettings:
        STORAGE_ROOT = Path("storage")
    settings = MockSettings()

from app.services.folder_service import FolderService

def test_default_company_path_structure():
    """Test the new path structure for the default company."""
    print("Testing new path structure for default company...")

    # Create folder service
    folder_service = FolderService(settings.STORAGE_ROOT)

    # Simulate the default company
    default_company = {
        "id": "vertex-ar-default",
        "name": "Vertex AR",
        "storage_type": "local_disk",
        "storage_folder_path": "content"
    }

    # Test company identification
    is_default = folder_service.is_default_company(default_company)
    print(f"Is default company: {is_default}")

    # Test effective company slug
    effective_slug = folder_service.get_effective_company_slug(default_company)
    print(f"Effective company slug: '{effective_slug}' (empty means no redundant path segment)")

    # Test path building
    content_type = "portraits"
    order_id = "5f1e8cdb-ffa1-43d2-bf2d-c3d642a42562"

    # Build full path
    full_path = folder_service.build_order_path(default_company, content_type, order_id, "Image")
    print(f"Full path: {full_path}")

    # Build relative path
    relative_path = folder_service.build_relative_path(
        default_company, content_type, order_id, "test.jpg", "Image"
    )
    print(f"Relative path: {relative_path}")

    # Expected structure should be:
    # content/portraits/5f1e8cdb-ffa1-43d2-bf2d-c3d642a42562/Image/test.jpg
    # (without the vertex-ar-default segment and with shortened folder name)

    expected_parts = ["content", "portraits", order_id, "Image", "test.jpg"]
    expected_relative = "/".join(expected_parts)

    print(f"\nExpected relative path: {expected_relative}")
    print(f"Actual relative path:   {relative_path}")
    print(f"Paths match: {relative_path == expected_relative}")

    # Compare with a non-default company
    print("\n--- Comparison with non-default company ---")
    regular_company = {
        "id": "some-company-id",
        "name": "Some Company",
        "storage_type": "local_disk",
        "storage_folder_path": "content"
    }

    regular_relative_path = folder_service.build_relative_path(
        regular_company, content_type, order_id, "test.jpg", "Image"
    )
    print(f"Regular company path: {regular_relative_path}")

    # Regular company should still include the company slug
    expected_regular_parts = ["content", "some-company-id", "portraits", order_id, "Image", "test.jpg"]
    expected_regular = "/".join(expected_regular_parts)

    print(f"Expected regular path: {expected_regular}")
    print(f"Paths match: {regular_relative_path == expected_regular}")

if __name__ == "__main__":
    test_default_company_path_structure()
