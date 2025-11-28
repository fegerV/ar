#!/usr/bin/env python3
"""
Комплексное тестирование производительности с psutil
Включает тестирование памяти, CPU, дискового ввода-вывода и сети
"""

import os
import sys
import time
import json
import threading
import concurrent.futures
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional

# Добавляем путь к основному приложению
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'vertex-ar'))

try:
    import psutil
    import requests
    from fastapi.testclient import TestClient
    from main import app, Database, _hash_password
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Установите необходимые зависимости: pip install psutil requests")
    sys.exit(1)

@dataclass
class PerformanceMetrics:
    """Метрики производительности"""
    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    open_files: int
    threads: int

class PerformanceMonitor:
    """Монитор производительности системы"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.metrics_history: List[PerformanceMetrics] = []
        self.monitoring = False
        self.monitor_thread = None
        self.start_time = None
        
        # Начальные значения для IO счетчиков
        self.initial_io = self.process.io_counters()
        self.initial_net_io = psutil.net_io_counters()
    
    def start_monitoring(self):
        """Начать мониторинг"""
        self.monitoring = True
        self.start_time = time.time()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("📊 Мониторинг производительности запущен")
    
    def stop_monitoring(self):
        """Остановить мониторинг"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        print("📊 Мониторинг производительности остановлен")
    
    def _monitor_loop(self):
        """Основной цикл мониторинга"""
        while self.monitoring:
            try:
                # Получаем текущие метрики
                cpu_percent = self.process.cpu_percent()
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                memory_percent = self.process.memory_percent()
                
                # Дисковый ввод-вывод
                current_io = self.process.io_counters()
                disk_read_mb = (current_io.read_bytes - self.initial_io.read_bytes) / 1024 / 1024
                disk_write_mb = (current_io.write_bytes - self.initial_io.write_bytes) / 1024 / 1024
                
                # Сетевой ввод-вывод
                current_net_io = psutil.net_io_counters()
                net_sent_mb = (current_net_io.bytes_sent - self.initial_net_io.bytes_sent) / 1024 / 1024
                net_recv_mb = (current_net_io.bytes_recv - self.initial_net_io.bytes_recv) / 1024 / 1024
                
                # Другие метрики
                open_files = len(self.process.open_files())
                threads = self.process.num_threads()
                
                metrics = PerformanceMetrics(
                    timestamp=datetime.now(),
                    cpu_percent=cpu_percent,
                    memory_mb=memory_mb,
                    memory_percent=memory_percent,
                    disk_io_read_mb=disk_read_mb,
                    disk_io_write_mb=disk_write_mb,
                    network_sent_mb=net_sent_mb,
                    network_recv_mb=net_recv_mb,
                    open_files=open_files,
                    threads=threads
                )
                
                self.metrics_history.append(metrics)
                time.sleep(0.5)  # Собираем метрики каждые 0.5 секунды
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
    
    def get_summary(self) -> Dict:
        """Получить сводку метрик"""
        if not self.metrics_history:
            return {}
        
        cpu_values = [m.cpu_percent for m in self.metrics_history]
        memory_values = [m.memory_mb for m in self.metrics_history]
        
        summary = {
            'duration_seconds': time.time() - self.start_time if self.start_time else 0,
            'cpu': {
                'max': max(cpu_values),
                'min': min(cpu_values),
                'avg': sum(cpu_values) / len(cpu_values)
            },
            'memory': {
                'max_mb': max(memory_values),
                'min_mb': min(memory_values),
                'avg_mb': sum(memory_values) / len(memory_values),
                'peak_increase_mb': max(memory_values) - min(memory_values)
            },
            'disk_io': {
                'total_read_mb': self.metrics_history[-1].disk_io_read_mb,
                'total_write_mb': self.metrics_history[-1].disk_io_write_mb
            },
            'network': {
                'total_sent_mb': self.metrics_history[-1].network_sent_mb,
                'total_recv_mb': self.metrics_history[-1].network_recv_mb
            },
            'resources': {
                'max_open_files': max(m.open_files for m in self.metrics_history),
                'max_threads': max(m.threads for m in self.metrics_history)
            }
        }
        
        return summary
    
    def print_summary(self):
        """Вывести сводку метрик"""
        summary = self.get_summary()
        if not summary:
            print("Нет данных для анализа")
            return
        
        print("\n📈 Сводка производительности:")
        print(f"⏱️  Длительность теста: {summary['duration_seconds']:.2f} сек")
        
        print(f"\n🖥️  CPU:")
        print(f"   Максимум: {summary['cpu']['max']:.1f}%")
        print(f"   Среднее: {summary['cpu']['avg']:.1f}%")
        
        print(f"\n💾 Память:")
        print(f"   Пик: {summary['memory']['max_mb']:.1f} МБ")
        print(f"   Среднее: {summary['memory']['avg_mb']:.1f} МБ")
        print(f"   Рост пика: {summary['memory']['peak_increase_mb']:.1f} МБ")
        
        print(f"\n💿 Дисковый ввод-вывод:")
        print(f"   Прочитано: {summary['disk_io']['total_read_mb']:.1f} МБ")
        print(f"   Записано: {summary['disk_io']['total_write_mb']:.1f} МБ")
        
        print(f"\n🌐 Сеть:")
        print(f"   Отправлено: {summary['network']['total_sent_mb']:.1f} МБ")
        print(f"   Получено: {summary['network']['total_recv_mb']:.1f} МБ")
        
        print(f"\n🔧 Ресурсы:")
        print(f"   Максимум открытых файлов: {summary['resources']['max_open_files']}")
        print(f"   Максимум потоков: {summary['resources']['max_threads']}")

