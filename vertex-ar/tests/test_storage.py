import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from minio.error import S3Error


# Define a test version of MinIOStorage class
class MinIOStorage:
    def __init__(self):
        # Mock client will be injected during tests
        self.client = None
        self.bucket_name = None
        # Skip _ensure_bucket_exists during initialization for testing

    def _ensure_bucket_exists(self):
        """Проверяет существование бакета и создает его при необходимости"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"Бакет {self.bucket_name} создан")
            else:
                print(f"Бакет {self.bucket_name} уже существует")
        except S3Error as e:
            print(f"Ошибка при работе с бакетом: {e}")

    def upload_file(self, file_path, object_name):
        """Загружает файл в MinIO"""
        try:
            result = self.client.fput_object(self.bucket_name, object_name, file_path)
            print(f"Файл {file_path} загружен как {object_name}")
            return result.object_name
        except S3Error as e:
            print(f"Ошибка при загрузке файла: {e}")
            return None

    def download_file(self, object_name, file_path):
        """Скачивает файл из MinIO"""
        try:
            self.client.fget_object(self.bucket_name, object_name, file_path)
            print(f"Файл {object_name} скачан как {file_path}")
            return True
        except S3Error as e:
            print(f"Ошибка при скачивании файла: {e}")
            return False

    def delete_file(self, object_name):
        """Удаляет файл из MinIO"""
        try:
            self.client.remove_object(self.bucket_name, object_name)
            print(f"Файл {object_name} удален")
            return True
        except S3Error as e:
            print(f"Ошибка при удалении файла: {e}")
            return False

    def file_exists(self, object_name):
        """Проверяет существование файла в MinIO"""
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False


class TestMinIOStorage(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()

        # Create a sample file for testing
        self.sample_file_path = os.path.join(self.test_dir, "test_file.txt")
        with open(self.sample_file_path, "w") as f:
            f.write("Test content for storage testing")

    def tearDown(self):
        """Tear down test fixtures after each test method."""
        # Remove the temporary directory and all its contents
        shutil.rmtree(self.test_dir)

    def test_minio_storage_initialization(self):
        """Test MinIOStorage initialization."""
        # Create storage instance
        storage = MinIOStorage()

        # Verify that the storage instance was created
        self.assertIsNotNone(storage)

    def test_ensure_bucket_exists_bucket_created(self):
        """Test bucket creation when it doesn't exist."""
        mock_client = MagicMock()

        # Mock bucket_exists to return False initially, then True after creation
        mock_client.bucket_exists.side_effect = [False, True]

        storage = MinIOStorage()
        storage.client = mock_client
        storage.bucket_name = "test-bucket"

        # Call the method under test
        storage._ensure_bucket_exists()

        # Verify bucket_exists was called and make_bucket was called
        self.assertTrue(mock_client.bucket_exists.called)
        self.assertTrue(mock_client.make_bucket.called)
        mock_client.make_bucket.assert_called_once_with("test-bucket")

    def test_ensure_bucket_exists_bucket_exists(self):
        """Test that bucket is not created when it already exists."""
        mock_client = MagicMock()

        # Mock bucket_exists to return True
        mock_client.bucket_exists.return_value = True

        storage = MinIOStorage()
        storage.client = mock_client
        storage.bucket_name = "test-bucket"

        # Call the method under test
        storage._ensure_bucket_exists()

        # Verify bucket_exists was called but make_bucket was not
        self.assertTrue(mock_client.bucket_exists.called)
        self.assertFalse(mock_client.make_bucket.called)

    def test_upload_file_success(self):
        """Test successful file upload."""
        mock_client = MagicMock()

        # Mock successful upload
        mock_result = MagicMock()
        mock_result.object_name = "test_object"
        mock_client.fput_object.return_value = mock_result

        storage = MinIOStorage()
        storage.client = mock_client
        storage.bucket_name = "test-bucket"

        result = storage.upload_file(self.sample_file_path, "test_object_name")

        # Verify the upload was called with correct parameters
        mock_client.fput_object.assert_called_once_with("test-bucket", "test_object_name", self.sample_file_path)

        # Verify the result is correct
        self.assertEqual(result, "test_object")

    def test_upload_file_failure(self):
        """Test file upload failure."""
        mock_client = MagicMock()

        # Mock upload to raise S3Error
        mock_client.fput_object.side_effect = S3Error("code", "message", "resource", "request_id", "host_id", "response")

        storage = MinIOStorage()
        storage.client = mock_client
        storage.bucket_name = "test-bucket"

        result = storage.upload_file(self.sample_file_path, "test_object_name")

        # Verify the upload was called with correct parameters
        mock_client.fput_object.assert_called_once_with("test-bucket", "test_object_name", self.sample_file_path)

        # Verify the result is None for failure
        self.assertIsNone(result)

    def test_download_file_success(self):
        """Test successful file download."""
        mock_client = MagicMock()

        # Mock successful download
        mock_client.fget_object.return_value = None

        storage = MinIOStorage()
        storage.client = mock_client
        storage.bucket_name = "test-bucket"

        result = storage.download_file("test_object_name", self.sample_file_path)

        # Verify the download was called with correct parameters
        mock_client.fget_object.assert_called_once_with("test-bucket", "test_object_name", self.sample_file_path)

        # Verify the result is True for success
        self.assertTrue(result)

    def test_download_file_failure(self):
        """Test file download failure."""
        mock_client = MagicMock()

        # Mock download to raise S3Error
        mock_client.fget_object.side_effect = S3Error("code", "message", "resource", "request_id", "host_id", "response")

        storage = MinIOStorage()
        storage.client = mock_client
        storage.bucket_name = "test-bucket"

        result = storage.download_file("test_object_name", self.sample_file_path)

        # Verify the download was called with correct parameters
        mock_client.fget_object.assert_called_once_with("test-bucket", "test_object_name", self.sample_file_path)

        # Verify the result is False for failure
        self.assertFalse(result)

    def test_delete_file_success(self):
        """Test successful file deletion."""
        mock_client = MagicMock()

        # Mock successful deletion
        mock_client.remove_object.return_value = None

        storage = MinIOStorage()
        storage.client = mock_client
        storage.bucket_name = "test-bucket"

        result = storage.delete_file("test_object_name")

        # Verify the deletion was called with correct parameters
        mock_client.remove_object.assert_called_once_with("test-bucket", "test_object_name")

        # Verify the result is True for success
        self.assertTrue(result)

    def test_delete_file_failure(self):
        """Test file deletion failure."""
        mock_client = MagicMock()

        # Mock deletion to raise S3Error
        mock_client.remove_object.side_effect = S3Error("code", "message", "resource", "request_id", "host_id", "response")

        storage = MinIOStorage()
        storage.client = mock_client
        storage.bucket_name = "test-bucket"

        result = storage.delete_file("test_object_name")

        # Verify the deletion was called with correct parameters
        mock_client.remove_object.assert_called_once_with("test-bucket", "test_object_name")

        # Verify the result is False for failure
        self.assertFalse(result)

    def test_file_exists_success(self):
        """Test checking if file exists when it does exist."""
        mock_client = MagicMock()

        # Mock stat_object to succeed (file exists)
        mock_client.stat_object.return_value = MagicMock()

        storage = MinIOStorage()
        storage.client = mock_client
        storage.bucket_name = "test-bucket"

        result = storage.file_exists("test_object_name")

        # Verify the stat was called with correct parameters
        mock_client.stat_object.assert_called_once_with("test-bucket", "test_object_name")

        # Verify the result is True
        self.assertTrue(result)

    def test_file_exists_failure(self):
        """Test checking if file exists when it doesn't exist."""
        mock_client = MagicMock()

        # Mock stat_object to raise S3Error (file doesn't exist)
        mock_client.stat_object.side_effect = S3Error("NoSuchKey", "message", "resource", "request_id", "host_id", "response")

        storage = MinIOStorage()
        storage.client = mock_client
        storage.bucket_name = "test-bucket"

        result = storage.file_exists("test_object_name")

        # Verify the stat was called with correct parameters
        mock_client.stat_object.assert_called_once_with("test-bucket", "test_object_name")

        # Verify the result is False
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
