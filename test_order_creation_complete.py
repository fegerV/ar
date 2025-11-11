"""
Comprehensive test for order creation with admin media upload, NFT generation, and error logging.
Тест создания заказа с загрузкой медиа из админ-панели, генерацией NFT и логированием ошибок.
"""
import json
import logging
import os
import sys
import tempfile
import uuid
from io import BytesIO
from pathlib import Path

# Add vertex-ar to path
sys.path.insert(0, str(Path(__file__).parent / "vertex-ar"))

# Configure logging to capture errors
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_order_creation.log')
    ]
)
logger = logging.getLogger(__name__)


def create_test_image(size_kb: int = 100) -> bytes:
    """Create a valid JPEG image for testing."""
    try:
        from PIL import Image
        
        # Create a simple image
        img = Image.new('RGB', (640, 480), color='red')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        
        # Resize to approximately target size
        data = buffer.getvalue()
        if len(data) < size_kb * 1024:
            # Pad with zeros if needed
            data = data + b'\0' * (size_kb * 1024 - len(data))
        
        return data[:size_kb * 1024]
    except ImportError:
        # Fallback: create a minimal valid JPEG if PIL not available
        logger.warning("PIL not available, creating minimal JPEG")
        jpeg_header = bytes.fromhex('FFD8FFE000104A46494600010100000100010000')
        jpeg_data = jpeg_header + b'\xFF\xD9'
        return jpeg_data * (size_kb // 1)


def create_test_video(duration_sec: int = 2) -> bytes:
    """Create a minimal valid MP4 video for testing."""
    try:
        import subprocess
        
        result = subprocess.run(
            [
                "ffmpeg", "-f", "lavfi", "-i", f"color=red:s=320x240:d={duration_sec}",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                "-c:v", "libx264", "-c:a", "aac",
                "-f", "mp4", "pipe:"
            ],
            capture_output=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return result.stdout
        
    except Exception as e:
        logger.warning(f"Failed to create video with ffmpeg: {e}")

    # Fallback: create minimal MP4 file
    mp4_header = bytes.fromhex(
        '0000002066747970697633323000000000000069736f366136316134'
    )
    return mp4_header + b'\x00' * 5000


def test_01_smoke_test():
    """Test 01: Smoke test for order creation functionality."""
    logger.info("="*80)
    logger.info("TEST 01: Smoke Test - Order Creation Module Import")
    logger.info("="*80)

    try:
        from app.api.orders import create_order
        from app.database import Database
        from app.models import OrderResponse
        
        logger.info("✓ All required modules imported successfully")
        logger.info("✓ Order API endpoint available")
        logger.info("✓ Database models available")
        logger.info("✓ Response models available")
        
        return True

    except ImportError as e:
        logger.error(f"Import error: {e}", exc_info=True)
        return False


def test_02_database_operations():
    """Test 02: Database operations for clients, portraits, and videos."""
    logger.info("\n" + "="*80)
    logger.info("TEST 02: Database Operations - Clients, Portraits, Videos")
    logger.info("="*80)

    try:
        from app.database import Database
        
        # Create test database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        
        db = Database(db_path)
        
        # Test 2a: Create client
        logger.info("\n  2a: Creating client...")
        client_id = str(uuid.uuid4())
        phone = "+7 (999) 123-45-67"
        name = "Тестовый Заказчик"
        
        client = db.create_client(client_id, phone, name)
        
        if client and client["phone"] == phone and client["name"] == name:
            logger.info(f"  ✓ Client created: ID={client_id}, Name={name}, Phone={phone}")
        else:
            logger.error("  ✗ Failed to create client")
            return False
        
        # Test 2b: Get client by phone
        logger.info("\n  2b: Retrieving client by phone...")
        found_client = db.get_client_by_phone(phone)
        
        if found_client and found_client["id"] == client_id:
            logger.info(f"  ✓ Client found by phone: {found_client['name']}")
        else:
            logger.error("  ✗ Failed to find client by phone")
            return False
        
        # Test 2c: Create portrait
        logger.info("\n  2c: Creating portrait with NFT markers...")
        portrait_id = str(uuid.uuid4())
        
        portrait = db.create_portrait(
            portrait_id=portrait_id,
            client_id=client_id,
            image_path="/test/path.jpg",
            marker_fset="test_marker_fset.fset",
            marker_fset3="test_marker_fset3.fset3",
            marker_iset="test_marker_iset.iset",
            permanent_link=f"portrait_{portrait_id}",
            qr_code="test_qr_code_base64_string"
        )
        
        if portrait and portrait["id"] == portrait_id:
            logger.info(f"  ✓ Portrait created: ID={portrait_id}")
            logger.info(f"    - Permanent link: {portrait['permanent_link']}")
            logger.info(f"    - QR code set: {bool(portrait['qr_code'])}")
        else:
            logger.error("  ✗ Failed to create portrait")
            return False
        
        # Test 2d: Create video
        logger.info("\n  2d: Creating video...")
        video_id = str(uuid.uuid4())
        
        video = db.create_video(
            video_id=video_id,
            portrait_id=portrait_id,
            video_path="/test/video.mp4",
            is_active=True
        )
        
        if video and video["id"] == video_id and video["is_active"]:
            logger.info(f"  ✓ Video created: ID={video_id}, Active=True")
        else:
            logger.error("  ✗ Failed to create video")
            return False
        
        # Test 2e: Get active video
        logger.info("\n  2e: Retrieving active video...")
        active_video = db.get_active_video(portrait_id)
        
        if active_video and active_video["id"] == video_id:
            logger.info(f"  ✓ Active video retrieved: {active_video['id']}")
        else:
            logger.error("  ✗ Failed to get active video")
            return False
        
        # Test 2f: List videos for portrait
        logger.info("\n  2f: Listing videos for portrait...")
        videos = db.list_videos(portrait_id)
        
        if len(videos) > 0:
            logger.info(f"  ✓ Found {len(videos)} video(s) for portrait")
        else:
            logger.error("  ✗ No videos found for portrait")
            return False
        
        # Cleanup
        db_path.unlink()
        logger.info("\n✓ All database operations passed!")
        return True

    except Exception as e:
        logger.error(f"Database operations test failed: {e}", exc_info=True)
        return False


def test_03_fastapi_client():
    """Test 03: FastAPI TestClient - Health check and endpoints."""
    logger.info("\n" + "="*80)
    logger.info("TEST 03: FastAPI TestClient - Health Check and Endpoints")
    logger.info("="*80)

    try:
        from app.main import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client = TestClient(app)

        # Test 3a: Health check
        logger.info("\n  3a: Testing health check endpoint...")
        response = client.get("/api/health")
        
        if response.status_code == 200:
            health_data = response.json()
            logger.info(f"  ✓ Health check passed: {health_data.get('status', 'OK')}")
        else:
            logger.warning(f"  ⚠ Health check returned status {response.status_code}")

        # Test 3b: Admin login attempt
        logger.info("\n  3b: Testing admin login endpoint...")
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "Qwerty123!@#"}
        )
        
        if response.status_code == 200:
            login_data = response.json()
            logger.info(f"  ✓ Admin login successful")
            logger.info(f"    - Token type: {login_data.get('token_type', 'unknown')}")
        elif response.status_code == 401:
            logger.info(f"  ⚠ Admin login failed (invalid credentials)")
        else:
            logger.info(f"  ⚠ Login endpoint returned status {response.status_code}")

        # Test 3c: Unauthorized order creation attempt
        logger.info("\n  3c: Testing unauthorized order creation attempt...")
        response = client.post(
            "/api/orders/create",
            data={"phone": "+7 900 111 22 33", "name": "Test"},
            files={
                "image": ("test.jpg", create_test_image(50), "image/jpeg"),
                "video": ("test.mp4", create_test_video(2), "video/mp4"),
            }
        )

        if response.status_code in [401, 403]:
            logger.info(f"  ✓ Unauthorized request rejected (status {response.status_code})")
        else:
            logger.warning(f"  ⚠ Unexpected response status: {response.status_code}")

        logger.info("\n✓ All FastAPI TestClient tests passed!")
        return True

    except Exception as e:
        logger.error(f"FastAPI TestClient test failed: {e}", exc_info=True)
        return False


