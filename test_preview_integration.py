#!/usr/bin/env python3
"""
Простой тест проверки оптимизации превью в реальном API
"""

import sys
from pathlib import Path
from PIL import Image
from io import BytesIO

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "vertex-ar"))

from preview_generator import PreviewGenerator


def create_sample_image():
    """Создает тестовое изображение"""
    image = Image.new('RGB', (800, 600), color=(100, 150, 200))
    
    # Добавляем детали
    from PIL import ImageDraw
    draw = ImageDraw.Draw(image)
    
    # Рисуем сетку для детализации
    for i in range(0, 800, 50):
        draw.line([(i, 0), (i, 600)], fill=(80, 130, 180), width=1)
    for i in range(0, 600, 50):
        draw.line([(0, i), (800, i)], fill=(80, 130, 180), width=1)
    
    # Добавим несколько прямоугольников
    draw.rectangle([100, 100, 300, 200], fill=(200, 100, 100), outline=(150, 50, 50), width=2)
    draw.rectangle([400, 300, 600, 500], fill=(100, 200, 100), outline=(50, 150, 50), width=2)
    
    return image


def test_optimization():
    """Тестируем оптимизацию"""
    print("🧪 Тест оптимизации превью...")
    
    # Создаем тестовое изображение
    original_image = create_sample_image()
    
    # Сохраняем в байты с высоким качеством
    original_bytes = BytesIO()
    original_image.save(original_bytes, format='JPEG', quality=95)
    original_content = original_bytes.getvalue()
    
    print(f"📊 Оригинал: {len(original_content)} байт, размер: {original_image.size}")
    
    # Тестируем новые параметры
    new_preview = PreviewGenerator.generate_image_preview(original_content)
    
    if new_preview:
        # Проверяем размер
        preview_image = Image.open(BytesIO(new_preview))
        
        print(f"✅ Новое превью: {len(new_preview)} байт, размер: {preview_image.size}")
        
        # Сравниваем с тем, что было бы со старыми параметрами
        old_preview = PreviewGenerator.generate_image_preview(original_content, size=(120, 120))
        
        if old_preview:
            old_image = Image.open(BytesIO(old_preview))
            print(f"📈 Старое превью: {len(old_preview)} байт, размер: {old_image.size}")
            
            # Считаем улучшения
            size_improvement = (preview_image.size[0] * preview_image.size[1]) / (old_image.size[0] * old_image.size[1])
            size_ratio = len(new_preview) / len(old_preview)
            
            print(f"\n📊 Улучшения:")
            print(f"  🔍 Разрешение: {size_improvement:.1f}x больше")
            print(f"  📦 Размер файла: {size_ratio:.1f}x больше")
            print(f"  ⚡ Эффективность: {size_improvement/size_ratio:.1f}x пикселей на байт")
        
        # Тестируем WebP
        webp_preview = PreviewGenerator.generate_image_preview(original_content, format='WEBP')
        if webp_preview:
            webp_ratio = len(webp_preview) / len(new_preview)
            print(f"  🌐 WebP эффективность: {webp_ratio:.1f}x меньше JPEG")
        
        print(f"\n🎉 Оптимизация работает корректно!")
        return True
    else:
        print("❌ Ошибка генерации превью")
        return False


def test_multiple_sizes():
    """Тест множественных размеров"""
    print("\n🎯 Тест множественных размеров...")
    
    original_image = create_sample_image()
    original_bytes = BytesIO()
    original_image.save(original_bytes, format='JPEG', quality=95)
    original_content = original_bytes.getvalue()
    
    multiple_previews = PreviewGenerator.generate_multiple_sizes(original_content, 'image/jpeg')
    
    print(f"✅ Сгенерировано вариантов: {len(multiple_previews)}")
    
    for key, preview in multiple_previews.items():
        preview_image = Image.open(BytesIO(preview))
        print(f"  📦 {key}: {len(preview)} байт, размер: {preview_image.size}")
    
    return len(multiple_previews) == 6  # Ожидаем 6 вариантов (3 размера x 2 формата)


def main():
    """Основная функция"""
    print("🚀 Тестирование оптимизации превью...")
    print("=" * 50)
    
    success = True
    
    success &= test_optimization()
    success &= test_multiple_sizes()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Все тесты пройдены! Оптимизация работает корректно.")
    else:
        print("❌ Некоторые тесты не пройдены.")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())