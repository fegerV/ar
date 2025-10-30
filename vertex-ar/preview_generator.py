from PIL import Image
import os
import tempfile
from io import BytesIO
import mimetypes
from storage_local import local_storage as storage
import uuid
import logging
from typing import Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PreviewGenerator:
    """Класс для генерации превью для различных типов файлов"""
    
    @staticmethod
    def generate_image_preview(image_content: bytes, size=(200, 200)) -> Optional[bytes]:
        """Генерирует превью для изображений"""
        logger.info(f"Начинаем генерацию превью для изображения, размер: {len(image_content)} байт")
        try:
            # Открываем изображение
            image = Image.open(BytesIO(image_content))
            logger.info(f"Изображение успешно открыто, размеры: {image.size}")
            
            # Сохраняем оригинальные размеры
            original_width, original_height = image.size
            
            # Создаем превью с сохранением пропорций
            image.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Создаем новое изображение с белым фоном
            preview = Image.new('RGB', size, (255, 255, 255))
            
            # Вычисляем позицию для центрирования изображения
            x = (size[0] - image.size[0]) // 2
            y = (size[1] - image.size[1]) // 2
            
            # Вставляем изображение в центр
            preview.paste(image, (x, y))
            
            # Сохраняем превью в байтовый буфер
            buffer = BytesIO()
            preview.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            
            return buffer.getvalue()
        except Exception as e:
            logger.exception(f"Ошибка при генерации превью изображения: {e}")
            return None
    
    @staticmethod
    def generate_video_preview(video_content: bytes, size=(200, 200), frame_time=1.0) -> Optional[bytes]:
        """Генерирует превью для видео (использует заглушку без OpenCV)"""
        logger.info(f"Начинаем генерацию превью для видео, размер: {len(video_content)} байт")
        logger.info("Используем заглушку для превью видео (OpenCV отключен)")
        return PreviewGenerator.generate_video_preview_stub(size)
    
    @staticmethod
    def generate_video_preview_stub(size=(200, 200)) -> Optional[bytes]:
        """Создает заглушку для превью видео"""
        try:
            # Создаем стандартное изображение-заглушку для видео
            preview = Image.new('RGB', size, (30, 30))  # Темный фон
            
            # Добавляем символ воспроизведения
            from PIL import ImageDraw
            draw = ImageDraw.Draw(preview)
            
            # Рисуем треугольник как символ воспроизведения
            center_x, center_y = size[0] // 2, size[1] // 2
            triangle_size = min(size) // 4
            triangle_points = [
                (center_x - triangle_size//2, center_y - triangle_size//2),  # Левая точка
                (center_x - triangle_size//2, center_y + triangle_size//2),  # Нижняя точка
                (center_x + triangle_size//2, center_y)                     # Правая точка
            ]
            draw.polygon(triangle_points, fill=(255, 255, 255))  # Белый треугольник
            
            # Сохраняем превью в байтовый буфер
            buffer = BytesIO()
            preview.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Ошибка при генерации заглушки превью видео: {e}")
            return None
    
    @staticmethod
    def generate_document_preview(document_content: bytes, size=(200, 200)) -> Optional[bytes]:
        """Генерирует превью для документов (пока просто заглушка)"""
        try:
            # Для документов создаем стандартное изображение-заглушку
            preview = Image.new('RGB', size, (240, 240, 240))
            
            # Добавляем символ документа (условно)
            # В реальной реализации можно использовать шрифты или изображения
            from PIL import ImageDraw, ImageFont
            
            draw = ImageDraw.Draw(preview)
            
            # Рисуем прямоугольник с закругленными углами как иконку документа
            draw.rounded_rectangle([50, 50, 150, 150], radius=10, fill=(20, 200, 200), outline=(150, 150, 150), width=2)
            
            # Рисуем несколько линий как текст документа
            for i in range(3):
                y_pos = 70 + i * 15
                draw.line([70, y_pos, 130, y_pos], fill=(100, 100, 100), width=2)
            
            # Сохраняем превью в байтовый буфер
            buffer = BytesIO()
            preview.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Ошибка при генерации превью документа: {e}")
            return None
    
    @staticmethod
    def generate_preview(file_content: bytes, file_type: str, size=(200, 200)) -> Optional[bytes]:
        """Основной метод для генерации превью в зависимости от типа файла"""
        if file_type.startswith('image/'):
            return PreviewGenerator.generate_image_preview(file_content, size)
        elif file_type.startswith('video/'):
            return PreviewGenerator.generate_video_preview(file_content, size)
        elif file_type in ['application/pdf', 'application/msword',
                          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                          'application/vnd.ms-powerpoint',
                          'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                          'application/vnd.ms-excel',
                          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                          'text/plain', 'text/csv']:
            return PreviewGenerator.generate_document_preview(file_content, size)
        else:
            # Для неизвестных типов файлов создаем стандартную заглушку
            return PreviewGenerator.generate_document_preview(file_content, size)


def generate_and_save_preview(file_content: bytes, file_type: str, record_id: str, preview_type: str = "thumbnail") -> Optional[str]:
    """Генерирует и сохраняет превью в MinIO"""
    try:
        logger.info(f"Начинаем генерацию превью для {record_id}, тип: {file_type}, подтип: {preview_type}")
        
        # Генерируем превью
        preview_content = PreviewGenerator.generate_preview(file_content, file_type)
        
        if preview_content:
            logger.info(f"Превью успешно сгенерировано для {record_id}, размер: {len(preview_content)} байт")
            
            # Определяем имя объекта для превью
            preview_filename = f"previews/{record_id}_{preview_type}.jpg"
            logger.info(f"Пытаемся сохранить превью с именем: {preview_filename}")
            
            # Загружаем превью в хранилище
            result = storage.upload_file(preview_content, preview_filename, "image/jpeg")
            
            if result:
                logger.info(f"Превью успешно сохранено: {preview_filename}")
                return preview_filename
            else:
                logger.error(f"Не удалось сохранить превью: {preview_filename}")
                return None
        else:
            logger.error(f"Не удалось сгенерировать превью для {record_id}, тип файла: {file_type}")
            return None
    except Exception as e:
        logger.exception(f"Ошибка при генерации и сохранении превью: {e}")
        return None