#!/usr/bin/env python3
"""
Базовый тест проверки psutil и производительности
"""

import json
import os
import sys
import time
from datetime import datetime

# Добавляем путь к основному приложению
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vertex-ar"))

try:
    import psutil

    print("✅ psutil импортирован успешно")
    print(f"Версия psutil: {psutil.__version__}")

    # Получаем информацию о системе
    print(f"CPU count: {psutil.cpu_count()}")
    print(f"Memory total: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.2f} GB")

    # Тест мониторинга процесса
    process = psutil.Process()
    print(f"Current process PID: {process.pid}")
    print(f"Current memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")

    # Тест сбора метрик
    print("\n📊 Тест сбора метрик производительности...")

    metrics = []
    for i in range(5):
        cpu_percent = process.cpu_percent()
        memory_mb = process.memory_info().rss / 1024 / 1024

        metric = {
            "timestamp": datetime.now().isoformat(),
            "iteration": i,
            "cpu_percent": cpu_percent,
            "memory_mb": memory_mb,
            "open_files": len(process.open_files()),
            "threads": process.num_threads(),
        }

        metrics.append(metric)
        print(f"  Итерация {i}: CPU={cpu_percent:.1f}%, Memory={memory_mb:.1f}MB")

        # Небольшая нагрузка
        time.sleep(0.5)

    # Сохраняем метрики
    with open("psutil_basic_test.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\n✅ Базовый тест psutil завершен успешно!")
    print(f"📄 Метрики сохранены в psutil_basic_test.json")

except ImportError as e:
    print(f"❌ Ошибка импорта psutil: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Ошибка выполнения: {e}")
    sys.exit(1)
