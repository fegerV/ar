"""
Remote storage integration for backups.
Supports Yandex Disk and Google Drive.
"""
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

from logging_setup import get_logger

logger = get_logger(__name__)


class RemoteStorage(ABC):
    """Base class for remote storage providers."""
    
    @abstractmethod
    def upload_file(self, local_path: Path, remote_path: str) -> Dict[str, Any]:
        """Upload a file to remote storage."""
        pass
    
    @abstractmethod
    def download_file(self, remote_path: str, local_path: Path) -> Dict[str, Any]:
        """Download a file from remote storage."""
        pass
    
    @abstractmethod
    def list_files(self, remote_dir: str = "") -> List[Dict[str, Any]]:
        """List files in remote storage."""
        pass
    
    @abstractmethod
    def delete_file(self, remote_path: str) -> Dict[str, Any]:
        """Delete a file from remote storage."""
        pass
    
    @abstractmethod
    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage quota and usage information."""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test if connection to remote storage is working."""
        pass


class YandexDiskStorage(RemoteStorage):
    """Yandex Disk storage implementation."""
    
    BASE_URL = "https://cloud-api.yandex.net/v1/disk"
    
    def __init__(self, oauth_token: str):
        """
        Initialize Yandex Disk storage.
        
        Args:
            oauth_token: OAuth token for Yandex Disk API
        """
        self.oauth_token = oauth_token
        self.headers = {
            "Authorization": f"OAuth {oauth_token}",
            "Accept": "application/json"
        }
    
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
    
    def test_connection(self) -> bool:
        """Test Yandex Disk connection."""
        try:
            response = self._make_request("GET", "/")
            return response.status_code == 200
        except Exception as e:
            logger.error("Yandex Disk connection test failed", error=str(e))
            return False
    
    def get_storage_info(self) -> Dict[str, Any]:
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
    
    def upload_file(self, local_path: Path, remote_path: str) -> Dict[str, Any]:
        """Upload file to Yandex Disk."""
        try:
            # Get upload URL
            response = self._make_request(
                "GET",
                "/resources/upload",
                params={"path": remote_path, "overwrite": "true"}
            )
            upload_url = response.json()["href"]
            
            # Upload file
            with open(local_path, "rb") as f:
                upload_response = requests.put(upload_url, files={"file": f})
                upload_response.raise_for_status()
            
            logger.info(
                "File uploaded to Yandex Disk",
                local_path=str(local_path),
                remote_path=remote_path
            )
            
            return {
                "success": True,
                "remote_path": remote_path,
                "size": local_path.stat().st_size
            }
            
        except Exception as e:
            logger.error(
                "Failed to upload file to Yandex Disk",
                error=str(e),
                local_path=str(local_path)
            )
            return {"success": False, "error": str(e)}
    
    def download_file(self, remote_path: str, local_path: Path) -> Dict[str, Any]:
        """Download file from Yandex Disk."""
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
            
            # Save file
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(download_response.content)
            
            logger.info(
                "File downloaded from Yandex Disk",
                remote_path=remote_path,
                local_path=str(local_path)
            )
            
            return {
                "success": True,
                "local_path": str(local_path),
                "size": local_path.stat().st_size
            }
            
        except Exception as e:
            logger.error(
                "Failed to download file from Yandex Disk",
                error=str(e),
                remote_path=remote_path
            )
            return {"success": False, "error": str(e)}
    
    def list_files(self, remote_dir: str = "disk:/") -> List[Dict[str, Any]]:
        """List files in Yandex Disk directory."""
        try:
            response = self._make_request(
                "GET",
                "/resources",
                params={"path": remote_dir, "limit": 1000}
            )
            data = response.json()
            
            files = []
            for item in data.get("_embedded", {}).get("items", []):
                if item.get("type") == "file":
                    files.append({
                        "name": item.get("name"),
                        "path": item.get("path"),
                        "size": item.get("size", 0),
                        "created": item.get("created"),
                        "modified": item.get("modified"),
                        "mime_type": item.get("mime_type")
                    })
            
            return files
            
        except Exception as e:
            logger.error("Failed to list Yandex Disk files", error=str(e))
            return []
    
    def delete_file(self, remote_path: str) -> Dict[str, Any]:
        """Delete file from Yandex Disk."""
        try:
            self._make_request(
                "DELETE",
                "/resources",
                params={"path": remote_path, "permanently": "false"}
            )
            
            logger.info("File deleted from Yandex Disk", remote_path=remote_path)
            
            return {"success": True, "remote_path": remote_path}
            
        except Exception as e:
            logger.error(
                "Failed to delete file from Yandex Disk",
                error=str(e),
                remote_path=remote_path
            )
            return {"success": False, "error": str(e)}


