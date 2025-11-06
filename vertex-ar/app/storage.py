"""
Base storage adapter interface for Vertex AR.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class StorageAdapter(ABC):
    """Abstract base class for storage adapters."""

    @abstractmethod
    async def save_file(self, file_data: bytes, file_path: str) -> str:
        """Save file data to storage.

        Args:
            file_data: Raw file data
            file_path: Destination path within storage

        Returns:
            Public URL or path to access the file
        """
        pass

    @abstractmethod
    async def get_file(self, file_path: str) -> bytes:
        """Get file data from storage.

        Args:
            file_path: Path to the file in storage

        Returns:
            Raw file data
        """
        pass

    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from storage.

        Args:
            file_path: Path to the file in storage

        Returns:
            True if deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """Check if file exists in storage.

        Args:
            file_path: Path to the file in storage

        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
    def get_public_url(self, file_path: str) -> str:
        """Get public URL for file access.

        Args:
            file_path: Path to the file in storage

        Returns:
            Public URL string
        """
        pass
