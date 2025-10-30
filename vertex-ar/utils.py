"""
Вспомогательные утилиты для Vertex-AR
"""
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Tuple


def get_disk_usage(path: str = ".") -> Dict[str, int]:
    """
    Получить информацию о занятом и свободном дисковом пространстве
    """
    total, used, free = shutil.disk_usage(path)
    return {
        "total": total,
        "used": used,
        "free": free,
        "used_percent": round((used / total) * 100, 2),
        "free_percent": round((free / total) * 100, 2)
    }


def format_bytes(bytes_value: int) -> str:
    """
    Преобразовать байты в человеко-читаемый формат
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def get_storage_usage(storage_path: str = "storage") -> Dict[str, Any]:
    """
    Получить информацию об использовании хранилища
    """
    storage_dir = Path(storage_path)
    if not storage_dir.exists():
        return {"total_size": 0, "file_count": 0, "formatted_size": "0 B"}
    
    total_size = 0
    file_count = 0
    
    for dirpath, dirnames, filenames in os.walk(storage_dir):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
                file_count += 1
            except OSError:
                # Пропускаем файлы, к которым нет доступа
                continue
    
    return {
        "total_size": total_size,
        "file_count": file_count,
        "formatted_size": format_bytes(total_size)
    }