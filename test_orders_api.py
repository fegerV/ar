"""
Тесты для API управления заказами
"""
import os
import sys
from pathlib import Path

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent / "vertex-ar"))


def test_imports():
    """Проверка импортов"""
    try:
        from main import Database, app, database

        print("✓ Импорты успешны")
        return True
    except Exception as e:
        print(f"✗ Ошибка импорта: {e}")
        return False


def test_database_schema():
    """Проверка схемы базы данных"""
    try:
        import tempfile

        from main import Database

        # Создаем временную базу данных
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        db = Database(db_path)

        # Проверяем, что таблицы созданы
        cursor = db._execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        required_tables = ["users", "ar_content", "clients", "portraits", "videos"]
        for table in required_tables:
            if table in tables:
                print(f"✓ Таблица '{table}' создана")
            else:
                print(f"✗ Таблица '{table}' не найдена")
                return False

        # Проверяем индекс
        cursor = db._execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]

        if "idx_clients_phone" in indexes:
            print("✓ Индекс 'idx_clients_phone' создан")
        else:
            print("✗ Индекс 'idx_clients_phone' не найден")

        # Очищаем
        db_path.unlink()

        return True

    except Exception as e:
        print(f"✗ Ошибка проверки схемы БД: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_client_operations():
    """Проверка операций с клиентами"""
    try:
        import tempfile
        import uuid

        from main import Database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        db = Database(db_path)

        # Создание клиента
        client_id = str(uuid.uuid4())
        client = db.create_client(client_id, "+7 (999) 123-45-67", "Тестовый Клиент")

        if client and client["phone"] == "+7 (999) 123-45-67":
            print("✓ Создание клиента")
        else:
            print("✗ Ошибка создания клиента")
            return False

        # Поиск клиента по телефону
        found = db.get_client_by_phone("+7 (999) 123-45-67")
        if found and found["id"] == client_id:
            print("✓ Поиск клиента по телефону")
        else:
            print("✗ Ошибка поиска клиента")
            return False

        # Поиск по части номера
        results = db.search_clients("999")
        if len(results) > 0 and results[0]["id"] == client_id:
            print("✓ Поиск по части номера")
        else:
            print("✗ Ошибка поиска по части номера")
            return False

        # Обновление клиента
        db.update_client(client_id, name="Обновленное Имя")
        updated = db.get_client(client_id)
        if updated and updated["name"] == "Обновленное Имя":
            print("✓ Обновление клиента")
        else:
            print("✗ Ошибка обновления клиента")
            return False

        # Удаление клиента
        if db.delete_client(client_id):
            print("✓ Удаление клиента")
        else:
            print("✗ Ошибка удаления клиента")
            return False

        db_path.unlink()
        return True

    except Exception as e:
        print(f"✗ Ошибка операций с клиентами: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_portrait_operations():
    """Проверка операций с портретами"""
    try:
        import tempfile
        import uuid

        from main import Database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        db = Database(db_path)

        # Создаем клиента
        client_id = str(uuid.uuid4())
        db.create_client(client_id, "+7 (999) 111-11-11", "Тест")

        # Создание портрета
        portrait_id = str(uuid.uuid4())
        portrait = db.create_portrait(
            portrait_id=portrait_id,
            client_id=client_id,
            image_path="/test/path.jpg",
            marker_fset="fset",
            marker_fset3="fset3",
            marker_iset="iset",
            permanent_link=f"http://test.com/portrait/{portrait_id}",
            qr_code="qr_base64",
        )

        if portrait and portrait["id"] == portrait_id:
            print("✓ Создание портрета")
        else:
            print("✗ Ошибка создания портрета")
            return False

        # Получение портрета по ссылке
        found = db.get_portrait_by_link(f"http://test.com/portrait/{portrait_id}")
        if found and found["id"] == portrait_id:
            print("✓ Поиск портрета по ссылке")
        else:
            print("✗ Ошибка поиска портрета по ссылке")
            return False

        # Список портретов клиента
        portraits = db.list_portraits(client_id)
        if len(portraits) == 1 and portraits[0]["id"] == portrait_id:
            print("✓ Список портретов клиента")
        else:
            print("✗ Ошибка получения списка портретов")
            return False

        # Увеличение просмотров
        db.increment_portrait_views(portrait_id)
        updated = db.get_portrait(portrait_id)
        if updated and updated["view_count"] == 1:
            print("✓ Увеличение просмотров")
        else:
            print("✗ Ошибка увеличения просмотров")
            return False

        db_path.unlink()
        return True

    except Exception as e:
        print(f"✗ Ошибка операций с портретами: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_video_operations():
    """Проверка операций с видео"""
    try:
        import tempfile
        import uuid

        from main import Database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        db = Database(db_path)

        # Создаем клиента и портрет
        client_id = str(uuid.uuid4())
        db.create_client(client_id, "+7 (999) 222-22-22", "Тест")

        portrait_id = str(uuid.uuid4())
        db.create_portrait(
            portrait_id=portrait_id,
            client_id=client_id,
            image_path="/test/path.jpg",
            marker_fset="fset",
            marker_fset3="fset3",
            marker_iset="iset",
            permanent_link=f"http://test.com/portrait/{portrait_id}",
        )

        # Создание первого видео (активно)
        video1_id = str(uuid.uuid4())
        video1 = db.create_video(video_id=video1_id, portrait_id=portrait_id, video_path="/test/video1.mp4", is_active=True)

        if video1 and video1["is_active"]:
            print("✓ Создание активного видео")
        else:
            print("✗ Ошибка создания активного видео")
            return False

        # Создание второго видео (не активно)
        video2_id = str(uuid.uuid4())
        video2 = db.create_video(video_id=video2_id, portrait_id=portrait_id, video_path="/test/video2.mp4", is_active=False)

        if video2 and not video2["is_active"]:
            print("✓ Создание неактивного видео")
        else:
            print("✗ Ошибка создания неактивного видео")
            return False

        # Получение активного видео
        active = db.get_active_video(portrait_id)
        if active and active["id"] == video1_id:
            print("✓ Получение активного видео")
        else:
            print("✗ Ошибка получения активного видео")
            return False

        # Список видео
        videos = db.list_videos(portrait_id)
        if len(videos) == 2:
            print("✓ Список видео портрета")
        else:
            print("✗ Ошибка получения списка видео")
            return False

        # Активация второго видео
        db.set_active_video(video2_id, portrait_id)

        # Проверяем, что второе видео активно, а первое нет
        video1_updated = db.get_video(video1_id)
        video2_updated = db.get_video(video2_id)

        if not video1_updated["is_active"] and video2_updated["is_active"]:
            print("✓ Переключение активного видео")
        else:
            print("✗ Ошибка переключения активного видео")
            return False

        # Проверяем get_active_video
        active_now = db.get_active_video(portrait_id)
        if active_now and active_now["id"] == video2_id:
            print("✓ Активное видео обновлено")
        else:
            print("✗ Ошибка обновления активного видео")
            return False

        db_path.unlink()
        return True

    except Exception as e:
        print(f"✗ Ошибка операций с видео: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 60)
    print("Тестирование API управления заказами")
    print("=" * 60 + "\n")

    tests = [
        ("Импорты", test_imports),
        ("Схема БД", test_database_schema),
        ("Операции с клиентами", test_client_operations),
        ("Операции с портретами", test_portrait_operations),
        ("Операции с видео", test_video_operations),
    ]

    results = []
    for name, test_func in tests:
        print(f"\nТест: {name}")
        print("-" * 60)
        result = test_func()
        results.append((name, result))
        print()

    print("=" * 60)
    print("Результаты тестирования:")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1

    print("=" * 60)
    print(f"Всего тестов: {len(results)}")
    print(f"Успешно: {passed}")
    print(f"Провалено: {failed}")
    print("=" * 60 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
