"""
Yandex Disk storage adapter for Vertex AR.
Stores photos, videos, previews, and NFT files on Yandex Disk.
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional
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
            logger.info("Created directory on Yandex Disk", directory=dir_path)
        except requests.exceptions.HTTPError as e:
            # Directory might already exist
            if e.response.status_code != 409:  # 409 = Conflict (already exists)
                raise
            logger.debug("Directory already exists on Yandex Disk", directory=dir_path)
    
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
    
    def ensure_directory(self, dir_path: str) -> bool:
        """
        Public method to ensure a directory exists on Yandex Disk.
        
        Args:
            dir_path: Directory path relative to base_path
            
        Returns:
            True if directory exists or was created, False on error
        """
        try:
            full_path = self._get_full_path(dir_path)
            self._ensure_directory_exists(full_path)
            return True
        except Exception as e:
            logger.error(
                "Failed to ensure directory exists",
                error=str(e),
                dir_path=dir_path
            )
            return False
    
    def ensure_path(self, path: str) -> bool:
        """
        Public method to ensure all directories in a path exist on Yandex Disk.
        Creates parent directories recursively if needed.
        
        Args:
            path: Full path with nested directories (e.g., 'folder/subfolder/file.txt')
            
        Returns:
            True if all directories exist or were created, False on error
        """
        try:
            # Split path and build directory hierarchy
            parts = path.split('/')
            # Remove filename if present (if last part has extension)
            if '.' in parts[-1]:
                parts = parts[:-1]
            
            # Create each directory level
            current_path = ""
            for part in parts:
                if not part:  # Skip empty parts from double slashes
                    continue
                current_path = f"{current_path}/{part}" if current_path else part
                full_path = self._get_full_path(current_path)
                self._ensure_directory_exists(full_path)
            
            logger.info("Ensured path exists on Yandex Disk", path=path)
            return True
        except Exception as e:
            logger.error(
                "Failed to ensure path exists",
                error=str(e),
                path=path
            )
            return False
    
    def ensure_order_structure(self, folder_id: str, content_type: str, order_id: str) -> Dict[str, bool]:
        """
        Create the required folder structure for an order on Yandex Disk.
        Structure: {folder_id}/{content_type}/{order_id}/[Image|QR|nft_markers|nft_cache]
        
        Args:
            folder_id: Base folder ID for the company
            content_type: Content type (e.g., 'portraits', 'videos')
            order_id: Unique order identifier
            
        Returns:
            Dict with success status for each subdirectory
        """
        subdirs = ['Image', 'QR', 'nft_markers', 'nft_cache']
        results = {}
        
        try:
            # Create base order path
            base_path = f"{folder_id}/{content_type}/{order_id}"
            self.ensure_path(base_path)
            
            # Create subdirectories
            for subdir in subdirs:
                subdir_path = f"{base_path}/{subdir}"
                success = self.ensure_path(subdir_path)
                results[subdir] = success
                
                if success:
                    logger.info(
                        "Created order subdirectory",
                        folder_id=folder_id,
                        content_type=content_type,
                        order_id=order_id,
                        subdir=subdir
                    )
                else:
                    logger.warning(
                        "Failed to create order subdirectory",
                        folder_id=folder_id,
                        content_type=content_type,
                        order_id=order_id,
                        subdir=subdir
                    )
            
            return results
            
        except Exception as e:
            logger.error(
                "Failed to create order structure",
                error=str(e),
                folder_id=folder_id,
                content_type=content_type,
                order_id=order_id
            )
            return {subdir: False for subdir in subdirs}
    
    def list_directories(self, path: str = "", limit: int = 100, offset: int = 0) -> Dict[str, any]:
        """
        List directories at the given path on Yandex Disk.
        
        Args:
            path: Path to list directories from (relative to base_path, empty for root)
            limit: Maximum number of items to return
            offset: Number of items to skip (for pagination)
            
        Returns:
            Dict with 'items' (list of directory info), 'total' count, 'has_more' flag
        """
        try:
            # Build full path
            if path:
                full_path = self._get_full_path(path)
            else:
                full_path = self.base_path
            
            # Request directory listing from Yandex Disk API
            response = self._make_request(
                "GET",
                "/resources",
                params={
                    "path": full_path,
                    "limit": limit,
                    "offset": offset,
                    "fields": "name,path,type,_embedded.items.name,_embedded.items.path,_embedded.items.type,_embedded.total,_embedded.limit,_embedded.offset"
                }
            )
            
            data = response.json()
            embedded = data.get("_embedded", {})
            all_items = embedded.get("items", [])
            
            # Filter only directories
            directories = [
                {
                    "name": item["name"],
                    "path": item["path"],
                    "type": item["type"]
                }
                for item in all_items
                if item.get("type") == "dir"
            ]
            
            total = len(directories)
            has_more = (offset + limit) < total
            
            logger.info(
                "Listed Yandex Disk directories",
                path=full_path,
                count=len(directories),
                offset=offset,
                limit=limit
            )
            
            return {
                "items": directories,
                "total": total,
                "has_more": has_more
            }
            
        except Exception as e:
            logger.error(
                "Failed to list Yandex Disk directories",
                error=str(e),
                path=path
            )
            raise Exception(f"Failed to list directories: {str(e)}")