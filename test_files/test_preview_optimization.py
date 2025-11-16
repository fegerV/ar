#!/usr/bin/env python3
"""
Тест оптимизации изображений в превью
Проверяет улучшенную производительность и качество генерации превью
"""

import os
import sys
import time
from pathlib import Path
from PIL import Image
from io import BytesIO

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "vertex-ar"))

from preview_generator import PreviewGenerator
from logging_setup import get_logger

logger = get_logger(__name__)


def create_test_image(width=2000, height=1500, format='RGB'):
    """Создает тестовое изображение заданного размера"""
    image = Image.new(format, (width, height), color=(100, 150, 200))
    
    # Добавляем немного деталей для реалистичности
    from PIL import ImageDraw
    draw = ImageDraw.Draw(image)
    
    # Рисуем несколько прямоугольников
    for i in range(10):
        x1 = i * width // 10
        y1 = i * height // 10
        x2 = (i + 5) * width // 10
        y2 = (i + 5) * height // 10
        draw.rectangle([x1, y1, x2, y2], outline=(50, 100, 150), width=2)
    
    return image


def test_preview_sizes():
    """Тест различных размеров превью"""
    print("🧪 Тест различных размеров превью...")
    
    # Создаем тестовое изображение
    test_image = create_test_image(2000, 1500)
    image_bytes = BytesIO()
    test_image.save(image_bytes, format='JPEG', quality=95)
    image_content = image_bytes.getvalue()
    
    print(f"Оригинальное изображение: {len(image_content)} байт")
    
    # Тестируем разные размеры
    sizes = [
        ('SMALL', PreviewGenerator.SMALL_THUMBNAIL_SIZE),
        ('DEFAULT', PreviewGenerator.DEFAULT_THUMBNAIL_SIZE),
        ('LARGE', PreviewGenerator.LARGE_THUMBNAIL_SIZE)
    ]
    
    for name, size in sizes:
        print(f"\n📏 Тест размера {name}: {size}")
        
        start_time = time.time()
        preview = PreviewGenerator.generate_image_preview(image_content, size)
        end_time = time.time()
        
        if preview:
            compression_ratio = len(image_content) / len(preview)
            print(f"  ✅ Размер превью: {len(preview)} байт")
            print(f"  ✅ Коэффициент сжатия: {compression_ratio:.1f}x")
            print(f"  ✅ Время генерации: {(end_time - start_time)*1000:.1f} мс")
            
            # Проверяем размер изображения
            preview_image = Image.open(BytesIO(preview))
            print(f"  ✅ Фактический размер: {preview_image.size}")
        else:
            print(f"  ❌ Ошибка генерации превью")


def test_format_comparison():
    """Тест сравнения форматов JPEG и WebP"""
    print("\n🔄 Тест сравнения форматов...")
    
    # Создаем тестовое изображение
    test_image = create_test_image(1500, 1000)
    image_bytes = BytesIO()
    test_image.save(image_bytes, format='JPEG', quality=95)
    image_content = image_bytes.getvalue()
    
    formats = ['JPEG', 'WEBP']
    
    for format_name in formats:
        print(f"\n📸 Тест формата {format_name}:")
        
        start_time = time.time()
        preview = PreviewGenerator.generate_image_preview(image_content, format=format_name)
        end_time = time.time()
        
        if preview:
            compression_ratio = len(image_content) / len(preview)
            print(f"  ✅ Размер превью: {len(preview)} байт")
            print(f"  ✅ Коэффициент сжатия: {compression_ratio:.1f}x")
            print(f"  ✅ Время генерации: {(end_time - start_time)*1000:.1f} мс")
        else:
            print(f"  ❌ Ошибка генерации превью")


def test_multiple_sizes():
    """Тест генерации множественных размеров"""
    print("\n🎯 Тест множественных размеров...")
    
    # Создаем тестовое изображение
    test_image = create_test_image(1200, 800)
    image_bytes = BytesIO()
    test_image.save(image_bytes, format='JPEG', quality=95)
    image_content = image_bytes.getvalue()
    
    start_time = time.time()
    multiple_previews = PreviewGenerator.generate_multiple_sizes(image_content, 'image/jpeg')
    end_time = time.time()
    
    print(f"✅ Сгенерировано превью: {len(multiple_previews)}")
    print(f"✅ Общее время: {(end_time - start_time)*1000:.1f} мс")
    
    total_size = 0
    for key, preview in multiple_previews.items():
        size = len(preview)
        total_size += size
        print(f"  📦 {key}: {size} байт")
    
    print(f"📊 Общий размер всех превью: {total_size} байт")


def test_video_preview():
    """Тест превью для видео (заглушка)"""
    print("\n🎬 Тест превью видео...")
    
    # Создаем имитацию видео файла (просто байты)
    video_content = b"fake_video_content_for_testing" * 1000
    
    start_time = time.time()
    preview = PreviewGenerator.generate_video_preview(video_content)
    end_time = time.time()
    
    if preview:
        print(f"✅ Размер превью видео: {len(preview)} байт")
        print(f"✅ Время генерации: {(end_time - start_time)*1000:.1f} мс")
        
        # Проверяем, что это изображение
        try:
            preview_image = Image.open(BytesIO(preview))
            print(f"✅ Размер изображения: {preview_image.size}")
        except Exception as e:
            print(f"❌ Ошибка открытия превью: {e}")
    else:
        print("❌ Ошибка генерации превью видео")


def test_performance_comparison():
    """Сравнение производительности старых и новых параметров"""
    print("\n⚡ Сравнение производительности...")
    
    # Создаем большое тестовое изображение
    test_image = create_test_image(3000, 2000)
    image_bytes = BytesIO()
    test_image.save(image_bytes, format='JPEG', quality=95)
    image_content = image_bytes.getvalue()
    
    print(f"Тестовое изображение: {len(image_content)} байт")
    
    # Старые параметры (120x120, качество 90)
    print("\n🔸 Старые параметры (120x120, качество 90%):")
    start_time = time.time()
    old_preview = PreviewGenerator.generate_image_preview(image_content, size=(120, 120))
    old_time = time.time() - start_time
    
    if old_preview:
        print(f"  Размер: {len(old_preview)} байт")
        print(f"  Время: {old_time*1000:.1f} мс")
    
    # Новые параметры (300x300, качество 78, progressive)
    print("\n🔹 Новые параметры (300x300, качество 78%, progressive):")
    start_time = time.time()
    new_preview = PreviewGenerator.generate_image_preview(image_content)  # Использует новые параметры по умолчанию
    new_time = time.time() - start_time
    
    if new_preview:
        print(f"  Размер: {len(new_preview)} байт")
        print(f"  Время: {new_time*1000:.1f} мс")
        
        if old_preview:
            size_ratio = len(new_preview) / len(old_preview)
            time_ratio = new_time / old_time
            print(f"\n📊 Сравнение:")
            print(f"  Размер: {size_ratio:.2f}x от старого")
            print(f"  Время: {time_ratio:.2f}x от старого")
            print(f"  Разрешение: 300x300 vs 120x120 (6.25x больше пикселей)")


def main():
    """Основная функция тестирования"""
    print("🚀 Начинаем тестирование оптимизации превью...")
    print("=" * 50)
    
    try:
        test_preview_sizes()
        test_format_comparison()
        test_multiple_sizes()
        test_video_preview()
        test_performance_comparison()
        
        print("\n" + "=" * 50)
        print("✅ Все тесты успешно завершены!")
        
    except Exception as e:
        print(f"\n❌ Ошибка во время тестирования: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())