class GoogleDriveStorage(RemoteStorage):
    """Google Drive storage implementation."""
    
    BASE_URL = "https://www.googleapis.com/drive/v3"
    UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
    
    def __init__(self, credentials: Dict[str, Any]):
        """
        Initialize Google Drive storage.
        
        Args:
            credentials: Google API credentials (can be OAuth token or service account)
        """
        self.credentials = credentials
        self.access_token = credentials.get("access_token")
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        self.folder_id = credentials.get("folder_id")  # Optional: specific folder for backups
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to Google Drive API."""
        url = f"{self.BASE_URL}{endpoint}"
        kwargs.setdefault("headers", self.headers)
        
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error("Google Drive API request failed", error=str(e), endpoint=endpoint)
            raise
    
    def test_connection(self) -> bool:
        """Test Google Drive connection."""
        try:
            response = self._make_request("GET", "/about", params={"fields": "user"})
            return response.status_code == 200
        except Exception as e:
            logger.error("Google Drive connection test failed", error=str(e))
            return False
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get Google Drive storage information."""
        try:
            response = self._make_request(
                "GET",
                "/about",
                params={"fields": "storageQuota"}
            )
            data = response.json()
            quota = data.get("storageQuota", {})
            
            total = int(quota.get("limit", 0))
            usage = int(quota.get("usage", 0))
            
            return {
                "success": True,
                "provider": "google_drive",
                "total_space": total,
                "used_space": usage,
                "available_space": total - usage,
                "trash_size": int(quota.get("usageInDriveTrash", 0))
            }
        except Exception as e:
            logger.error("Failed to get Google Drive storage info", error=str(e))
            return {"success": False, "error": str(e)}
    
    def upload_file(self, local_path: Path, remote_path: str) -> Dict[str, Any]:
        """Upload file to Google Drive."""
        try:
            # Prepare file metadata
            metadata = {
                "name": Path(remote_path).name,
            }
            
            if self.folder_id:
                metadata["parents"] = [self.folder_id]
            
            # Upload file using multipart
            with open(local_path, "rb") as f:
                files = {
                    "data": ("metadata", json.dumps(metadata), "application/json"),
                    "file": (metadata["name"], f, "application/octet-stream")
                }
                
                response = requests.post(
                    f"{self.UPLOAD_URL}?uploadType=multipart",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    files=files
                )
                response.raise_for_status()
            
            file_data = response.json()
            
            logger.info(
                "File uploaded to Google Drive",
                local_path=str(local_path),
                file_id=file_data.get("id")
            )
            
            return {
                "success": True,
                "remote_path": remote_path,
                "file_id": file_data.get("id"),
                "size": local_path.stat().st_size
            }
            
        except Exception as e:
            logger.error(
                "Failed to upload file to Google Drive",
                error=str(e),
                local_path=str(local_path)
            )
            return {"success": False, "error": str(e)}
    
    def download_file(self, remote_path: str, local_path: Path) -> Dict[str, Any]:
        """Download file from Google Drive."""
        try:
            # Find file by name
            file_id = self._find_file_by_name(Path(remote_path).name)
            
            if not file_id:
                return {"success": False, "error": "File not found"}
            
            # Download file
            response = self._make_request("GET", f"/files/{file_id}", params={"alt": "media"})
            
            # Save file
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(response.content)
            
            logger.info(
                "File downloaded from Google Drive",
                file_id=file_id,
                local_path=str(local_path)
            )
            
            return {
                "success": True,
                "local_path": str(local_path),
                "size": local_path.stat().st_size
            }
            
        except Exception as e:
            logger.error(
                "Failed to download file from Google Drive",
                error=str(e),
                remote_path=remote_path
            )
            return {"success": False, "error": str(e)}
    
    def _find_file_by_name(self, filename: str) -> Optional[str]:
        """Find file ID by name."""
        try:
            query = f"name='{filename}' and trashed=false"
            if self.folder_id:
                query += f" and '{self.folder_id}' in parents"
            
            response = self._make_request(
                "GET",
                "/files",
                params={
                    "q": query,
                    "fields": "files(id, name)"
                }
            )
            
            files = response.json().get("files", [])
            return files[0]["id"] if files else None
            
        except Exception as e:
            logger.error("Failed to find file in Google Drive", error=str(e), filename=filename)
            return None
    
    def list_files(self, remote_dir: str = "") -> List[Dict[str, Any]]:
        """List files in Google Drive."""
        try:
            query = "trashed=false and mimeType!='application/vnd.google-apps.folder'"
            if self.folder_id:
                query += f" and '{self.folder_id}' in parents"
            
            response = self._make_request(
                "GET",
                "/files",
                params={
                    "q": query,
                    "fields": "files(id, name, size, createdTime, modifiedTime, mimeType)",
                    "pageSize": 1000
                }
            )
            
            files = []
            for item in response.json().get("files", []):
                files.append({
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "size": int(item.get("size", 0)),
                    "created": item.get("createdTime"),
                    "modified": item.get("modifiedTime"),
                    "mime_type": item.get("mimeType")
                })
            
            return files
            
        except Exception as e:
            logger.error("Failed to list Google Drive files", error=str(e))
            return []
    
    def delete_file(self, remote_path: str) -> Dict[str, Any]:
        """Delete file from Google Drive."""
        try:
            # Find file by name
            file_id = self._find_file_by_name(Path(remote_path).name)
            
            if not file_id:
                return {"success": False, "error": "File not found"}
            
            self._make_request("DELETE", f"/files/{file_id}")
            
            logger.info("File deleted from Google Drive", file_id=file_id)
            
            return {"success": True, "remote_path": remote_path}
            
        except Exception as e:
            logger.error(
                "Failed to delete file from Google Drive",
                error=str(e),
                remote_path=remote_path
            )
            return {"success": False, "error": str(e)}


