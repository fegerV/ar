#!/usr/bin/env python3
"""
Тестирование генерации превью из реального видеофайла
"""
import os
import sys
from pathlib import Path

# Добавляем путь к vertex-ar в sys.path
sys.path.insert(0, str(Path(__file__).parent / "vertex-ar"))

from preview_generator import PreviewGenerator
from PIL import Image
from io import BytesIO
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_real_video_preview():
    """Тест генерации превью из реального видеофайла"""
    logger.info("=== Тест генерации превью из реального видео ===")
    
    video_path = "test_video.mp4"
    
    if not os.path.exists(video_path):
        logger.error(f"Видеофайл не найден: {video_path}")
        return False
    
    # Читаем видеофайл
    with open(video_path, "rb") as f:
        video_content = f.read()
    
    logger.info(f"Видеофайл прочитан, размер: {len(video_content)} байт")
    
    # Генерируем превью
    preview = PreviewGenerator.generate_video_preview(video_content)
    
    if preview:
        logger.info(f"✅ Превью видео успешно сгенерировано, размер: {len(preview)} байт")
        
        # Проверяем размер превью
        preview_image = Image.open(BytesIO(preview))
        logger.info(f"Размеры превью: {preview_image.size}")
        
        # Сохраняем превью для визуальной проверки
        with open("test_real_video_preview.jpg", "wb") as f:
            f.write(preview)
        logger.info("Превью сохранено в файл test_real_video_preview.jpg")
        
        return True
    else:
        logger.error("❌ Не удалось сгенерировать превью видео")
        return False


def main():
    """Основная функция тестирования"""
    logger.info("Начинаем тестирование генерации превью из реального видео...")
    
    result = test_real_video_preview()
    
    # Выводим итоговые результаты
    logger.info("\n=== Итоги тестирования ===")
    status = "✅ УСПЕХ" if result else "❌ ОШИБКА"
    logger.info(f"Реальное видео: {status}")
    
    if result:
        logger.info("🎉 Тест пройден успешно!")
        return 0
    else:
        logger.error("❌ Тест не пройден")
        return 1


if __name__ == "__main__":
    sys.exit(main())
