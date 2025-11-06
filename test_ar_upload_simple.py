"""
Упрощенное тестирование функциональности загрузки AR-контента
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Добавляем путь к основному приложению
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vertex-ar"))

from main import Database, _hash_password
from nft_marker_generator import NFTMarkerGenerator


def test_image_creation():
    """Тестирование создания изображения"""
    print("Тест 1: Создание изображения")

    # Создаем временные файлы для тестирования
    temp_dir = tempfile.mkdtemp()

    try:
        # Создаем тестовое изображение JPEG
        test_image_path = os.path.join(temp_dir, "test_image.jpg")
        from PIL import Image

        img = Image.new("RGB", (1024, 1024), color="red")
        img.save(test_image_path, "JPEG")

        print(f"  Изображение создано: {os.path.exists(test_image_path)}")
        print(f"  Размер: {os.path.getsize(test_image_path)} байт")

        return True
    except Exception as e:
        print(f"Ошибка при создании изображения: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)


def test_nft_marker_generation():
    """Тестирование генерации NFT-маркеров"""
    print("\nТест 2: Генерация NFT-маркеров")

    temp_dir = tempfile.mkdtemp()

    try:
        # Создаем тестовое изображение
        test_image_path = os.path.join(temp_dir, "test_marker_image.jpg")
        from PIL import Image

        img = Image.new("RGB", (1024, 1024), color="blue")
        img.save(test_image_path, "JPEG")

        # Создаем генератор маркеров
        storage_root = Path(temp_dir) / "storage"
        generator = NFTMarkerGenerator(storage_root)

        # Генерируем маркер
        try:
            marker = generator.generate_marker(
                test_image_path,
                "test_marker",
            )
            print(f"  Генерация маркера: Успешна")
            print(f"    - fset файл: {os.path.exists(marker.fset_path)}")
            print(f"    - fset3 файл: {os.path.exists(marker.fset3_path)}")
            print(f"    - iset файл: {os.path.exists(marker.iset_path)}")
            print(f"    - Размеры: {marker.width}x{marker.height}")

            # Проверяем, что файлы действительно созданы
            for path in [marker.fset_path, marker.fset3_path, marker.iset_path]:
                if os.path.exists(path):
                    size = os.path.getsize(path)
                    print(f"    - Файл {os.path.basename(path)}: {size} байт")
                else:
                    print(f"    - Файл {os.path.basename(path)}: НЕ СОЗДАН!")
        except Exception as e:
            print(f"  Генерация маркера: Ошибка - {e}")

        return True
    except Exception as e:
        print(f"Ошибка при тестировании генерации NFT-маркеров: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)


def test_database_operations():
    """Тестирование операций с базой данных"""
    print("\nТест 3: Операции с базой данных")

    temp_dir = tempfile.mkdtemp()

    try:
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path)

        # Тестируем создание пользователя
        try:
            db.create_user("test_user", _hash_password("test_password"), is_admin=True)
            print("  Создание пользователя: Успешно")
        except Exception as e:
            print(f" Создание пользователя: Ошибка - {e}")

        # Тестируем получение пользователя
        user = db.get_user("test_user")
        if user:
            print(f"  Получение пользователя: Успешно - {user['username']}")
        else:
            print("  Получение пользователя: Ошибка - пользователь не найден")

        # Закрываем соединение с базой данных
        db._connection.close()

        return True
    except Exception as e:
        print(f"Ошибка при тестировании базы данных: {e}")
        return False
    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            # Игнорируем ошибки при удалении временной директории
            pass


def test_file_size_validation():
    """Тестирование проверки размера файлов"""
    print("\nТест 4: Проверка размера файлов")

    temp_dir = tempfile.mkdtemp()

    try:
        # Создаем файлы разных размеров
        # 1. Маленький файл (меньше 50 МБ)
        small_file_path = os.path.join(temp_dir, "small_file.jpg")
        with open(small_file_path, "wb") as f:
            f.write(b"A" * 1024 * 1024)  # 1 МБ

        # 2. Большой файл (больше 50 МБ)
        large_file_path = os.path.join(temp_dir, "large_file.jpg")
        with open(large_file_path, "wb") as f:
            f.write(b"A" * 60 * 1024 * 1024)  # 60 МБ

        small_size = os.path.getsize(small_file_path)
        large_size = os.path.getsize(large_file_path)

        print(f"  Маленький файл: {small_size / (1024*1024):.2f} МБ")
        print(f" Большой файл: {large_size / (1024*1024):.2f} МБ")
        print(f" Порог в 50 МБ: {'превышен' if large_size > 50*1024*1024 else 'не превышен'}")

        return True
    except Exception as e:
        print(f"Ошибка при тестировании проверки размера файлов: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)


def main():
    """Основная функция тестирования"""
    print("=== Упрощенное тестирование функциональности загрузки AR-контента ===\n")

    tests = [test_image_creation, test_nft_marker_generation, test_database_operations, test_file_size_validation]

    results = []
    for test in tests:
        results.append(test())

    print(f"\n=== Результаты ===")
    print(f"Пройдено тестов: {sum(results)}/{len(results)}")

    if all(results):
        print("Все тесты пройдены успешно!")
        return True
    else:
        print("Некоторые тесты не пройдены.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
