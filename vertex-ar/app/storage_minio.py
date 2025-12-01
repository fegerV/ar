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
    
    async def create_directory(self, dir_path: str) -> bool:
        """Create a directory in MinIO storage.
        
        MinIO/S3 doesn't have true directories, but we create a marker object.
        
        Args:
            dir_path: Directory path to create
            
        Returns:
            True if created successfully or already exists
        """
        from io import BytesIO
        from minio.error import S3Error
        
        # Ensure dir_path ends with /
        if not dir_path.endswith('/'):
            dir_path += '/'
        
        try:
            # Create a zero-byte marker object for the directory
            self.client.put_object(
                self.bucket,
                dir_path,
                BytesIO(b''),
                length=0
            )
            return True
        except S3Error:
            return False
    
    async def directory_exists(self, dir_path: str) -> bool:
        """Check if directory exists in MinIO storage.
        
        Args:
            dir_path: Directory path to check
            
        Returns:
            True if directory exists
        """
        from minio.error import S3Error
        
        # Ensure dir_path ends with /
        if not dir_path.endswith('/'):
            dir_path += '/'
        
        try:
            # Check if the directory marker exists
            self.client.stat_object(self.bucket, dir_path)
            return True
        except S3Error:
            # Also check if there are any objects with this prefix
            try:
                objects = list(self.client.list_objects(
                    self.bucket,
                    prefix=dir_path,
                    max_keys=1
                ))
                return len(objects) > 0
            except S3Error:
                return False
    
    async def list_directories(self, base_path: str = "") -> list:
        """List directories at the given path in MinIO storage.
        
        Args:
            base_path: Base path to list directories from
            
        Returns:
            List of directory names (not full paths)
        """
        from minio.error import S3Error
        
        # Ensure base_path ends with / if not empty
        if base_path and not base_path.endswith('/'):
            base_path += '/'
        
        try:
            # List objects with delimiter to get "directories"
            objects = self.client.list_objects(
                self.bucket,
                prefix=base_path,
                recursive=False
            )
            
            directories = set()
            for obj in objects:
                # Extract directory name from object key
                if obj.is_dir:
                    # Remove prefix and trailing slash
                    dir_name = obj.object_name[len(base_path):].rstrip('/')
                    if dir_name:
                        directories.add(dir_name)
                else:
                    # Check if object is in a subdirectory
                    relative_path = obj.object_name[len(base_path):]
                    if '/' in relative_path:
                        dir_name = relative_path.split('/')[0]
                        directories.add(dir_name)
            
            return sorted(list(directories))
        except S3Error:
            return []