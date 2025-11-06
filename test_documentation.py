"""
Тестирование документации приложения
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Добавляем путь к основному приложению
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vertex-ar"))


def test_readme_completeness():
    """Проверка актуальности README.md"""
    print("Тест 1: Актуальность README.md")

    try:
        # Проверяем наличие файла README.md
        readme_path = Path("vertex-ar/README.md")
        if not readme_path.exists():
            print("  Файл README.md не найден: ОШИБКА")
            return False

        print("  Файл README.md найден: УСПЕШНО")

        # Читаем содержимое файла
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Проверяем наличие ключевых разделов
        required_sections = [
            "Vertex AR",
            "Описание",
            "Функциональность",
            "Установка",
            "Запуск",
            "Использование",
            "API",
            "Технологии",
            "Лицензия",
        ]

        missing_sections = []
        for section in required_sections:
            if section not in content:
                missing_sections.append(section)

        if missing_sections:
            print(f"  Отсутствующие разделы: {missing_sections}: ОШИБКА")
            return False
        else:
            print("  Все необходимые разделы присутствуют: УСПЕШНО")

        # Проверяем актуальность информации о версии
        version_file = Path("vertex-ar/VERSION")
        if version_file.exists():
            with open(version_file, "r") as f:
                current_version = f.read().strip()

            if current_version in content:
                print(f"  Версия {current_version} указана в README.md: УСПЕШНО")
            else:
                print(f"  Версия {current_version} не указана в README.md: ОШИБКА")
                return False
        else:
            print("  Файл VERSION не найден: ОШИБКА")
            return False

        return True
    except Exception as e:
        print(f"  Ошибка при проверке актуальности README.md: {e}")
        return False


def test_installation_instructions():
    """Проверка инструкций по установке и запуску"""
    print("\nТест 2: Инструкции по установке и запуску")

    try:
        # Проверяем наличие файла README_DEPLOYMENT.md
        deployment_readme_path = Path("vertex-ar/README_DEPLOYMENT.md")
        if not deployment_readme_path.exists():
            print("  Файл README_DEPLOYMENT.md не найден: ОШИБКА")
            return False

        print("  Файл README_DEPLOYMENT.md найден: УСПЕШНО")

        # Читаем содержимое файла
        with open(deployment_readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Проверяем наличие ключевых разделов
        required_sections = [
            "Развертывание",
            "Установка зависимостей",
            "Настройка окружения",
            "Запуск приложения",
            "Docker",
            "Конфигурация",
        ]

        missing_sections = []
        for section in required_sections:
            if section not in content:
                missing_sections.append(section)

        if missing_sections:
            print(f"  Отсутствующие разделы: {missing_sections}: ОШИБКА")
            return False
        else:
            print("  Все необходимые разделы присутствуют: УСПЕШНО")

        # Проверяем наличие команд установки
        required_commands = ["pip install", "python -m main", "docker-compose up"]

        missing_commands = []
        for command in required_commands:
            if command not in content:
                missing_commands.append(command)

        if missing_commands:
            print(f"  Отсутствующие команды: {missing_commands}: ОШИБКА")
            return False
        else:
            print("  Все необходимые команды присутствуют: УСПЕШНО")

        return True
    except Exception as e:
        print(f"  Ошибка при проверке инструкций по установке и запуску: {e}")
        return False


def test_api_documentation():
    """Проверка API документации"""
    print("\nТест 3: API документация")

    try:
        # Проверяем наличие файла PROJECT_DOCS.md
        api_docs_path = Path("vertex-ar/PROJECT_DOCS.md")
        if not api_docs_path.exists():
            print("  Файл PROJECT_DOCS.md не найден: ОШИБКА")
            return False

        print("  Файл PROJECT_DOCS.md найден: УСПЕШНО")

        # Читаем содержимое файла
        with open(api_docs_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Проверяем наличие ключевых разделов
        required_sections = ["API Endpoints", "Аутентификация", "Загрузка контента", "Генерация маркеров", "Просмотр контента"]

        missing_sections = []
        for section in required_sections:
            if section not in content:
                missing_sections.append(section)

        if missing_sections:
            print(f"  Отсутствующие разделы: {missing_sections}: ОШИБКА")
            return False
        else:
            print("  Все необходимые разделы присутствуют: УСПЕШНО")

        # Проверяем наличие описания эндпоинтов
        required_endpoints = ["/auth/register", "/auth/login", "/ar/upload", "/ar/list", "/nft-marker/generate"]

        missing_endpoints = []
        for endpoint in required_endpoints:
            if endpoint not in content:
                missing_endpoints.append(endpoint)

        if missing_endpoints:
            print(f"  Отсутствующие эндпоинты: {missing_endpoints}: ОШИБКА")
            return False
        else:
            print("  Все необходимые эндпоинты описаны: УСПЕШНО")

        return True
    except Exception as e:
        print(f"  Ошибка при проверке API документации: {e}")
        return False


def test_changelog_consistency():
    """Проверка согласованности CHANGELOG.md"""
    print("\nТест 4: Согласованность CHANGELOG.md")

    try:
        # Проверяем наличие файла CHANGELOG.md
        changelog_path = Path("vertex-ar/CHANGELOG.md")
        if not changelog_path.exists():
            print("  Файл CHANGELOG.md не найден: ОШИБКА")
            return False

        print("  Файл CHANGELOG.md найден: УСПЕШНО")

        # Читаем содержимое файла
        with open(changelog_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Проверяем наличие последней версии из файла VERSION
        version_file = Path("vertex-ar/VERSION")
        if version_file.exists():
            with open(version_file, "r") as f:
                current_version = f.read().strip()

            if current_version in content:
                print(f"  Версия {current_version} указана в CHANGELOG.md: УСПЕШНО")
            else:
                print(f"  Версия {current_version} не указана в CHANGELOG.md: ОШИБКА")
                return False
        else:
            print("  Файл VERSION не найден: ОШИБКА")
            return False

        # Проверяем форматирование изменений
        if "##" in content and "-" in content:
            print("  Форматирование изменений корректно: УСПЕШНО")
        else:
            print("  Форматирование изменений некорректно: ОШИБКА")
            return False

        return True
    except Exception as e:
        print(f"  Ошибка при проверке согласованности CHANGELOG.md: {e}")
        return False


def test_license_information():
    """Проверка информации о лицензии"""
    print("\nТест 5: Информация о лицензии")

    try:
        # Проверяем наличие файла LICENSE
        license_path = Path("vertex-ar/LICENSE")
        if not license_path.exists():
            print("  Файл LICENSE не найден: ОШИБКА")
            return False

        print("  Файл LICENSE найден: УСПЕШНО")

        # Читаем содержимое файла
        with open(license_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Проверяем наличие информации о лицензии MIT
        if "MIT License" in content or "MIT" in content:
            print("  Лицензия MIT указана: УСПЕШНО")
        else:
            print("  Лицензия MIT не указана: ОШИБКА")
            return False

        # Проверяем наличие информации об авторских правах
        if "Copyright" in content:
            print("  Информация об авторских правах указана: УСПЕШНО")
        else:
            print("  Информация об авторских правах не указана: ОШИБКА")
            return False

        return True
    except Exception as e:
        print(f"  Ошибка при проверке информации о лицензии: {e}")
        return False


def main():
    """Основная функция тестирования документации"""
    print("=== Тестирование документации ===\n")

    tests = [
        test_readme_completeness,
        test_installation_instructions,
        test_api_documentation,
        test_changelog_consistency,
        test_license_information,
    ]

    results = []
    for test in tests:
        results.append(test())

    print(f"\n=== Результаты ===")
    print(f"Пройдено тестов: {sum(results)}/{len(results)}")

    if all(results):
        print("Все тесты документации пройдены успешно!")
        return True
    else:
        print("Некоторые тесты документации не пройдены.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
