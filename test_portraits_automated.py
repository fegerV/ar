#!/usr/bin/env python3
"""
Полностью автоматизированные тесты для портретов
Включает создание данных, проверку всех API endpoints и валидацию
"""

import json
import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Добавляем путь к основному приложению
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vertex-ar"))

try:
    import psutil
    import requests
    from PIL import Image, ImageDraw
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Установите необходимые зависимости: pip install requests pillow psutil")
    sys.exit(1)


@dataclass
class TestResult:
    """Результат теста"""

    test_name: str
    success: bool
    duration: float
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class AutomatedPortraitsTester:
    """Автоматизированный тестер портретов"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.test_data = {}
        self.results: List[TestResult] = []
        self.temp_dir = None

    def login(self, username: str = "admin", password: str = "admin") -> bool:
        """Аутентификация в системе"""
        test_name = "Authentication"
        start_time = time.time()

        try:
            response = self.session.post(f"{self.base_url}/auth/login", json={"username": username, "password": password})

            duration = time.time() - start_time

            if response.status_code == 200:
                self.token = response.json()["access_token"]
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})

                result = TestResult(
                    test_name=test_name, success=True, duration=duration, details={"token_length": len(self.token)}
                )

                print(f"✅ {test_name}: Успешно ({duration:.3f}s)")
                self.results.append(result)
                return True
            else:
                result = TestResult(
                    test_name=test_name,
                    success=False,
                    duration=duration,
                    error_message=f"HTTP {response.status_code}: {response.text}",
                )

                print(f"❌ {test_name}: Ошибка ({duration:.3f}s)")
                self.results.append(result)
                return False

        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(test_name=test_name, success=False, duration=duration, error_message=str(e))

            print(f"❌ {test_name}: Исключение ({duration:.3f}s)")
            self.results.append(result)
            return False

    def create_test_data(self) -> bool:
        """Создать тестовые данные"""
        test_name = "Test Data Creation"
        start_time = time.time()

        try:
            self.temp_dir = tempfile.mkdtemp()

            # Создаем тестовые изображения и видео
            test_clients = [
                {"name": "Иван Петров", "phone": "+79991112233"},
                {"name": "Мария Иванова", "phone": "+79992223344"},
                {"name": "Алексей Сидоров", "phone": "+79993334455"},
            ]

            created_orders = []

            for i, client in enumerate(test_clients):
                # Создаем изображение
                img = Image.new("RGB", (800, 600), color="white")
                draw = ImageDraw.Draw(img)

                # Рисуем уникальный портрет для каждого клиента
                colors = ["lightblue", "lightgreen", "lightpink"]
                draw.ellipse([250, 150, 550, 450], fill=colors[i], outline="black", width=3)
                draw.ellipse([320, 250, 360, 290], fill="black")
                draw.ellipse([440, 250, 480, 290], fill="black")
                draw.arc([300, 320, 500, 420], 0, 180, fill="black", width=5)
                draw.text([300, 500], client["name"], fill="black")

                img_path = os.path.join(self.temp_dir, f"portrait_{i}.jpg")
                img.save(img_path)

                # Создаем видео файл
                video_path = os.path.join(self.temp_dir, f"video_{i}.mp4")
                with open(video_path, "wb") as f:
                    f.write(f'Video content for {client["name"]}'.encode())

                # Создаем заказ
                with open(img_path, "rb") as img, open(video_path, "rb") as vid:
                    files = {"image": (f"portrait_{i}.jpg", img, "image/jpeg"), "video": (f"video_{i}.mp4", vid, "video/mp4")}
                    data = {"phone": client["phone"], "name": client["name"]}

                    response = self.session.post(f"{self.base_url}/orders/create", files=files, data=data)

                if response.status_code == 200:
                    order_data = response.json()
                    created_orders.append({"client": client, "order": order_data})

                    # Добавляем второе видео для первого клиента
                    if i == 0:
                        video2_path = os.path.join(self.temp_dir, f"video_{i}_2.mp4")
                        with open(video2_path, "wb") as f:
                            f.write(f'Second video for {client["name"]}'.encode())

                        with open(video2_path, "rb") as vid2:
                            files = {"video": (f"video_{i}_2.mp4", vid2, "video/mp4")}
                            data = {"portrait_id": order_data["portrait"]["id"]}

                            response = self.session.post(f"{self.base_url}/videos/add", files=files, data=data)

            duration = time.time() - start_time

            self.test_data = {"clients": test_clients, "orders": created_orders}

            result = TestResult(
                test_name=test_name,
                success=True,
                duration=duration,
                details={"clients_created": len(test_clients), "orders_created": len(created_orders)},
            )

            print(f"✅ {test_name}: Создано {len(created_orders)} заказов ({duration:.3f}s)")
            self.results.append(result)
            return True

        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(test_name=test_name, success=False, duration=duration, error_message=str(e))

            print(f"❌ {test_name}: {e} ({duration:.3f}s)")
            self.results.append(result)
            return False

    def test_client_search(self) -> bool:
        """Тест поиска клиентов"""
        test_name = "Client Search"
        start_time = time.time()

        try:
            # Тест поиска по полному номеру
            client = self.test_data["clients"][0]
            response = self.session.get(f"{self.base_url}/clients/search", params={"phone": client["phone"]})

            duration = time.time() - start_time

            if response.status_code == 200:
                search_results = response.json()
                found = len(search_results) > 0

                result = TestResult(
                    test_name=test_name,
                    success=found,
                    duration=duration,
                    details={"search_phone": client["phone"], "results_count": len(search_results)},
                )

                print(f"✅ {test_name}: Найдено {len(search_results)} клиентов ({duration:.3f}s)")
                self.results.append(result)
                return found
            else:
                result = TestResult(
                    test_name=test_name, success=False, duration=duration, error_message=f"HTTP {response.status_code}"
                )

                print(f"❌ {test_name}: Ошибка HTTP {response.status_code} ({duration:.3f}s)")
                self.results.append(result)
                return False

        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(test_name=test_name, success=False, duration=duration, error_message=str(e))

            print(f"❌ {test_name}: {e} ({duration:.3f}s)")
            self.results.append(result)
            return False

    def test_client_list(self) -> bool:
        """Тест списка клиентов"""
        test_name = "Client List"
        start_time = time.time()

        try:
            response = self.session.get(f"{self.base_url}/clients/list")
            duration = time.time() - start_time

            if response.status_code == 200:
                clients = response.json()
                success = len(clients) >= len(self.test_data["clients"])

                result = TestResult(
                    test_name=test_name,
                    success=success,
                    duration=duration,
                    details={"clients_count": len(clients), "expected_min": len(self.test_data["clients"])},
                )

                print(f"✅ {test_name}: {len(clients)} клиентов ({duration:.3f}s)")
                self.results.append(result)
                return success
            else:
                result = TestResult(
                    test_name=test_name, success=False, duration=duration, error_message=f"HTTP {response.status_code}"
                )

                print(f"❌ {test_name}: Ошибка HTTP {response.status_code} ({duration:.3f}s)")
                self.results.append(result)
                return False

        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(test_name=test_name, success=False, duration=duration, error_message=str(e))

            print(f"❌ {test_name}: {e} ({duration:.3f}s)")
            self.results.append(result)
            return False

    def test_portrait_list(self) -> bool:
        """Тест списка портретов"""
        test_name = "Portrait List"
        start_time = time.time()

        try:
            response = self.session.get(f"{self.base_url}/portraits/list")
            duration = time.time() - start_time

            if response.status_code == 200:
                portraits = response.json()
                success = len(portraits) >= len(self.test_data["orders"])

                result = TestResult(
                    test_name=test_name,
                    success=success,
                    duration=duration,
                    details={"portraits_count": len(portraits), "expected_min": len(self.test_data["orders"])},
                )

                print(f"✅ {test_name}: {len(portraits)} портретов ({duration:.3f}s)")
                self.results.append(result)
                return success
            else:
                result = TestResult(
                    test_name=test_name, success=False, duration=duration, error_message=f"HTTP {response.status_code}"
                )

                print(f"❌ {test_name}: Ошибка HTTP {response.status_code} ({duration:.3f}s)")
                self.results.append(result)
                return False

        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(test_name=test_name, success=False, duration=duration, error_message=str(e))

            print(f"❌ {test_name}: {e} ({duration:.3f}s)")
            self.results.append(result)
            return False

    def test_portrait_details(self) -> bool:
        """Тест детальной информации о портрете"""
        test_name = "Portrait Details"
        start_time = time.time()

        try:
            # Берем первый портрет
            portrait_id = self.test_data["orders"][0]["order"]["portrait"]["id"]
            response = self.session.get(f"{self.base_url}/portraits/{portrait_id}/details")
            duration = time.time() - start_time

            if response.status_code == 200:
                details = response.json()
                has_client = "client" in details
                has_portrait = "portrait" in details
                has_videos = "videos" in details

                success = has_client and has_portrait and has_videos

                result = TestResult(
                    test_name=test_name,
                    success=success,
                    duration=duration,
                    details={
                        "has_client": has_client,
                        "has_portrait": has_portrait,
                        "has_videos": has_videos,
                        "videos_count": len(details.get("videos", [])),
                    },
                )

                print(f"✅ {test_name}: Детали получены, видео: {len(details.get('videos', []))} ({duration:.3f}s)")
                self.results.append(result)
                return success
            else:
                result = TestResult(
                    test_name=test_name, success=False, duration=duration, error_message=f"HTTP {response.status_code}"
                )

                print(f"❌ {test_name}: Ошибка HTTP {response.status_code} ({duration:.3f}s)")
                self.results.append(result)
                return False

        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(test_name=test_name, success=False, duration=duration, error_message=str(e))

            print(f"❌ {test_name}: {e} ({duration:.3f}s)")
            self.results.append(result)
            return False

    def test_video_management(self) -> bool:
        """Тест управления видео"""
        test_name = "Video Management"
        start_time = time.time()

        try:
            # Берем первый портрет (у него должно быть 2 видео)
            portrait_id = self.test_data["orders"][0]["order"]["portrait"]["id"]

            # Получаем список видео
            response = self.session.get(f"{self.base_url}/videos/list/{portrait_id}")

            if response.status_code != 200:
                raise Exception(f"Не удалось получить список видео: {response.status_code}")

            videos = response.json()

            if len(videos) < 2:
                raise Exception(f"Ожидается минимум 2 видео, получено: {len(videos)}")

            # Находим неактивное видео и активируем его
            inactive_video = None
            for video in videos:
                if not video["is_active"]:
                    inactive_video = video
                    break

            if not inactive_video:
                raise Exception("Не найдено неактивное видео для активации")

            # Активируем видео
            response = self.session.put(f"{self.base_url}/videos/{inactive_video['id']}/activate")

            if response.status_code != 200:
                raise Exception(f"Не удалось активировать видео: {response.status_code}")

            duration = time.time() - start_time

            result = TestResult(
                test_name=test_name,
                success=True,
                duration=duration,
                details={"total_videos": len(videos), "activated_video_id": inactive_video["id"]},
            )

            print(f"✅ {test_name}: Управление видео успешно ({duration:.3f}s)")
            self.results.append(result)
            return True

        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(test_name=test_name, success=False, duration=duration, error_message=str(e))

            print(f"❌ {test_name}: {e} ({duration:.3f}s)")
            self.results.append(result)
            return False

    def test_public_portrait_access(self) -> bool:
        """Тест публичного доступа к портрету"""
        test_name = "Public Portrait Access"
        start_time = time.time()

        try:
            # Берем первый портрет
            portrait_id = self.test_data["orders"][0]["order"]["portrait"]["id"]

            # Создаем новый клиент без авторизации для публичного доступа
            public_session = requests.Session()

            # Запрашиваем публичную страницу портрета
            response = public_session.get(f"{self.base_url}/portrait/{portrait_id}")
            duration = time.time() - start_time

            # Проверяем что страница доступна (HTML контент)
            success = response.status_code == 200 and "html" in response.headers.get("content-type", "")

            result = TestResult(
                test_name=test_name,
                success=success,
                duration=duration,
                details={
                    "portrait_id": portrait_id,
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type", ""),
                },
            )

            print(f"✅ {test_name}: Публичный доступ работает ({duration:.3f}s)")
            self.results.append(result)
            return success

        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(test_name=test_name, success=False, duration=duration, error_message=str(e))

            print(f"❌ {test_name}: {e} ({duration:.3f}s)")
            self.results.append(result)
            return False

    def test_system_endpoints(self) -> bool:
        """Тест системных эндпоинтов"""
        test_name = "System Endpoints"
        start_time = time.time()

        try:
            endpoints = ["/admin/system-info", "/admin/storage-info", "/admin/content-stats"]

            results = {}

            for endpoint in endpoints:
                response = self.session.get(f"{self.base_url}{endpoint}")
                results[endpoint] = {"status_code": response.status_code, "success": response.status_code == 200}

            duration = time.time() - start_time
            success_count = sum(1 for r in results.values() if r["success"])

            result = TestResult(
                test_name=test_name,
                success=success_count == len(endpoints),
                duration=duration,
                details={
                    "total_endpoints": len(endpoints),
                    "successful_endpoints": success_count,
                    "endpoint_results": results,
                },
            )

            print(f"✅ {test_name}: {success_count}/{len(endpoints)} эндпоинтов ({duration:.3f}s)")
            self.results.append(result)
            return success_count == len(endpoints)

        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(test_name=test_name, success=False, duration=duration, error_message=str(e))

            print(f"❌ {test_name}: {e} ({duration:.3f}s)")
            self.results.append(result)
            return False

    def test_data_integrity(self) -> bool:
        """Тест целостности данных"""
        test_name = "Data Integrity"
        start_time = time.time()

        try:
            # Проверяем что все созданные клиенты доступны
            clients_response = self.session.get(f"{self.base_url}/clients/list")
            if clients_response.status_code != 200:
                raise Exception("Не удалось получить список клиентов")

            clients = clients_response.json()
            created_clients = {order["client"]["phone"] for order in self.test_data["orders"]}
            found_clients = {client["phone"] for client in clients}

            missing_clients = created_clients - found_clients

            # Проверяем что все портреты доступны
            portraits_response = self.session.get(f"{self.base_url}/portraits/list")
            if portraits_response.status_code != 200:
                raise Exception("Не удалось получить список портретов")

            portraits = portraits_response.json()
            expected_portraits = len(self.test_data["orders"])

            duration = time.time() - start_time

            success = len(missing_clients) == 0 and len(portraits) >= expected_portraits

            result = TestResult(
                test_name=test_name,
                success=success,
                duration=duration,
                details={
                    "expected_clients": len(created_clients),
                    "found_clients": len(found_clients),
                    "missing_clients": len(missing_clients),
                    "expected_portraits": expected_portraits,
                    "found_portraits": len(portraits),
                },
            )

            print(f"✅ {test_name}: Целостность данных проверена ({duration:.3f}s)")
            self.results.append(result)
            return success

        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(test_name=test_name, success=False, duration=duration, error_message=str(e))

            print(f"❌ {test_name}: {e} ({duration:.3f}s)")
            self.results.append(result)
            return False

    def cleanup_test_data(self):
        """Очистка тестовых данных"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print("🧹 Тестовые данные очищены")

    def run_all_tests(self) -> bool:
        """Запустить все автоматизированные тесты"""
        print("=" * 60)
        print("🤖 АВТОМАТИЗИРОВАННОЕ ТЕСТИРОВАНИЕ ПОРТРЕТОВ")
        print("=" * 60)

        tests = [
            ("Аутентификация", self.login),
            ("Создание тестовых данных", self.create_test_data),
            ("Поиск клиентов", self.test_client_search),
            ("Список клиентов", self.test_client_list),
            ("Список портретов", self.test_portrait_list),
            ("Детали портрета", self.test_portrait_details),
            ("Управление видео", self.test_video_management),
            ("Публичный доступ", self.test_public_portrait_access),
            ("Системные эндпоинты", self.test_system_endpoints),
            ("Целостность данных", self.test_data_integrity),
        ]

        all_passed = True

        for test_name, test_func in tests:
            print(f"\n🧪 {test_name}...")
            try:
                result = test_func()
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"❌ Критическая ошибка в тесте {test_name}: {e}")
                all_passed = False

        try:
            # Сохраняем отчет
            self.save_automated_report()

            # Выводим сводку
            self.print_summary()

        finally:
            self.cleanup_test_data()

        return all_passed

    def save_automated_report(self, filename: str = "automated_portraits_report.json"):
        """Сохранить отчет автоматизированного тестирования"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "test_summary": {
                "total_tests": len(self.results),
                "successful_tests": len([r for r in self.results if r.success]),
                "failed_tests": len([r for r in self.results if not r.success]),
                "total_duration": sum(r.duration for r in self.results),
            },
            "test_results": [],
        }

        for result in self.results:
            report["test_results"].append(
                {
                    "test_name": result.test_name,
                    "success": result.success,
                    "duration": result.duration,
                    "details": result.details,
                    "error_message": result.error_message,
                }
            )

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Отчет автоматизированного тестирования сохранен: {filename}")

    def print_summary(self):
        """Вывести сводку результатов"""
        print("\n" + "=" * 60)
        print("📊 СВОДКА АВТОМАТИЗИРОВАННОГО ТЕСТИРОВАНИЯ")
        print("=" * 60)

        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        print(f"Всего тестов: {len(self.results)}")
        print(f"Успешных: {len(successful)}")
        print(f"Неудачных: {len(failed)}")
        print(f"Успешность: {len(successful) / len(self.results) * 100:.1f}%")
        print(f"Общее время: {sum(r.duration for r in self.results):.3f} сек")

        if failed:
            print("\n❌ Неудачные тесты:")
            for result in failed:
                print(f"  - {result.test_name}: {result.error_message}")

        print("\n✅ Успешные тесты:")
        for result in successful:
            print(f"  - {result.test_name} ({result.duration:.3f}s)")


def main():
    """Основная функция"""
    tester = AutomatedPortraitsTester()
    success = tester.run_all_tests()

    if success:
        print("\n🎉 Все автоматизированные тесты пройдены успешно!")
    else:
        print("\n⚠️  Некоторые автоматизированные тесты не пройдены")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
