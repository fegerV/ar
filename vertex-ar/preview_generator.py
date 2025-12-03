from PIL import Image
import os
import tempfile
from io import BytesIO
import mimetypes
from storage_adapter import get_storage
import uuid
from typing import Optional
import cv2
import numpy as np

from logging_setup import get_logger

logger = get_logger(__name__)


def normalize_path(path: str) -> str:
    """
    Normalize a path to use forward slashes consistently.

    Args:
        path: Path string to normalize

    Returns:
        Normalized path string with forward slashes
    """
    # Replace backslashes with forward slashes for consistent storage
    return path.replace("\\", "/")


class PreviewGenerator:
    """Класс для генерации превью для различных типов файлов"""

    @staticmethod
    def generate_image_preview(image_content: bytes, size=(300, 300), format='webp') -> Optional[bytes]:
        """Генерирует превью для изображений с улучшенным качеством и поддержкой WebP"""
        logger.info(f"Начинаем генерацию превью для изображения, размер: {len(image_content)} байт, целевой размер: {size}, формат: {format}")
        try:
            # Открываем изображение
            image = Image.open(BytesIO(image_content))
            logger.info(f"Изображение успешно открыто, размеры: {image.size}, формат: {image.format}")

            # Конвертируем в RGB если необходимо
            if image.mode in ('RGBA', 'LA', 'P'):
                # Создаем белый фон для полупрозрачных изображений
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background

            # Создаем превью с сохранением пропорций и высоким качеством
            image.thumbnail(size, Image.Resampling.LANCZOS)

            # Создаем новое изображение с белым фоном
            preview = Image.new('RGB', size, (255, 255, 255))

            # Вычисляем позицию для центрирования изображения
            x = (size[0] - image.size[0]) // 2
            y = (size[1] - image.size[1]) // 2

            # Вставляем изображение в центр
            preview.paste(image, (x, y))

            # Сохраняем превью в байтовый буфер с оптимальными настройками
            buffer = BytesIO()

            if format.lower() == 'webp':
                # WebP с лучшим сжатием
                preview.save(buffer, format='WEBP', quality=85, method=6)
            else:
                # JPEG с высоким качеством
                preview.save(buffer, format='JPEG', quality=92, optimize=True)

            buffer.seek(0)

            logger.info(f"Превью изображения успешно сгенерировано, формат: {format}, размер превью: {len(buffer.getvalue())} байт")
            return buffer.getvalue()
        except Exception as e:
            logger.exception(f"Ошибка при генерации превью изображения: {e}")
            return None

    @staticmethod
    def generate_video_preview(video_content: bytes, size=(300, 300), frame_time=None, format='webp') -> Optional[bytes]:
        """Генерирует превью для видео с улучшенным качеством и поддержкой WebP"""

        # Validate input
        if not video_content or len(video_content) == 0:
            logger.error("Пустое видео содержимое")
            return PreviewGenerator.generate_video_preview_stub(size, format)

        logger.info(f"Начинаем генерацию превью для видео, размер: {len(video_content)} байт, целевой размер: {size}, формат: {format}")

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

                # Применяем небольшой размытие для уменьшения артефактов сжатия
                frame = cv2.GaussianBlur(frame, (3, 3), 0)

                # Конвертируем BGR (OpenCV) в RGB (PIL)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Конвертируем numpy array в PIL Image
                pil_image = Image.fromarray(frame_rgb)

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

                # Рисуем треугольник воспроизведения
                triangle_size = circle_radius
                triangle_points = [
                    (center_x - triangle_size//2, center_y - triangle_size//2),  # Левая точка
                    (center_x - triangle_size//2, center_y + triangle_size//2),  # Нижняя точка
                    (center_x + triangle_size//2, center_y)                     # Правая точка
                ]
                draw.polygon(triangle_points, fill=(255, 255, 255))  # Белый треугольник

                # Сохраняем превью в байтовый буфер
                buffer = BytesIO()

                if format.lower() == 'webp':
                    # WebP с лучшим сжатием
                    preview.save(buffer, format='WEBP', quality=85, method=6)
                else:
                    # JPEG с высоким качеством
                    preview.save(buffer, format='JPEG', quality=92, optimize=True)

                buffer.seek(0)
                preview_bytes = buffer.getvalue()

                # Validate the generated preview
                if len(preview_bytes) == 0:
                    logger.error("Сгенерированное превью видео имеет нулевой размер")
                    return PreviewGenerator.generate_video_preview_stub(size, format)

                logger.info(f"Превью видео успешно сгенерировано из кадра {middle_frame}, формат: {format}, размер превью: {len(preview_bytes)} байт")
                return preview_bytes

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
    def generate_video_preview_stub(size=(300, 300), format='webp') -> Optional[bytes]:
        """Создает заглушку для превью видео с поддержкой WebP"""
        try:
            # Создаем стандартное изображение-заглушку для видео
            preview = Image.new('RGB', size, (30, 30, 30))  # Темный фон

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

            if format.lower() == 'webp':
                preview.save(buffer, format='WEBP', quality=85, method=6)
            else:
                preview.save(buffer, format='JPEG', quality=92, optimize=True)

            buffer.seek(0)
            preview_bytes = buffer.getvalue()

            # Validate the generated stub
            if len(preview_bytes) == 0:
                logger.error("Заглушка превью видео имеет нулевой размер")
                return None

            return preview_bytes
        except Exception as e:
            logger.error(f"Ошибка при генерации заглушки превью видео: {e}")
            return None

    @staticmethod
    def generate_document_preview(document_content: bytes, size=(120, 120)) -> Optional[bytes]:
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
    def generate_preview(file_content: bytes, file_type: str, size=(300, 300), format='webp') -> Optional[bytes]:
        """Основной метод для генерации превью в зависимости от типа файла с поддержкой WebP"""
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
            return PreviewGenerator.generate_document_preview(file_content, size)
        else:
            # Для неизвестных типов файлов создаем стандартную заглушку
            return PreviewGenerator.generate_document_preview(file_content, size)


def generate_and_save_preview(file_content: bytes, file_type: str, record_id: str, preview_type: str = "thumbnail", size=(300, 300), format='webp') -> Optional[str]:
    """Генерирует и сохраняет превью в хранилище с поддержкой WebP"""
    try:
        logger.info(f"Начинаем генерацию превью для {record_id}, тип: {file_type}, подтип: {preview_type}, размер: {size}, формат: {format}")

        # Генерируем превью
        preview_content = PreviewGenerator.generate_preview(file_content, file_type, size, format)

        if preview_content:
            logger.info(f"Превью успешно сгенерировано для {record_id}, размер: {len(preview_content)} байт")

            # Определяем имя объекта для превью с правильным расширением
            extension = 'webp' if format.lower() == 'webp' else 'jpg'
            preview_filename = f"previews/{record_id}_{preview_type}.{extension}"
            logger.info(f"Пытаемся сохранить превью с именем: {preview_filename}")

            # Определяем MIME тип
            mime_type = "image/webp" if format.lower() == 'webp' else "image/jpeg"

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
