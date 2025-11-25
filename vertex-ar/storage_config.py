"""
Storage configuration manager for Vertex AR.
Handles different storage types for different content types.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

from logging_setup import get_logger

logger = get_logger(__name__)


class StorageConfig:
    """Storage configuration for different content types."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize storage configuration.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path or Path("config/storage_config.json")
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load storage configuration from file."""
        if not self.config_path.exists():
            logger.info("Storage config not found, creating default", path=str(self.config_path))
            default_config = self._get_default_config()
            self._save_config(default_config)
            return default_config
        
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info("Storage config loaded", path=str(self.config_path))
            return config
        except Exception as e:
            logger.error("Failed to load storage config", error=str(e))
            return self._get_default_config()
    
    def _save_config(self, config: Dict[str, Any]):
        """Save storage configuration to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("Storage config saved", path=str(self.config_path))
        except Exception as e:
            logger.error("Failed to save storage config", error=str(e))
            raise
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default storage configuration."""
        return {
            "content_types": {
                "portraits": {
                    "storage_type": "local",
                    "yandex_disk": {
                        "enabled": False,
                        "base_path": "vertex-ar/portraits"
                    }
                },
                "videos": {
                    "storage_type": "local",
                    "yandex_disk": {
                        "enabled": False,
                        "base_path": "vertex-ar/videos"
                    }
                },
                "previews": {
                    "storage_type": "local",
                    "yandex_disk": {
                        "enabled": False,
                        "base_path": "vertex-ar/previews"
                    }
                },
                "nft_markers": {
                    "storage_type": "local",
                    "yandex_disk": {
                        "enabled": False,
                        "base_path": "vertex-ar/nft_markers"
                    }
                }
            },
            "backup_settings": {
                "auto_split_backups": True,
                "max_backup_size_mb": 500,
                "chunk_size_mb": 100,
                "compression": "gz"
            },
            "yandex_disk": {
                "oauth_token": "",
                "enabled": False
            },
            "minio": {
                "enabled": False,
                "endpoint": "",
                "access_key": "",
                "secret_key": "",
                "bucket": ""
            }
        }
    
    def get_storage_type(self, content_type: str) -> str:
        """Get storage type for content type."""
        return self.config.get("content_types", {}).get(content_type, {}).get("storage_type", "local")
    
    def set_storage_type(self, content_type: str, storage_type: str):
        """Set storage type for content type."""
        if "content_types" not in self.config:
            self.config["content_types"] = {}
        if content_type not in self.config["content_types"]:
            self.config["content_types"][content_type] = {}
        
        self.config["content_types"][content_type]["storage_type"] = storage_type
        self._save_config(self.config)
    
    def get_yandex_config(self, content_type: str) -> Dict[str, Any]:
        """Get Yandex Disk configuration for content type."""
        return self.config.get("content_types", {}).get(content_type, {}).get("yandex_disk", {})
    
    def set_yandex_config(self, content_type: str, enabled: bool, base_path: str = None):
        """Set Yandex Disk configuration for content type."""
        if "content_types" not in self.config:
            self.config["content_types"] = {}
        if content_type not in self.config["content_types"]:
            self.config["content_types"][content_type] = {}
        if "yandex_disk" not in self.config["content_types"][content_type]:
            self.config["content_types"][content_type]["yandex_disk"] = {}
        
        yandex_config = self.config["content_types"][content_type]["yandex_disk"]
        yandex_config["enabled"] = enabled
        
        if base_path:
            yandex_config["base_path"] = base_path
        
        self._save_config(self.config)
    
    def get_backup_settings(self) -> Dict[str, Any]:
        """Get backup settings."""
        return self.config.get("backup_settings", self._get_default_config()["backup_settings"])
    
    def set_backup_settings(self, settings: Dict[str, Any]):
        """Set backup settings."""
        if "backup_settings" not in self.config:
            self.config["backup_settings"] = {}
        
        self.config["backup_settings"].update(settings)
        self._save_config(self.config)
    
    def get_yandex_token(self) -> str:
        """Get Yandex Disk OAuth token."""
        return self.config.get("yandex_disk", {}).get("oauth_token", "")
    
    def set_yandex_token(self, token: str):
        """Set Yandex Disk OAuth token."""
        if "yandex_disk" not in self.config:
            self.config["yandex_disk"] = {}
        
        self.config["yandex_disk"]["oauth_token"] = token
        self.config["yandex_disk"]["enabled"] = bool(token)
        self._save_config(self.config)
    
    def is_yandex_enabled(self) -> bool:
        """Check if Yandex Disk is enabled."""
        return self.config.get("yandex_disk", {}).get("enabled", False)
    
    def get_minio_config(self) -> Dict[str, Any]:
        """Get MinIO configuration."""
        return self.config.get("minio", {})
    
    def set_minio_config(self, config: Dict[str, Any]):
        """Set MinIO configuration."""
        if "minio" not in self.config:
            self.config["minio"] = {}
        
        self.config["minio"].update(config)
        self._save_config(self.config)
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get entire configuration."""
        return self.config.copy()
    
    def update_config(self, updates: Dict[str, Any]):
        """Update configuration with new values."""
        self.config.update(updates)
        self._save_config(self.config)


# Global configuration instance
_storage_config = None


def get_storage_config() -> StorageConfig:
    """Get global storage configuration instance."""
    global _storage_config
    if _storage_config is None:
        _storage_config = StorageConfig()
    return _storage_config