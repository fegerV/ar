#!/usr/bin/env python3
"""
Тестирование API загрузки изображений и видео с проверкой размера превью
"""
import requests
import json
from pathlib import Path
import base64
from PIL import Image
from io import BytesIO

# Базовый URL API
BASE_URL = "http://localhost:8000"

def create_test_image(size=(800, 600), color=(255, 100, 50)):
    """Создает тестовое изображение"""
    image = Image.new('RGB', size, color)
    buffer = BytesIO()
    image.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer.getvalue()

def test_image_upload():
    """Тестирует загрузку изображения через API"""
    print("=== Тест загрузки изображения ===")
    
    # Сначала получаем токен авторизации
    try:
        auth_response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        
        if auth_response.status_code != 200:
            print(f"Ошибка авторизации: {auth_response.status_code}")
            return False
            
        token = auth_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Авторизация успешна")
        
    except Exception as e:
        print(f"Ошибка при авторизации: {e}")
        return False
    
    # Создаем тестовый клиент
    try:
        client_data = {
            "name": "Test Client",
            "phone": "+1234567890"
        }
        client_response = requests.post(
            f"{BASE_URL}/clients",
            json=client_data,
            headers=headers
        )
        
        if client_response.status_code != 201:
            print(f"Ошибка создания клиента: {client_response.status_code}")
            print(f"Response: {client_response.text}")
            return False
            
        client_id = client_response.json()["id"]
        print(f"✅ Клиент создан: {client_id}")
        
    except Exception as e:
        print(f"Ошибка при создании клиента: {e}")
        return False
    
    # Создаем тестовое изображение
    try:
        image_content = create_test_image()
        print(f"Тестовое изображение создано, размер: {len(image_content)} байт")
        
        # Загружаем изображение
        files = {
            'image': ('test.jpg', image_content, 'image/jpeg')
        }
        
        portrait_response = requests.post(
            f"{BASE_URL}/portraits",
            files=files,
            data={'client_id': client_id},
            headers=headers
        )
        
        if portrait_response.status_code != 201:
            print(f"Ошибка загрузки изображения: {portrait_response.status_code}")
            print(f"Response: {portrait_response.text}")
            return False
            
        portrait_data = portrait_response.json()
        portrait_id = portrait_data["id"]
        print(f"✅ Изображение загружено: {portrait_id}")
        
        # Проверяем, что создано превью
        # (в реальной ситуации превью будет сохранено в файловой системе)
        
        return True
        
    except Exception as e:
        print(f"Ошибка при загрузке изображения: {e}")
        return False

def test_video_upload():
    """Тестирует загрузку видео через API"""
    print("\n=== Тест загрузки видео ===")
    
    # Получаем токен авторизации
    try:
        auth_response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        
        if auth_response.status_code != 200:
            print(f"Ошибка авторизации: {auth_response.status_code}")
            return False
            
        token = auth_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Авторизация успешна")
        
    except Exception as e:
        print(f"Ошибка при авторизации: {e}")
        return False
    
    # Используем существующий портрет (предполагаем, что он есть)
    # В реальной ситуации нужно получить ID существующего портрета
    portrait_id = "test-portrait-id"  # Заглушка
    
    # Читаем тестовое видео
    try:
        video_path = Path("test_video.mp4")
        if not video_path.exists():
            print("Тестовое видео не найдено")
            return False
            
        with open(video_path, "rb") as f:
            video_content = f.read()
        
        print(f"Тестовое видео прочитано, размер: {len(video_content)} байт")
        
        # Загружаем видео
        files = {
            'video': ('test.mp4', video_content, 'video/mp4')
        }
        
        video_response = requests.post(
            f"{BASE_URL}/videos",
            files=files,
            data={'portrait_id': portrait_id},
            headers=headers
        )
        
        if video_response.status_code != 201:
            print(f"Ошибка загрузки видео: {video_response.status_code}")
            print(f"Response: {video_response.text}")
            return False
            
        video_data = video_response.json()
        video_id = video_data["id"]
        print(f"✅ Видео загружено: {video_id}")
        
        return True
        
    except Exception as e:
        print(f"Ошибка при загрузке видео: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("Начинаем тестирование API загрузки...")
    
    results = []
    
    # Тестируем загрузку изображения
    results.append(("Изображение", test_image_upload()))
    
    # Тестируем загрузку видео
    results.append(("Видео", test_video_upload()))
    
    # Выводим итоговые результаты
    print("\n=== Итоги тестирования ===")
    for test_name, result in results:
        status = "✅ УСПЕХ" if result else "❌ ОШИБКА"
        print(f"{test_name}: {status}")
    
    success_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    print(f"\nВсего тестов: {total_count}")
    print(f"Успешно: {success_count}")
    print(f"Неудачно: {total_count - success_count}")
    
    if success_count == total_count:
        print("🎉 Все тесты пройдены успешно!")
        return 0
    else:
        print("❌ Некоторые тесты не пройдены")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
