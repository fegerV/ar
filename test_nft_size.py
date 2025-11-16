#!/usr/bin/env python3
"""
Test script to verify NFT marker size display functionality.
"""
import requests
import tempfile
import os
from pathlib import Path

def create_test_video():
    """Create a small test video file."""
    # Create a simple test file (this would normally be a real video)
    test_content = b"FAKE_VIDEO_CONTENT_FOR_TESTING" * 1000  # ~37KB
    return test_content

def test_video_upload_with_size():
    """Test video upload API with file size calculation."""
    base_url = "http://localhost:8000"
    
    # First, login as admin
    session = requests.Session()
    
    # Login
    login_data = {
        "username": "superar",
        "password": "ffE48f0ns@HQ"
    }
    
    try:
        response = session.post(f"{base_url}/admin/login", data=login_data, allow_redirects=False)
        print(f"Login response status: {response.status_code}")
        
        if response.status_code != 302:
            print("Login failed")
            return False
            
        # Create test video
        video_content = create_test_video()
        
        # Create test client and portrait first
        client_data = {
            "phone": "+79998887766",
            "name": "Test Client for Size"
        }
        
        client_response = session.post(f"{base_url}/clients", json=client_data)
        if client_response.status_code == 200:
            client_id = client_response.json()["id"]
            print(f"Created client: {client_id}")
        else:
            print("Failed to create client")
            return False
        
        # Create portrait
        portrait_data = {
            "client_id": client_id,
            "image_path": "/test/path.jpg",
            "marker_fset": "test_fset",
            "marker_fset3": "test_fset3", 
            "marker_iset": "test_iset",
            "permanent_link": "test-size-link"
        }
        
        portrait_response = session.post(f"{base_url}/portraits", json=portrait_data)
        if portrait_response.status_code == 200:
            portrait_id = portrait_response.json()["id"]
            print(f"Created portrait: {portrait_id}")
        else:
            print("Failed to create portrait")
            return False
        
        # Upload video
        files = {
            "video": ("test_video.mp4", video_content, "video/mp4")
        }
        data = {
            "portrait_id": portrait_id,
            "description": "Test video with size calculation",
            "is_active": "true"
        }
        
        upload_response = session.post(
            f"{base_url}/portraits/{portrait_id}/videos",
            files=files,
            data=data
        )
        
        print(f"Video upload response status: {upload_response.status_code}")
        
        if upload_response.status_code == 201:
            video_data = upload_response.json()
            print(f"Video created: {video_data}")
            print(f"File size in response: {video_data.get('file_size_mb')} MB")
            
            # Test getting video details
            video_id = video_data["id"]
            video_detail_response = session.get(f"{base_url}/videos/{video_id}")
            if video_detail_response.status_code == 200:
                video_detail = video_detail_response.json()
                print(f"Video detail file size: {video_detail.get('file_size_mb')} MB")
            
            # Test listing videos for portrait
            list_response = session.get(f"{base_url}/videos/portrait/{portrait_id}")
            if list_response.status_code == 200:
                videos = list_response.json()
                print(f"Listed {len(videos)} videos")
                for video in videos:
                    print(f"  - {video.get('description')}: {video.get('file_size_mb')} MB")
            
            return True
        else:
            print(f"Upload failed: {upload_response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("Could not connect to server. Make sure the app is running on localhost:8000")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing NFT marker size functionality...")
    success = test_video_upload_with_size()
    if success:
        print("✅ Test completed successfully!")
    else:
        print("❌ Test failed!")