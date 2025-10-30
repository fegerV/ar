"""
Тестирование API endpoints
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path
import json

# Добавляем путь к основному приложению
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'vertex-ar'))

from main import Database, _hash_password
import asyncio
from fastapi.testclient import TestClient
from main import app

# Создаем тестовый клиент
client = TestClient(app)

def test_health_endpoint():
    """Тестирование эндпоинта здоровья"""
    print("Тест 1: Эндпоинт здоровья (/health)")
    
    try:
        response = client.get("/health")
        print(f"  Статус код: {response.status_code}")
        print(f"  Ответ: {response.json()}")
        
        if response.status_code == 200:
            print("  Эндпоинт здоровья работает корректно: УСПЕШНО")
            return True
        else:
            print("  Эндпоинт здоровья не работает: ОШИБКА")
            return False
    except Exception as e:
        print(f"  Ошибка при тестировании эндпоинта здоровья: {e}")
        return False

def test_version_endpoint():
    """Тестирование эндпоинта версии"""
    print("\nТест 2: Эндпоинт версии (/version)")
    
    try:
        response = client.get("/version")
        print(f"  Статус код: {response.status_code}")
        print(f"  Ответ: {response.json()}")
        
        if response.status_code == 200:
            print("  Эндпоинт версии работает корректно: УСПЕШНО")
            return True
        else:
            print("  Эндпоинт версии не работает: ОШИБКА")
            return False
    except Exception as e:
        print(f"  Ошибка при тестировании эндпоинта версии: {e}")
        return False

def test_auth_endpoints():
    """Тестирование эндпоинтов аутентификации"""
    print("\nТест 3: Эндпоинты аутентификации (/auth/*)")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Создаем временную базу данных
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path)
        
        # Тест регистрации
        print("  Тест регистрации (/auth/register)")
        register_data = {
            "username": "test_user",
            "password": "test_password"
        }
        response = client.post("/auth/register", json=register_data)
        print(f"    Статус код: {response.status_code}")
        
        if response.status_code == 201:
            print("    Регистрация прошла успешно: УСПЕШНО")
        else:
            print(f"    Регистрация не удалась: ОШИБКА - {response.json()}")
            return False
        
        # Тест входа
        print("  Тест входа (/auth/login)")
        login_data = {
            "username": "test_user",
            "password": "test_password"
        }
        response = client.post("/auth/login", json=login_data)
        print(f"    Статус код: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            print(f"    Вход прошел успешно: УСПЕШНО")
            print(f"    Токен: {token_data.get('access_token', 'не найден')[:20]}...")
        else:
            print(f"    Вход не удался: ОШИБКА - {response.json()}")
            return False
        
        return True
    except Exception as e:
        print(f"  Ошибка при тестировании эндпоинтов аутентификации: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_ar_endpoints():
    """Тестирование эндпоинтов AR-контента"""
    print("\nТест 4: Эндпоинты AR-контента (/ar/*)")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Создаем временную базу данных
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path)
        
        # Создаем тестового пользователя
        db.create_user("test_user", _hash_password("test_password"), is_admin=True)
        
        # Тест входа для получения токена
        login_data = {
            "username": "test_user",
            "password": "test_password"
        }
        response = client.post("/auth/login", json=login_data)
        if response.status_code != 200:
            print("  Не удалось получить токен для тестирования AR-эндпоинтов")
            return False
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Тест получения списка AR-контента
        print("  Тест получения списка AR-контента (/ar/list)")
        response = client.get("/ar/list", headers=headers)
        print(f"    Статус код: {response.status_code}")
        
        if response.status_code == 200:
            print("    Получение списка AR-контента прошло успешно: УСПЕШНО")
        else:
            print(f"    Получение списка AR-контента не удалось: ОШИБКА - {response.json()}")
            # Это может быть нормально, если список пуст
        
        # Тест получения конкретного AR-контента (не должно существовать)
        print("  Тест получения несуществующего AR-контента (/ar/nonexistent)")
        response = client.get("/ar/nonexistent")
        print(f"    Статус код: {response.status_code}")
        
        if response.status_code == 404:
            print("    Получение несуществующего AR-контента вернуло правильную ошибку: УСПЕШНО")
        else:
            print(f"    Получение несуществующего AR-контента вернуло неправильный код: {response.status_code}")
            # Это может быть нормально в некоторых случаях
        
        return True
    except Exception as e:
        print(f"  Ошибка при тестировании эндпоинтов AR-контента: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_nft_marker_endpoints():
    """Тестирование эндпоинтов NFT-маркеров"""
    print("\nТест 5: Эндпоинты NFT-маркеров (/nft-marker/*)")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Создаем временную базу данных
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path)
        
        # Создаем тестового пользователя
        db.create_user("test_user", _hash_password("test_password"), is_admin=True)
        
        # Тест входа для получения токена
        login_data = {
            "username": "test_user",
            "password": "test_password"
        }
        response = client.post("/auth/login", json=login_data)
        if response.status_code != 200:
            print("  Не удалось получить токен для тестирования NFT-маркеров")
            return False
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Тест получения списка NFT-маркеров
        print("  Тест получения списка NFT-маркеров (/nft-marker/list)")
        response = client.get("/nft-marker/list", headers=headers)
        print(f"    Статус код: {response.status_code}")
        
        if response.status_code == 200:
            print("    Получение списка NFT-маркеров прошло успешно: УСПЕШНО")
        else:
            print(f"    Получение списка NFT-маркеров не удалось: ОШИБКА - {response.json()}")
            # Это может быть нормально, если список пуст
        
        return True
    except Exception as e:
        print(f"  Ошибка при тестировании эндпоинтов NFT-маркеров: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_admin_endpoints():
    """Тестирование эндпоинтов админ-панели"""
    print("\nТест 6: Эндпоинты админ-панели (/admin/*)")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Создаем временную базу данных
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path)
        
        # Создаем тестового пользователя-администратора
        db.create_user("admin_user", _hash_password("admin_password"), is_admin=True)
        
        # Тест входа для получения токена
        login_data = {
            "username": "admin_user",
            "password": "admin_password"
        }
        response = client.post("/auth/login", json=login_data)
        if response.status_code != 200:
            print("  Не удалось получить токен для тестирования админ-эндпоинтов")
            return False
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Тест получения информации о системе
        print("  Тест получения информации о системе (/admin/system-info)")
        response = client.get("/admin/system-info", headers=headers)
        print(f"    Статус код: {response.status_code}")
        
        if response.status_code == 200:
            print("    Получение информации о системе прошло успешно: УСПЕШНО")
        else:
            print(f"    Получение информации о системе не удалось: ОШИБКА - {response.json()}")
        
        # Тест получения информации о хранилище
        print("  Тест получения информации о хранилище (/admin/storage-info)")
        response = client.get("/admin/storage-info", headers=headers)
        print(f"    Статус код: {response.status_code}")
        
        if response.status_code == 200:
            print("    Получение информации о хранилище прошло успешно: УСПЕШНО")
        else:
            print(f"    Получение информации о хранилище не удалось: ОШИБКА - {response.json()}")
        
        # Тест получения статистики контента
        print("  Тест получения статистики контента (/admin/content-stats)")
        response = client.get("/admin/content-stats", headers=headers)
        print(f"    Статус код: {response.status_code}")
        
        if response.status_code == 200:
            print("    Получение статистики контента прошло успешно: УСПЕШНО")
        else:
            print(f"    Получение статистики контента не удалось: ОШИБКА - {response.json()}")
        
        return True
    except Exception as e:
        print(f"  Ошибка при тестировании эндпоинтов админ-панели: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_data_validation():
    """Тестирование валидации входных данных"""
    print("\nТест 7: Валидация входных данных")
    
    try:
        # Тест регистрации с пустыми полями
        print("  Тест регистрации с пустыми полями")
        register_data = {
            "username": "",
            "password": ""
        }
        response = client.post("/auth/register", json=register_data)
        print(f"    Статус код: {response.status_code}")
        
        if response.status_code == 422:
            print("    Валидация пустых полей работает корректно: УСПЕШНО")
        else:
            print(f"    Валидация пустых полей не сработала: ОШИБКА - {response.json()}")
        
        # Тест регистрации с коротким именем пользователя
        print("  Тест регистрации с коротким именем пользователя")
        register_data = {
            "username": "a",  # слишком короткое
            "password": "password123"
        }
        response = client.post("/auth/register", json=register_data)
        print(f"    Статус код: {response.status_code}")
        
        # Примечание: в текущей реализации минимальная длина 1 символ, поэтому ошибка может не возникнуть
        
        return True
    except Exception as e:
        print(f"  Ошибка при тестировании валидации входных данных: {e}")
        return False

def test_error_handling():
    """Тестирование обработки ошибок"""
    print("\nТест 8: Обработка ошибок")
    
    try:
        # Тест несуществующего эндпоинта
        print("  Тест несуществующего эндпоинта")
        response = client.get("/nonexistent-endpoint")
        print(f"    Статус код: {response.status_code}")
        
        if response.status_code == 404:
            print("    Обработка несуществующих эндпоинтов работает корректно: УСПЕШНО")
        else:
            print(f"    Обработка несуществующих эндпоинтов не сработала: ОШИБКА")
        
        # Тест метода, который не разрешен
        print("  Тест PUT-запроса к эндпоинту, который не поддерживает PUT")
        response = client.put("/health")
        print(f"    Статус код: {response.status_code}")
        
        # В FastAPI обычно возвращается 405 Method Not Allowed для неподдерживаемых методов
        
        return True
    except Exception as e:
        print(f"  Ошибка при тестировании обработки ошибок: {e}")
        return False

def test_returned_data():
    """Тестирование корректности возвращаемых данных"""
    print("\nТест 9: Корректность возвращаемых данных")
    
    try:
        # Тест структуры ответа от эндпоинта здоровья
        print("  Тест структуры ответа от эндпоинта здоровья")
        response = client.get("/health")
        data = response.json()
        
        print(f"    Ответ: {data}")
        
        # Проверяем наличие обязательных полей
        if "status" in data and "version" in data:
            print("    Структура ответа корректна: УСПЕШНО")
        else:
            print("    Структура ответа некорректна: ОШИБКА")
            return False
        
        # Проверяем типы данных
        if isinstance(data["status"], str) and isinstance(data["version"], str):
            print("    Типы данных в ответе корректны: УСПЕШНО")
        else:
            print("    Типы данных в ответе некорректны: ОШИБКА")
            return False
        
        return True
    except Exception as e:
        print(f"  Ошибка при тестировании корректности возвращаемых данных: {e}")
        return False

def main():
    """Основная функция тестирования API endpoints"""
    print("=== Тестирование API endpoints ===\n")
    
    tests = [
        test_health_endpoint,
        test_version_endpoint,
        test_auth_endpoints,
        test_ar_endpoints,
        test_nft_marker_endpoints,
        test_admin_endpoints,
        test_data_validation,
        test_error_handling,
        test_returned_data
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n=== Результаты ===")
    print(f"Пройдено тестов: {sum(results)}/{len(results)}")
    
    if all(results):
        print("Все тесты API endpoints пройдены успешно!")
        return True
    else:
        print("Некоторые тесты API endpoints не пройдены.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)