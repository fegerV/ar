#!/usr/bin/env python3
"""
Тестирование API портретов
Проверяет основной функционал создания и управления портретами
"""

import requests
import json
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"
TOKEN = None  # Будет получен после логина

def login(username="admin", password="admin"):
    """Вход в систему"""
    print(f"\n🔐 Вход в систему как {username}...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": username, "password": password}
    )
    if response.status_code == 200:
        global TOKEN
        TOKEN = response.json()["access_token"]
        print("✅ Вход выполнен успешно")
        return True
    else:
        print(f"❌ Ошибка входа: {response.status_code}")
        print(response.text)
        return False

def create_test_files():
    """Создать тестовые файлы"""
    print("\n📁 Создание тестовых файлов...")
    
    # Создаем простое тестовое изображение
    try:
        from PIL import Image, ImageDraw
        
        # Создаем изображение 800x600
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        # Рисуем простой портрет (круг с глазами и улыбкой)
        draw.ellipse([250, 150, 550, 450], fill='lightblue', outline='black', width=3)
        draw.ellipse([320, 250, 360, 290], fill='black')
        draw.ellipse([440, 250, 480, 290], fill='black')
        draw.arc([300, 320, 500, 420], 0, 180, fill='black', width=5)
        
        img.save('/tmp/test_portrait.jpg')
        print("✅ Тестовое изображение создано: /tmp/test_portrait.jpg")
        
        # Создаем фейковый видео файл (просто текстовый файл)
        with open('/tmp/test_video.mp4', 'wb') as f:
            f.write(b'fake video content for testing')
        print("✅ Тестовое видео создано: /tmp/test_video.mp4")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка создания тестовых файлов: {e}")
        return False

def test_create_order():
    """Тест создания заказа"""
    print("\n📦 Тест создания заказа...")
    
    files = {
        'image': open('/tmp/test_portrait.jpg', 'rb'),
        'video': open('/tmp/test_video.mp4', 'rb')
    }
    data = {
        'phone': '+79991234567',
        'name': 'Тестовый Клиент'
    }
    
    response = requests.post(
        f"{BASE_URL}/orders/create",
        headers={"Authorization": f"Bearer {TOKEN}"},
        files=files,
        data=data
    )
    
    files['image'].close()
    files['video'].close()
    
    if response.status_code == 200:
        order = response.json()
        print("✅ Заказ создан успешно!")
        print(f"   Клиент ID: {order['client']['id']}")
        print(f"   Портрет ID: {order['portrait']['id']}")
        print(f"   Постоянная ссылка: {order['portrait']['permanent_link']}")
        print(f"   Видео ID: {order['video']['id']}")
        return order
    else:
        print(f"❌ Ошибка создания заказа: {response.status_code}")
        print(response.text)
        return None

def test_search_clients(phone):
    """Тест поиска клиентов"""
    print(f"\n🔍 Поиск клиентов по телефону '{phone}'...")
    
    response = requests.get(
        f"{BASE_URL}/clients/search",
        headers={"Authorization": f"Bearer {TOKEN}"},
        params={"phone": phone}
    )
    
    if response.status_code == 200:
        clients = response.json()
        print(f"✅ Найдено клиентов: {len(clients)}")
        for client in clients:
            print(f"   - {client['name']} ({client['phone']})")
        return clients
    else:
        print(f"❌ Ошибка поиска: {response.status_code}")
        print(response.text)
        return []