class RemoteStorageManager:
    """Manager for remote storage operations."""
    
    def __init__(self, config_path: Path):
        """
        Initialize remote storage manager.
        
        Args:
            config_path: Path to configuration file with storage credentials
        """
        self.config_path = Path(config_path)
        self.storages: Dict[str, RemoteStorage] = {}
        self._load_config()
    
    def _load_config(self):
        """Load storage configuration from file."""
        if not self.config_path.exists():
            logger.warning("Remote storage config not found", path=str(self.config_path))
            return
        
        try:
            with open(self.config_path) as f:
                config = json.load(f)
            
            # Initialize Yandex Disk if configured
            if config.get("yandex_disk", {}).get("enabled"):
                token = config["yandex_disk"].get("oauth_token")
                if token:
                    self.storages["yandex_disk"] = YandexDiskStorage(token)
                    logger.info("Yandex Disk storage initialized")
            
            # Initialize Google Drive if configured
            if config.get("google_drive", {}).get("enabled"):
                credentials = config["google_drive"].get("credentials")
                if credentials:
                    self.storages["google_drive"] = GoogleDriveStorage(credentials)
                    logger.info("Google Drive storage initialized")
                    
        except Exception as e:
            logger.error("Failed to load remote storage config", error=str(e))
    
    def save_config(self, config: Dict[str, Any]):
        """Save storage configuration to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=2)
            
            # Reload configuration
            self._load_config()
            
            logger.info("Remote storage config saved")
            
        except Exception as e:
            logger.error("Failed to save remote storage config", error=str(e))
            raise
    
    def get_storage(self, provider: str) -> Optional[RemoteStorage]:
        """Get storage instance by provider name."""
        return self.storages.get(provider)
    
    def list_providers(self) -> List[str]:
        """List available storage providers."""
        return list(self.storages.keys())
    
    def test_all_connections(self) -> Dict[str, bool]:
        """Test connections to all configured storages."""
        results = {}
        for provider, storage in self.storages.items():
            results[provider] = storage.test_connection()
        return results


def get_remote_storage_manager(config_path: Optional[Path] = None) -> RemoteStorageManager:
    """Get remote storage manager instance."""
    if config_path is None:
        config_path = Path(os.getenv("REMOTE_STORAGE_CONFIG", "config/remote_storage.json"))
    
    return RemoteStorageManager(config_path)
