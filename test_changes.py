#!/usr/bin/env python3
"""
Test script to verify the changes for portrait preview display and order numbers.
"""

import sys
from pathlib import Path


def test_template_changes():
    """Test that template files have been updated correctly."""
    print("\nTesting template changes...")
    
    # Check admin_clients.html
    clients_template = Path("vertex-ar/templates/admin_clients.html")
    if not clients_template.exists():
        print("  ✗ admin_clients.html not found")
        return False
    
    content = clients_template.read_text()
    
    # Check for include_preview parameter in fetch call
    if 'include_preview=true' in content:
        print("  ✓ admin_clients.html includes include_preview parameter")
    else:
        print("  ✗ admin_clients.html missing include_preview parameter")
        return False
    
    # Check for image preview display
    if 'image_preview_data' in content:
        print("  ✓ admin_clients.html uses image_preview_data")
    else:
        print("  ✗ admin_clients.html missing image_preview_data usage")
        return False
    
    # Check for img tag with portrait preview
    if '<img src="${previewSrc}" class="portrait-preview"' in content:
        print("  ✓ admin_clients.html displays portrait preview images")
    else:
        print("  ✗ admin_clients.html missing portrait preview image display")
        return False
    
    # Check admin_dashboard.html
    dashboard_template = Path("vertex-ar/templates/admin_dashboard.html")
    if not dashboard_template.exists():
        print("  ✗ admin_dashboard.html not found")
        return False
    
    content = dashboard_template.read_text()
    
    # Check for optimized order number logic
    if 'orderPositionMap' in content:
        print("  ✓ admin_dashboard.html has optimized order number logic")
    else:
        print("  ✗ admin_dashboard.html missing optimized order number logic")
        return False
    
    # Check that sorting is done once
    if 'sortedRecords.slice(startIndex, endIndex)' in content:
        print("  ✓ admin_dashboard.html sorts records before slicing")
    else:
        print("  ✗ admin_dashboard.html doesn't sort before slicing")
        return False
    
    return True


def test_api_changes():
    """Test that API files have been updated correctly."""
    print("\nTesting API changes...")
    
    portraits_api = Path("vertex-ar/app/api/portraits.py")
    if not portraits_api.exists():
        print("  ✗ portraits.py not found")
        return False
    
    content = portraits_api.read_text()
    
    # Check for include_preview parameter
    if 'include_preview: bool = False' in content:
        print("  ✓ portraits.py has include_preview parameter")
    else:
        print("  ✗ portraits.py missing include_preview parameter")
        return False
    
    # Check for preview data loading logic
    if 'image_preview_data' in content and 'data:image/webp;base64' in content:
        print("  ✓ portraits.py loads and formats preview data")
    else:
        print("  ✗ portraits.py missing preview data loading logic")
        return False
    
    return True


def test_main_app_changes():
    """Test that main.py has app instance exported."""
    print("\nTesting main.py changes...")
    
    main_file = Path("vertex-ar/app/main.py")
    if not main_file.exists():
        print("  ✗ main.py not found")
        return False
    
    content = main_file.read_text()
    
    # Check for app instance
    if 'app = create_app()' in content:
        print("  ✓ main.py exports app instance")
    else:
        print("  ✗ main.py missing app instance export")
        return False
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing changes for portrait preview and order numbers")
    print("=" * 60)
    
    results = []
    
    results.append(("Template Changes", test_template_changes()))
    results.append(("API Changes", test_api_changes()))
    results.append(("Main App", test_main_app_changes()))
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
