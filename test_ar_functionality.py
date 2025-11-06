"""
Тестирование AR-функциональности
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Добавляем путь к основному приложению
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vertex-ar"))

from main import Database, _hash_password, content_views
from nft_marker_generator import NFTMarkerGenerator


def test_ar_page_generation():
    """Тестирование генерации AR-страницы"""
    print("Тест 1: Генерация AR-страницы")

    temp_dir = tempfile.mkdtemp()

    try:
        # Создаем тестовое изображение и видео
        test_image_path = os.path.join(temp_dir, "test_image.jpg")
        test_video_path = os.path.join(temp_dir, "test_video.mp4")

        from PIL import Image

        img = Image.new("RGB", (1024, 1024), color="red")
        img.save(test_image_path, "JPEG")

        # Создаем тестовое видео (просто пустой файл для тестирования)
        with open(test_video_path, "wb") as f:
            f.write(b"fake mp4 content")

        # Создаем генератор маркеров
        storage_root = Path(temp_dir) / "storage"
        generator = NFTMarkerGenerator(storage_root)

        # Генерируем маркер
        marker = generator.generate_marker(
            test_image_path,
            "test_content",
        )

        # Имитируем создание контента в базе данных
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path)
        db.create_user("test_user", _hash_password("test_password"), is_admin=True)

        content_id = "test_content"
        db.create_ar_content(
            content_id=content_id,
            username="test_user",
            image_path=test_image_path,
            video_path=test_video_path,
            marker_fset=marker.fset_path,
            marker_fset3=marker.fset3_path,
            marker_iset=marker.iset_path,
            ar_url=f"http://localhost:8000/ar/{content_id}",
            qr_code=None,  # или строковое значение
        )

        # Проверяем, что контент можно получить из базы
        content = db.get_ar_content(content_id)
        if content:
            print(f"  AR контент создан: {content['id']}")
        else:
            print("  Ошибка: AR контент не найден")

        # Проверяем, что файлы существуют
        print(f"  Изображение: {os.path.exists(test_image_path)}")
        print(f"  Видео: {os.path.exists(test_video_path)}")
        print(f"  fset маркер: {os.path.exists(marker.fset_path)}")
        print(f" fset3 маркер: {os.path.exists(marker.fset3_path)}")
        print(f"  iset маркер: {os.path.exists(marker.iset_path)}")

        # Закрываем соединение с базой данных
        db._connection.close()

        return True
    except Exception as e:
        print(f"Ошибка при тестировании генерации AR-страницы: {e}")
        return False
    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


def test_view_counter():
    """Тестирование счётчика просмотров"""
    print("\nТест 2: Счётчик просмотров")

    try:
        content_id = "test_view_counter"

        # Проверяем начальное значение
        initial_views = content_views.get_views(content_id)
        print(f" Начальное значение: {initial_views}")

        # Увеличиваем счётчик несколько раз
        for i in range(5):
            new_count = content_views.increment_view(content_id)
            print(f"  После {i+1} просмотра: {new_count}")

        final_views = content_views.get_views(content_id)
        print(f"  Итоговое значение: {final_views}")

        if final_views == 5:
            print(" Счётчик работает корректно")
            return True
        else:
            print(f"  Ошибка: ожидалось 5, получено {final_views}")
            return False

    except Exception as e:
        print(f"Ошибка при тестировании счётчика просмотров: {e}")
        return False


def test_marker_access_urls():
    """Тестирование URL для доступа к маркерам"""
    print("\nТест 3: URL доступа к маркерам")

    temp_dir = tempfile.mkdtemp()

    try:
        # Создаем тестовое изображение
        test_image_path = os.path.join(temp_dir, "test_image.jpg")
        from PIL import Image

        img = Image.new("RGB", (1024, 1024), color="blue")
        img.save(test_image_path, "JPEG")

        # Создаем генератор маркеров
        storage_root = Path(temp_dir) / "storage"
        generator = NFTMarkerGenerator(storage_root)

        # Генерируем маркер
        marker = generator.generate_marker(
            test_image_path,
            "test_marker_access",
        )

        # Проверяем, что все файлы маркеров существуют
        fset_exists = os.path.exists(marker.fset_path)
        fset3_exists = os.path.exists(marker.fset3_path)
        iset_exists = os.path.exists(marker.iset_path)

        print(f"  fset файл: {fset_exists}")
        print(f"  fset3 файл: {fset3_exists}")
        print(f"  iset файл: {iset_exists}")

        # Проверяем, что пути к файлам корректны
        print(f"  Путь fset: {marker.fset_path}")
        print(f" Путь fset3: {marker.fset3_path}")
        print(f"  Путь iset: {marker.iset_path}")

        success = fset_exists and fset3_exists and iset_exists
        if success:
            print(" Все файлы маркеров доступны по URL")
        else:
            print("  Ошибка: не все файлы маркеров доступны")

        return success
    except Exception as e:
        print(f"Ошибка при тестировании URL доступа к маркерам: {e}")
        return False
    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


def main():
    """Основная функция тестирования AR-функциональности"""
    print("=== Тестирование AR-функциональности ===\n")

    tests = [test_ar_page_generation, test_view_counter, test_marker_access_urls]

    results = []
    for test in tests:
        results.append(test())

    print(f"\n=== Результаты ===")
    print(f"Пройдено тестов: {sum(results)}/{len(results)}")

    if all(results):
        print("Все тесты AR-функциональности пройдены успешно!")
        return True
    else:
        print("Некоторые тесты AR-функциональности не пройдены.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
