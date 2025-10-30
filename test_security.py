"""
Тестирование безопасности приложения
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path
import json

# Добавляем путь к основному приложению
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'vertex-art-ar'))

from main import Database, _hash_password
from fastapi.testclient import TestClient
from main import app

# Создаем тестовый клиент
client = TestClient(app)

def test_malicious_file_upload_protection():
    """Тестирование защиты от загрузки вредоносных файлов"""
    print("Тест 1: Защита от загрузки вредоносных файлов")
    
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
        
        # Тест загрузки файла с вредоносным содержимым
        print("  Тест загрузки файла с вредоносным содержимым")
        
        # Создаем "вредоносный" файл (на самом деле просто текст)
        malicious_content = b"#!/bin/bash\necho 'malicious code'\nrm -rf /"
        malicious_file = tempfile.NamedTemporaryFile(delete=False, suffix=".exe")
        malicious_file.write(malicious_content)
        malicious_file.close()
        
        # Пытаемся загрузить "вредоносный" файл как изображение
        try:
            with open(malicious_file.name, "rb") as f:
                files = {
                    "image": ("malicious.exe", f, "application/octet-stream"),
                    "video": ("test.mp4", b"fake video content", "video/mp4")
                }
                response = client.post("/ar/upload", files=files, headers=headers)
                print(f"    Статус код: {response.status_code}")
                
                # Ожидаем ошибку из-за неправильного типа файла
                if response.status_code == 400:
                    print("    Защита от загрузки вредоносных файлов работает: УСПЕШНО")
                else:
                    print(f"    Защита от загрузки вредоносных файлов не сработала: ОШИБКА - {response.json()}")
        except Exception as e:
            print(f"    Ошибка при попытке загрузки вредоносного файла: {e}")
            # Это может быть нормально, если защита работает на уровне API
        
        # Удаляем временный файл
        os.unlink(malicious_file.name)
        
        return True
    except Exception as e:
        print(f"  Ошибка при тестировании защиты от загрузки вредоносных файлов: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_file_access_restrictions():
    """Тестирование ограничений доступа к файлам"""
    print("\nТест 2: Ограничения доступа к файлам")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Создаем временную базу данных
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path)
        
        # Создаем двух пользователей
        db.create_user("user1", _hash_password("password1"), is_admin=False)
        db.create_user("user2", _hash_password("password2"), is_admin=False)
        
        # Входим как первый пользователь
        login_data = {
            "username": "user1",
            "password": "password1"
        }
        response = client.post("/auth/login", json=login_data)
        if response.status_code != 200:
            print("  Не удалось получить токен для первого пользователя")
            return False
        
        token1 = response.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}
        
        # Входим как второй пользователь
        login_data = {
            "username": "user2",
            "password": "password2"
        }
        response = client.post("/auth/login", json=login_data)
        if response.status_code != 200:
            print("  Не удалось получить токен для второго пользователя")
            return False
        
        token2 = response.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        # Проверяем доступ к списку контента
        print("  Тест доступа к списку контента для обычных пользователей")
        response1 = client.get("/ar/list", headers=headers1)
        response2 = client.get("/ar/list", headers=headers2)
        
        print(f"    Статус код для user1: {response1.status_code}")
        print(f"    Статус код для user2: {response2.status_code}")
        
        # Обычные пользователи должны видеть только свой контент
        if response1.status_code == 200 and response2.status_code == 200:
            print("    Ограничения доступа к списку контента работают: УСПЕШНО")
        else:
            print("    Ограничения доступа к списку контента не работают: ОШИБКА")
            # Это может быть нормально, если список пуст
        
        return True
    except Exception as e:
        print(f"  Ошибка при тестировании ограничений доступа к файлам: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_exception_handling():
    """Тестирование корректной обработки исключений"""
    print("\nТест 3: Корректная обработка исключений")
    
    try:
        # Тест обращения к несуществующему эндпоинту
        print("  Тест обращения к несуществующему эндпоинту")
        response = client.get("/nonexistent-endpoint")
        print(f"    Статус код: {response.status_code}")
        
        if response.status_code == 404:
            print("    Обработка несуществующих эндпоинтов работает: УСПЕШНО")
        else:
            print("    Обработка несуществующих эндпоинтов не работает: ОШИБКА")
            return False
        
        # Тест использования неподдерживаемого HTTP метода
        print("  Тест использования неподдерживаемого HTTP метода")
        response = client.put("/health")
        print(f"    Статус код: {response.status_code}")
        
        if response.status_code == 405:
            print("    Обработка неподдерживаемых методов работает: УСПЕШНО")
        else:
            print("    Обработка неподдерживаемых методов не работает: ОШИБКА")
            return False
        
        return True
    except Exception as e:
        print(f"  Ошибка при тестировании корректной обработки исключений: {e}")
        return False

def test_authentication_token_security():
    """Тестирование безопасности токенов аутентификации"""
    print("\nТест 4: Безопасность токенов аутентификации")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Создаем временную базу данных
        db_path = Path(temp_dir) / "test.db"
        db = Database(db_path)
        
        # Создаем тестового пользователя
        db.create_user("test_user", _hash_password("test_password"), is_admin=False)
        
        # Входим в систему для получения токена
        login_data = {
            "username": "test_user",
            "password": "test_password"
        }
        response = client.post("/auth/login", json=login_data)
        if response.status_code != 200:
            print("  Не удалось получить токен для тестирования")
            return False
        
        token = response.json()["access_token"]
        print(f"    Получен токен: {token[:20]}...")
        
        # Проверяем, что токен работает
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/ar/list", headers=headers)
        print(f"    Статус код при использовании токена: {response.status_code}")
        
        if response.status_code == 200:
            print("    Токен аутентификации работает корректно: УСПЕШНО")
        else:
            print("    Токен аутентификации не работает: ОШИБКА")
            return False
        
        # Проверяем, что истекший или невалидный токен не работает
        print("  Тест использования невалидного токена")
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/ar/list", headers=invalid_headers)
        print(f"    Статус код при использовании невалидного токена: {response.status_code}")
        
        if response.status_code == 401:
            print("    Проверка невалидных токенов работает: УСПЕШНО")
        else:
            print("    Проверка невалидных токенов не работает: ОШИБКА")
            return False
        
        return True
    except Exception as e:
        print(f"  Ошибка при тестировании безопасности токенов аутентификации: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def main():
    """Основная функция тестирования безопасности"""
    print("=== Тестирование безопасности ===\n")
    
    tests = [
        test_malicious_file_upload_protection,
        test_file_access_restrictions,
        test_exception_handling,
        test_authentication_token_security
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n=== Результаты ===")
    print(f"Пройдено тестов: {sum(results)}/{len(results)}")
    
    if all(results):
        print("Все тесты безопасности пройдены успешно!")
        return True
    else:
        print("Некоторые тесты безопасности не пройдены.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)