#!/usr/bin/env python3
"""
Тестирование интеграции генератора NFT-маркеров из Stogram в Vertex Art AR
"""

import os
import tempfile
from pathlib import Path

# Импортируем новые модули
from nft_marker_generator import NFTMarkerGenerator, NFTMarkerConfig
from nft_maker import generate_nft_marker

def test_nft_marker_generator():
    """Тестирование базовой функциональности NFTMarkerGenerator"""
    print("Тестирование NFTMarkerGenerator...")
    
    # Создаем временный файл изображения для теста
    temp_img_path = None
    try:
        # Создаем простое изображение с помощью PIL
        try:
            from PIL import Image
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_img:
                temp_img_path = temp_img.name

            img = Image.new('RGB', (640, 480), color='red')
            img.save(temp_img_path)
            
            # Создаем генератор с временной директорией
            with tempfile.TemporaryDirectory() as temp_dir:
                generator = NFTMarkerGenerator(Path(temp_dir))
                
                # Тестируем анализ изображения
                analysis = generator.analyze_image(temp_img_path)
                print(f"Анализ изображения: {analysis}")
                
                # Тестируем генерацию маркера
                marker = generator.generate_marker(temp_img_path, "test_marker")
                print(f"Маркер сгенерирован: {marker.fset_path}, {marker.fset3_path}, {marker.iset_path}")
                
                # Проверяем, что файлы были созданы
                assert os.path.exists(marker.fset_path), "FSET файл не был создан"
                assert os.path.exists(marker.fset3_path), "FSET3 файл не был создан"
                assert os.path.exists(marker.iset_path), "ISET файл не был создан"
                
                print("Тест NFTMarkerGenerator пройден успешно!")
                return True
        except ImportError:
            print("PIL не установлен, пропускаем тест")
            return True  # Не считаем за ошибку, если PIL не установлен
        except Exception as e:
            print(f"Ошибка в тесте NFTMarkerGenerator: {e}")
            return False
    finally:
        # Удаляем временный файл
        if temp_img_path and os.path.exists(temp_img_path):
            os.remove(temp_img_path)

def test_generate_nft_marker_function():
    """Тестирование функции generate_nft_marker из nft_maker"""
    print("\nТестирование generate_nft_marker...")
    
    # Создаем временный файл изображения для теста
    temp_img_path = None
    try:
        try:
            from PIL import Image
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_img:
                temp_img_path = temp_img.name

            img = Image.new('RGB', (640, 480), color='blue')
            img.save(temp_img_path)
            
            # Создаем временную директорию для вывода
            with tempfile.TemporaryDirectory() as temp_out:
                # Тестируем функцию генерации маркера
                success = generate_nft_marker(temp_img_path, temp_out)
                print(f"Генерация маркера завершена: {success}")
                
                assert success, "Генерация маркера не удалась"
                
                # Проверяем, что файлы были созданы в выходной директории
                # Маркеры создаются в поддиректории nft_markers с именем маркера
                nft_markers_dir = os.path.join(temp_out, "nft_markers")
                marker_subdir = os.path.join(nft_markers_dir, os.path.basename(temp_img_path).split('.')[0])  # Имя файла без расширения
                
                if os.path.exists(marker_subdir):
                    marker_files = [f for f in os.listdir(marker_subdir) if f.endswith(('.fset', '.fset3', '.iset'))]
                    print(f"Созданные файлы маркеров: {marker_files}")
                    assert len(marker_files) >= 3, f"Должно быть создано как минимум 3 файла маркера, создано: {len(marker_files)}"
                else:
                    # Если поддиректория не существует, проверяем в nft_markers
                    if os.path.exists(nft_markers_dir):
                        for root, dirs, files in os.walk(nft_markers_dir):
                            marker_files = [f for f in files if f.endswith(('.fset', '.fset3', '.iset'))]
                            print(f"Созданные файлы маркеров: {marker_files}")
                            assert len(marker_files) >= 3, f"Должно быть создано как минимум 3 файла маркера, создано: {len(marker_files)}"
                            break  # Прерываем на первой директории
                    else:
                        marker_files = [f for f in os.listdir(temp_out) if f.endswith(('.fset', '.fset3', '.iset'))]
                        print(f"Созданные файлы маркеров: {marker_files}")
                        assert len(marker_files) >= 3, f"Должно быть создано как минимум 3 файла маркера, создано: {len(marker_files)}"
                
                print("Тест generate_nft_marker пройден успешно!")
                return True
        except ImportError:
            print("PIL не установлен, пропускаем тест")
            return True  # Не считаем за ошибку, если PIL не установлен
        except Exception as e:
            print(f"Ошибка в тесте generate_nft_marker: {e}")
            return False
    finally:
        # Удаляем временный файл
        if temp_img_path and os.path.exists(temp_img_path):
            os.remove(temp_img_path)

def test_nft_marker_config():
    """Тестирование конфигурации NFT-маркеров"""
    print("\nТестирование NFTMarkerConfig...")
    
    # Проверяем создание конфигурации с разными параметрами
    config1 = NFTMarkerConfig()
    print(f"Конфигурация по умолчанию: min_dpi={config1.min_dpi}, feature_density={config1.feature_density}")
    
    config2 = NFTMarkerConfig(min_dpi=150, feature_density="high")
    print(f"Конфигурация с параметрами: min_dpi={config2.min_dpi}, feature_density={config2.feature_density}")
    
    assert config1.min_dpi == 72, "Неправильное значение по умолчанию для min_dpi"
    assert config2.min_dpi == 150, "Неправильное значение min_dpi для кастомной конфигурации"
    assert config1.feature_density == "medium", "Неправильное значение по умолчанию для feature_density"
    assert config2.feature_density == "high", "Неправильное значение feature_density для кастомной конфигурации"
    
    print("Тест NFTMarkerConfig пройден успешно!")
    return True

def main():
    """Основная функция тестирования"""
    print("Начинаем тестирование интеграции NFT-генератора из Stogram в Vertex Art AR\n")
    
    tests = [
        test_nft_marker_generator,
        test_generate_nft_marker_function,
        test_nft_marker_config
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"Тест {test.__name__} завершился с ошибкой: {e}")
    
    print(f"\nРезультаты тестирования: {passed}/{total} тестов пройдено успешно")
    
    if passed == total:
        print("Все тесты пройдены! Интеграция работает корректно.")
        return True
    else:
        print("Не все тесты пройдены. Проверьте интеграцию.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
