"""
Тестирование новых функций админ-панели Vertex-Art-AR
"""
import os
import sys
import subprocess
import time
import requests
from pathlib import Path

def test_new_features():
    print("Тестирование новых функций админ-панели Vertex-Art-AR...")
    
    # Проверка наличия необходимых файлов
    required_files = [
        "vertex-art-ar/main.py",
        "vertex-art-ar/templates/admin.html",
        "vertex-art-ar/utils.py"
    ]
    
    print("1. Проверка наличия необходимых файлов...")
    for file in required_files:
        if Path(file).exists():
            print(f"   [OK] {file}")
        else:
            print(f"   [ERROR] {file} - НЕ НАЙДЕН!")
            return False
    
    # Проверка содержимого utils.py
    print("\n2. Проверка содержимого utils.py...")
    with open("vertex-art-ar/utils.py", "r", encoding="utf-8") as f:
        utils_content = f.read()
        required_functions = ["get_disk_usage", "get_storage_usage", "format_bytes"]
        
        for func in required_functions:
            if func in utils_content:
                print(f"   [OK] Функция {func} найдена")
            else:
                print(f"   [ERROR] Функция {func} НЕ найдена")
                return False
    
    # Проверка содержимого main.py
    print("\n3. Проверка содержимого main.py...")
    with open("vertex-art-ar/main.py", "r", encoding="utf-8") as f:
        main_content = f.read()
        
        # Проверка импорта utils
        if "from utils import" in main_content:
            print("   [OK] Импорт utils в main.py подтвержден")
        else:
            print("   [ERROR] Импорт utils НЕ найден в main.py")
            return False
            
        # Проверка новых эндпоинтов
        required_endpoints = [
            "/admin/system-info",
            "/admin/storage-info", 
            "/admin/content-stats"
        ]
        
        for endpoint in required_endpoints:
            if endpoint in main_content:
                print(f"   [OK] Эндпоинт {endpoint} найден")
            else:
                print(f"   [ERROR] Эндпоинт {endpoint} НЕ найден")
                return False
    
    # Проверка содержимого admin.html
    print("\n4. Проверка содержимого admin.html...")
    with open("vertex-art-ar/templates/admin.html", "r", encoding="utf-8") as f:
        admin_content = f.read()
        
        # Проверка наличия новых элементов интерфейса
        required_elements = [
            "storage-info",
            "content-stats",
            "diskUsageBar",
            "statsList",
            "loadSystemInfo",
            "loadContentStats"
        ]
        
        for element in required_elements:
            if element in admin_content:
                print(f"   [OK] Элемент {element} найден")
            else:
                print(f"   [ERROR] Элемент {element} НЕ найден")
                return False
    
    # Проверка наличия новых CSS-классов
    print("\n5. Проверка CSS-классов в admin.html...")
    css_classes = [
        "storage-info",
        "storage-bars",
        "storage-bar-container",
        "storage-bar-label",
        "storage-bar",
        "storage-bar-fill",
        "storage-details",
        "storage-detail",
        "content-stats",
        "stats-grid",
        "stat-item"
    ]
    
    for css_class in css_classes:
        if f".{css_class}" in admin_content or css_class in admin_content:
            print(f"   [OK] CSS-класс {css_class} найден")
        else:
            print(f"   [ERROR] CSS-класс {css_class} НЕ найден")
            return False
    
    # Проверка наличия новых JavaScript-функций
    print("\n6. Проверка JavaScript-функций в admin.html...")
    js_functions = [
        "loadSystemInfo",
        "updateSystemInfo",
        "loadContentStats",
        "updateContentStats"
    ]
    
    for js_func in js_functions:
        if js_func in admin_content:
            print(f"   [OK] JavaScript-функция {js_func} найдена")
        else:
            print(f"   [ERROR] JavaScript-функция {js_func} НЕ найдена")
            return False
    
    print("\n7. Проверка структуры проекта...")
    # Проверка наличия директории storage
    storage_dir = Path("vertex-art-ar/storage")
    if storage_dir.exists():
        print("   [OK] Директория storage существует")
    else:
        print("   [WARN] Директория storage НЕ существует (будет создана при запуске)")
    
    print("\nТестирование новых функций админ-панели завершено!")
    print("\nОсновные улучшения:")
    print("- Добавлена информация о дисковом пространстве")
    print("- Добавлена статистика просмотров AR-контента")
    print("- Улучшен интерфейс админ-панели")
    print("- Добавлены новые CSS-классы и JavaScript-функции")
    print("- Созданы вспомогательные утилиты (utils.py)")
    
    return True

if __name__ == "__main__":
    success = test_new_features()
    if success:
        print("\n[SUCCESS] Все тесты новых функций пройдены успешно!")
        sys.exit(0)
    else:
        print("\n[ERROR] Один или несколько тестов не пройдены")
        sys.exit(1)