"""
Тестирование функциональности админ-панели
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Добавляем путь к основному приложению
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vertex-ar"))

from fastapi import HTTPException
from main import Database, _hash_password, require_admin


def test_admin_access():
    """Тестирование доступа к админ-панели только для администраторов"""
    print("Тест 1: Доступ к админ-панели только для администраторов")

    temp_dir = tempfile.mkdtemp()

    try:
        # Создаем временную базу данных
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path)

        # Создаем обычного пользователя
        db.create_user("regular_user", _hash_password("regular_password"), is_admin=False)

        # Создаем администратора
        db.create_user("admin_user", _hash_password("admin_password"), is_admin=True)

        # Проверяем доступ обычного пользователя
        try:
            require_admin("regular_user")
            print("  Обычный пользователь получил доступ к админ-панели: ОШИБКА")
            return False
        except HTTPException as e:
            if e.status_code == 403:
                print("  Обычный пользователь заблокирован от доступа к админ-панели: УСПЕШНО")
            else:
                print(f"  Неожиданный код ошибки для обычного пользователя: {e.status_code}")
                return False
        except Exception as e:
            print(f"  Другая ошибка при проверке доступа обычного пользователя: {e}")
            return False

        # Проверяем доступ администратора
        try:
            result = require_admin("admin_user")
            if result == "admin_user":
                print("  Администратор получил доступ к админ-панели: УСПЕШНО")
            else:
                print(f"  Администратор получил доступ, но вернулось неверное значение: {result}")
                return False
        except HTTPException as e:
            print(f"  Администратор не получил доступ к админ-панели: ОШИБКА - {e.detail}")
            return False
        except Exception as e:
            print(f"  Другая ошибка при проверке доступа администратора: {e}")
            return False

        return True
    except Exception as e:
        print(f"Ошибка при тестировании доступа к админ-панели: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_ar_content_listing():
    """Тестирование отображения списка AR-контента"""
    print("\nТест 2: Отображение списка AR-контента")

    temp_dir = tempfile.mkdtemp()

    try:
        # Создаем временную базу данных
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path)

        # Создаем пользователей
        db.create_user("user1", _hash_password("password1"), is_admin=False)
        db.create_user("user2", _hash_password("password2"), is_admin=False)
        db.create_user("admin", _hash_password("adminpass"), is_admin=True)

        # Создаем тестовый AR-контент для разных пользователей
        content1 = db.create_ar_content(
            content_id="content1",
            username="user1",
            image_path="/path/to/image1.jpg",
            video_path="/path/to/video1.mp4",
            marker_fset="/path/to/marker1.fset",
            marker_fset3="/path/to/marker1.fset3",
            marker_iset="/path/to/marker1.iset",
            ar_url="http://localhost:8000/ar/content1",
            qr_code="qr1",
        )

        content2 = db.create_ar_content(
            content_id="content2",
            username="user2",
            image_path="/path/to/image2.jpg",
            video_path="/path/to/video2.mp4",
            marker_fset="/path/to/marker2.fset",
            marker_fset3="/path/to/marker2.fset3",
            marker_iset="/path/to/marker2.iset",
            ar_url="http://localhost:8000/ar/content2",
            qr_code="qr2",
        )

        # Проверяем список контента для администратора (должен видеть всё)
        admin_content = db.list_ar_content()
        print(f"  Количество контента для администратора: {len(admin_content)}")

        # Проверяем список контента для обычных пользователей (должны видеть только свой)
        user1_content = db.list_ar_content("user1")
        user2_content = db.list_ar_content("user2")
        print(f"  Количество контента для user1: {len(user1_content)}")
        print(f"  Количество контента для user2: {len(user2_content)}")

        # Проверяем, что администратор видит весь контент
        if len(admin_content) == 2:
            print("  Администратор видит весь контент: УСПЕШНО")
        else:
            print(f"  Администратор должен видеть 2 элемента, но видит {len(admin_content)}: ОШИБКА")
            return False

        # Проверяем, что обычные пользователи видят только свой контент
        if len(user1_content) == 1 and len(user2_content) == 1:
            print("  Обычные пользователи видят только свой контент: УСПЕШНО")
        else:
            print(
                f"  Пользователи должны видеть по 1 элементу, но user1 видит {len(user1_content)}, user2 видит {len(user2_content)}: ОШИБКА"
            )
            return False

        return True
    except Exception as e:
        print(f"Ошибка при тестировании отображения списка AR-контента: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_system_resources_info():
    """Тестирование информации о системных ресурсах"""
    print("\nТест 3: Информация о системных ресурсах")

    try:
        # Импортируем функции для получения информации о системных ресурсах
        from utils import format_bytes, get_disk_usage, get_storage_usage

        # Получаем информацию о диске
        disk_info = get_disk_usage()
        print(f"  Общий объем диска: {format_bytes(disk_info['total'])}")
        print(f"  Использовано диска: {format_bytes(disk_info['used'])}")
        print(f"  Свободно диска: {format_bytes(disk_info['free'])}")
        print(f"  Процент использования: {disk_info['used_percent']:.2f}%")

        # Получаем информацию о хранилище
        storage_info = get_storage_usage()
        print(f"  Общий размер хранилища: {storage_info['formatted_size']}")
        print(f"  Количество файлов: {storage_info['file_count']}")

        # Проверяем, что информация получена корректно
        if disk_info["total"] > 0 and disk_info["used"] >= 0 and disk_info["free"] >= 0:
            print("  Информация о системных ресурсах получена корректно: УСПЕШНО")
            return True
        else:
            print("  Ошибка при получении информации о системных ресурсах: ОШИБКА")
            return False

    except Exception as e:
        print(f"Ошибка при тестировании информации о системных ресурсах: {e}")
        return False


def test_storage_info():
    """Тестирование информации об использовании хранилища"""
    print("\nТест 4: Информация об использовании хранилища")

    try:
        # Импортируем функции для получения информации о хранилище
        from utils import format_bytes, get_storage_usage

        # Получаем информацию о хранилище
        try:
            storage_info = get_storage_usage()
            print(f"  Общий размер хранилища: {storage_info['formatted_size']}")
            print(f"  Количество файлов: {storage_info['file_count']}")

            # Проверяем, что информация получена корректно
            if "formatted_size" in storage_info and "file_count" in storage_info:
                print("  Информация об использовании хранилища получена корректно: УСПЕШНО")
                return True
            else:
                print("  Ошибка при получении информации об использовании хранилища: ОШИБКА")
                return False
        except Exception as e:
            print(f"  Ошибка при получении информации об использовании хранилища: {e}")
            return False

    except Exception as e:
        print(f"Ошибка при тестировании информации об использовании хранилища: {e}")
        return False


def test_content_statistics():
    """Тестирование статистики просмотров контента"""
    print("\nТест 5: Статистика просмотров контента")

    temp_dir = tempfile.mkdtemp()

    try:
        # Создаем временную базу данных
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path)

        # Создаем тестовый AR-контент
        content = db.create_ar_content(
            content_id="test_content",
            username="test_user",
            image_path="/path/to/image.jpg",
            video_path="/path/to/video.mp4",
            marker_fset="/path/to/marker.fset",
            marker_fset3="/path/to/marker.fset3",
            marker_iset="/path/to/marker.iset",
            ar_url="http://localhost:8000/ar/test_content",
            qr_code="test_qr",
        )

        # Имитируем просмотры контента
        from main import content_views

        # Увеличиваем счетчик просмотров несколько раз
        for i in range(5):
            view_count = content_views.increment_view("test_content")
            print(f"  Просмотр #{i+1}: {view_count}")

        # Получаем статистику просмотров
        all_views = content_views.get_all_views()
        test_content_views = all_views.get("test_content", 0)

        print(f"  Общее количество просмотров для test_content: {test_content_views}")

        # Проверяем, что счетчик работает корректно
        if test_content_views == 5:
            print("  Статистика просмотров контента работает корректно: УСПЕШНО")
            return True
        else:
            print(f"  Ошибка в статистике просмотров: ожидалось 5, получено {test_content_views}")
            return False

    except Exception as e:
        print(f"Ошибка при тестировании статистики просмотров контента: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Основная функция тестирования админ-панели"""
    print("=== Тестирование админ-панели ===\n")

    tests = [
        test_admin_access,
        test_ar_content_listing,
        test_system_resources_info,
        test_storage_info,
        test_content_statistics,
    ]

    results = []
    for test in tests:
        results.append(test())

    print(f"\n=== Результаты ===")
    print(f"Пройдено тестов: {sum(results)}/{len(results)}")

    if all(results):
        print("Все тесты админ-панели пройдены успешно!")
        return True
    else:
        print("Некоторые тесты админ-панели не пройдены.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
