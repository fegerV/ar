"""
MinIO storage adapter for Vertex AR.
"""
from urllib.parse import urljoin
from typing import Optional

from app.storage import StorageAdapter


class MinioStorageAdapter(StorageAdapter):
    """MinIO storage implementation."""
    
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str):
        """Initialize MinIO storage adapter.
        
        Args:
            endpoint: MinIO server endpoint
            access_key: MinIO access key
            secret_key: MinIO secret key
            bucket: MinIO bucket name
        """
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        
        try:
            from minio import Minio
            self.client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=False  # Set to True for HTTPS
            )
            
            # Create bucket if it doesn't exist
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                
        except ImportError:
            raise ImportError("minio package is required for MinIO storage. Install with: pip install minio")
    
    async def save_file(self, file_data: bytes, file_path: str) -> str:
        """Save file data to MinIO.
        
        Args:
            file_data: Raw file data
            file_path: Destination path within storage
            
        Returns:
            Public URL to access the file
        """
        from io import BytesIO
        from minio.error import S3Error
        
        try:
            self.client.put_object(
                self.bucket,
                file_path,
                BytesIO(file_data),
                length=len(file_data)
            )
            return self.get_public_url(file_path)
        except S3Error as e:
            raise Exception(f"Failed to save file to MinIO: {e}")
    
    async def get_file(self, file_path: str) -> bytes:
        """Get file data from MinIO.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            Raw file data
        """
        from minio.error import S3Error
        
        try:
            response = self.client.get_object(self.bucket, file_path)
            return response.read()
        except S3Error as e:
            raise FileNotFoundError(f"File not found in MinIO: {file_path}")
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from MinIO.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            True if deleted successfully, False otherwise
        """
        from minio.error import S3Error
        
        try:
            self.client.remove_object(self.bucket, file_path)
            return True
        except S3Error:
            return False
    
    async def file_exists(self, file_path: str) -> bool:
        """Check if file exists in MinIO.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            True if file exists, False otherwise
        """
        from minio.error import S3Error
        
        try:
            self.client.stat_object(self.bucket, file_path)
            return True
        except S3Error:
            return False
    
    def get_public_url(self, file_path: str) -> str:
        """Get public URL for file access.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            Public URL string
        """
        from app.config import settings
        if not self.endpoint.startswith('http'):
            protocol = 'https' if self.endpoint.endswith(':443') else 'http'
            base_url = f"{protocol}://{self.endpoint}"
        else:
            base_url = self.endpoint
            
        return f"{base_url}/{self.bucket}/{file_path}"