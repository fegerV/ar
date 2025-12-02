#!/usr/bin/env python3
"""
Нагрузочное тестирование API портретов
Тестирует производительность под высокой нагрузкой
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
from typing import Dict, List, Optional
from dataclasses import dataclass

import pytest

# Добавляем путь к основному приложению
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "vertex-ar"))

try:
    import psutil
    import requests
    from PIL import Image, ImageDraw
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Установите необходимые зависимости: pip install psutil requests pillow")
    pytest.skip(f"Missing dependencies: {e}", allow_module_level=True)

@dataclass
class LoadTestMetrics:
    """Метрики нагрузочного теста"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time: float
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    requests_per_second: float
    errors: List[str]

class PortraitsLoadTester:
    """Нагрузочный тестер для API портретов"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.test_files = []
        self.results = {}
        
    def login(self, username: str = "admin", password: str = "admin") -> bool:
        """Аутентификация в системе"""
        print(f"🔐 Вход в систему как {username}...")
        
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                self.token = response.json()["access_token"]
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                print("✅ Аутентификация успешна")
                return True
            else:
                print(f"❌ Ошибка аутентификации: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"❌ Ошибка при входе: {e}")
            return False
    
    def create_test_files(self, count: int = 10) -> bool:
        """Создать тестовые файлы"""
        print(f"📁 Создание {count} тестовых файлов...")
        
        self.test_files = []
        
        try:
            for i in range(count):
                # Создаем изображение
                img = Image.new('RGB', (800, 600), color='white')
                draw = ImageDraw.Draw(img)
                
                # Рисуем простой портрет
                draw.ellipse([250, 150, 550, 450], fill='lightblue', outline='black', width=3)
                draw.ellipse([320, 250, 360, 290], fill='black')
                draw.ellipse([440, 250, 480, 290], fill='black')
                draw.arc([300, 320, 500, 420], 0, 180, fill='black', width=5)
                draw.text([350, 500], f"Test {i+1}", fill='black')
                
                img_path = f"/tmp/test_portrait_{i}.jpg"
                img.save(img_path)
                
                # Создаем фейковый видео файл
                video_path = f"/tmp/test_video_{i}.mp4"
                with open(video_path, 'wb') as f:
                    f.write(f'fake video content for test {i+1}'.encode())
                
                self.test_files.append({
                    'image': img_path,
                    'video': video_path,
                    'name': f'Тестовый Клиент {i+1}',
                    'phone': f'+7999123456{i:02d}'
                })
            
            print(f"✅ Создано {len(self.test_files)} наборов файлов")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания файлов: {e}")
            return False
    
    def cleanup_test_files(self):
        """Очистка тестовых файлов"""
        print("🧹 Очистка тестовых файлов...")
        
        for file_set in self.test_files:
            try:
                if os.path.exists(file_set['image']):
                    os.remove(file_set['image'])
                if os.path.exists(file_set['video']):
                    os.remove(file_set['video'])
            except Exception as e:
                print(f"Ошибка удаления файла: {e}")
        
        self.test_files = []
    
    def create_order_single(self, file_set: Dict) -> Dict:
        """Создать один заказ"""
        start_time = time.time()
        
        try:
            with open(file_set['image'], 'rb') as img, open(file_set['video'], 'rb') as vid:
                files = {
                    'image': (os.path.basename(file_set['image']), img, 'image/jpeg'),
                    'video': (os.path.basename(file_set['video']), vid, 'video/mp4')
                }
                data = {
                    'phone': file_set['phone'],
                    'name': file_set['name']
                }
                
                response = self.session.post(
                    f"{self.base_url}/orders/create",
                    files=files,
                    data=data
                )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'data': response.json()
                }
            else:
                return {
                    'success': False,
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'error': response.text
                }
                
        except Exception as e:
            return {
                'success': False,
                'response_time': time.time() - start_time,
                'error': str(e)
            }
    
    def test_concurrent_orders(self, num_orders: int = 20, max_workers: int = 5) -> LoadTestMetrics:
        """Тест конкурентного создания заказов"""
        print(f"\n🔄 Тест: {num_orders} конкурентных заказов (workers: {max_workers})")
        
        if len(self.test_files) < num_orders:
            print(f"Недостаточно тестовых файлов. Создаем еще...")
            self.create_test_files(num_orders)
        
        start_time = time.time()
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Отправляем задачи
            futures = []
            for i in range(num_orders):
                file_set = self.test_files[i % len(self.test_files)]
                future = executor.submit(self.create_order_single, file_set)
                futures.append(future)
            
            # Собираем результаты
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        'success': False,
                        'response_time': 0,
                        'error': str(e)
                    })
        
        total_time = time.time() - start_time
        
        # Анализируем результаты
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        response_times = [r['response_time'] for r in results]
        
        metrics = LoadTestMetrics(
            total_requests=len(results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            total_time=total_time,
            avg_response_time=sum(response_times) / len(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            requests_per_second=len(results) / total_time if total_time > 0 else 0,
            errors=[r.get('error', 'Unknown error') for r in failed]
        )
        
        # Выводим результаты
        print(f"  Всего запросов: {metrics.total_requests}")
        print(f"  Успешных: {metrics.successful_requests}")
        print(f"  Неудачных: {metrics.failed_requests}")
        print(f"  Общее время: {metrics.total_time:.2f} сек")
        print(f"  Запросов/сек: {metrics.requests_per_second:.2f}")
        print(f"  Среднее время ответа: {metrics.avg_response_time:.3f} сек")
        print(f"  Минимальное время ответа: {metrics.min_response_time:.3f} сек")
        print(f"  Максимальное время ответа: {metrics.max_response_time:.3f} сек")
        
        if metrics.errors:
            print(f"  Ошибки: {len(set(metrics.errors))} уникальных")
            for error in set(metrics.errors[:3]):  # Показываем первые 3 уникальные ошибки
                print(f"    - {error}")
        
        success_rate = metrics.successful_requests / metrics.total_requests * 100
        print(f"  Успешность: {success_rate:.1f}%")
        
        self.results['concurrent_orders'] = metrics
        return metrics
    
    def test_api_endpoints(self, num_requests: int = 100) -> LoadTestMetrics:
        """Тест различных API эндпоинтов"""
        print(f"\n🌐 Тест: {num_requests} запросов к различным эндпоинтам")
        
        endpoints = [
            ("/clients/list", "GET", None),
            ("/portraits/list", "GET", None),
            ("/admin/system-info", "GET", None),
            ("/admin/storage-info", "GET", None),
            ("/admin/content-stats", "GET", None)
        ]
        
        start_time = time.time()
        results = []
        
        def make_request(endpoint_info):
            endpoint, method, _ = endpoint_info
            request_start = time.time()
            
            try:
                if method == "GET":
                    response = self.session.get(f"{self.base_url}{endpoint}")
                
                request_time = time.time() - request_start
                
                return {
                    'success': response.status_code == 200,
                    'response_time': request_time,
                    'status_code': response.status_code,
                    'endpoint': endpoint
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'response_time': time.time() - request_start,
                    'error': str(e),
                    'endpoint': endpoint
                }
        
        # Выполняем запросы
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(num_requests):
                endpoint = endpoints[i % len(endpoints)]
                future = executor.submit(make_request, endpoint)
                futures.append(future)
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        'success': False,
                        'response_time': 0,
                        'error': str(e)
                    })
        
        total_time = time.time() - start_time
        
        # Анализируем результаты
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        response_times = [r['response_time'] for r in results]
        
        metrics = LoadTestMetrics(
            total_requests=len(results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            total_time=total_time,
            avg_response_time=sum(response_times) / len(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            requests_per_second=len(results) / total_time if total_time > 0 else 0,
            errors=[r.get('error', 'Unknown error') for r in failed]
        )
        
        # Анализ по эндпоинтам
        endpoint_stats = {}
        for result in results:
            endpoint = result.get('endpoint', 'unknown')
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {'total': 0, 'success': 0, 'times': []}
            
            endpoint_stats[endpoint]['total'] += 1
            if result['success']:
                endpoint_stats[endpoint]['success'] += 1
            endpoint_stats[endpoint]['times'].append(result['response_time'])
        
        print(f"  Всего запросов: {metrics.total_requests}")
        print(f"  Успешных: {metrics.successful_requests}")
        print(f"  Неудачных: {metrics.failed_requests}")
        print(f"  Запросов/сек: {metrics.requests_per_second:.2f}")
        print(f"  Среднее время ответа: {metrics.avg_response_time:.3f} сек")
        
        print("\n  Статистика по эндпоинтам:")
        for endpoint, stats in endpoint_stats.items():
            success_rate = stats['success'] / stats['total'] * 100
            avg_time = sum(stats['times']) / len(stats['times']) if stats['times'] else 0
            print(f"    {endpoint}: {stats['success']}/{stats['total']} ({success_rate:.1f}%) - {avg_time:.3f}s")
        
        self.results['api_endpoints'] = metrics
        return metrics
    
    def test_stress_load(self, duration_seconds: int = 60) -> LoadTestMetrics:
        """Стресс-тест в течение указанного времени"""
        print(f"\n💪 Стресс-тест: {duration_seconds} секунд непрерывной нагрузки")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        results = []
        request_count = 0
        
        def continuous_requests():
            nonlocal request_count
            while time.time() < end_time:
                request_start = time.time()
                
                try:
                    # Чередуем разные запросы
                    endpoints = [
                        "/clients/list",
                        "/portraits/list", 
                        "/admin/system-info"
                    ]
                    endpoint = endpoints[request_count % len(endpoints)]
                    
                    response = self.session.get(f"{self.base_url}{endpoint}")
                    request_time = time.time() - request_start
                    
                    results.append({
                        'success': response.status_code == 200,
                        'response_time': request_time,
                        'status_code': response.status_code
                    })
                    
                    request_count += 1
                    
                except Exception as e:
                    results.append({
                        'success': False,
                        'response_time': time.time() - request_start,
                        'error': str(e)
                    })
                
                # Небольшая задержка между запросами
                time.sleep(0.01)
        
        # Запускаем несколько потоков
        threads = []
        for _ in range(5):  # 5 потоков
            thread = threading.Thread(target=continuous_requests)
            thread.start()
            threads.append(thread)
        
        # Ждем завершения
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Анализируем результаты
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        response_times = [r['response_time'] for r in results]
        
        metrics = LoadTestMetrics(
            total_requests=len(results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            total_time=total_time,
            avg_response_time=sum(response_times) / len(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            requests_per_second=len(results) / total_time if total_time > 0 else 0,
            errors=[r.get('error', 'Unknown error') for r in failed]
        )
        
        print(f"  Всего запросов: {metrics.total_requests}")
        print(f"  Успешных: {metrics.successful_requests}")
        print(f"  Неудачных: {metrics.failed_requests}")
        print(f"  Запросов/сек: {metrics.requests_per_second:.2f}")
        print(f"  Среднее время ответа: {metrics.avg_response_time:.3f} сек")
        
        success_rate = metrics.successful_requests / metrics.total_requests * 100
        print(f"  Успешность: {success_rate:.1f}%")
        
        self.results['stress_load'] = metrics
        return metrics
    
    def run_all_load_tests(self) -> bool:
        """Запустить все нагрузочные тесты"""
        print("=" * 60)
        print("🚀 НАГРУЗОЧНОЕ ТЕСТИРОВАНИЕ API ПОРТРЕТОВ")
        print("=" * 60)
        
        # Аутентификация
        if not self.login():
            return False
        
        # Создание тестовых файлов
        if not self.create_test_files(20):
            return False
        
        try:
            tests = [
                ("Конкурентное создание заказов", lambda: self.test_concurrent_orders(20, 5)),
                ("Тест API эндпоинтов", lambda: self.test_api_endpoints(100)),
                ("Стресс-тест", lambda: self.test_stress_load(30))  # 30 секунд для демо
            ]
            
            all_passed = True
            for test_name, test_func in tests:
                print(f"\n{'='*20} {test_name} {'='*20}")
                metrics = test_func()
                
                # Считаем тест успешным если >90% запросов успешны
                success_rate = metrics.successful_requests / metrics.total_requests * 100
                test_passed = success_rate >= 90
                
                if not test_passed:
                    all_passed = False
                
                print(f"Результат: {'✅ УСПЕХ' if test_passed else '❌ НЕ УСПЕХ'}")
            
            # Сохраняем отчет
            self.save_load_test_report()
            
            return all_passed
            
        finally:
            self.cleanup_test_files()
    
    def save_load_test_report(self, filename: str = "load_test_report.json"):
        """Сохранить отчет нагрузочного тестирования"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url,
            'test_results': {},
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024
            }
        }
        
        for test_name, metrics in self.results.items():
            report['test_results'][test_name] = {
                'total_requests': metrics.total_requests,
                'successful_requests': metrics.successful_requests,
                'failed_requests': metrics.failed_requests,
                'total_time': metrics.total_time,
                'avg_response_time': metrics.avg_response_time,
                'min_response_time': metrics.min_response_time,
                'max_response_time': metrics.max_response_time,
                'requests_per_second': metrics.requests_per_second,
                'success_rate': metrics.successful_requests / metrics.total_requests * 100,
                'errors': list(set(metrics.errors)) if metrics.errors else []
            }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Отчет нагрузочного тестирования сохранен: {filename}")

def main():
    """Основная функция"""
    tester = PortraitsLoadTester()
    success = tester.run_all_load_tests()
    
    if success:
        print("\n🎉 Все нагрузочные тесты пройдены успешно!")
    else:
        print("\n⚠️  Некоторые нагрузочные тесты не пройдены")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)