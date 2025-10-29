#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, 'vertex-art-ar')

from PIL import Image
from io import BytesIO
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_image_preview():
    """Тест генерации превью для изображения"""
    try:
        # Создаем простое тестовое изображение
        test_image = Image.new('RGB', (400, 300), color='red')
        buffer = BytesIO()
        test_image.save(buffer, format='JPEG')
        image_content = buffer.getvalue()
        
        print(f"Создано тестовое изображение размером {len(image_content)} байт")
        
        # Импортируем функцию из модуля
        from preview_generator import PreviewGenerator
        
        # Генерируем превью
        preview = PreviewGenerator.generate_image_preview(image_content, size=(200, 200))
        
        if preview:
            print(f"✅ Превью успешно сгенерировано! Размер: {len(preview)} байт")
            return True
        else:
            print("❌ Не удалось сгенерировать превью")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_video_preview():
    """Тест генерации превью для видео (заглушка)"""
    try:
        from preview_generator import PreviewGenerator
        
        # Используем заглушку для видео
        video_content = b"fake video content"
        preview = PreviewGenerator.generate_video_preview(video_content)
        
        if preview:
            print(f"✅ Заглушка для видео успешно создана! Размер: {len(preview)} байт")
            return True
        else:
            print("❌ Не удалось создать заглушку для видео")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании видео: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Тестирование генерации превью...")
    
    print("\n1. Тест генерации превью изображения:")
    image_result = test_image_preview()
    
    print("\n2. Тест генерации превью видео:")
    video_result = test_video_preview()
    
    if image_result and video_result:
        print("\n✅ Все тесты пройдены успешно!")
    else:
        print("\n❌ Некоторые тесты не пройдены")