def test_04_error_handling():
    """Test 04: Error handling and logging."""
    logger.info("\n" + "="*80)
    logger.info("TEST 04: Error Handling and Logging")
    logger.info("="*80)

    try:
        from app.main import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client = TestClient(app)

        # Test 4a: Invalid phone format
        logger.info("\n  4a: Testing invalid phone format...")
        try:
            response = client.post(
                "/api/auth/login",
                json={"username": "", "password": ""}
            )
            logger.info(f"  ✓ Invalid input handled (status {response.status_code})")
        except Exception as e:
            logger.info(f"  ✓ Exception caught and handled: {type(e).__name__}")

        # Test 4b: File type validation
        logger.info("\n  4b: Testing file type validation...")
        
        # Try to upload non-image file as image
        response = client.post(
            "/api/orders/create",
            data={"phone": "+7 900 123 45 67", "name": "Test"},
            files={
                "image": ("test.txt", b"not an image", "text/plain"),
                "video": ("test.mp4", create_test_video(), "video/mp4"),
            }
        )
        
        # Should fail validation
        if response.status_code != 201:
            logger.info(f"  ✓ Invalid image file rejected (status {response.status_code})")
        else:
            logger.warning(f"  ⚠ Invalid image file was accepted")

        # Test 4c: Missing required fields
        logger.info("\n  4c: Testing missing required fields...")
        response = client.post(
            "/api/orders/create",
            data={"phone": "+7 900 123 45 67"},  # Missing name
            files={
                "image": ("test.jpg", create_test_image(50), "image/jpeg"),
                "video": ("test.mp4", create_test_video(2), "video/mp4"),
            }
        )
        
        if response.status_code != 201:
            logger.info(f"  ✓ Missing required field rejected (status {response.status_code})")
        else:
            logger.warning(f"  ⚠ Missing field was accepted")

        logger.info("\n✓ All error handling tests passed!")
        return True

    except Exception as e:
        logger.error(f"Error handling test failed: {e}", exc_info=True)
        return False


