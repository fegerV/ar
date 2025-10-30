#!/usr/bin/env python3
"""
Test script to verify UI improvements in admin panel and login page
"""
from pathlib import Path
import re


def test_admin_template():
    """Test admin.html for UI improvements"""
    admin_path = Path("vertex-ar/templates/admin.html")
    content = admin_path.read_text()
    
    tests = {
        "Has viewport meta tag": 'name="viewport"' in content,
        "Has dark mode support": 'data-theme="dark"' in content,
        "Has CSS variables": ':root {' in content and '--primary-color' in content,
        "Has ARIA labels": 'aria-label' in content,
        "Has ARIA live regions": 'aria-live' in content,
        "Has progress bar": 'progress-bar' in content,
        "Has toast notifications": 'showToast' in content,
        "Has file validation": 'MAX_FILE_SIZE' in content and 'formatFileSize' in content,
        "Has theme toggle": 'themeToggle' in content and 'setTheme' in content,
        "Has responsive grids": 'grid-template-columns: repeat(auto-fit' in content,
        "Has media queries": '@media' in content,
        "Has keyboard support": 'keydown' in content,
        "Has loading states": 'loading' in content,
        "Has network status": 'offline' in content and 'online' in content,
        "Has semantic HTML": '<header' in content and '<section' in content,
        "Has proper form attributes": 'aria-describedby' in content,
        "Has smooth transitions": 'transition:' in content,
        "Has hover effects": ':hover' in content,
        "Has print styles": '@media print' in content,
    }
    
    print("🧪 Testing admin.html improvements:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in tests.items():
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print()
    
    return failed == 0


def test_login_template():
    """Test login.html for UI improvements"""
    login_path = Path("vertex-ar/templates/login.html")
    content = login_path.read_text()
    
    tests = {
        "Has viewport meta tag": 'name="viewport"' in content,
        "Has dark mode support": 'data-theme="dark"' in content,
        "Has CSS variables": ':root {' in content and '--primary-color' in content,
        "Has ARIA labels": 'aria-label' in content,
        "Has password toggle": 'passwordToggle' in content,
        "Has remember me": 'rememberMe' in content,
        "Has form validation": 'showError' in content,
        "Has theme toggle": 'themeToggle' in content and 'setTheme' in content,
        "Has loading states": 'loading' in content,
        "Has network status": 'offline' in content and 'online' in content,
        "Has smooth animations": '@keyframes' in content,
        "Has gradient background": 'linear-gradient' in content,
        "Has responsive design": '@media' in content,
        "Has auto-focus": '.focus()' in content,
        "Has keyboard shortcuts": 'keydown' in content,
        "Has proper form attributes": 'autocomplete' in content,
    }
    
    print("🧪 Testing login.html improvements:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in tests.items():
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print()
    
    return failed == 0


def analyze_improvements():
    """Analyze and report on specific improvements"""
    admin_path = Path("vertex-ar/templates/admin.html")
    login_path = Path("vertex-ar/templates/login.html")
    
    admin_content = admin_path.read_text()
    login_content = login_path.read_text()
    
    print("📊 Improvement Analysis:")
    print("=" * 60)
    
    # Count specific features
    admin_aria_labels = len(re.findall(r'aria-label=', admin_content))
    admin_media_queries = len(re.findall(r'@media', admin_content))
    admin_css_vars = len(re.findall(r'--[\w-]+:', admin_content))
    
    login_aria_labels = len(re.findall(r'aria-label=', login_content))
    login_media_queries = len(re.findall(r'@media', login_content))
    login_css_vars = len(re.findall(r'--[\w-]+:', login_content))
    
    print(f"📄 Admin Panel:")
    print(f"   • {admin_aria_labels} ARIA labels for accessibility")
    print(f"   • {admin_media_queries} media queries for responsiveness")
    print(f"   • {admin_css_vars} CSS variables for theming")
    print(f"   • {len(admin_content)} characters")
    print()
    
    print(f"📄 Login Page:")
    print(f"   • {login_aria_labels} ARIA labels for accessibility")
    print(f"   • {login_media_queries} media queries for responsiveness")
    print(f"   • {login_css_vars} CSS variables for theming")
    print(f"   • {len(login_content)} characters")
    print()
    
    print("✨ Key Features Added:")
    print("   • Dark mode with localStorage persistence")
    print("   • Toast notification system")
    print("   • File preview and validation")
    print("   • Progress bars for uploads")
    print("   • Network status monitoring")
    print("   • Keyboard accessibility")
    print("   • Mobile-responsive design")
    print("   • Print-friendly styles")
    print("=" * 60)


if __name__ == "__main__":
    print("🎨 UI/UX Improvements Verification")
    print("=" * 60)
    print()
    
    admin_passed = test_admin_template()
    login_passed = test_login_template()
    
    analyze_improvements()
    
    print()
    if admin_passed and login_passed:
        print("✅ All UI/UX improvements verified successfully!")
        exit(0)
    else:
        print("⚠️  Some tests failed. Please review the results above.")
        exit(1)
