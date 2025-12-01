"""
Unit tests for storage adapter folder provisioning functionality.
Tests folder creation/listing primitives for Local, Yandex, and MinIO adapters.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from app.storage_local import LocalStorageAdapter
from app.storage_yandex import YandexDiskStorageAdapter
from app.storage_minio import MinioStorageAdapter


# ===== LocalStorageAdapter Tests =====

@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def local_adapter(temp_storage):
    """Create LocalStorageAdapter instance."""
    return LocalStorageAdapter(temp_storage)


@pytest.mark.asyncio
async def test_local_create_directory(local_adapter, temp_storage):
    """Test creating directory in local storage."""
    result = await local_adapter.create_directory("test_dir")
    
    assert result is True
    assert (temp_storage / "test_dir").exists()
    assert (temp_storage / "test_dir").is_dir()


@pytest.mark.asyncio
async def test_local_create_nested_directory(local_adapter, temp_storage):
    """Test creating nested directory structure."""
    result = await local_adapter.create_directory("parent/child/grandchild")
    
    assert result is True
    assert (temp_storage / "parent" / "child" / "grandchild").exists()


@pytest.mark.asyncio
async def test_local_create_directory_idempotent(local_adapter):
    """Test that creating existing directory succeeds."""
    await local_adapter.create_directory("test_dir")
    result = await local_adapter.create_directory("test_dir")
    
    assert result is True


@pytest.mark.asyncio
async def test_local_directory_exists(local_adapter, temp_storage):
    """Test checking if directory exists."""
    await local_adapter.create_directory("test_dir")
    
    assert await local_adapter.directory_exists("test_dir") is True
    assert await local_adapter.directory_exists("nonexistent") is False


@pytest.mark.asyncio
async def test_local_list_directories(local_adapter, temp_storage):
    """Test listing directories in local storage."""
    # Create some directories
    await local_adapter.create_directory("dir1")
    await local_adapter.create_directory("dir2")
    await local_adapter.create_directory("dir3")
    
    # Create a file (should not be listed)
    (temp_storage / "file.txt").touch()
    
    directories = await local_adapter.list_directories("")
    
    assert "dir1" in directories
    assert "dir2" in directories
    assert "dir3" in directories
    assert "file.txt" not in directories


@pytest.mark.asyncio
async def test_local_list_nested_directories(local_adapter):
    """Test listing directories in subdirectory."""
    await local_adapter.create_directory("parent/child1")
    await local_adapter.create_directory("parent/child2")
    
    directories = await local_adapter.list_directories("parent")
    
    assert "child1" in directories
    assert "child2" in directories


@pytest.mark.asyncio
async def test_local_list_nonexistent_directory(local_adapter):
    """Test listing directories in nonexistent path."""
    directories = await local_adapter.list_directories("nonexistent")
    
    assert directories == []


@pytest.mark.asyncio
async def test_local_provision_hierarchy(local_adapter, temp_storage):
    """Test provisioning complete hierarchy via adapter."""
    company_slug = "test_company"
    category_slugs = ["portraits", "diplomas"]
    subfolders = ["Image", "QR", "nft_markers", "nft_cache"]
    
    result = await local_adapter.provision_hierarchy(
        company_slug,
        category_slugs,
        subfolders
    )
    
    assert result["success"] is True
    assert result["company_slug"] == company_slug
    assert result["categories_provisioned"] == 2
    assert len(result["failed_paths"]) == 0
    
    # Verify directories exist
    for category_slug in category_slugs:
        base_path = temp_storage / company_slug / category_slug
        assert base_path.exists()
        
        for subfolder in subfolders:
            assert (base_path / subfolder).exists()


# ===== YandexDiskStorageAdapter Tests =====

@pytest.fixture
def mock_yandex_session():
    """Mock Yandex Disk session."""
    session = MagicMock()
    session.request = MagicMock()
    return session


@pytest.fixture
def yandex_adapter(monkeypatch):
    """Create YandexDiskStorageAdapter with mocked session."""
    with patch('app.storage_yandex.YandexDiskStorageAdapter._create_session') as mock_session:
        mock_session.return_value = MagicMock()
        
        # Mock _ensure_directory_exists_sync to avoid real API calls during init
        with patch('app.storage_yandex.YandexDiskStorageAdapter._ensure_directory_exists_sync'):
            adapter = YandexDiskStorageAdapter(
                oauth_token="test_token",
                base_path="test-base"
            )
            return adapter


@pytest.mark.asyncio
async def test_yandex_create_directory(yandex_adapter, monkeypatch):
    """Test creating directory in Yandex Disk."""
    # Mock _ensure_directory_exists
    async def mock_ensure_directory(path):
        return True
    
    monkeypatch.setattr(yandex_adapter, "_ensure_directory_exists", mock_ensure_directory)
    
    result = await yandex_adapter.create_directory("test_dir")
    
    assert result is True


@pytest.mark.asyncio
async def test_yandex_directory_exists(yandex_adapter, monkeypatch):
    """Test checking if directory exists in Yandex Disk."""
    # Mock cache check
    async def mock_cache_get(key):
        return None
    
    monkeypatch.setattr(yandex_adapter.directory_cache, "get", mock_cache_get)
    
    # Mock API request
    mock_response = MagicMock()
    mock_response.json.return_value = {"type": "dir"}
    
    async def mock_make_request(*args, **kwargs):
        return mock_response
    
    with patch.object(yandex_adapter, '_make_request', return_value=mock_response):
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Mock run_in_executor
        async def mock_executor(executor, func):
            return mock_response
        
        with patch.object(loop, 'run_in_executor', side_effect=mock_executor):
            result = await yandex_adapter.directory_exists("test_dir")
    
    assert result is True


@pytest.mark.asyncio
async def test_yandex_list_directories(yandex_adapter):
    """Test listing directories in Yandex Disk."""
    # Mock API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "_embedded": {
            "items": [
                {"name": "dir1", "type": "dir"},
                {"name": "dir2", "type": "dir"},
                {"name": "file.txt", "type": "file"}
            ]
        }
    }
    
    with patch.object(yandex_adapter, '_make_request', return_value=mock_response):
        import asyncio
        loop = asyncio.get_event_loop()
        
        async def mock_executor(executor, func):
            return mock_response
        
        with patch.object(loop, 'run_in_executor', side_effect=mock_executor):
            result = await yandex_adapter.list_directories("")
    
    assert "dir1" in result
    assert "dir2" in result
    assert "file.txt" not in result


@pytest.mark.asyncio
async def test_yandex_provision_hierarchy(yandex_adapter, monkeypatch):
    """Test provisioning hierarchy via Yandex adapter."""
    # Mock create_directory to succeed
    async def mock_create_directory(path):
        return True
    
    monkeypatch.setattr(yandex_adapter, "create_directory", mock_create_directory)
    
    company_slug = "test_company"
    category_slugs = ["portraits", "diplomas"]
    subfolders = ["Image", "QR"]
    
    result = await yandex_adapter.provision_hierarchy(
        company_slug,
        category_slugs,
        subfolders
    )
    
    assert result["success"] is True
    assert result["categories_provisioned"] == 2
    assert len(result["failed_paths"]) == 0


# ===== MinioStorageAdapter Tests =====

# Skip MinIO tests if minio package not available
try:
    import minio
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False

pytestmark_minio = pytest.mark.skipif(not MINIO_AVAILABLE, reason="minio package not installed")


@pytest.fixture
def mock_minio_client():
    """Mock MinIO client."""
    if not MINIO_AVAILABLE:
        pytest.skip("minio package not installed")
    
    with patch('minio.Minio') as mock_minio:
        client = MagicMock()
        client.bucket_exists.return_value = True
        mock_minio.return_value = client
        yield client


@pytest.fixture
def minio_adapter(mock_minio_client):
    """Create MinioStorageAdapter with mocked client."""
    with patch('minio.Minio', return_value=mock_minio_client):
        adapter = MinioStorageAdapter(
            endpoint="localhost:9000",
            access_key="test_key",
            secret_key="test_secret",
            bucket="test-bucket"
        )
        adapter.client = mock_minio_client
        return adapter


@pytest.mark.skipif(not MINIO_AVAILABLE, reason="minio package not installed")
@pytest.mark.asyncio
async def test_minio_create_directory(minio_adapter):
    """Test creating directory in MinIO."""
    result = await minio_adapter.create_directory("test_dir")
    
    assert result is True
    # Verify put_object was called with directory marker
    minio_adapter.client.put_object.assert_called_once()
    call_args = minio_adapter.client.put_object.call_args
    assert call_args[0][1].endswith('/')  # Directory marker


@pytest.mark.skipif(not MINIO_AVAILABLE, reason="minio package not installed")
@pytest.mark.asyncio
async def test_minio_directory_exists(minio_adapter):
    """Test checking if directory exists in MinIO."""
    # Mock stat_object to succeed
    minio_adapter.client.stat_object.return_value = MagicMock()
    
    result = await minio_adapter.directory_exists("test_dir")
    
    assert result is True


@pytest.mark.skipif(not MINIO_AVAILABLE, reason="minio package not installed")
@pytest.mark.asyncio
async def test_minio_directory_exists_via_prefix(minio_adapter):
    """Test checking directory existence via object prefix."""
    from minio.error import S3Error
    
    # Mock stat_object to fail (no marker)
    minio_adapter.client.stat_object.side_effect = S3Error(
        code="NoSuchKey",
        message="Not found",
        resource="",
        request_id="",
        host_id="",
        response=MagicMock()
    )
    
    # Mock list_objects to return objects with prefix
    mock_obj = MagicMock()
    minio_adapter.client.list_objects.return_value = [mock_obj]
    
    result = await minio_adapter.directory_exists("test_dir")
    
    assert result is True


@pytest.mark.skipif(not MINIO_AVAILABLE, reason="minio package not installed")
@pytest.mark.asyncio
async def test_minio_list_directories(minio_adapter):
    """Test listing directories in MinIO."""
    # Mock objects with different types
    mock_obj1 = MagicMock()
    mock_obj1.is_dir = True
    mock_obj1.object_name = "dir1/"
    
    mock_obj2 = MagicMock()
    mock_obj2.is_dir = True
    mock_obj2.object_name = "dir2/"
    
    mock_obj3 = MagicMock()
    mock_obj3.is_dir = False
    mock_obj3.object_name = "file.txt"
    
    minio_adapter.client.list_objects.return_value = [mock_obj1, mock_obj2, mock_obj3]
    
    result = await minio_adapter.list_directories("")
    
    assert "dir1" in result
    assert "dir2" in result
    # File should not be in list (handled by subdirectory logic)


@pytest.mark.skipif(not MINIO_AVAILABLE, reason="minio package not installed")
@pytest.mark.asyncio
async def test_minio_provision_hierarchy(minio_adapter):
    """Test provisioning hierarchy via MinIO adapter."""
    company_slug = "test_company"
    category_slugs = ["portraits"]
    subfolders = ["Image", "QR"]
    
    result = await minio_adapter.provision_hierarchy(
        company_slug,
        category_slugs,
        subfolders
    )
    
    assert result["success"] is True
    assert result["categories_provisioned"] == 1
    
    # Verify put_object was called multiple times (for each directory)
    assert minio_adapter.client.put_object.call_count >= 3  # base + 2 subfolders


# ===== Error Handling Tests =====

@pytest.mark.asyncio
async def test_provision_hierarchy_partial_failure(local_adapter, temp_storage, monkeypatch):
    """Test that provision_hierarchy reports partial failures correctly."""
    company_slug = "test_company"
    category_slugs = ["good", "bad"]
    subfolders = ["Image"]
    
    # Mock create_directory to fail for "bad" category
    original_create = local_adapter.create_directory
    
    async def mock_create(path):
        if "bad" in path:
            raise OSError("Simulated error")
        return await original_create(path)
    
    monkeypatch.setattr(local_adapter, "create_directory", mock_create)
    
    result = await local_adapter.provision_hierarchy(
        company_slug,
        category_slugs,
        subfolders
    )
    
    assert result["success"] is False
    assert len(result["failed_paths"]) == 1
    assert result["failed_paths"][0]["category"] == "bad"
    assert result["hierarchy"]["good"]["success"] is True
    assert result["hierarchy"]["bad"]["success"] is False
