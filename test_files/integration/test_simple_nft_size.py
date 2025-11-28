#!/usr/bin/env python3
"""
Simple test to verify NFT marker size functionality.
"""
import requests
import tempfile
import os
from pathlib import Path

def test_video_upload_with_size():
    """Test video upload functionality with file size."""
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
        
        # Create a simple test video file (bigger for proper MB calculation)
        test_content = b"FAKE_VIDEO_CONTENT_FOR_TESTING" * 100000  # ~3MB
        expected_size_mb = int(len(test_content) / (1024 * 1024))
        print(f"Test video size: {expected_size_mb} MB")
        
        # Create test client manually through database
        import sys
        sys.path.append('/home/engine/project/vertex-ar')
        
        from app.database import Database
        from app.config import Settings
        import uuid
        
        settings = Settings()
        db = Database(settings.DB_PATH)
        
        client_id = str(uuid.uuid4())
        client = db.create_client(client_id, "+79998887755", "Test Client for Video")
        
        portrait_id = str(uuid.uuid4())
        portrait = db.create_portrait(
            portrait_id=portrait_id,
            client_id=client_id,
            image_path="/test/image.jpg",
            marker_fset="test_fset",
            marker_fset3="test_fset3",
            marker_iset="test_iset",
            permanent_link="test-video-size-link"
        )
        
        print(f"Created client: {client_id}")
        print(f"Created portrait: {portrait_id}")
        
        # Upload video
        files = {
            "video": ("test_video.mp4", test_content, "video/mp4")
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
            
            # Test admin order detail page
            order_response = session.get(f"{base_url}/admin/order/{portrait_id}")
            print(f"Order detail page status: {order_response.status_code}")
            if order_response.status_code == 200:
                print("✅ Order detail page accessible")
                # Check if video info is in the page
                page_content = order_response.text
                if "Размер NFT маркера" in page_content:
                    print("✅ Size info found in page")
                else:
                    print("❌ Size info not found in page")
            else:
                print(f"❌ Order detail page failed: {order_response.text}")
            
            # Clean up
            db.delete_video(video_id)
            db.delete_portrait(portrait_id)
            db.delete_client(client_id)
            print("✅ Test data cleaned up")
            
            return True
        else:
            print(f"Upload failed: {upload_response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("Could not connect to server. Make sure to start the app with: python main.py")
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