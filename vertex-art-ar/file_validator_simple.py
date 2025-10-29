import os
from typing import Tuple, Optional
import logging
from PIL import Image
import cv2
import tempfile

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileValidator:
    """Упрощенный валидатор файлов без использования python-magic"""
    
    @staticmethod
    def get_safe_file_type(file_content: bytes, filename: str) -> str:
        """Определяет тип файла на основе расширения и содержимого"""
        # Сначала определяем по расширению
        _, ext = os.path.splitext(filename.lower())
        
        if ext in ['.jpg', '.jpeg']:
            return "image/jpeg"
        elif ext in ['.png']:
            return "image/png"
        elif ext in ['.mp4']:
            return "video/mp4"
        else:
            # Если расширение неизвестно, пытаемся определить по содержимому
            return FileValidator._detect_content_type(file_content)
    
    @staticmethod
    def _detect_content_type(file_content: bytes) -> str:
        """Определяет тип файла по содержимому"""
        # Проверяем JPEG
        if file_content[:3] == b'\xff\xd8\xff':
            return "image/jpeg"
        
        # Проверяем PNG
        if file_content[:8] == b'\x89PNG\r\n\x1a\n':
            return "image/png"
        
        # Проверяем MP4 (обычно начинается с определенного заголовка)
        if b'ftyp' in file_content[:32]:
            return "video/mp4"
        
        return "application/octet-stream"  # неизвестный тип
    
    @staticmethod
    def validate_image_content(image_content: bytes) -> Tuple[bool, Optional[str]]:
        """Валидирует содержимое изображения"""
        try:
            # Создаем временный файл для проверки изображения
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_file.write(image_content)
                temp_path = temp_file.name
            
            # Пытаемся открыть изображение с помощью PIL
            with Image.open(temp_path) as img:
                # Проверяем, что изображение можно открыть и получить размеры
                width, height = img.size
                logger.info(f"Image validation successful: {width}x{height}")
                
            # Удаляем временный файл
            os.unlink(temp_path)
            return True, None
            
        except Exception as e:
            logger.error(f"Image validation failed: {str(e)}")
            # Удаляем временный файл, если он был создан
            try:
                os.unlink(temp_path)
            except:
                pass
            return False, f"Invalid image content: {str(e)}"
    
    @staticmethod
    def validate_video_content(video_content: bytes) -> Tuple[bool, Optional[str]]:
        """Валидирует содержимое видео"""
        try:
            # Создаем временный файл для проверки видео
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                temp_file.write(video_content)
                temp_path = temp_file.name
            
            # Пытаемся открыть видео с помощью OpenCV
            cap = cv2.VideoCapture(temp_path)
            
            if not cap.isOpened():
                logger.error("Could not open video file")
                cap.release()
                os.unlink(temp_path)
                return False, "Invalid video file"
            
            # Проверяем, что видео содержит кадры
            ret, frame = cap.read()
            if not ret:
                logger.error("Could not read video frames")
                cap.release()
                os.unlink(temp_path)
                return False, "Video file contains no frames"
            
            # Получаем параметры видео
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            logger.info(f"Video validation successful: {width}x{height}, {fps}fps, {frame_count} frames")
            
            cap.release()
            os.unlink(temp_path)
            return True, None
            
        except Exception as e:
            logger.error(f"Video validation failed: {str(e)}")
            # Удаляем временный файл, если он был создан
            try:
                os.unlink(temp_path)
            except:
                pass
            return False, f"Invalid video content: {str(e)}"