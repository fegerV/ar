from PIL import Image
import os
import tempfile
from io import BytesIO
import mimetypes
from storage_adapter import get_storage
import uuid
from typing import Optional, Dict
import cv2
import numpy as np

from logging_setup import get_logger

logger = get_logger(__name__)


class PreviewGenerator:
    """Класс для генерации превью для различных типов файлов"""
    
    # Оптимизированные размеры превью для современных интерфейсов
    DEFAULT_THUMBNAIL_SIZE = (300, 300)  # Увеличено с 120x120 для лучшего UX
    SMALL_THUMBNAIL_SIZE = (150, 150)    # Для списков и мобильных устройств
    LARGE_THUMBNAIL_SIZE = (500, 500)    # Для детальных представлений
    
    # Оптимизированное качество для баланса размера и качества
    OPTIMAL_JPEG_QUALITY = 78  # Снижено с 90% для уменьшения размера файла
    
    @staticmethod
    def generate_image_preview(image_content: bytes, size=None, format='JPEG') -> Optional[bytes]:
        """Генерирует оптимизированное превью для изображений"""
        if size is None:
            size = PreviewGenerator.DEFAULT_THUMBNAIL_SIZE
            
        logger.info(f"Начинаем генерацию превью для изображения, размер: {len(image_content)} байт, целевой размер: {size}")
        try:
            # Открываем изображение
            image = Image.open(BytesIO(image_content))
            logger.info(f"Изображение успешно открыто, размеры: {image.size}, формат: {image.format}")
            
            # Конвертируем в RGB если необходимо (для PNG с альфа-каналом)
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                image = background
            
            # Сохраняем оригинальные размеры
            original_width, original_height = image.size
            
            # Оптимизация: если изображение уже меньше нужного размера, не увеличиваем его
            if original_width <= size[0] and original_height <= size[1]:
                logger.info(f"Изображение уже имеет оптимальный размер, используем оригинал")
                preview = image.copy()
            else:
                # Создаем превью с сохранением пропорций используя LANCZOS для лучшего качества
                image_copy = image.copy()
                image_copy.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Создаем новое изображение с белым фоном
                preview = Image.new('RGB', size, (255, 255, 255))
                
                # Вычисляем позицию для центрирования изображения
                x = (size[0] - image_copy.size[0]) // 2
                y = (size[1] - image_copy.size[1]) // 2
                
                # Вставляем изображение в центр
                preview.paste(image_copy, (x, y))
            
            # Сохраняем превью в байтовый буфер с оптимизированными настройками
            buffer = BytesIO()
            
            if format.upper() == 'WEBP':
                # Используем WebP для лучшей компрессии
                preview.save(buffer, format='WEBP', quality=80, method=6)
            else:
                # Используем progressive JPEG с оптимизированным качеством
                preview.save(buffer, format='JPEG', quality=PreviewGenerator.OPTIMAL_JPEG_QUALITY, progressive=True)
            
            buffer.seek(0)
            
            logger.info(f"Превью изображения успешно сгенерировано, формат: {format}, размер превью: {len(buffer.getvalue())} байт")
            return buffer.getvalue()
        except Exception as e:
            logger.exception(f"Ошибка при генерации превью изображения: {e}")
            return None
    
    @staticmethod
    def generate_video_preview(video_content: bytes, size=None, frame_time=None, format='JPEG') -> Optional[bytes]:
        """Генерирует оптимизированное превью для видео, извлекая кадр из середины"""
        if size is None:
            size = PreviewGenerator.DEFAULT_THUMBNAIL_SIZE
            
        logger.info(f"Начинаем генерацию превью для видео, размер: {len(video_content)} байт, целевой размер: {size}")
        
        try:
            # Сохраняем видео во временный файл
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
                temp_video.write(video_content)
                temp_video_path = temp_video.name
            
            try:
                # Открываем видео с помощью OpenCV
                cap = cv2.VideoCapture(temp_video_path)
                
                if not cap.isOpened():
                    logger.error("Не удалось открыть видео с помощью OpenCV")
                    return PreviewGenerator.generate_video_preview_stub(size, format)
                
                # Получаем общее количество кадров
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                
                logger.info(f"Видео открыто успешно: всего кадров={total_frames}, FPS={fps}")
                
                if total_frames <= 0:
                    logger.error("Видео не содержит кадров")
                    return PreviewGenerator.generate_video_preview_stub(size, format)
                
                # Вычисляем номер кадра из середины видео
                middle_frame = total_frames // 2
                
                # Устанавливаем позицию на середину видео
                cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)
                
                # Читаем кадр
                ret, frame = cap.read()
                
                if not ret or frame is None:
                    logger.error(f"Не удалось прочитать кадр {middle_frame} из видео")
                    # Пробуем первый кадр как fallback
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        logger.error("Не удалось прочитать даже первый кадр")
                        return PreviewGenerator.generate_video_preview_stub(size, format)
                
                logger.info(f"Кадр успешно извлечен, размер: {frame.shape}")
                
                # Оптимизация: применяем небольшое размытие для уменьшения артефактов сжатия
                frame_blurred = cv2.GaussianBlur(frame, (3, 3), 0.5)
                
                # Конвертируем BGR (OpenCV) в RGB (PIL)
                frame_rgb = cv2.cvtColor(frame_blurred, cv2.COLOR_BGR2RGB)
                
                # Конвертируем numpy array в PIL Image
                pil_image = Image.fromarray(frame_rgb)
                
                # Оптимизация: если кадр уже меньше нужного размера, не увеличиваем его
                if pil_image.size[0] <= size[0] and pil_image.size[1] <= size[1]:
                    preview = pil_image.copy()
                    # Создаем фон нужного размера
                    background = Image.new('RGB', size, (0, 0, 0))
                    x = (size[0] - preview.size[0]) // 2
                    y = (size[1] - preview.size[1]) // 2
                    background.paste(preview, (x, y))
                    preview = background
                else:
                    # Создаем превью с сохранением пропорций
                    pil_image.thumbnail(size, Image.Resampling.LANCZOS)
                    
                    # Создаем новое изображение с черным фоном (для видео)
                    preview = Image.new('RGB', size, (0, 0, 0))
                    
                    # Вычисляем позицию для центрирования
                    x = (size[0] - pil_image.size[0]) // 2
                    y = (size[1] - pil_image.size[1]) // 2
                    
                    # Вставляем кадр в центр
                    preview.paste(pil_image, (x, y))
                
                # Добавляем иконку воспроизведения поверх превью
                from PIL import ImageDraw
                draw = ImageDraw.Draw(preview)
                
                # Рисуем полупрозрачный круг в центре
                center_x, center_y = size[0] // 2, size[1] // 2
                circle_radius = min(size) // 8
                
                # Рисуем улучшенный треугольник воспроизведения
                triangle_size = circle_radius
                triangle_points = [
                    (center_x - triangle_size//2, center_y - triangle_size//2),  # Левая точка
                    (center_x - triangle_size//2, center_y + triangle_size//2),  # Нижняя точка
                    (center_x + triangle_size//2, center_y)                     # Правая точка
                ]
                draw.polygon(triangle_points, fill=(255, 255, 255))  # Белый треугольник
                
                # Сохраняем превью в байтовый буфер с оптимизированными настройками
                buffer = BytesIO()
                
                if format.upper() == 'WEBP':
                    preview.save(buffer, format='WEBP', quality=75, method=6)
                else:
                    preview.save(buffer, format='JPEG', quality=PreviewGenerator.OPTIMAL_JPEG_QUALITY - 5, progressive=True)
                
                buffer.seek(0)
                
                logger.info(f"Превью видео успешно сгенерировано из кадра {middle_frame}, формат: {format}, размер превью: {len(buffer.getvalue())} байт")
                return buffer.getvalue()
                
            finally:
                # Освобождаем ресурсы
                if 'cap' in locals():
                    cap.release()
                # Удаляем временный файл
                try:
                    os.unlink(temp_video_path)
                except:
                    pass
                    
        except Exception as e:
            logger.exception(f"Ошибка при генерации превью видео: {e}")
            logger.info("Используем заглушку для превью видео")
            return PreviewGenerator.generate_video_preview_stub(size, format)
    
    @staticmethod
    def generate_video_preview_stub(size=None, format='JPEG') -> Optional[bytes]:
        """Создает оптимизированную заглушку для превью видео"""
        if size is None:
            size = PreviewGenerator.DEFAULT_THUMBNAIL_SIZE
            
        try:
            # Создаем стандартное изображение-заглушку для видео
            preview = Image.new('RGB', size, (30, 30, 30))  # Темный фон
            
            # Добавляем символ воспроизведения
            from PIL import ImageDraw
            draw = ImageDraw.Draw(preview)
            
            # Рисуем улучшенный треугольник как символ воспроизведения
            center_x, center_y = size[0] // 2, size[1] // 2
            triangle_size = min(size) // 4
            triangle_points = [
                (center_x - triangle_size//2, center_y - triangle_size//2),  # Левая точка
                (center_x - triangle_size//2, center_y + triangle_size//2),  # Нижняя точка
                (center_x + triangle_size//2, center_y)                     # Правая точка
            ]
            draw.polygon(triangle_points, fill=(255, 255, 255))  # Белый треугольник
            
            # Сохраняем превью в байтовый буфер с оптимизированными настройками
            buffer = BytesIO()
            
            if format.upper() == 'WEBP':
                preview.save(buffer, format='WEBP', quality=70, method=6)
            else:
                preview.save(buffer, format='JPEG', quality=PreviewGenerator.OPTIMAL_JPEG_QUALITY - 10, progressive=True)
            
            buffer.seek(0)
            
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Ошибка при генерации заглушки превью видео: {e}")
            return None
    
    @staticmethod
    def generate_document_preview(document_content: bytes, size=None, format='JPEG') -> Optional[bytes]:
        """Генерирует оптимизированное превью для документов (пока просто заглушка)"""
        if size is None:
            size = PreviewGenerator.DEFAULT_THUMBNAIL_SIZE
            
        try:
            # Для документов создаем стандартное изображение-заглушку
            preview = Image.new('RGB', size, (240, 240, 240))
            
            # Добавляем символ документа (условно)
            # В реальной реализации можно использовать шрифты или изображения
            from PIL import ImageDraw, ImageFont
            
            draw = ImageDraw.Draw(preview)
            
            # Рисуем прямоугольник с закругленными углами как иконку документа
            margin = min(size) // 8
            draw.rounded_rectangle(
                [margin, margin, size[0] - margin, size[1] - margin], 
                radius=10, 
                fill=(20, 200, 200), 
                outline=(150, 150, 150), 
                width=2
            )
            
            # Рисуем несколько линий как текст документа
            for i in range(3):
                y_pos = margin * 2 + i * (size[1] - margin * 4) // 4
                line_width = size[0] - margin * 4
                draw.line([margin * 2, y_pos, margin * 2 + line_width, y_pos], fill=(100, 100, 100), width=2)
            
            # Сохраняем превью в байтовый буфер с оптимизированными настройками
            buffer = BytesIO()
            
            if format.upper() == 'WEBP':
                preview.save(buffer, format='WEBP', quality=70, method=6)
            else:
                preview.save(buffer, format='JPEG', quality=PreviewGenerator.OPTIMAL_JPEG_QUALITY - 15, progressive=True)
            
            buffer.seek(0)
            
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Ошибка при генерации превью документа: {e}")
            return None
    
    @staticmethod
    def generate_preview(file_content: bytes, file_type: str, size=None, format='JPEG') -> Optional[bytes]:
        """Основной метод для генерации превью в зависимости от типа файла"""
        if size is None:
            size = PreviewGenerator.DEFAULT_THUMBNAIL_SIZE
            
        if file_type.startswith('image/'):
            return PreviewGenerator.generate_image_preview(file_content, size, format)
        elif file_type.startswith('video/'):
            return PreviewGenerator.generate_video_preview(file_content, size, format=format)
        elif file_type in ['application/pdf', 'application/msword',
                          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                          'application/vnd.ms-powerpoint',
                          'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                          'application/vnd.ms-excel',
                          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                          'text/plain', 'text/csv']:
            return PreviewGenerator.generate_document_preview(file_content, size, format)
        else:
            # Для неизвестных типов файлов создаем стандартную заглушку
            return PreviewGenerator.generate_document_preview(file_content, size, format)

    @staticmethod
    def generate_multiple_sizes(file_content: bytes, file_type: str, formats=('JPEG', 'WEBP')) -> Dict[str, bytes]:
        """Генерирует превью в нескольких размерах и форматах для оптимальной производительности"""
        results = {}
        
        for format_name in formats:
            for size_name, size_tuple in [('small', PreviewGenerator.SMALL_THUMBNAIL_SIZE),
                                         ('default', PreviewGenerator.DEFAULT_THUMBNAIL_SIZE),
                                         ('large', PreviewGenerator.LARGE_THUMBNAIL_SIZE)]:
                preview = PreviewGenerator.generate_preview(file_content, file_type, size_tuple, format_name)
                if preview:
                    key = f"{size_name}_{format_name.lower()}"
                    results[key] = preview
                    logger.info(f"Generated preview: {key}, size: {len(preview)} bytes")
        
        return results


def generate_and_save_preview(file_content: bytes, file_type: str, record_id: str, preview_type: str = "thumbnail", size=None, format='JPEG') -> Optional[str]:
    """Генерирует и сохраняет оптимизированное превью в хранилище"""
    try:
        if size is None:
            size = PreviewGenerator.DEFAULT_THUMBNAIL_SIZE
            
        logger.info(f"Начинаем генерацию превью для {record_id}, тип: {file_type}, подтип: {preview_type}, размер: {size}, формат: {format}")
        
        # Генерируем превью
        preview_content = PreviewGenerator.generate_preview(file_content, file_type, size, format)
        
        if preview_content:
            logger.info(f"Превью успешно сгенерировано для {record_id}, размер: {len(preview_content)} байт")
            
            # Определяем имя объекта для превью с учетом формата
            extension = 'jpg' if format.upper() == 'JPEG' else format.lower()
            preview_filename = f"previews/{record_id}_{preview_type}_{size[0]}x{size[1]}.{extension}"
            logger.info(f"Пытаемся сохранить превью с именем: {preview_filename}")
            
            # Определяем MIME тип
            mime_type = f"image/{format.lower()}" if format.upper() != 'JPEG' else "image/jpeg"
            
            # Загружаем превью в хранилище
            storage = get_storage()
            result = storage.upload_file(preview_content, preview_filename, mime_type)
            
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


def generate_and_save_multiple_previews(file_content: bytes, file_type: str, record_id: str) -> Dict[str, str]:
    """Генерирует и сохраняет превью в нескольких размерах и форматах"""
    try:
        logger.info(f"Начинаем генерацию множественных превью для {record_id}, тип: {file_type}")
        
        # Генерируем превью в разных размерах и форматах
        preview_data = PreviewGenerator.generate_multiple_sizes(file_content, file_type)
        
        saved_previews = {}
        
        for key, content in preview_data.items():
            # Определяем имя файла
            preview_filename = f"previews/{record_id}_{key}.jpg" if 'jpeg' in key else f"previews/{record_id}_{key}.webp"
            
            # Определяем MIME тип
            mime_type = "image/jpeg" if 'jpeg' in key else "image/webp"
            
            # Загружаем превью в хранилище
            storage = get_storage()
            result = storage.upload_file(content, preview_filename, mime_type)
            
            if result:
                saved_previews[key] = preview_filename
                logger.info(f"Сохранено превью: {preview_filename}, размер: {len(content)} байт")
            else:
                logger.error(f"Не удалось сохранить превью: {preview_filename}")
        
        logger.info(f"Успешно сохранено {len(saved_previews)} превью для {record_id}")
        return saved_previews
        
    except Exception as e:
        logger.exception(f"Ошибка при генерации и сохранении множественных превью: {e}")
        return {}