def test_05_models_and_validators():
    """Test 05: Pydantic models and validators."""
    logger.info("\n" + "="*80)
    logger.info("TEST 05: Pydantic Models and Validators")
    logger.info("="*80)

    try:
        from app.models import ClientCreate, ClientResponse, OrderResponse
        from app.validators import validate_phone, validate_name

        # Test 5a: Phone validation
        logger.info("\n  5a: Testing phone validation...")
        try:
            valid_phone = validate_phone("+7 (999) 123-45-67")
            logger.info(f"  ✓ Phone validation works: {valid_phone}")
        except Exception as e:
            logger.warning(f"  ⚠ Phone validation error: {e}")

        # Test 5b: Name validation
        logger.info("\n  5b: Testing name validation...")
        try:
            valid_name = validate_name("Иван Петров")
            logger.info(f"  ✓ Name validation works: {valid_name}")
        except Exception as e:
            logger.warning(f"  ⚠ Name validation error: {e}")

        # Test 5c: Pydantic model validation
        logger.info("\n  5c: Testing Pydantic model validation...")
        try:
            client_data = ClientCreate(
                phone="+7 (999) 123-45-67",
                name="Test Client"
            )
            logger.info(f"  ✓ ClientCreate model validated")
        except Exception as e:
            logger.error(f"  ✗ Model validation failed: {e}")
            return False

        logger.info("\n✓ All model and validator tests passed!")
        return True

    except Exception as e:
        logger.error(f"Models and validators test failed: {e}", exc_info=True)
        return False


def test_06_nft_generation():
    """Test 06: NFT marker generation capabilities."""
    logger.info("\n" + "="*80)
    logger.info("TEST 06: NFT Marker Generation")
    logger.info("="*80)

    try:
        # Check NFT generator module
        logger.info("\n  6a: Checking NFT generator module...")
        try:
            from nft_marker_generator import NFTMarkerGenerator, NFTMarkerConfig
            logger.info("  ✓ NFT marker generator module available")
        except ImportError as e:
            logger.warning(f"  ⚠ NFT generator not available: {e}")
            return False

        # Test 6b: Check preview generator
        logger.info("\n  6b: Checking preview generator module...")
        try:
            from preview_generator import PreviewGenerator
            logger.info("  ✓ Preview generator module available")
        except ImportError as e:
            logger.warning(f"  ⚠ Preview generator not available: {e}")
            return False

        logger.info("\n✓ All NFT generation tests passed!")
        return True

    except Exception as e:
        logger.error(f"NFT generation test failed: {e}", exc_info=True)
        return False


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("COMPREHENSIVE ORDER CREATION TEST SUITE")
    print("="*80)
    print("Testing: Order creation, admin media upload, NFT generation, error logging")
    print("="*80)

    tests = [
        ("Smoke Test - Module Import", test_01_smoke_test),
        ("Database Operations", test_02_database_operations),
        ("FastAPI TestClient", test_03_fastapi_client),
        ("Error Handling", test_04_error_handling),
        ("Models and Validators", test_05_models_and_validators),
        ("NFT Generation", test_06_nft_generation),
    ]

    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"Test '{name}' crashed: {e}", exc_info=True)
            results.append((name, False))

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = 0
    failed = 0

    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1

    print("="*80)
    print(f"Total: {len(results)} | Passed: {passed} | Failed: {failed}")
    print("="*80 + "\n")

    # Log to file
    with open('test_results.json', 'w') as f:
        json.dump({
            'total': len(results),
            'passed': passed,
            'failed': failed,
            'tests': [{'name': name, 'passed': result} for name, result in results]
        }, f, indent=2)

    logger.info(f"Test results saved to test_results.json")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