class ComprehensivePerformanceTester:
    """Комплексный тестер производительности"""
    
    def __init__(self):
        self.client = TestClient(app)
        self.monitor = PerformanceMonitor()
        self.temp_dir = None
        self.test_results = {}
    
    def setup_test_environment(self):
        """Настройка тестового окружения"""
        print("🔧 Настройка тестового окружения...")
        self.temp_dir = tempfile.mkdtemp()
        
        # Создаем временную базу данных
        db_path = Path(self.temp_dir) / "test.db"
        self.db = Database(db_path)
        
        # Создаем администратора
        self.db.create_user("admin", _hash_password("admin"), is_admin=True)
        
        # Получаем токен
        response = self.client.post("/auth/login", json={
            "username": "admin",
            "password": "admin"
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
            print("✅ Тестовое окружение настроено")
            return True
        else:
            print("❌ Не удалось получить токен администратора")
            return False
    
    def cleanup_test_environment(self):
        """Очистка тестового окружения"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print("🧹 Тестовое окружение очищено")
    
    def test_large_file_performance(self):
        """Тест производительности с большими файлами"""
        print("\n📁 Тест 1: Производительность с большими файлами")
        
        self.monitor.start_monitoring()
        
        try:
            # Создаем большие файлы
            large_image = Path(self.temp_dir) / "large_image.jpg"
            large_video = Path(self.temp_dir) / "large_video.mp4"
            
            print("  Создание тестовых файлов...")
            with open(large_image, "wb") as f:
                f.write(os.urandom(10 * 1024 * 1024))  # 10 МБ
            
            with open(large_video, "wb") as f:
                f.write(os.urandom(20 * 1024 * 1024))  # 20 МБ
            
            # Загружаем файлы
            print("  Загрузка файлов...")
            start_time = time.time()
            
            with open(large_image, "rb") as img, open(large_video, "rb") as vid:
                files = {
                    "image": ("large_image.jpg", img, "image/jpeg"),
                    "video": ("large_video.mp4", vid, "video/mp4")
                }
                response = self.client.post("/ar/upload", files=files, headers=self.headers)
            
            upload_time = time.time() - start_time
            
            self.monitor.stop_monitoring()
            
            success = response.status_code == 200
            self.test_results['large_file_upload'] = {
                'success': success,
                'upload_time': upload_time,
                'file_size_mb': 30,
                'throughput_mbps': (30 / upload_time) if upload_time > 0 else 0,
                'performance': self.monitor.get_summary()
            }
            
            print(f"  Время загрузки: {upload_time:.2f} сек")
            print(f"  Пропускная способность: {30 / upload_time:.2f} МБ/с")
            print(f"  Статус: {'✅ УСПЕХ' if success else '❌ ОШИБКА'}")
            
            return success
            
        except Exception as e:
            self.monitor.stop_monitoring()
            print(f"  Ошибка: {e}")
            return False
    
    def test_concurrent_requests(self):
        """Тест производительности с конкурентными запросами"""
        print("\n🔄 Тест 2: Конкурентные запросы")
        
        self.monitor.start_monitoring()
        
        try:
            # Создаем тестовый файл
            test_file = Path(self.temp_dir) / "test.jpg"
            with open(test_file, "wb") as f:
                f.write(os.urandom(1024 * 1024))  # 1 МБ
            
            def make_request():
                """Выполнить один запрос"""
                try:
                    with open(test_file, "rb") as f:
                        files = {"image": ("test.jpg", f, "image/jpeg")}
                        response = self.client.post("/ar/upload", files=files, headers=self.headers)
                    return response.status_code == 200
                except:
                    return False
            
            # Выполняем конкурентные запросы
            print("  Выполнение 10 конкурентных запросов...")
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
            
            total_time = time.time() - start_time
            success_count = sum(results)
            
            self.monitor.stop_monitoring()
            
            self.test_results['concurrent_requests'] = {
                'success': success_count >= 8,  # Хотя бы 80% успешных
                'total_requests': 10,
                'successful_requests': success_count,
                'total_time': total_time,
                'requests_per_second': 10 / total_time if total_time > 0 else 0,
                'performance': self.monitor.get_summary()
            }
            
            print(f"  Успешных запросов: {success_count}/10")
            print(f"  Общее время: {total_time:.2f} сек")
            print(f"  Запросов в секунду: {10 / total_time:.2f}")
            print(f"  Статус: {'✅ УСПЕХ' if success_count >= 8 else '❌ ОШИБКА'}")
            
            return success_count >= 8
            
        except Exception as e:
            self.monitor.stop_monitoring()
            print(f"  Ошибка: {e}")
            return False
    
    def test_memory_leak_detection(self):
        """Тест на утечки памяти"""
        print("\n🔍 Тест 3: Обнаружение утечек памяти")
        
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_samples = []
        
        try:
            # Выполняем много операций для обнаружения утечек
            for i in range(50):
                # Создаем пользователя
                self.db.create_user(f"user_{i}", _hash_password(f"pass_{i}"))
                
                # Замеряем память
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)
                
                if i % 10 == 0:
                    print(f"  Итерация {i}: {current_memory:.1f} МБ")
            
            final_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_increase = final_memory - initial_memory
            max_memory = max(memory_samples)
            
            # Проверяем на утечки (рост памяти не должен превышать 100 МБ)
            memory_leak_detected = memory_increase > 100
            
            self.test_results['memory_leak'] = {
                'success': not memory_leak_detected,
                'initial_memory_mb': initial_memory,
                'final_memory_mb': final_memory,
                'memory_increase_mb': memory_increase,
                'max_memory_mb': max_memory,
                'samples_count': len(memory_samples)
            }
            
            print(f"  Начальная память: {initial_memory:.1f} МБ")
            print(f"  Финальная память: {final_memory:.1f} МБ")
            print(f"  Рост памяти: {memory_increase:.1f} МБ")
            print(f"  Максимальная память: {max_memory:.1f} МБ")
            print(f"  Статус: {'✅ НЕТ УТЕЧЕК' if not memory_leak_detected else '❌ ОБНАРУЖЕНА УТЕЧКА'}")
            
            return not memory_leak_detected
            
        except Exception as e:
            print(f"  Ошибка: {e}")
            return False
    
    def test_database_performance(self):
        """Тест производительности базы данных"""
        print("\n🗄️  Тест 4: Производительность базы данных")
        
        try:
            # Тест пакетной вставки
            print("  Тест пакетной вставки...")
            start_time = time.time()
            
            users = []
            for i in range(100):
                user_id = self.db.create_user(f"batch_user_{i}", _hash_password(f"pass_{i}"))
                users.append(user_id)
            
            batch_time = time.time() - start_time
            
            # Тест запросов
            print("  Тест запросов...")
            start_time = time.time()
            
            for user_id in users[:10]:  # Тестируем первые 10
                user = self.db.get_user(user_id)
            
            query_time = time.time() - start_time
            
            self.test_results['database_performance'] = {
                'success': True,
                'batch_insert_time': batch_time,
                'batch_insert_count': 100,
                'batch_rate': 100 / batch_time if batch_time > 0 else 0,
                'query_time': query_time,
                'query_count': 10,
                'query_rate': 10 / query_time if query_time > 0 else 0
            }
            
            print(f"  Пакетная вставка (100 записей): {batch_time:.3f} сек")
            print(f"  Скорость вставки: {100 / batch_time:.0f} записей/сек")
            print(f"  Запросы (10 записей): {query_time:.3f} сек")
            print(f"  Скорость запросов: {10 / query_time:.0f} запросов/сек")
            print("  Статус: ✅ УСПЕХ")
            
            return True
            
        except Exception as e:
            print(f"  Ошибка: {e}")
            return False
    
    def run_all_tests(self):
        """Запустить все тесты"""
        print("=" * 60)
        print("🚀 Комплексное тестирование производительности")
        print("=" * 60)
        
        if not self.setup_test_environment():
            print("❌ Не удалось настроить тестовое окружение")
            return False
        
        try:
            tests = [
                self.test_large_file_performance,
                self.test_concurrent_requests,
                self.test_memory_leak_detection,
                self.test_database_performance
            ]
            
            results = []
            for test in tests:
                result = test()
                results.append(result)
            
            # Выводим сводку
            self.print_comprehensive_summary()
            
            success_count = sum(results)
            print(f"\n📊 Итоговые результаты: {success_count}/{len(results)} тестов пройдено")
            
            if success_count == len(results):
                print("🎉 Все тесты производительности пройдены!")
                return True
            else:
                print("⚠️  Некоторые тесты не пройдены")
                return False
        
        finally:
            self.cleanup_test_environment()
    
    def print_comprehensive_summary(self):
        """Вывести комплексную сводку"""
        print("\n" + "=" * 60)
        print("📈 КОМПЛЕКСНАЯ СВОДКА ПРОИЗВОДИТЕЛЬНОСТИ")
        print("=" * 60)
        
        for test_name, result in self.test_results.items():
            print(f"\n🧪 {test_name.replace('_', ' ').title()}:")
            print(f"   Статус: {'✅ УСПЕХ' if result['success'] else '❌ ОШИБКА'}")
            
            if 'performance' in result:
                perf = result['performance']
                if perf:
                    print(f"   CPU avg: {perf.get('cpu', {}).get('avg', 0):.1f}%")
                    print(f"   Memory peak: {perf.get('memory', {}).get('max_mb', 0):.1f} МБ")
                    print(f"   Duration: {perf.get('duration_seconds', 0):.2f} сек")
    
    def save_report(self, filename: str = "performance_report.json"):
        """Сохранить отчет в файл"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
                'disk_total_gb': psutil.disk_usage('/').total / 1024 / 1024 / 1024
            },
            'test_results': self.test_results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Отчет сохранен в файл: {filename}")

def main():
    """Основная функция"""
    tester = ComprehensivePerformanceTester()
    success = tester.run_all_tests()
    
    # Сохраняем отчет
    tester.save_report()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)