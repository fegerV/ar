"""
Local filesystem storage adapter for Vertex AR.
"""

import os
import shutil
from pathlib import Path
from typing import Optional

from app.storage import StorageAdapter


class LocalStorageAdapter(StorageAdapter):
    """Local filesystem storage implementation."""

    def __init__(self, storage_root: Path):
        """Initialize local storage adapter.

        Args:
            storage_root: Root directory for file storage
        """
        self.storage_root = Path(storage_root)
        self.storage_root.mkdir(parents=True, exist_ok=True)

    async def save_file(self, file_data: bytes, file_path: str) -> str:
        """Save file data to local filesystem.

        Args:
            file_data: Raw file data
            file_path: Destination path within storage

        Returns:
            Public URL to access the file
        """
        full_path = self.storage_root / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(file_data)

        return self.get_public_url(file_path)

    async def get_file(self, file_path: str) -> bytes:
        """Get file data from local filesystem.

        Args:
            file_path: Path to the file in storage

        Returns:
            Raw file data
        """
        full_path = self.storage_root / file_path

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(full_path, "rb") as f:
            return f.read()

    async def delete_file(self, file_path: str) -> bool:
        """Delete file from local filesystem.

        Args:
            file_path: Path to the file in storage

        Returns:
            True if deleted successfully, False otherwise
        """
        full_path = self.storage_root / file_path

        try:
            if full_path.exists():
                full_path.unlink()
                # Try to remove parent directories if they're empty
                try:
                    parent = full_path.parent
                    while parent != self.storage_root:
                        if parent.exists() and not any(parent.iterdir()):
                            parent.rmdir()
                        else:
                            break
                        parent = parent.parent
                except OSError:
                    pass  # Directory not empty or other error
                return True
            return False
        except OSError:
            return False

    async def file_exists(self, file_path: str) -> bool:
        """Check if file exists in local filesystem.

        Args:
            file_path: Path to the file in storage

        Returns:
            True if file exists, False otherwise
        """
        full_path = self.storage_root / file_path
        return full_path.exists() and full_path.is_file()

    def get_public_url(self, file_path: str) -> str:
        """Get public URL for file access.

        Args:
            file_path: Path to the file in storage

        Returns:
            Public URL string
        """
        from app.config import settings

        return f"{settings.BASE_URL}/storage/{file_path}"
