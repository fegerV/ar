#!/usr/bin/env python3
"""
Тестовый скрипт для проверки генерации превью изображений и видео
"""
import os
import sys
import tempfile
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


def create_test_image(size=(800, 600), color=(255, 0, 0)):
    """Создает тестовое изображение"""
    image = Image.new('RGB', size, color)
    buffer = BytesIO()
    image.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer.getvalue()


def test_image_preview():
    """Тест генерации превью изображения"""
    logger.info("=== Тест генерации превью изображения ===")
    
    # Создаем тестовое изображение
    test_image_content = create_test_image()
    logger.info(f"Создано тестовое изображение, размер: {len(test_image_content)} байт")
    
    # Генерируем превью
    preview = PreviewGenerator.generate_image_preview(test_image_content)
    
    if preview:
        logger.info(f"✅ Превью изображения успешно сгенерировано, размер: {len(preview)} байт")
        
        # Проверяем размер превью
        preview_image = Image.open(BytesIO(preview))
        logger.info(f"Размеры превью: {preview_image.size}")
        
        # Сохраняем превью для визуальной проверки
        with open("test_image_preview.jpg", "wb") as f:
            f.write(preview)
        logger.info("Превью сохранено в файл test_image_preview.jpg")
        
        return True
    else:
        logger.error("❌ Не удалось сгенерировать превью изображения")
        return False


def test_video_preview():
    """Тест генерации превью видео (с заглушкой, так как у нас нет реального видео)"""
    logger.info("=== Тест генерации превью видео ===")
    
    # Создаем тестовые "видео" данные (на самом деле это просто байты)
    # В реальной ситуации здесь были бы данные видеофайла
    test_video_content = b"fake_video_content" * 1000  # Имитация видеофайла
    logger.info(f"Созданы тестовые данные видео, размер: {len(test_video_content)} байт")
    
    # Генерируем превью (должна сработать заглушка)
    preview = PreviewGenerator.generate_video_preview(test_video_content)
    
    if preview:
        logger.info(f"✅ Превью видео успешно сгенерировано (заглушка), размер: {len(preview)} байт")
        
        # Проверяем размер превью
        preview_image = Image.open(BytesIO(preview))
        logger.info(f"Размеры превью: {preview_image.size}")
        
        # Сохраняем превью для визуальной проверки
        with open("test_video_preview.jpg", "wb") as f:
            f.write(preview)
        logger.info("Превью сохранено в файл test_video_preview.jpg")
        
        return True
    else:
        logger.error("❌ Не удалось сгенерировать превью видео")
        return False


def test_video_preview_stub():
    """Тест генерации заглушки превью видео"""
    logger.info("=== Тест заглушки превью видео ===")
    
    # Генерируем заглушку
    preview = PreviewGenerator.generate_video_preview_stub()
    
    if preview:
        logger.info(f"✅ Заглушка превью видео успешно сгенерирована, размер: {len(preview)} байт")
        
        # Проверяем размер превью
        preview_image = Image.open(BytesIO(preview))
        logger.info(f"Размеры заглушки: {preview_image.size}")
        
        # Сохраняем заглушку для визуальной проверки
        with open("test_video_stub.jpg", "wb") as f:
            f.write(preview)
        logger.info("Заглушка сохранена в файл test_video_stub.jpg")
        
        return True
    else:
        logger.error("❌ Не удалось сгенерировать заглушку превью видео")
        return False


def test_document_preview():
    """Тест генерации превью документа"""
    logger.info("=== Тест генерации превью документа ===")
    
    # Создаем тестовые данные документа
    test_document_content = b"fake_document_content" * 100
    logger.info(f"Созданы тестовые данные документа, размер: {len(test_document_content)} байт")
    
    # Генерируем превью
    preview = PreviewGenerator.generate_document_preview(test_document_content)
    
    if preview:
        logger.info(f"✅ Превью документа успешно сгенерировано, размер: {len(preview)} байт")
        
        # Проверяем размер превью
        preview_image = Image.open(BytesIO(preview))
        logger.info(f"Размеры превью: {preview_image.size}")
        
        # Сохраняем превью для визуальной проверки
        with open("test_document_preview.jpg", "wb") as f:
            f.write(preview)
        logger.info("Превью сохранено в файл test_document_preview.jpg")
        
        return True
    else:
        logger.error("❌ Не удалось сгенерировать превью документа")
        return False


def main():
    """Основная функция тестирования"""
    logger.info("Начинаем тестирование генерации превью...")
    
    from io import BytesIO
    
    results = []
    
    # Тестируем различные типы превью
    results.append(("Изображение", test_image_preview()))
    results.append(("Видео (заглушка)", test_video_preview()))
    results.append(("Заглушка видео", test_video_preview_stub()))
    results.append(("Документ", test_document_preview()))
    
    # Выводим итоговые результаты
    logger.info("\n=== Итоги тестирования ===")
    for test_name, result in results:
        status = "✅ УСПЕХ" if result else "❌ ОШИБКА"
        logger.info(f"{test_name}: {status}")
    
    success_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    logger.info(f"\nВсего тестов: {total_count}")
    logger.info(f"Успешно: {success_count}")
    logger.info(f"Неудачно: {total_count - success_count}")
    
    if success_count == total_count:
        logger.info("🎉 Все тесты пройдены успешно!")
        return 0
    else:
        logger.error("❌ Некоторые тесты не пройдены")
        return 1


if __name__ == "__main__":
    sys.exit(main())
