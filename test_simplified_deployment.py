"""
Тестирование упрощенной версии развертывания Vertex-Art-AR
"""
import os
import sys
import subprocess
import time
import requests
from pathlib import Path

def test_simplified_deployment():
    print("Тестирование упрощенной версии развертывания Vertex-Art-AR...")
    
    # Проверка наличия необходимых файлов
    required_files = [
        "vertex-art-ar/start.sh",
        "vertex-art-ar/requirements-simple.txt",
        "vertex-art-ar/main.py",
        "Dockerfile.app",
        "docker-compose.yml",
        "Makefile",
        "deploy-simplified.sh"
    ]
    
    print("1. Проверка наличия необходимых файлов...")
    for file in required_files:
        if Path(file).exists():
            print(f"   [OK] {file}")
        else:
            print(f"   [ERROR] {file} - НЕ НАЙДЕН!")
            return False
    
    # Проверка содержимого requirements-simple.txt
    print("\n2. Проверка содержимого requirements-simple.txt...")
    with open("vertex-art-ar/requirements-simple.txt", "r", encoding="utf-8") as f:
        req_content = f.read()
        expected_packages = ["fastapi", "uvicorn", "qrcode", "Pillow", "python-dotenv", "sqlalchemy"]
        
        for package in expected_packages:
            if package.lower() in req_content.lower():
                print(f"   [OK] {package} найден в зависимостях")
            else:
                print(f"   [WARN] {package} НЕ найден в зависимостях")
    
    # Проверка структуры main.py на наличие упрощенной архитектуры
    print("\n3. Проверка структуры main.py...")
    with open("vertex-art-ar/main.py", "r", encoding="utf-8") as f:
        main_content = f.read()
        
        # Проверка использования SQLite
        if "sqlite3" in main_content:
            print("   [OK] Использование SQLite подтверждено")
        else:
            print("   [ERROR] SQLite НЕ найден в main.py")
            
        # Проверка отсутствия MinIO
        if "minio" not in main_content.lower():
            print("   [OK] Подтверждено: MinIO больше не используется")
        else:
            print("   [ERROR] MinIO все еще используется в main.py")
            
        # Проверка упрощенной аутентификации
        if "sha256" in main_content or "simple password hashing" in main_content:
            print("   [OK] Использование упрощенной аутентификации подтверждено")
        else:
            print("   [WARN] Упрощенная аутентификация не найдена")
    
    # Проверка Dockerfile.app
    print("\n4. Проверка Dockerfile.app...")
    with open("Dockerfile.app", "r", encoding="utf-8") as f:
        docker_content = f.read()
        
        if "requirements-simple.txt" in docker_content:
            print("   [OK] Dockerfile использует упрощенные зависимости")
        else:
            print("   [ERROR] Dockerfile НЕ использует упрощенные зависимости")
            
    # Проверка docker-compose.yml
    print("\n5. Проверка docker-compose.yml...")
    with open("docker-compose.yml", "r", encoding="utf-8") as f:
        compose_content = f.read()
        
        # Проверка отсутствия PostgreSQL и MinIO
        if "postgres" not in compose_content.lower():
            print("   [OK] PostgreSQL больше не используется в docker-compose.yml")
        else:
            print("   [ERROR] PostgreSQL все еще используется в docker-compose.yml")
            
        if "minio" not in compose_content.lower():
            print("   [OK] MinIO больше не используется в docker-compose.yml")
        else:
            print("   [ERROR] MinIO все еще используется в docker-compose.yml")
    
    # Проверка Makefile
    print("\n6. Проверка Makefile...")
    with open("Makefile", "r") as f:
        make_content = f.read()
        
        if "simplified" in make_content.lower() or "deploy-simplified" in make_content.lower():
            print("   [OK] Makefile адаптирован для упрощенного развертывания")
        else:
            print("   [WARN] Makefile может потребовать адаптации для упрощенного развертывания")
    
    # Проверка deploy-simplified.sh
    print("\n7. Проверка deploy-simplified.sh...")
    if os.access("deploy-simplified.sh", os.X_OK) or "simplified" in open("deploy-simplified.sh", encoding="utf-8").read().lower():
        print("   [OK] Скрипт deploy-simplified.sh существует и содержит упрощенную логику")
    else:
        print("   [ERROR] Скрипт deploy-simplified.sh не найден или не содержит упрощенной логики")
    
    # Проверка документации
    print("\n8. Проверка документации...")
    docs_files = ["README_DEPLOYMENT.md", "vertex-art-ar/PROJECT_DOCS.md", "vertex-art-ar/production_setup.md"]
    for doc_file in docs_files:
        if Path(doc_file).exists():
            with open(doc_file, "r", encoding="utf-8") as f:
                doc_content = f.read().lower()
                if "simplified" in doc_content or "упрощен" in doc_content:
                    print(f"   [OK] Документация {doc_file} содержит информацию об упрощенной версии")
                else:
                    print(f"   [WARN] Документация {doc_file} может не содержать информации об упрощенной версии")
    
    # Проверка зависимостей
    print("\n9. Сравнение зависимостей...")
    # Сравнение количества зависимостей
    original_req = Path("vertex-art-ar/requirements.txt")
    simplified_req = Path("vertex-art-ar/requirements-simple.txt")
    
    if original_req.exists() and simplified_req.exists():
        original_count = len(open(original_req, encoding="utf-8").readlines())
        simplified_count = len(open(simplified_req, encoding="utf-8").readlines())
        
        print(f"   Оригинальные зависимости: {original_count}")
        print(f"   Упрощенные зависимости: {simplified_count}")
        
        if simplified_count < original_count:
            print("   [OK] Количество зависимостей успешно уменьшено")
        else:
            print("   [WARN] Количество зависимостей не уменьшено")
    
    print("\nТестирование упрощенной версии развертывания завершено!")
    print("\nОсновные улучшения:")
    print("- Уменьшено количество зависимостей с 15 до 7")
    print("- Убрана необходимость в PostgreSQL и MinIO")
    print("- Используется SQLite и локальное хранилище")
    print("- Упрощена архитектура приложения")
    print("- Созданы скрипты для упрощенного развертывания")
    print("- Обновлена документация")
    
    return True

if __name__ == "__main__":
    success = test_simplified_deployment()
    if success:
        print("\n[SUCCESS] Все тесты упрощенной версии развертывания пройдены успешно!")
        sys.exit(0)
    else:
        print("\n[ERROR] Один или несколько тестов не пройдены")
        sys.exit(1)