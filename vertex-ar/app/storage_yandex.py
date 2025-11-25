"""
Yandex Disk storage adapter for Vertex AR.
Stores photos, videos, previews, and NFT files on Yandex Disk.
"""
import json
import os
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests

from app.storage import StorageAdapter
from logging_setup import get_logger

logger = get_logger(__name__)


class YandexDiskStorageAdapter(StorageAdapter):
    """Yandex Disk storage implementation for media files."""
    
    BASE_URL = "https://cloud-api.yandex.net/v1/disk"
    
    def __init__(self, oauth_token: str, base_path: str = "vertex-ar"):
        """
        Initialize Yandex Disk storage adapter.
        
        Args:
            oauth_token: OAuth token for Yandex Disk API
            base_path: Base directory path on Yandex Disk
        """
        self.oauth_token = oauth_token
        self.base_path = base_path.rstrip('/')
        self.headers = {
            "Authorization": f"OAuth {oauth_token}",
            "Accept": "application/json"
        }
        
        # Ensure base directory exists
        self._ensure_directory_exists(self.base_path)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to Yandex Disk API."""
        url = f"{self.BASE_URL}{endpoint}"
        kwargs.setdefault("headers", self.headers)
        
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error("Yandex Disk API request failed", error=str(e), endpoint=endpoint)
            raise
    
    def _ensure_directory_exists(self, dir_path: str):
        """Ensure directory exists on Yandex Disk."""
        try:
            self._make_request("PUT", "/resources", params={"path": dir_path})
        except requests.exceptions.HTTPError as e:
            # Directory might already exist
            if e.response.status_code != 409:  # 409 = Conflict (already exists)
                raise
    
    def _get_full_path(self, file_path: str) -> str:
        """Get full path on Yandex Disk."""
        return f"{self.base_path}/{file_path}".replace('//', '/')
    
    def _get_upload_url(self, remote_path: str) -> str:
        """Get upload URL for a file."""
        response = self._make_request(
            "GET",
            "/resources/upload",
            params={"path": remote_path, "overwrite": "true"}
        )
        return response.json()["href"]
    
    async def save_file(self, file_data: bytes, file_path: str) -> str:
        """Save file data to Yandex Disk.
        
        Args:
            file_data: Raw file data
            file_path: Destination path within storage
            
        Returns:
            Public URL to access the file
        """
        remote_path = self._get_full_path(file_path)
        
        try:
            # Get upload URL
            upload_url = self._get_upload_url(remote_path)
            
            # Upload file
            upload_response = requests.put(upload_url, data=file_data)
            upload_response.raise_for_status()
            
            logger.info(
                "File saved to Yandex Disk",
                file_path=file_path,
                remote_path=remote_path,
                size_bytes=len(file_data)
            )
            
            return self.get_public_url(file_path)
            
        except Exception as e:
            logger.error(
                "Failed to save file to Yandex Disk",
                error=str(e),
                file_path=file_path
            )
            raise Exception(f"Failed to save file to Yandex Disk: {str(e)}")
    
    async def get_file(self, file_path: str) -> bytes:
        """Get file data from Yandex Disk.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            Raw file data
        """
        remote_path = self._get_full_path(file_path)
        
        try:
            # Get download URL
            response = self._make_request(
                "GET",
                "/resources/download",
                params={"path": remote_path}
            )
            download_url = response.json()["href"]
            
            # Download file
            download_response = requests.get(download_url)
            download_response.raise_for_status()
            
            logger.info(
                "File downloaded from Yandex Disk",
                file_path=file_path,
                remote_path=remote_path,
                size_bytes=len(download_response.content)
            )
            
            return download_response.content
            
        except Exception as e:
            logger.error(
                "Failed to get file from Yandex Disk",
                error=str(e),
                file_path=file_path
            )
            raise FileNotFoundError(f"File not found on Yandex Disk: {file_path}")
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from Yandex Disk.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            True if deleted successfully, False otherwise
        """
        remote_path = self._get_full_path(file_path)
        
        try:
            self._make_request(
                "DELETE",
                "/resources",
                params={"path": remote_path, "permanently": "true"}
            )
            
            logger.info(
                "File deleted from Yandex Disk",
                file_path=file_path,
                remote_path=remote_path
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to delete file from Yandex Disk",
                error=str(e),
                file_path=file_path
            )
            return False
    
    async def file_exists(self, file_path: str) -> bool:
        """Check if file exists in Yandex Disk.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            True if file exists, False otherwise
        """
        remote_path = self._get_full_path(file_path)
        
        try:
            self._make_request("GET", "/resources", params={"path": remote_path})
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:  # Not found
                return False
            raise
        except Exception:
            return False
    
    def get_public_url(self, file_path: str) -> str:
        """Get public URL for file access.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            Public URL string
        """
        from app.config import settings
        
        # For Yandex Disk, we need to create a public link or use download URL
        # For now, return a special URL that will be handled by the API
        remote_path = self._get_full_path(file_path)
        encoded_path = quote(remote_path)
        return f"{settings.BASE_URL}/api/yandex-disk/file/{encoded_path}"
    
    def get_download_url(self, file_path: str) -> str:
        """Get direct download URL for a file."""
        remote_path = self._get_full_path(file_path)
        
        try:
            response = self._make_request(
                "GET",
                "/resources/download",
                params={"path": remote_path}
            )
            return response.json()["href"]
        except Exception as e:
            logger.error(
                "Failed to get download URL",
                error=str(e),
                file_path=file_path
            )
            raise
    
    def create_public_link(self, file_path: str) -> str:
        """Create a public link for a file."""
        remote_path = self._get_full_path(file_path)
        
        try:
            response = self._make_request(
                "PUT",
                "/resources/publish",
                params={"path": remote_path}
            )
            
            # Get public URL
            info_response = self._make_request(
                "GET",
                "/resources",
                params={"path": remote_path, "public_key": True}
            )
            
            public_url = info_response.json().get("public_url")
            if public_url:
                logger.info(
                    "Public link created",
                    file_path=file_path,
                    public_url=public_url
                )
                return public_url
            else:
                raise Exception("Failed to get public URL")
                
        except Exception as e:
            logger.error(
                "Failed to create public link",
                error=str(e),
                file_path=file_path
            )
            raise
    
    def get_storage_info(self) -> dict:
        """Get Yandex Disk storage information."""
        try:
            response = self._make_request("GET", "/")
            data = response.json()
            
            return {
                "success": True,
                "provider": "yandex_disk",
                "total_space": data.get("total_space", 0),
                "used_space": data.get("used_space", 0),
                "available_space": data.get("total_space", 0) - data.get("used_space", 0),
                "trash_size": data.get("trash_size", 0)
            }
        except Exception as e:
            logger.error("Failed to get Yandex Disk storage info", error=str(e))
            return {"success": False, "error": str(e)}
    
    def test_connection(self) -> bool:
        """Test Yandex Disk connection."""
        try:
            response = self._make_request("GET", "/")
            return response.status_code == 200
        except Exception as e:
            logger.error("Yandex Disk connection test failed", error=str(e))
            return False