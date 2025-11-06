#!/usr/bin/env python3
"""
Профилирование памяти для Vertex AR приложения
Использует memory_profiler для детального анализа использования памяти
"""

import os
import shutil
import sys
import tempfile
import time
from functools import wraps
from pathlib import Path
from typing import Dict, List

# Добавляем путь к основному приложению
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vertex-ar"))

try:
    import psutil
    from fastapi.testclient import TestClient
    from main import Database, _hash_password, app
    from memory_profiler import profile
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Установите необходимые зависимости: pip install memory-profiler psutil")
    sys.exit(1)


def memory_usage_decorator(func):
    """Декоратор для измерения использования памяти"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # МБ

        print(f"🔍 Начало выполнения {func.__name__}: {initial_memory:.2f} МБ")

        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()

        final_memory = process.memory_info().rss / 1024 / 1024  # МБ
        memory_increase = final_memory - initial_memory

        print(f"🔍 Завершение {func.__name__}: {final_memory:.2f} МБ (+{memory_increase:.2f})")
        print(f"⏱️  Время выполнения: {end_time - start_time:.3f} сек")

        return result

    return wrapper


class MemoryProfiler:
    """Профилировщик памяти для приложения"""

    def __init__(self):
        self.client = TestClient(app)
        self.token = None
        self.headers = None
        self.temp_dir = None
        self.memory_snapshots = []

    def setup(self) -> bool:
        """Настройка профилировщика"""
        print("🔧 Настройка профилировщика памяти...")

        try:
            # Создаем временную базу данных
            self.temp_dir = tempfile.mkdtemp()
            db_path = Path(self.temp_dir) / "test.db"
            self.db = Database(db_path)

            # Создаем администратора
            self.db.create_user("admin", _hash_password("admin"), is_admin=True)

            # Получаем токен
            response = self.client.post("/auth/login", json={"username": "admin", "password": "admin"})

            if response.status_code == 200:
                self.token = response.json()["access_token"]
                self.headers = {"Authorization": f"Bearer {self.token}"}
                print("✅ Профилировщик настроен")
                return True
            else:
                print("❌ Не удалось получить токен")
                return False

        except Exception as e:
            print(f"❌ Ошибка настройки: {e}")
            return False

    def take_memory_snapshot(self, label: str):
        """Сделать снимок памяти"""
        process = psutil.Process()
        memory_info = process.memory_info()

        snapshot = {
            "label": label,
            "timestamp": time.time(),
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent(),
            "open_files": len(process.open_files()),
            "threads": process.num_threads(),
        }

        self.memory_snapshots.append(snapshot)
        print(f"📸 Снимок памяти '{label}': {snapshot['rss_mb']:.2f} МБ")

        return snapshot

    @memory_usage_decorator
    def profile_database_operations(self):
        """Профилирование операций с базой данных"""
        print("\n🗄️  Профилирование операций с базой данных...")

        self.take_memory_snapshot("db_start")

        # Создаем много пользователей
        print("  Создание 1000 пользователей...")
        for i in range(1000):
            self.db.create_user(f"user_{i}", _hash_password(f"pass_{i}"))

            if i % 100 == 0:
                self.take_memory_snapshot(f"db_users_{i}")

        # Запрашиваем пользователей
        print("  Запрос пользователей...")
        for i in range(0, 1000, 100):
            user = self.db.get_user(i + 1)  # ID начинаются с 1

        self.take_memory_snapshot("db_end")

    @memory_usage_decorator
    def profile_file_operations(self):
        """Профилирование файловых операций"""
        print("\n📁 Профилирование файловых операций...")

        self.take_memory_snapshot("files_start")

        # Создаем большие файлы
        files = []
        for i in range(10):
            file_path = Path(self.temp_dir) / f"large_file_{i}.dat"

            with open(file_path, "wb") as f:
                # Записываем 5 МБ данных
                for j in range(5):
                    f.write(os.urandom(1024 * 1024))

            files.append(file_path)

            if i % 3 == 0:
                self.take_memory_snapshot(f"files_created_{i}")

        # Читаем файлы
        print("  Чтение файлов...")
        for i, file_path in enumerate(files):
            with open(file_path, "rb") as f:
                content = f.read()

            if i % 3 == 0:
                self.take_memory_snapshot(f"files_read_{i}")

        # Удаляем файлы
        print("  Удаление файлов...")
        for file_path in files:
            file_path.unlink()

        self.take_memory_snapshot("files_end")

    @memory_usage_decorator
    def profile_api_requests(self):
        """Профилирование API запросов"""
        print("\n🌐 Профилирование API запросов...")

        self.take_memory_snapshot("api_start")

        # Создаем тестовый файл
        test_file = Path(self.temp_dir) / "test.jpg"
        with open(test_file, "wb") as f:
            f.write(os.urandom(1024 * 1024))  # 1 МБ

        # Выполняем множество запросов
        print("  Выполнение 100 запросов...")
        for i in range(100):
            # Разные типы запросов
            if i % 4 == 0:
                # Системная информация
                self.client.get("/admin/system-info", headers=self.headers)
            elif i % 4 == 1:
                # Информация о хранилище
                self.client.get("/admin/storage-info", headers=self.headers)
            elif i % 4 == 2:
                # Статистика
                self.client.get("/admin/content-stats", headers=self.headers)
            else:
                # Загрузка файла
                with open(test_file, "rb") as f:
                    files = {"image": ("test.jpg", f, "image/jpeg")}
                    self.client.post("/ar/upload", files=files, headers=self.headers)

            if i % 25 == 0:
                self.take_memory_snapshot(f"api_requests_{i}")

        self.take_memory_snapshot("api_end")

    @memory_usage_decorator
    def profile_portrait_operations(self):
        """Профилирование операций с портретами"""
        print("\n🖼️  Профилирование операций с портретами...")

        self.take_memory_snapshot("portraits_start")

        # Создаем тестовые файлы для портретов
        portrait_files = []
        for i in range(5):
            # Изображение
            img_path = Path(self.temp_dir) / f"portrait_{i}.jpg"
            with open(img_path, "wb") as f:
                f.write(os.urandom(2 * 1024 * 1024))  # 2 МБ

            # Видео
            video_path = Path(self.temp_dir) / f"video_{i}.mp4"
            with open(video_path, "wb") as f:
                f.write(os.urandom(5 * 1024 * 1024))  # 5 МБ

            portrait_files.append((img_path, video_path))

        # Создаем портреты
        portrait_ids = []
        for i, (img_path, video_path) in enumerate(portrait_files):
            with open(img_path, "rb") as img, open(video_path, "rb") as vid:
                files = {"image": (f"portrait_{i}.jpg", img, "image/jpeg"), "video": (f"video_{i}.mp4", vid, "video/mp4")}
                data = {"phone": f"+7999123456{i:02d}", "name": f"Тестовый Клиент {i}"}

                response = self.client.post("/orders/create", files=files, data=data, headers=self.headers)

                if response.status_code == 200:
                    portrait_id = response.json()["portrait"]["id"]
                    portrait_ids.append(portrait_id)

            if i % 2 == 0:
                self.take_memory_snapshot(f"portraits_created_{i}")

        # Запрашиваем информацию о портретах
        print("  Запрос информации о портретах...")
        for portrait_id in portrait_ids:
            self.client.get(f"/portraits/{portrait_id}/details", headers=self.headers)

        self.take_memory_snapshot("portraits_end")

    def profile_memory_leaks(self):
        """Проверка на утечки памяти"""
        print("\n🔍 Проверка на утечки памяти...")

        initial_snapshot = self.take_memory_snapshot("leak_test_start")

        # Выполняем операции несколько раз
        for cycle in range(3):
            print(f"  Цикл {cycle + 1}/3...")

            # Создаем и удаляем много данных
            temp_users = []
            for i in range(100):
                user_id = self.db.create_user(f"temp_user_{cycle}_{i}", _hash_password("temp"))
                temp_users.append(user_id)

            # Создаем временные файлы
            temp_files = []
            for i in range(10):
                file_path = Path(self.temp_dir) / f"temp_file_{cycle}_{i}.dat"
                with open(file_path, "wb") as f:
                    f.write(os.urandom(1024 * 1024))  # 1 МБ
                temp_files.append(file_path)

            # Удаляем временные файлы
            for file_path in temp_files:
                file_path.unlink()

            self.take_memory_snapshot(f"leak_test_cycle_{cycle + 1}")

        final_snapshot = self.take_memory_snapshot("leak_test_end")

        # Анализируем утечки
        memory_increase = final_snapshot["rss_mb"] - initial_snapshot["rss_mb"]

        print(f"\n📊 Анализ утечек памяти:")
        print(f"  Начальная память: {initial_snapshot['rss_mb']:.2f} МБ")
        print(f"  Финальная память: {final_snapshot['rss_mb']:.2f} МБ")
        print(f"  Общий рост: {memory_increase:.2f} МБ")

        # Проверяем критерии утечки
        leak_threshold = 50  # МБ
        if memory_increase > leak_threshold:
            print(f"  ❌ Обнаружена утечка памяти (> {leak_threshold} МБ)")
            return False
        else:
            print(f"  ✅ Значительных утечек памяти не обнаружено")
            return True

    def generate_memory_report(self):
        """Сгенерировать отчет по использованию памяти"""
        print("\n📈 Генерация отчета по памяти...")

        if not self.memory_snapshots:
            print("  Нет данных для анализа")
            return

        # Анализ снимков
        rss_values = [s["rss_mb"] for s in self.memory_snapshots]

        report = {
            "snapshots": self.memory_snapshots,
            "analysis": {
                "initial_memory_mb": rss_values[0] if rss_values else 0,
                "final_memory_mb": rss_values[-1] if rss_values else 0,
                "peak_memory_mb": max(rss_values) if rss_values else 0,
                "memory_increase_mb": rss_values[-1] - rss_values[0] if len(rss_values) > 1 else 0,
                "avg_memory_mb": sum(rss_values) / len(rss_values) if rss_values else 0,
            },
        }

        # Сохраняем отчет
        import json

        with open("memory_profile_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"  💾 Отчет сохранен: memory_profile_report.json")

        # Выводим сводку
        analysis = report["analysis"]
        print(f"\n📊 Сводка по памяти:")
        print(f"  Начальная: {analysis['initial_memory_mb']:.2f} МБ")
        print(f"  Пиковая: {analysis['peak_memory_mb']:.2f} МБ")
        print(f"  Финальная: {analysis['final_memory_mb']:.2f} МБ")
        print(f"  Рост: {analysis['memory_increase_mb']:.2f} МБ")
        print(f"  Средняя: {analysis['avg_memory_mb']:.2f} МБ")

    def cleanup(self):
        """Очистка ресурсов"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print("🧹 Ресурсы очищены")

    def run_full_profiling(self):
        """Запустить полное профилирование"""
        print("=" * 60)
        print("🧠 ПРОФИЛИРОВАНИЕ ПАМЯТИ VERTEX AR")
        print("=" * 60)

        if not self.setup():
            return False

        try:
            # Начальный снимок
            self.take_memory_snapshot("profiling_start")

            # Запускаем все тесты
            self.profile_database_operations()
            self.profile_file_operations()
            self.profile_api_requests()
            self.profile_portrait_operations()

            # Проверка утечек
            no_leaks = self.profile_memory_leaks()

            # Финальный снимок
            self.take_memory_snapshot("profiling_end")

            # Генерируем отчет
            self.generate_memory_report()

            return no_leaks

        finally:
            self.cleanup()


# Декоратор для профилирования отдельных функций
@profile
def profile_function_example():
    """Пример профилируемой функции"""
    # Создаем большие структуры данных
    big_list = []
    for i in range(100000):
        big_list.append({"id": i, "data": "x" * 100})

    # Выполняем операции
    processed = []
    for item in big_list:
        processed.append(item["id"] * 2)

    return len(processed)


def main():
    """Основная функция"""
    print("🚀 Запуск профилирования памяти...")

    # Вариант 1: Полное профилирование приложения
    profiler = MemoryProfiler()
    success = profiler.run_full_profiling()

    # Вариант 2: Профилирование отдельной функции
    print("\n🔬 Профилирование отдельной функции...")
    profile_function_example()

    if success:
        print("\n🎉 Профилирование завершено без утечек памяти!")
    else:
        print("\n⚠️  Обнаружены утечки памяти")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
