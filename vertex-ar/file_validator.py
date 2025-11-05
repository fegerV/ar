import magic
import imghdr
from PIL import Image
from io import BytesIO
from typing import Tuple

from logging_setup import get_logger

logger = get_logger(__name__)

class FileValidator:
    """Класс для валидации файлов различных типов"""
    
    @staticmethod
    def validate_image_content(content: bytes, min_dimension: int = 1024) -> Tuple[bool, str]:
        """
        Проверяет, что содержимое действительно является изображением
        Возвращает (успех, сообщение об ошибке)
        """
        try:
            # Используем python-magic для проверки типа файла
            file_type = magic.from_buffer(content, mime=True)
            if file_type not in ['image/jpeg', 'image/png']:
                return False, f"Недопустимый тип изображения: {file_type}"
            
            # Дополнительная проверка с помощью PIL
            image = Image.open(BytesIO(content))
            width, height = image.size
            
            if width < min_dimension and height < min_dimension:
                return False, f"Изображение слишком маленькое. Минимальный размер: {min_dimension}px по одной стороне"
            
            # Проверяем, что изображение не повреждено
            image.verify()
                
            return True, ""
        except Exception as e:
            logger.error(f"Ошибка при валидации изображения: {e}")
            return False, f"Изображение повреждено или недействительно: {str(e)}"
    
    @staticmethod
    def validate_video_content(content: bytes) -> Tuple[bool, str]:
        """
        Проверяет, что содержимое действительно является MP4 видео
        Возвращает (успех, сообщение об ошибке)
        """
        try:
            # Используем python-magic для проверки типа видеофайла
            file_type = magic.from_buffer(content, mime=True)
            if file_type != 'video/mp4':
                return False, f"Недопустимый тип видео: {file_type}, ожидается video/mp4"
            
            # Резервная проверка по сигнатуре MP4 файла
            if len(content) < 12:
                return False, "Файл видео слишком мал"
            
            # Проверяем заголовок MP4 файла (обычно начинается с размера и сигнатуры)
            # MP4 файлы часто начинаются с определенных байтов сигнатуры
            if content[4:8] == b'ftyp':
                # Проверяем, что тип файла - mp4
                brand = content[8:12]
                valid_brands = [b'mp41', b'mp42', b'isom', b'MP42']
                if brand in valid_brands:
                    return True, ""
                else:
                    return False, f"Недопустимый тип MP4 бренда: {brand}"
            return False, "Файл не является действительным MP4 видео"
        except Exception as e:
            logger.error(f"Ошибка при валидации видео: {e}")
            return False, f"Видео повреждено или недействительно: {str(e)}"
    
    @staticmethod
    def get_safe_file_type(file_content: bytes, original_filename: str = None) -> str:
        """Безопасно определяет тип файла по содержимому"""
        try:
            # Используем python-magic для определения типа файла по содержимому
            mime_type = magic.from_buffer(file_content, mime=True)
            if mime_type:
                return mime_type
        except Exception:
            pass
        
        # Резервная проверка с помощью других методов
        # Сначала проверяем изображения
        image_type = imghdr.what(None, file_content)
        if image_type:
            return f"image/{image_type}"
        
        # Для видео используем специальную проверку
        if FileValidator._is_video_content(file_content):
            return "video/mp4"
        
        # Если не удалось определить по содержимому, используем mimetype по имени файла
        if original_filename:
            import mimetypes
            detected_mime_type, _ = mimetypes.guess_type(original_filename)
            if detected_mime_type:
                return detected_mime_type
        
        return "application/octet-stream"
    
    @staticmethod
    def _is_video_content(content: bytes) -> bool:
        """Внутренний метод для проверки, является ли контент видео"""
        try:
            if content[4:8] == b'ftyp':
                brand = content[8:12]
                valid_brands = [b'mp41', b'mp42', b'isom', b'MP42']
                return brand in valid_brands
        except Exception:
            pass
        return False