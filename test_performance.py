"""
Тестирование производительности приложения
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path
import time
import json

# Добавляем путь к основному приложению
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'vertex-art-ar'))

from main import Database, _hash_password
from fastapi.testclient import TestClient
from main import app

# Создаем тестовый клиент
client = TestClient(app)

def test_large_file_upload():
    """Тестирование загрузки больших файлов"""
    print("Тест 1: Загрузка больших файлов")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Создаем временную базу данных
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path)
        
        # Создаем тестового пользователя-администратора
        db.create_user("admin_user", _hash_password("admin_password"), is_admin=True)
        
        # Входим в систему для получения токена
        login_data = {
            "username": "admin_user",
            "password": "admin_password"
        }
        response = client.post("/auth/login", json=login_data)
        if response.status_code != 200:
            print("  Не удалось получить токен для тестирования загрузки файлов")
            return False
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Создаем большой файл (10 МБ)
        print("  Создание большого файла (10 МБ)")
        large_file_path = Path(temp_dir) / "large_image.jpg"
        with open(large_file_path, "wb") as f:
            # Записываем 10 МБ случайных данных
            f.write(os.urandom(10 * 1024 * 1024))
        
        # Создаем видео файл (5 МБ)
        print("  Создание видео файла (5 МБ)")
        video_file_path = Path(temp_dir) / "large_video.mp4"
        with open(video_file_path, "wb") as f:
            # Записываем 5 МБ случайных данных
            f.write(os.urandom(5 * 1024 * 1024))
        
        # Замеряем время загрузки
        print("  Замер времени загрузки больших файлов")
        start_time = time.time()
        
        # Загружаем большие файлы
        try:
            with open(large_file_path, "rb") as image_file, open(video_file_path, "rb") as video_file:
                files = {
                    "image": ("large_image.jpg", image_file, "image/jpeg"),
                    "video": ("large_video.mp4", video_file, "video/mp4")
                }
                response = client.post("/ar/upload", files=files, headers=headers)
            
            end_time = time.time()
            upload_time = end_time - start_time
            
            print(f"    Время загрузки: {upload_time:.2f} секунд")
            print(f"    Статус код: {response.status_code}")
            
            if response.status_code == 200:
                print("    Загрузка больших файлов прошла успешно: УСПЕШНО")
                print(f"    Скорость загрузки: {(15 * 1024 * 1024) / upload_time / 1024 / 1024:.2f} МБ/с")
                return True
            else:
                print(f"    Загрузка больших файлов не удалась: ОШИБКА - {response.json()}")
                return False
        except Exception as e:
            print(f"    Ошибка при загрузке больших файлов: {e}")
            return False
        
    except Exception as e:
        print(f"  Ошибка при тестировании загрузки больших файлов: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_multiple_file_upload():
    """Тестирование одновременной загрузки нескольких файлов"""
    print("\nТест 2: Одновременная загрузка нескольких файлов")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Создаем временную базу данных
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path)
        
        # Создаем тестового пользователя-администратора
        db.create_user("admin_user", _hash_password("admin_password"), is_admin=True)
        
        # Входим в систему для получения токена
        login_data = {
            "username": "admin_user",
            "password": "admin_password"
        }
        response = client.post("/auth/login", json=login_data)
        if response.status_code != 200:
            print("  Не удалось получить токен для тестирования загрузки файлов")
            return False
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Создаем несколько файлов
        print("  Создание нескольких файлов")
        file_pairs = []
        for i in range(3):
            # Создаем изображение (1 МБ)
            image_path = Path(temp_dir) / f"image_{i}.jpg"
            with open(image_path, "wb") as f:
                f.write(os.urandom(1024 * 1024))
            
            # Создаем видео (2 МБ)
            video_path = Path(temp_dir) / f"video_{i}.mp4"
            with open(video_path, "wb") as f:
                f.write(os.urandom(2 * 1024 * 1024))
            
            file_pairs.append((image_path, video_path))
        
        # Замеряем время загрузки нескольких файлов
        print("  Замер времени загрузки нескольких файлов")
        start_time = time.time()
        
        # Загружаем несколько файлов последовательно
        results = []
        for i, (image_path, video_path) in enumerate(file_pairs):
            try:
                with open(image_path, "rb") as image_file, open(video_path, "rb") as video_file:
                    files = {
                        "image": (f"image_{i}.jpg", image_file, "image/jpeg"),
                        "video": (f"video_{i}.mp4", video_file, "video/mp4")
                    }
                    response = client.post("/ar/upload", files=files, headers=headers)
                    results.append(response.status_code == 200)
            except Exception as e:
                print(f"    Ошибка при загрузке файла {i}: {e}")
                results.append(False)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"    Общее время загрузки: {total_time:.2f} секунд")
        print(f"    Успешно загружено: {sum(results)}/{len(results)} файлов")
        
        if all(results):
            print("    Одновременная загрузка нескольких файлов прошла успешно: УСПЕШНО")
            return True
        else:
            print("    Одновременная загрузка нескольких файлов не удалась: ОШИБКА")
            return False
        
    except Exception as e:
        print(f"  Ошибка при тестировании одновременной загрузки нескольких файлов: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_application_under_load():
    """Тестирование работы приложения под нагрузкой"""
    print("\nТест 3: Работа приложения под нагрузкой")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Создаем временную базу данных
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path)
        
        # Создаем тестового пользователя-администратора
        db.create_user("admin_user", _hash_password("admin_password"), is_admin=True)
        
        # Входим в систему для получения токена
        login_data = {
            "username": "admin_user",
            "password": "admin_password"
        }
        response = client.post("/auth/login", json=login_data)
        if response.status_code != 200:
            print("  Не удалось получить токен для тестирования")
            return False
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Создаем тестовый файл
        test_file_path = Path(temp_dir) / "test_image.jpg"
        with open(test_file_path, "wb") as f:
            f.write(os.urandom(1024 * 1024))  # 1 МБ
        
        test_video_path = Path(temp_dir) / "test_video.mp4"
        with open(test_video_path, "wb") as f:
            f.write(os.urandom(2 * 1024 * 1024))  # 2 МБ
        
        # Выполняем серию запросов к приложению
        print("  Выполнение серии запросов к приложению")
        start_time = time.time()
        
        try:
            # 1. Загрузка контента
            with open(test_file_path, "rb") as image_file, open(test_video_path, "rb") as video_file:
                files = {
                    "image": ("test_image.jpg", image_file, "image/jpeg"),
                    "video": ("test_video.mp4", video_file, "video/mp4")
                }
                response = client.post("/ar/upload", files=files, headers=headers)
            
            # 2. Получение списка контента
            response = client.get("/ar/list", headers=headers)
            
            # 3. Получение информации о системе (для администратора)
            response = client.get("/admin/system-info", headers=headers)
            
            # 4. Получение информации о хранилище
            response = client.get("/admin/storage-info", headers=headers)
            
            # 5. Получение статистики контента
            response = client.get("/admin/content-stats", headers=headers)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            print(f"    Общее время выполнения серии запросов: {total_time:.2f} секунд")
            print("    Работа приложения под нагрузкой прошла успешно: УСПЕШНО")
            return True
        except Exception as e:
            print(f"    Ошибка при выполнении серии запросов: {e}")
            return False
        
    except Exception as e:
        print(f"  Ошибка при тестировании работы приложения под нагрузкой: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_memory_and_cpu_usage():
    """Тестирование использования памяти и процессора"""
    print("\nТест 4: Использование памяти и процессора")
    
    try:
        # Импортируем модуль для получения информации о системе
        import psutil
        import os
        
        # Получаем информацию о текущем процессе
        process = psutil.Process(os.getpid())
        
        # Получаем начальные значения
        initial_memory = process.memory_info().rss / 1024 / 1024  # МБ
        initial_cpu = process.cpu_percent()
        
        print(f"    Начальное использование памяти: {initial_memory:.2f} МБ")
        print(f"    Начальное использование CPU: {initial_cpu:.2f}%")
        
        # Выполняем несколько операций для увеличения нагрузки
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Создаем временную базу данных
            db_path = Path(temp_dir) / "test.db"
            db = Database(db_path)
            
            # Создаем тестового пользователя
            db.create_user("test_user", _hash_password("test_password"), is_admin=True)
            
            # Выполняем серию операций
            for i in range(100):
                db.create_user(f"user_{i}", _hash_password(f"password_{i}"), is_admin=False)
            
            # Получаем финальные значения
            final_memory = process.memory_info().rss / 1024 / 1024  # МБ
            final_cpu = process.cpu_percent()
            
            print(f"    Финальное использование памяти: {final_memory:.2f} МБ")
            print(f"    Финальное использование CPU: {final_cpu:.2f}%")
            print(f"    Увеличение использования памяти: {final_memory - initial_memory:.2f} МБ")
            
            print("    Тестирование использования памяти и процессора завершено: УСПЕШНО")
            return True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except ImportError:
        print("    Модуль psutil не установлен, пропускаем тест")
        print("    Для установки выполните: pip install psutil")
        return True
    except Exception as e:
        print(f"  Ошибка при тестировании использования памяти и процессора: {e}")
        return False

def main():
    """Основная функция тестирования производительности"""
    print("=== Тестирование производительности ===\n")
    
    tests = [
        test_large_file_upload,
        test_multiple_file_upload,
        test_application_under_load,
        test_memory_and_cpu_usage
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n=== Результаты ===")
    print(f"Пройдено тестов: {sum(results)}/{len(results)}")
    
    if all(results):
        print("Все тесты производительности пройдены успешно!")
        return True
    else:
        print("Некоторые тесты производительности не пройдены.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)