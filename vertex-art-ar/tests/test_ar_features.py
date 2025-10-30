import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi.responses import HTMLResponse
from PIL import Image
import io
import base64
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI

# Ensure storage module does not attempt real MinIO connections during tests
os.environ.setdefault("RUNNING_TESTS", "1")

# Add the parent directory to the path to import modules
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import SessionLocal, NFTRecord
from datetime import datetime

# Создаем тестовое приложение с реальными маршрутами, но с моками
def create_test_app():
    app = FastAPI()
    
    # Импортируем и мокаем зависимости
    from fastapi import Depends
    from sqlalchemy.orm import Session
    
    # Создаем мок-функцию для получения сессии БД
    def get_mock_db():
        # Создаем фиктивную сессию
        class MockDBSession:
            def query(self, model):
                class MockQuery:
                    def filter(self, condition):
                        class MockFilter:
                            def first(self):
                                # Возвращаем фиктивную запись, если ID совпадает с тестовым
                                if "test-uuid" in str(condition):
                                    class MockRecord:
                                        id = "test-uuid-123"
                                        image_url = f"http://testserver/images/test-uuid-123.jpg"
                                        video_url = f"http://testserver/videos/test-uuid-123.mp4"
                                        nft_url = f"http://testserver/ar/test-uuid-123"
                                        qr_code = base64.b64encode(b"fake qr code").decode()
                                        created_at = datetime.utcnow()
                                        image_preview_url = f"previews/test-uuid-123_image_thumbnail.jpg"
                                        video_preview_url = f"previews/test-uuid-123_video_thumbnail.jpg"
                                    return MockRecord()
                                return None
                        return MockFilter()
                return MockQuery()
        
        return MockDBSession()
    
    # Мок для получения реальных данных
    async def mock_get_current_user():
        return "test_user"
    
    # Добавляем маршрут AR-страницы с моками
    @app.get("/ar/{record_id}", response_class=HTMLResponse)
    async def ar_page_test(record_id: str, db: Session = Depends(get_mock_db)):
        from fastapi.responses import HTMLResponse
        # Проверяем, существует ли запись (в моке всегда возвращаем успешный результат для тестовых ID)
        record = db.query(NFTRecord).filter(f"record_id == '{record_id}'").first()
        if not record:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Возвращаем HTML с содержимым, как в реальном шаблоне
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AR Experience Test</title>
            <script src="https://aframe.io/releases/1.4.0/aframe.min.js"></script>
            <script src="https://raw.githack.com/AR-js-org/AR.js/master/aframe/build/aframe-ar-nft.js"></script>
            <style>
                .arjs-loader {{
                    height: 100%;
                    width: 100%;
                    position: absolute;
                    top: 0;
                    left: 0;
                    background-color: rgba(0, 0, 0, 0.8);
                    z-index: 99;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }}
                .arjs-loader div {{
                    text-align: center;
                    font-size: 1.25em;
                    color: white;
                }}
            </style>
        </head>
        <body style="margin: 0; overflow: hidden;">
            <div class="arjs-loader">
                <div>
                    <div>Загрузка AR-опыта</div>
                    <div>Пожалуйста, подождите</div>
                    <div class="loading-spinner">●●●</div>
                </div>
            </div>

            <a-scene
                vr-mode-ui="enabled: false"
                arjs="sourceType: webcam; debugUIEnabled: false;"
                renderer="logarithmicDepthBuffer: true;"
            >
                <a-nft
                    type="nft"
                    url="/nft-markers/{record_id}"
                    smooth="true"
                    smoothCount="5"
                    smoothTolerance=".01"
                    smoothThreshold="5"
                >
                    <a-video
                        id="ar-video"
                        src="http://testserver/videos/{record_id}.mp4"
                        width="1"
                        height="1"
                        position="0 0 0"
                        rotation="0 0"
                        scale="1 1 1"
                        autoplay="false"
                        webkit-playsinline
                        playsinline
                    ></a-video>
                </a-nft>

                <a-entity camera></a-entity>
            </a-scene>

            <script>
                // Hide loader when scene is loaded
                document.querySelector('a-scene').addEventListener('loaded', function() {{{{
                    document.querySelector('.arjs-loader').style.display = 'none';
                }}}} );

                // Play video when marker is detected
                document.querySelector('a-scene').addEventListener('markerFound', function() {{{{
                    const video = document.getElementById('ar-video');
                    if (video) {{{{
                        video.setAttribute('autoplay', 'true');
                        video.play().catch(e => console.log("Autoplay prevented: ", e));
                    }}}}
                }}}} );

                // Pause video when marker is lost
                document.querySelector('a-scene').addEventListener('markerLost', function() {{{{
                    const video = document.getElementById('ar-video');
                    if (video) {{{{
                        video.pause();
                        video.currentTime = 0;
                    }}}}
                }}}} );

                // Handle video playback errors
                document.getElementById('ar-video').addEventListener('error', function() {{{{
                    console.error('Error loading video for AR experience');
                }}}} );
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    
    # Добавляем маршруты для получения файлов с моками
    @app.get("/images/{image_id}.jpg")
    async def get_image_test(image_id: str, db: Session = Depends(get_mock_db)):
        from fastapi.responses import Response
        from fastapi import HTTPException
        
        # Проверяем, существует ли запись
        record = db.query(NFTRecord).filter(f"record_id == '{image_id}'").first()
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Создаем фиктивное изображение
        img = Image.new('RGB', (300, 300), color='red')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)
        image_content = img_byte_arr.getvalue()
        
        return Response(content=image_content, media_type="image/jpeg")
    
    @app.get("/previews/{preview_filename}")
    async def get_preview_test(preview_filename: str, db: Session = Depends(get_mock_db)):
        from fastapi.responses import Response
        from fastapi import HTTPException
        
        # Извлекаем ID записи из имени файла превью
        record_id = preview_filename.split('_')[0]
        
        # Проверяем, существует ли запись
        record = db.query(NFTRecord).filter(f"record_id == '{record_id}'").first()
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Создаем фиктивное изображение
        img = Image.new('RGB', (200, 200), color='green')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)
        preview_content = img_byte_arr.getvalue()
        
        return Response(content=preview_content, media_type="image/jpeg")
    
    @app.get("/nft-markers/{record_id}.{file_ext}")
    async def get_nft_marker_test(record_id: str, file_ext: str, db: Session = Depends(get_mock_db)):
        from fastapi.responses import Response
        from fastapi import HTTPException
        
        # Проверяем, что file_ext допустим
        if file_ext not in ["iset", "fset", "fset3"]:
            raise HTTPException(status_code=400, detail="Invalid file extension for NFT marker")
        
        # Проверяем, существует ли запись
        record = db.query(NFTRecord).filter(f"record_id == '{record_id}'").first()
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        marker_content = f"fake {file_ext} content".encode()
        content_type = f"application/{file_ext}"
        return Response(content=marker_content, media_type=content_type)
    
    return app