def test_list_clients():
    """Тест списка клиентов"""
    print("\n👥 Получение списка всех клиентов...")
    
    response = requests.get(
        f"{BASE_URL}/clients/list",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    
    if response.status_code == 200:
        clients = response.json()
        print(f"✅ Всего клиентов: {len(clients)}")
        return clients
    else:
        print(f"❌ Ошибка получения списка: {response.status_code}")
        print(response.text)
        return []

def test_list_portraits(client_id=None):
    """Тест списка портретов"""
    print(f"\n🖼️  Получение списка портретов...")
    
    params = {"client_id": client_id} if client_id else {}
    response = requests.get(
        f"{BASE_URL}/portraits/list",
        headers={"Authorization": f"Bearer {TOKEN}"},
        params=params
    )
    
    if response.status_code == 200:
        portraits = response.json()
        print(f"✅ Найдено портретов: {len(portraits)}")
        for portrait in portraits:
            print(f"   - ID: {portrait['id'][:8]}... (просмотров: {portrait['view_count']})")
        return portraits
    else:
        print(f"❌ Ошибка получения списка: {response.status_code}")
        print(response.text)
        return []

def test_add_video(portrait_id):
    """Тест добавления видео"""
    print(f"\n🎬 Добавление видео к портрету {portrait_id[:8]}...")
    
    files = {
        'video': open('/tmp/test_video.mp4', 'rb')
    }
    data = {
        'portrait_id': portrait_id
    }
    
    response = requests.post(
        f"{BASE_URL}/videos/add",
        headers={"Authorization": f"Bearer {TOKEN}"},
        files=files,
        data=data
    )
    
    files['video'].close()
    
    if response.status_code == 200:
        video = response.json()
        print("✅ Видео добавлено успешно!")
        print(f"   Видео ID: {video['id']}")
        print(f"   Активно: {video['is_active']}")
        return video
    else:
        print(f"❌ Ошибка добавления видео: {response.status_code}")
        print(response.text)
        return None

def test_list_videos(portrait_id):
    """Тест списка видео"""
    print(f"\n🎥 Получение списка видео для портрета {portrait_id[:8]}...")
    
    response = requests.get(
        f"{BASE_URL}/videos/list/{portrait_id}",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    
    if response.status_code == 200:
        videos = response.json()
        print(f"✅ Найдено видео: {len(videos)}")
        for video in videos:
            active = "✓ Активно" if video['is_active'] else ""
            print(f"   - ID: {video['id'][:8]}... {active}")
        return videos
    else:
        print(f"❌ Ошибка получения списка: {response.status_code}")
        print(response.text)
        return []

def test_activate_video(video_id):
    """Тест активации видео"""
    print(f"\n▶️  Активация видео {video_id[:8]}...")
    
    response = requests.put(
        f"{BASE_URL}/videos/{video_id}/activate",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    
    if response.status_code == 200:
        video = response.json()
        print("✅ Видео активировано успешно!")
        print(f"   Активно: {video['is_active']}")
        return video
    else:
        print(f"❌ Ошибка активации видео: {response.status_code}")
        print(response.text)
        return None

def test_portrait_details(portrait_id):
    """Тест получения детальной информации"""
    print(f"\n📋 Получение детальной информации о портрете {portrait_id[:8]}...")
    
    response = requests.get(
        f"{BASE_URL}/portraits/{portrait_id}/details",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    
    if response.status_code == 200:
        details = response.json()
        print("✅ Информация получена!")
        print(f"   Клиент: {details['client']['name']}")
        print(f"   Телефон: {details['client']['phone']}")
        print(f"   Ссылка: {details['portrait']['permanent_link']}")
        print(f"   Видео: {len(details['videos'])}")
        return details
    else:
        print(f"❌ Ошибка получения информации: {response.status_code}")
        print(response.text)
        return None

def main():
    """Основная функция тестирования"""
    print("=" * 60)
    print("🧪 Тестирование API управления портретами")
    print("=" * 60)
    
    # Вход в систему
    if not login():
        print("\n❌ Не удалось войти в систему")
        return
    
    # Создание тестовых файлов
    if not create_test_files():
        print("\n⚠️  Не удалось создать тестовые файлы, используем существующие")
    
    # Создание заказа
    order = test_create_order()
    if not order:
        print("\n❌ Тесты прерваны: не удалось создать заказ")
        return
    
    portrait_id = order['portrait']['id']
    client_id = order['client']['id']
    
    # Поиск клиентов
    test_search_clients("999")
    
    # Список клиентов
    test_list_clients()
    
    # Список портретов
    test_list_portraits(client_id)
    
    # Детальная информация
    test_portrait_details(portrait_id)
    
    # Список видео
    videos = test_list_videos(portrait_id)
    
    # Добавление второго видео
    new_video = test_add_video(portrait_id)
    
    # Обновленный список видео
    videos = test_list_videos(portrait_id)
    
    # Активация второго видео
    if new_video:
        test_activate_video(new_video['id'])
        
        # Проверка что видео активировано
        test_list_videos(portrait_id)
    
    print("\n" + "=" * 60)
    print("✅ Все тесты завершены!")
    print("=" * 60)
    print(f"\n🔗 Постоянная ссылка портрета: {order['portrait']['permanent_link']}")
    print("\n📝 Примечание: Эта ссылка не изменится при смене видео")

if __name__ == "__main__":
    main()
