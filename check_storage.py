#!/usr/bin/env python3
"""
Storage Connection Check Script for Vertex AR

This script tests the connection to configured storage backend
and provides diagnostic information.
"""
import os
import sys
from pathlib import Path

# Add vertex-ar to path
sys.path.insert(0, str(Path(__file__).parent / "vertex-ar"))

from dotenv import load_dotenv
load_dotenv()

def main():
    """Check storage configuration and connectivity"""
    print("=" * 60)
    print("Vertex AR - Storage Connection Check")
    print("=" * 60)
    print()
    
    # Read configuration
    storage_type = os.getenv("STORAGE_TYPE", "local")
    print(f"📦 Storage Type: {storage_type}")
    print()
    
    if storage_type == "local":
        print("📁 Local Storage Configuration:")
        storage_path = os.getenv("STORAGE_PATH", "./storage")
        bucket_name = os.getenv("MINIO_BUCKET", "vertex-art-bucket")
        print(f"   Path: {storage_path}")
        print(f"   Bucket: {bucket_name}")
        print()
        
        # Try to create storage
        try:
            from storage_adapter import LocalStorageAdapter
            storage = LocalStorageAdapter()
            print("✅ Local storage initialized successfully")
            print(f"   Storage path: {storage.storage_path}")
            
            # Test write
            test_content = b"Connection test"
            result = storage.upload_file(test_content, "test-connection.txt", "text/plain")
            if result:
                print("✅ Test file upload successful")
                
                # Test read
                downloaded = storage.download_file("test-connection.txt")
                if downloaded == test_content:
                    print("✅ Test file download successful")
                else:
                    print("❌ Test file download failed - content mismatch")
                
                # Cleanup
                storage.delete_file("test-connection.txt")
                print("✅ Test file cleanup successful")
            else:
                print("❌ Test file upload failed")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return 1
            
    elif storage_type == "minio":
        print("☁️  MinIO Storage Configuration:")
        endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        bucket = os.getenv("MINIO_BUCKET", "vertex-art-bucket")
        secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        public_url = os.getenv("MINIO_PUBLIC_URL", "")
        
        print(f"   Endpoint: {endpoint}")
        print(f"   Bucket: {bucket}")
        print(f"   Secure: {secure}")
        if public_url:
            print(f"   Public URL: {public_url}")
        print()
        
        # Check if MinIO is reachable
        print("🔍 Checking MinIO connectivity...")
        import socket
        try:
            host, port = endpoint.split(":")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, int(port)))
            sock.close()
            
            if result == 0:
                print(f"✅ MinIO endpoint is reachable at {endpoint}")
            else:
                print(f"❌ Cannot connect to MinIO at {endpoint}")
                print(f"   Make sure MinIO server is running")
                return 1
                
        except Exception as e:
            print(f"❌ Error checking connectivity: {e}")
            return 1
        
        # Try to initialize MinIO storage
        try:
            from storage_adapter import MinIOStorageAdapter
            storage = MinIOStorageAdapter()
            print("✅ MinIO storage initialized successfully")
            
            # Test write
            test_content = b"Connection test"
            result = storage.upload_file(test_content, "test-connection.txt", "text/plain")
            if result:
                print("✅ Test file upload successful")
                print(f"   URL: {result}")
                
                # Test read
                downloaded = storage.download_file("test-connection.txt")
                if downloaded == test_content:
                    print("✅ Test file download successful")
                else:
                    print("❌ Test file download failed - content mismatch")
                
                # Cleanup
                storage.delete_file("test-connection.txt")
                print("✅ Test file cleanup successful")
            else:
                print("❌ Test file upload failed")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return 1
    else:
        print(f"❌ Unknown storage type: {storage_type}")
        print(f"   Valid options: local, minio")
        return 1
    
    print()
    print("=" * 60)
    print("🎉 Storage check completed successfully!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