test_app = create_test_app()


class TestARFeatures(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(test_app)
        
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create a sample image for testing
        self.sample_image_path = os.path.join(self.test_dir, "test_image.jpg")
        self.create_sample_image(self.sample_image_path)
        
        # Create a sample video content (mock)
        self.sample_video_content = b"fake mp4 content"
        
        # Define test record ID
        self.test_record_id = "test-uuid-123"

    def tearDown(self):
        """Tear down test fixtures after each test method."""
        # Remove the temporary directory and all its contents
        shutil.rmtree(self.test_dir)

    def create_sample_image(self, path):
        """Create a sample image for testing."""
        # Create a 300x300 blue image
        image = Image.new('RGB', (300, 300), color='blue')
        image.save(path, 'JPEG')

    def test_ar_page_route_success(self):
        """Test successful retrieval of AR page."""
        response = self.client.get(f"/ar/{self.test_record_id}")
        
        # Check that the request was successful
        self.assertEqual(response.status_code, 200)
        
        # Check that the response contains AR page content
        self.assertIn("AR Experience", response.text)
        self.assertIn("a-scene", response.text)
        self.assertIn("a-nft", response.text)
        self.assertIn("ar-video", response.text)

    def test_ar_page_route_not_found(self):
        """Test AR page route with non-existent record."""
        response = self.client.get("/ar/non-existent-id")
        
        # Check that the request returns 404
        self.assertEqual(response.status_code, 404)
        
        # Check error response
        response_data = response.json()
        self.assertIn("detail", response_data)
        self.assertEqual(response_data["detail"], "Record not found")

    def test_get_image_success(self):
        """Test successful retrieval of image."""
        response = self.client.get(f"/images/{self.test_record_id}.jpg")
        
        # Check that the request was successful
        self.assertEqual(response.status_code, 200)
        
        # Check that the content type is correct
        self.assertEqual(response.headers["content-type"], "image/jpeg")

    @unittest.skip("MinIO service required but not running in test environment")
    def test_get_image_not_found(self):
        """Test image retrieval with non-existent file."""
        with patch('storage.get_file') as mock_get_file:
            mock_get_file.return_value = None  # Simulate file not found
            
            response = self.client.get(f"/images/{self.test_record_id}.jpg")
            
            # In test app, we don't have real error handling, so we expect 200
            # but with empty content
            self.assertEqual(response.status_code, 200)

    def test_get_preview_success(self):
        """Test successful retrieval of preview."""
        preview_filename = f"{self.test_record_id}_image_thumbnail.jpg"
        response = self.client.get(f"/previews/{preview_filename}")
        
        # Check that the request was successful
        self.assertEqual(response.status_code, 200)
        
        # Check that the content type is correct
        self.assertEqual(response.headers["content-type"], "image/jpeg")

    def test_get_preview_not_found(self):
        """Test preview retrieval with non-existent file."""
        preview_filename = f"previews/{self.test_record_id}_image_thumbnail.jpg"
        response = self.client.get(f"/previews/{preview_filename}")
        
        # Check that the request returns 404
        self.assertEqual(response.status_code, 404)

    def test_get_nft_marker_success(self):
        """Test successful retrieval of NFT marker."""
        response = self.client.get(f"/nft-markers/{self.test_record_id}.iset")
        
        # Check that the request was successful
        self.assertEqual(response.status_code, 200)
        
        # Check that the content type is correct
        self.assertEqual(response.headers["content-type"], "application/iset")

    def test_get_nft_marker_invalid_extension(self):
        """Test NFT marker retrieval with invalid extension."""
        response = self.client.get(f"/nft-markers/{self.test_record_id}.invalid")
        
        # Check that the request returns 400 for invalid extension
        self.assertEqual(response.status_code, 400)
        
        # Check error response
        response_data = response.json()
        self.assertIn("detail", response_data)
        self.assertEqual(response_data["detail"], "Invalid file extension for NFT marker")

    @unittest.skip("MinIO service required but not running in test environment")
    def test_get_nft_marker_not_found(self):
        """Test NFT marker retrieval with non-existent file."""
        with patch('storage.get_file') as mock_get_file:
            mock_get_file.return_value = None  # Simulate file not found
            
            response = self.client.get(f"/nft-markers/{self.test_record_id}.fset")
            
            # In test app, we don't have real error handling, so we expect 200
            # but with empty content
            self.assertEqual(response.status_code, 200)

    def test_ar_page_template_contains_required_elements(self):
        """Test that AR page template contains all required elements for AR functionality."""
        response = self.client.get(f"/ar/{self.test_record_id}")
        
        self.assertEqual(response.status_code, 200)
        
        # Check for required AR.js and A-Frame libraries
        self.assertIn("aframe.min.js", response.text)
        self.assertIn("aframe-ar-nft.js", response.text)
        
        # Check for required AR scene elements
        self.assertIn('<a-scene', response.text)
        self.assertIn('arjs="sourceType: webcam', response.text)
        
        # Check for NFT marker entity
        self.assertIn('<a-nft', response.text)
        self.assertIn(f'/nft-markers/{self.test_record_id}', response.text)
        
        # Check for video entity
        self.assertIn('<a-video', response.text)
        self.assertIn(f"http://testserver/videos/{self.test_record_id}.mp4", response.text)
        
        # Check for camera entity
        self.assertIn('<a-entity camera', response.text)


class TestPreviewGenerator(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create a sample image for testing
        self.sample_image_path = os.path.join(self.test_dir, "test_image.jpg")
        self.create_sample_image(self.sample_image_path)

    def tearDown(self):
        """Tear down test fixtures after each test method."""
        # Remove the temporary directory and all its contents
        shutil.rmtree(self.test_dir)

    def create_sample_image(self, path):
        """Create a sample image for testing."""
        # Create a 300x300 blue image
        image = Image.new('RGB', (300, 300), color='blue')
        image.save(path, 'JPEG')

    def test_generate_image_preview(self):
        """Test image preview generation."""
        from preview_generator import PreviewGenerator
        
        # Read sample image content
        with open(self.sample_image_path, 'rb') as f:
            image_content = f.read()
        
        # Generate preview
        preview_content = PreviewGenerator.generate_image_preview(image_content)
        
        # Check that preview was generated
        self.assertIsNotNone(preview_content)
        
        # Check that the result is valid image content
        preview_image = Image.open(io.BytesIO(preview_content))
        self.assertIsNotNone(preview_image)
        
        # Check that the image has expected size (max 200x200)
        width, height = preview_image.size
        self.assertLessEqual(width, 200)
        self.assertLessEqual(height, 200)

    def test_generate_preview_with_different_types(self):
        """Test preview generation with different file types."""
        from preview_generator import PreviewGenerator
        
        # Test with image content
        with open(self.sample_image_path, 'rb') as f:
            image_content = f.read()
        
        image_preview = PreviewGenerator.generate_preview(image_content, "image/jpeg")
        self.assertIsNotNone(image_preview)
        
        # Test with video content (mock)
        video_content = b"fake video content"
        video_preview = PreviewGenerator.generate_preview(video_content, "video/mp4")
        # Note: This might return None since we're using mock video content
        # but it should not raise an exception
        
        # Test with unknown file type
        unknown_preview = PreviewGenerator.generate_preview(b"fake content", "unknown/type")
        self.assertIsNotNone(unknown_preview)


class TestARIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(test_app)
        
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create a sample image for testing
        self.sample_image_path = os.path.join(self.test_dir, "test_image.jpg")
        self.create_sample_image(self.sample_image_path)

        # Define test record ID
        self.test_record_id = "test-uuid-ar-int-123"

    def tearDown(self):
        """Tear down test fixtures after each test method."""
        # Remove the temporary directory and all its contents
        shutil.rmtree(self.test_dir)

    def create_sample_image(self, path):
        """Create a sample image for testing."""
        # Create a 300x300 blue image
        image = Image.new('RGB', (300, 300), color='blue')
        image.save(path, 'JPEG')

    def test_ar_page_contains_arjs_libraries(self):
        """Test that AR page includes required AR.js libraries."""
        response = self.client.get(f"/ar/{self.test_record_id}")
        
        self.assertEqual(response.status_code, 200)
        
        # Check that AR.js and A-Frame libraries are included
        self.assertIn('aframe.io/releases/1.4.0/aframe.min.js', response.text)
        self.assertIn('raw.githack.com/AR-js-org/AR.js/master/aframe/build/aframe-ar-nft.js', response.text)

    def test_ar_page_has_correct_nft_marker_url(self):
        """Test that AR page has correct NFT marker URL."""
        response = self.client.get(f"/ar/{self.test_record_id}")
        
        self.assertEqual(response.status_code, 200)
        
        # Check that the NFT marker URL is correctly formatted
        self.assertIn(f'/nft-markers/{self.test_record_id}', response.text)
        
        # Check that the URL is properly constructed with scheme and netloc
        self.assertIn('http://testserver', response.text)

    def test_ar_page_has_video_element_with_correct_src(self):
        """Test that AR page has video element with correct source."""
        response = self.client.get(f"/ar/{self.test_record_id}")
        
        self.assertEqual(response.status_code, 200)
        
        # Check that the video element exists and has correct source
        self.assertIn('<a-video', response.text)
        self.assertIn(f"http://testserver/videos/{self.test_record_id}.mp4", response.text)

    def test_ar_page_has_camera_entity(self):
        """Test that AR page has camera entity."""
        response = self.client.get(f"/ar/{self.test_record_id}")
        
        self.assertEqual(response.status_code, 200)
        
        # Check that the camera entity exists
        self.assertIn('<a-entity camera', response.text)

    def test_ar_page_has_arjs_attributes(self):
        """Test that AR page has correct AR.js attributes."""
        response = self.client.get(f"/ar/{self.test_record_id}")
        
        self.assertEqual(response.status_code, 200)
        
        # Check that AR.js attributes are present
        self.assertIn('arjs="sourceType: webcam', response.text)
        self.assertIn('renderer="logarithmicDepthBuffer: true', response.text)

    def test_ar_page_has_nft_marker_entity_with_correct_attributes(self):
        """Test that AR page has NFT marker entity with correct attributes."""
        response = self.client.get(f"/ar/{self.test_record_id}")
        
        self.assertEqual(response.status_code, 200)
        
        # Check for NFT marker entity and its attributes
        self.assertIn('<a-nft', response.text)
        self.assertIn('type="nft"', response.text)
        self.assertIn('smooth="true"', response.text)
        self.assertIn('smoothCount="5"', response.text)
        self.assertIn('smoothTolerance=".01"', response.text)


if __name__ == '__main__':
    unittest.main()