#!/usr/bin/env python3
"""
Тестирование интеграции с MinIO и локальным хранилищем
Проверяет работу с различными типами хранилищ
"""

import os
import sys
import time
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Добавляем путь к основному приложению
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'vertex-ar'))

try:
    import requests
    from PIL import Image, ImageDraw
    from minio import Minio
    from minio.error import S3Error
    import psutil
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Установите необходимые зависимости: pip install requests pillow minio psutil")
    sys.exit(1)

@dataclass
class StorageTestResult:
    """Результат теста хранилища"""
    test_name: str
    success: bool
    duration: float
    file_size_mb: float
    upload_speed_mbps: float
    download_speed_mbps: float
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class StorageIntegrationTester:
    """Тестер интеграции хранилищ"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.test_files = []
        self.results: List[StorageTestResult] = []
        self.minio_client = None
        self.temp_dir = None
        
    def setup_minio_client(self) -> bool:
        """Настроить клиент MinIO"""
        print("🔧 Настройка MinIO клиента...")
        
        try:
            # Проверяем переменные окружения для MinIO
            minio_endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
            minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
            minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
            minio_secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
            
            self.minio_client = Minio(
                endpoint=minio_endpoint,
                access_key=minio_access_key,
                secret_key=minio_secret_key,
                secure=minio_secure
            )
            
            # Проверяем соединение
            buckets = self.minio_client.list_buckets()
            print(f"✅ MinIO клиент настроен. Доступно бакетов: {len(buckets)}")
            
            # Создаем тестовый бакет если его нет
            bucket_name = "test-storage"
            if not self.minio_client.bucket_exists(bucket_name):
                self.minio_client.make_bucket(bucket_name)
                print(f"📦 Создан тестовый бакет: {bucket_name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка настройки MinIO: {e}")
            print("⚠️  Продолжаем тесты с локальным хранилищем")
            self.minio_client = None
            return False
    
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
    
    def create_test_files(self, sizes_mb: List[int] = [1, 5, 10, 20]) -> bool:
        """Создать тестовые файлы разных размеров"""
        print(f"📁 Создание тестовых файлов размеров: {sizes_mb} МБ...")
        
        self.test_files = []
        self.temp_dir = tempfile.mkdtemp()
        
        try:
            for i, size_mb in enumerate(sizes_mb):
                # Создаем изображение
                img = Image.new('RGB', (800, 600), color='white')
                draw = ImageDraw.Draw(img)
                
                # Рисуем простой портрет
                draw.ellipse([250, 150, 550, 450], fill='lightblue', outline='black', width=3)
                draw.ellipse([320, 250, 360, 290], fill='black')
                draw.ellipse([440, 250, 480, 290], fill='black')
                draw.arc([300, 320, 500, 420], 0, 180, fill='black', width=5)
                draw.text([300, 500], f"Test {size_mb}MB", fill='black')
                
                img_path = os.path.join(self.temp_dir, f"test_image_{size_mb}mb.jpg")
                img.save(img_path, quality=95)
                
                # Создаем видео файл нужного размера
                video_path = os.path.join(self.temp_dir, f"test_video_{size_mb}mb.mp4")
                with open(video_path, 'wb') as f:
                    # Записываем случайные данные нужного размера
                    remaining = size_mb * 1024 * 1024
                    chunk_size = 1024 * 1024  # 1MB chunks
                    
                    while remaining > 0:
                        chunk = os.urandom(min(chunk_size, remaining))
                        f.write(chunk)
                        remaining -= len(chunk)
                
                # Проверяем фактический размер
                actual_size_mb = os.path.getsize(video_path) / 1024 / 1024
                
                self.test_files.append({
                    'image': img_path,
                    'video': video_path,
                    'size_mb': actual_size_mb,
                    'name': f'Тестовый Клиент {size_mb}MB',
                    'phone': f'+7999123456{size_mb:02d}'
                })
            
            print(f"✅ Создано {len(self.test_files)} наборов файлов")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания файлов: {e}")
            return False
    
    def test_local_storage_upload(self, file_set: Dict) -> StorageTestResult:
        """Тест загрузки в локальное хранилище"""
        test_name = "Local Storage Upload"
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
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                order_data = response.json()
                upload_speed = file_set['size_mb'] / duration if duration > 0 else 0
                
                return StorageTestResult(
                    test_name=test_name,
                    success=True,
                    duration=duration,
                    file_size_mb=file_set['size_mb'],
                    upload_speed_mbps=upload_speed,
                    download_speed_mbps=0,
                    metadata={
                        'order_id': order_data.get('portrait', {}).get('id'),
                        'client_id': order_data.get('client', {}).get('id'),
                        'storage_type': 'local'
                    }
                )
            else:
                return StorageTestResult(
                    test_name=test_name,
                    success=False,
                    duration=duration,
                    file_size_mb=file_set['size_mb'],
                    upload_speed_mbps=0,
                    download_speed_mbps=0,
                    error_message=f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            return StorageTestResult(
                test_name=test_name,
                success=False,
                duration=time.time() - start_time,
                file_size_mb=file_set['size_mb'],
                upload_speed_mbps=0,
                download_speed_mbps=0,
                error_message=str(e)
            )
    
    def test_minio_direct_upload(self, file_set: Dict) -> StorageTestResult:
        """Тест прямой загрузки в MinIO"""
        if not self.minio_client:
            return StorageTestResult(
                test_name="MinIO Direct Upload",
                success=False,
                duration=0,
                file_size_mb=0,
                upload_speed_mbps=0,
                download_speed_mbps=0,
                error_message="MinIO клиент не настроен"
            )
        
        test_name = "MinIO Direct Upload"
        start_time = time.time()
        
        try:
            bucket_name = "test-storage"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Загружаем изображение
            image_object = f"test_images/{timestamp}_image.jpg"
            self.minio_client.fput_object(
                bucket_name,
                image_object,
                file_set['image']
            )
            
            # Загружаем видео
            video_object = f"test_videos/{timestamp}_video.mp4"
            self.minio_client.fput_object(
                bucket_name,
                video_object,
                file_set['video']
            )
            
            duration = time.time() - start_time
            upload_speed = file_set['size_mb'] / duration if duration > 0 else 0
            
            return StorageTestResult(
                test_name=test_name,
                success=True,
                duration=duration,
                file_size_mb=file_set['size_mb'],
                upload_speed_mbps=upload_speed,
                download_speed_mbps=0,
                metadata={
                    'bucket': bucket_name,
                    'image_object': image_object,
                    'video_object': video_object,
                    'storage_type': 'minio_direct'
                }
            )
            
        except Exception as e:
            return StorageTestResult(
                test_name=test_name,
                success=False,
                duration=time.time() - start_time,
                file_size_mb=file_set['size_mb'],
                upload_speed_mbps=0,
                download_speed_mbps=0,
                error_message=str(e)
            )
    
    def test_minio_download(self, file_set: Dict) -> StorageTestResult:
        """Тест скачивания из MinIO"""
        if not self.minio_client:
            return StorageTestResult(
                test_name="MinIO Download",
                success=False,
                duration=0,
                file_size_mb=0,
                upload_speed_mbps=0,
                download_speed_mbps=0,
                error_message="MinIO клиент не настроен"
            )
        
        test_name = "MinIO Download"
        start_time = time.time()
        
        try:
            bucket_name = "test-storage"
            
            # Сначала загружаем файл для теста
            video_object = "test_download/test_video.mp4"
            self.minio_client.fput_object(
                bucket_name,
                video_object,
                file_set['video']
            )
            
            # Создаем временный файл для скачивания
            download_path = os.path.join(self.temp_dir, "downloaded_video.mp4")
            
            # Скачиваем файл
            self.minio_client.fget_object(
                bucket_name,
                video_object,
                download_path
            )
            
            duration = time.time() - start_time
            downloaded_size = os.path.getsize(download_path) / 1024 / 1024
            download_speed = downloaded_size / duration if duration > 0 else 0
            
            # Проверяем целостность файла
            original_size = os.path.getsize(file_set['video'])
            downloaded_size_bytes = os.path.getsize(download_path)
            
            integrity_ok = original_size == downloaded_size_bytes
            
            # Удаляем временный файл
            os.remove(download_path)
            
            return StorageTestResult(
                test_name=test_name,
                success=integrity_ok,
                duration=duration,
                file_size_mb=downloaded_size,
                upload_speed_mbps=0,
                download_speed_mbps=download_speed,
                metadata={
                    'bucket': bucket_name,
                    'object': video_object,
                    'integrity_check': integrity_ok,
                    'storage_type': 'minio_download'
                }
            )
            
        except Exception as e:
            return StorageTestResult(
                test_name=test_name,
                success=False,
                duration=time.time() - start_time,
                file_size_mb=0,
                upload_speed_mbps=0,
                download_speed_mbps=0,
                error_message=str(e)
            )
    
    def test_storage_performance_comparison(self) -> bool:
        """Сравнительный тест производительности хранилищ"""
        print("\n🏁 Сравнительный тест производительности хранилищ")
        
        if len(self.test_files) == 0:
            print("❌ Нет тестовых файлов")
            return False
        
        # Берем файл среднего размера для сравнения
        test_file = self.test_files[len(self.test_files) // 2]
        print(f"  Тестовый файл: {test_file['size_mb']:.2f} МБ")
        
        # Тест локального хранилища
        print("  📁 Тест локального хранилища...")
        local_result = self.test_local_storage_upload(test_file)
        self.results.append(local_result)
        
        if local_result.success:
            print(f"    ✅ Загрузка: {local_result.duration:.2f} сек ({local_result.upload_speed_mbps:.2f} МБ/с)")
        else:
            print(f"    ❌ Ошибка: {local_result.error_message}")
        
        # Тест MinIO
        if self.minio_client:
            print("  🗄️  Тест MinIO...")
            
            # Прямая загрузка в MinIO
            minio_upload_result = self.test_minio_direct_upload(test_file)
            self.results.append(minio_upload_result)
            
            if minio_upload_result.success:
                print(f"    ✅ Загрузка: {minio_upload_result.duration:.2f} сек ({minio_upload_result.upload_speed_mbps:.2f} МБ/с)")
            else:
                print(f"    ❌ Ошибка: {minio_upload_result.error_message}")
            
            # Тест скачивания из MinIO
            minio_download_result = self.test_minio_download(test_file)
            self.results.append(minio_download_result)
            
            if minio_download_result.success:
                print(f"    ✅ Скачивание: {minio_download_result.duration:.2f} сек ({minio_download_result.download_speed_mbps:.2f} МБ/с)")
            else:
                print(f"    ❌ Ошибка: {minio_download_result.error_message}")
        
        return True
    
    def test_storage_scalability(self) -> bool:
        """Тест масштабируемости хранилища"""
        print("\n📈 Тест масштабируемости хранилища")
        
        success_count = 0
        total_tests = len(self.test_files)
        
        for i, file_set in enumerate(self.test_files):
            print(f"  📊 Тест файла {i+1}/{total_tests} ({file_set['size_mb']:.1f} МБ)...")
            
            result = self.test_local_storage_upload(file_set)
            self.results.append(result)
            
            if result.success:
                success_count += 1
                print(f"    ✅ {result.duration:.2f} сек ({result.upload_speed_mbps:.2f} МБ/с)")
            else:
                print(f"    ❌ {result.error_message}")
        
        print(f"  Успешно: {success_count}/{total_tests} тестов")
        return success_count >= total_tests * 0.8  # 80% успех
    
    def test_concurrent_storage_operations(self) -> bool:
        """Тест конкурентных операций с хранилищем"""
        print("\n🔄 Тест конкурентных операций с хранилищем")
        
        import threading
        import concurrent.futures
        
        # Берем первые 5 файлов для теста
        test_files = self.test_files[:5]
        
        def upload_file(file_set):
            return self.test_local_storage_upload(file_set)
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(upload_file, file_set) for file_set in test_files]
            concurrent_results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Анализируем результаты
        successful = [r for r in concurrent_results if r.success]
        success_rate = len(successful) / len(concurrent_results) * 100
        
        print(f"  Конкурентных загрузок: {len(concurrent_results)}")
        print(f"  Успешных: {len(successful)} ({success_rate:.1f}%)")
        print(f"  Общее время: {total_time:.2f} сек")
        
        # Добавляем результаты
        self.results.extend(concurrent_results)
        
        return success_rate >= 80  # 80% успех
    
    def test_storage_system_resources(self) -> bool:
        """Тест использования системных ресурсов при работе с хранилищем"""
        print("\n💾 Тест использования системных ресурсов")
        
        process = psutil.Process()
        
        # Начальные метрики
        initial_memory = process.memory_info().rss / 1024 / 1024
        initial_cpu = process.cpu_percent()
        
        print(f"  Начальная память: {initial_memory:.1f} МБ")
        print(f"  Начальный CPU: {initial_cpu:.1f}%")
        
        # Выполняем несколько загрузок
        test_files = self.test_files[:3]  # 3 файла для теста
        
        for i, file_set in enumerate(test_files):
            print(f"  Загрузка файла {i+1}...")
            result = self.test_local_storage_upload(file_set)
            self.results.append(result)
            
            # Замеряем метрики после каждой загрузки
            current_memory = process.memory_info().rss / 1024 / 1024
            current_cpu = process.cpu_percent()
            
            print(f"    Память: {current_memory:.1f} МБ (+{current_memory - initial_memory:.1f})")
            print(f"    CPU: {current_cpu:.1f}%")
        
        # Финальные метрики
        final_memory = process.memory_info().rss / 1024 / 1024
        final_cpu = process.cpu_percent()
        memory_increase = final_memory - initial_memory
        
        print(f"\n  Финальная память: {final_memory:.1f} МБ")
        print(f"  Рост памяти: {memory_increase:.1f} МБ")
        print(f"  Финальный CPU: {final_cpu:.1f}%")
        
        # Проверяем на утечки памяти (рост не должен превышать 100 МБ)
        memory_ok = memory_increase < 100
        
        print(f"  Проверка памяти: {'✅ OK' if memory_ok else '❌ Превышен лимит'}")
        
        return memory_ok
    
    def cleanup_test_files(self):
        """Очистка тестовых файлов"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print("🧹 Тестовые файлы очищены")
    
    def run_all_storage_tests(self) -> bool:
        """Запустить все тесты хранилища"""
        print("=" * 60)
        print("🗄️  ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ ХРАНИЛИЩ")
        print("=" * 60)
        
        # Настройка MinIO
        self.setup_minio_client()
        
        # Аутентификация
        if not self.login():
            return False
        
        # Создание тестовых файлов
        if not self.create_test_files([1, 5, 10, 20]):
            return False
        
        try:
            tests = [
                ("Сравнительный тест производительности", self.test_storage_performance_comparison),
                ("Тест масштабируемости", self.test_storage_scalability),
                ("Тест конкурентных операций", self.test_concurrent_storage_operations),
                ("Тест системных ресурсов", self.test_storage_system_resources)
            ]
            
            all_passed = True
            for test_name, test_func in tests:
                print(f"\n{'='*20} {test_name} {'='*20}")
                result = test_func()
                
                if not result:
                    all_passed = False
                
                print(f"Результат: {'✅ УСПЕХ' if result else '❌ НЕ УСПЕХ'}")
            
            # Сохраняем отчет
            self.save_storage_report()
            
            return all_passed
            
        finally:
            self.cleanup_test_files()
    
    def save_storage_report(self, filename: str = "storage_integration_report.json"):
        """Сохранить отчет тестирования хранилищ"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url,
            'minio_available': self.minio_client is not None,
            'test_results': [],
            'summary': {
                'total_tests': len(self.results),
                'successful_tests': len([r for r in self.results if r.success]),
                'failed_tests': len([r for r in self.results if not r.success])
            },
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
                'disk_total_gb': psutil.disk_usage('/').total / 1024 / 1024 / 1024
            }
        }
        
        for result in self.results:
            report['test_results'].append({
                'test_name': result.test_name,
                'success': result.success,
                'duration': result.duration,
                'file_size_mb': result.file_size_mb,
                'upload_speed_mbps': result.upload_speed_mbps,
                'download_speed_mbps': result.download_speed_mbps,
                'error_message': result.error_message,
                'metadata': result.metadata
            })
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Отчет тестирования хранилищ сохранен: {filename}")
    
    def print_summary(self):
        """Вывести сводку результатов"""
        print("\n" + "=" * 60)
        print("📊 СВОДКА ТЕСТИРОВАНИЯ ХРАНИЛИЩ")
        print("=" * 60)
        
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        
        print(f"Всего тестов: {len(self.results)}")
        print(f"Успешных: {len(successful)}")
        print(f"Неудачных: {len(failed)}")
        print(f"Успешность: {len(successful) / len(self.results) * 100:.1f}%")
        
        # Группировка по типам тестов
        test_types = {}
        for result in self.results:
            test_type = result.test_name
            if test_type not in test_types:
                test_types[test_type] = {'total': 0, 'success': 0, 'avg_speed': 0, 'speeds': []}
            
            test_types[test_type]['total'] += 1
            if result.success:
                test_types[test_type]['success'] += 1
                if result.upload_speed_mbps > 0:
                    test_types[test_type]['speeds'].append(result.upload_speed_mbps)
        
        print("\nСтатистика по типам тестов:")
        for test_type, stats in test_types.items():
            success_rate = stats['success'] / stats['total'] * 100
            avg_speed = sum(stats['speeds']) / len(stats['speeds']) if stats['speeds'] else 0
            print(f"  {test_type}:")
            print(f"    Успешность: {success_rate:.1f}% ({stats['success']}/{stats['total']})")
            print(f"    Средняя скорость: {avg_speed:.2f} МБ/с")

def main():
    """Основная функция"""
    tester = StorageIntegrationTester()
    success = tester.run_all_storage_tests()
    
    # Выводим сводку
    tester.print_summary()
    
    if success:
        print("\n🎉 Все тесты интеграции хранилищ пройдены успешно!")
    else:
        print("\n⚠️  Некоторые тесты интеграции хранилищ не пройдены")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)