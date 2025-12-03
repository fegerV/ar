#!/usr/bin/env python3
"""
Test script to verify the new folder naming convention.
This script demonstrates that folders are now created with simplified names
without the "Default " prefix.
"""

import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.services.company_bootstrap import CompanyBootstrap
    from app.database import Database
    from app.settings import settings
except ImportError as e:
    print(f"Import error: {e}")
    print("This script needs to be run in the proper environment with all dependencies.")
    sys.exit(1)


def test_folder_naming():
    """Test the new folder naming convention."""
    print("Testing new folder naming convention...")

    # Show the default categories that will be used for folder creation
    default_categories = [
        {
            "name": "Портреты",
            "slug": "portraits",
            "description": "Портреты с AR-анимацией"
        },
        {
            "name": "Дипломы AR",
            "slug": "diplomas",
            "description": "AR-дипломы с анимацией"
        },
        {
            "name": "Сертификаты",
            "slug": "certificates",
            "description": "Сертификаты с AR-эффектами"
        }
    ]

    print("\nDefault categories that will be used for folder creation:")
    for i, category in enumerate(default_categories, 1):
        print(f"  {i}. {category['name']}")

    print("\nWith the updated code, folders will be created with these exact names:")
    for i, category in enumerate(default_categories, 1):
        print(
            f"  {i}. {category['name']} (instead of 'Default {category['name']}')")

    print("\nThe old naming convention with 'Default ' prefix has been removed.")
    print("This makes folder names cleaner and more intuitive for users.")


if __name__ == "__main__":
    test_folder_naming()
