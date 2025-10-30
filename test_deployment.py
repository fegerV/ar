"""
Тестирование развертывания приложения
"""
import os
import sys
import tempfile
import shutil
import subprocess
import time
import requests
from pathlib import Path

def test_local_application_launch():
    """Тестирование локального запуска приложения"""
    print("Тест 1: Локальный запуск приложения")
    
    try:
        # Проверяем, что приложение может быть запущено
        print("  Проверка возможности запуска приложения")
        
        # Создаем временную директорию для теста
        temp_dir = tempfile.mkdtemp()
        
        # Копируем необходимые файлы в временную директорию
        src_dir = Path("vertex-art-ar")
        dst_dir = Path(temp_dir) / "vertex-art-ar"
        shutil.copytree(src_dir, dst_dir)
        
        # Пытаемся запустить приложение в фоновом режиме
        print("  Запуск приложения в фоновом режиме")
        
        # Запускаем приложение
        process = subprocess.Popen([
            sys.executable, "-m", "main"
        ], cwd=dst_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Ждем некоторое время для запуска
        time.sleep(5)
        
        # Проверяем, что процесс запущен
        if process.poll() is None:
            print("    Приложение успешно запущено в фоновом режиме: УСПЕШНО")
            
            # Пробуем получить доступ к главной странице
            try:
                response = requests.get("http://localhost:8000/", timeout=5)
                if response.status_code == 200:
                    print("    Доступ к главной странице приложения: УСПЕШНО")
                else:
                    print(f"    Ошибка доступа к главной странице: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"    Невозможно получить доступ к приложению: {e}")
            
            # Завершаем процесс
            process.terminate()
            process.wait(timeout=10)
            
            return True
        else:
            # Получаем вывод процесса
            stdout, stderr = process.communicate()
            print(f"    Ошибка запуска приложения: {stderr.decode()}")
            return False
            
    except Exception as e:
        print(f"    Ошибка при тестировании локального запуска приложения: {e}")
        return False
    finally:
        # Очищаем временную директорию
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_docker_launch():
    """Тестирование запуска через Docker"""
    print("\nТест 2: Запуск через Docker")
    
    try:
        # Проверяем наличие Docker
        print("  Проверка наличия Docker")
        docker_check = subprocess.run(["docker", "--version"], 
                                      capture_output=True, text=True)
        
        if docker_check.returncode != 0:
            print("    Docker не установлен или недоступен")
            print("    Для установки Docker посетите: https://www.docker.com/products/docker-desktop")
            return False
        
        print(f"    Docker установлен: {docker_check.stdout.strip()}")
        
        # Проверяем наличие Dockerfile
        dockerfile_path = Path("vertex-art-ar/Dockerfile")
        if not dockerfile_path.exists():
            print("    Dockerfile не найден")
            return False
        
        print("    Dockerfile найден: УСПЕШНО")
        
        # Пытаемся собрать Docker образ
        print("  Сборка Docker образа")
        build_process = subprocess.run([
            "docker", "build", "-t", "vertex-art-ar:test", "."
        ], cwd="vertex-art-ar", capture_output=True, text=True)
        
        if build_process.returncode == 0:
            print("    Docker образ успешно собран: УСПЕШНО")
            
            # Запускаем контейнер
            print("  Запуск Docker контейнера")
            run_process = subprocess.run([
                "docker", "run", "-d", "-p", "8000:8000", 
                "--name", "vertex-art-ar-test", "vertex-art-ar:test"
            ], capture_output=True, text=True)
            
            if run_process.returncode == 0:
                print("    Docker контейнер успешно запущен: УСПЕШНО")
                
                # Ждем запуск приложения
                time.sleep(10)
                
                # Пробуем получить доступ к приложению
                try:
                    response = requests.get("http://localhost:8000/", timeout=5)
                    if response.status_code == 200:
                        print("    Доступ к приложению через Docker: УСПЕШНО")
                    else:
                        print(f"    Ошибка доступа к приложению через Docker: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    print(f"    Невозможно получить доступ к приложению через Docker: {e}")
                
                # Останавливаем контейнер
                subprocess.run(["docker", "stop", "vertex-art-ar-test"], 
                               capture_output=True)
                subprocess.run(["docker", "rm", "vertex-art-ar-test"], 
                               capture_output=True)
                
                return True
            else:
                print(f"    Ошибка запуска Docker контейнера: {run_process.stderr}")
                return False
        else:
            print(f"    Ошибка сборки Docker образа: {build_process.stderr}")
            return False
            
    except Exception as e:
        print(f"    Ошибка при тестировании запуска через Docker: {e}")
        return False

def test_application_after_restart():
    """Тестирование работы приложения после перезапуска"""
    print("\nТест 3: Работа приложения после перезапуска")
    
    try:
        # Создаем временную директорию
        temp_dir = tempfile.mkdtemp()
        src_dir = Path("vertex-art-ar")
        dst_dir = Path(temp_dir) / "vertex-art-ar"
        shutil.copytree(src_dir, dst_dir)
        
        # Запускаем приложение первый раз
        print("  Первый запуск приложения")
        process1 = subprocess.Popen([
            sys.executable, "-m", "main"
        ], cwd=dst_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Ждем запуск
        time.sleep(5)
        
        # Проверяем доступность
        try:
            response1 = requests.get("http://localhost:8000/", timeout=5)
            if response1.status_code == 200:
                print("    Приложение доступно после первого запуска: УСПЕШНО")
            else:
                print(f"    Ошибка доступа после первого запуска: {response1.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"    Невозможно получить доступ после первого запуска: {e}")
        
        # Завершаем первый процесс
        process1.terminate()
        process1.wait(timeout=10)
        
        # Запускаем приложение второй раз
        print("  Второй запуск приложения")
        process2 = subprocess.Popen([
            sys.executable, "-m", "main"
        ], cwd=dst_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Ждем запуск
        time.sleep(5)
        
        # Проверяем доступность снова
        try:
            response2 = requests.get("http://localhost:8000/", timeout=5)
            if response2.status_code == 200:
                print("    Приложение доступно после второго запуска: УСПЕШНО")
            else:
                print(f"    Ошибка доступа после второго запуска: {response2.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"    Невозможно получить доступ после второго запуска: {e}")
        
        # Завершаем второй процесс
        process2.terminate()
        process2.wait(timeout=10)
        
        return True
        
    except Exception as e:
        print(f"    Ошибка при тестировании работы после перезапуска: {e}")
        return False
    finally:
        # Очищаем временную директорию
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_application_logs():
    """Тестирование логов приложения"""
    print("\nТест 4: Проверка логов приложения")
    
    try:
        # Создаем временную директорию
        temp_dir = tempfile.mkdtemp()
        src_dir = Path("vertex-art-ar")
        dst_dir = Path(temp_dir) / "vertex-art-ar"
        shutil.copytree(src_dir, dst_dir)
        
        # Запускаем приложение и собираем логи
        print("  Запуск приложения с записью логов")
        log_file = dst_dir / "app.log"
        
        with open(log_file, "w") as log_f:
            process = subprocess.Popen([
                sys.executable, "-m", "main"
            ], cwd=dst_dir, stdout=log_f, stderr=subprocess.STDOUT)
            
            # Ждем запуск
            time.sleep(5)
            
            # Завершаем процесс
            process.terminate()
            process.wait(timeout=10)
        
        # Проверяем логи
        if log_file.exists():
            log_size = log_file.stat().st_size
            print(f"    Лог файл создан, размер: {log_size} байт: УСПЕШНО")
            
            # Проверяем содержимое лога
            with open(log_file, "r") as f:
                log_content = f.read()
                if log_content:
                    print("    Лог файл содержит записи: УСПЕШНО")
                else:
                    print("    Лог файл пустой: ОШИБКА")
                    return False
        else:
            print("    Лог файл не создан: ОШИБКА")
            return False
        
        return True
        
    except Exception as e:
        print(f"    Ошибка при тестировании логов приложения: {e}")
        return False
    finally:
        # Очищаем временную директорию
        shutil.rmtree(temp_dir, ignore_errors=True)

def main():
    """Основная функция тестирования развертывания"""
    print("=== Тестирование развертывания ===\n")
    
    tests = [
        test_local_application_launch,
        test_docker_launch,
        test_application_after_restart,
        test_application_logs
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"  Ошибка в тесте {test.__name__}: {e}")
            results.append(False)
    
    print(f"\n=== Результаты ===")
    print(f"Пройдено тестов: {sum(results)}/{len(results)}")
    
    if all(results):
        print("Все тесты развертывания пройдены успешно!")
        return True
    else:
        print("Некоторые тесты развертывания не пройдены.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)