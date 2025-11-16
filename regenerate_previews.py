#!/usr/bin/env python3
"""
Скрипт для регенерации существующих превью с новыми оптимизированными параметрами
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, List

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "vertex-ar"))

from app.database import Database
from preview_generator import PreviewGenerator, generate_and_save_preview
from logging_setup import get_logger
import shutil

logger = get_logger(__name__)


def regenerate_portrait_previews(database: Database) -> Dict[str, int]:
    """Регенерирует превью для всех портретов"""
    results = {"success": 0, "failed": 0, "skipped": 0}
    
    logger.info("Начинаем регенерацию превью портретов...")
    
    # Получаем все портреты
    portraits = database.list_portraits()
    logger.info(f"Найдено портретов: {len(portraits)}")
    
    for portrait in portraits:
        try:
            portrait_id = portrait["id"]
            image_path = Path(portrait["image_path"])
            
            if not image_path.exists():
                logger.warning(f"Файл изображения не найден: {image_path}")
                results["skipped"] += 1
                continue
            
            # Читаем оригинальное изображение
            with open(image_path, "rb") as f:
                image_content = f.read()
            
            # Генерируем новое превью с оптимизированными параметрами
            preview_content = PreviewGenerator.generate_image_preview(image_content)
            
            if preview_content:
                # Сохраняем новое превью
                client_id = portrait["client_id"]
                storage_root = Path("storage")
                client_storage = storage_root / "portraits" / client_id / portrait_id
                client_storage.mkdir(parents=True, exist_ok=True)
                
                new_preview_path = client_storage / f"{portrait_id}_preview.jpg"
                
                # Резервное копирование старого превью
                old_preview_path = portrait.get("image_preview_path")
                if old_preview_path and Path(old_preview_path).exists():
                    backup_path = Path(old_preview_path).with_suffix(".jpg.backup")
                    shutil.copy2(old_preview_path, backup_path)
                    logger.info(f"Создан бэкап старого превью: {backup_path}")
                
                # Сохраняем новое превью
                with open(new_preview_path, "wb") as f:
                    f.write(preview_content)
                
                # Обновляем путь в базе данных
                database.update_portrait_preview(portrait_id, str(new_preview_path))
                
                old_size = Path(old_preview_path).stat().st_size if old_preview_path and Path(old_preview_path).exists() else 0
                new_size = len(preview_content)
                
                logger.info(f"✅ Превью регенерировано для {portrait_id}: {old_size} -> {new_size} байт")
                results["success"] += 1
            else:
                logger.error(f"❌ Не удалось сгенерировать превью для {portrait_id}")
                results["failed"] += 1
                
        except Exception as e:
            logger.error(f"❌ Ошибка при регенерации превью для портрета {portrait.get('id')}: {e}")
            results["failed"] += 1
    
    return results


def regenerate_video_previews(database: Database) -> Dict[str, int]:
    """Регенерирует превью для всех видео"""
    results = {"success": 0, "failed": 0, "skipped": 0}
    
    logger.info("Начинаем регенерацию превью видео...")
    
    # Получаем все портреты и их видео
    portraits = database.list_portraits()
    
    for portrait in portraits:
        try:
            portrait_id = portrait["id"]
            videos = database.list_videos(portrait_id)
            
            for video in videos:
                video_id = video["id"]
                video_path = Path(video["video_path"])
                
                if not video_path.exists():
                    logger.warning(f"Файл видео не найден: {video_path}")
                    results["skipped"] += 1
                    continue
                
                # Читаем оригинальное видео
                with open(video_path, "rb") as f:
                    video_content = f.read()
                
                # Генерируем новое превью с оптимизированными параметрами
                preview_content = PreviewGenerator.generate_video_preview(video_content)
                
                if preview_content:
                    # Сохраняем новое превью
                    client_id = portrait["client_id"]
                    storage_root = Path("storage")
                    client_storage = storage_root / "portraits" / client_id / portrait_id
                    client_storage.mkdir(parents=True, exist_ok=True)
                    
                    new_preview_path = client_storage / f"{video_id}_preview.jpg"
                    
                    # Резервное копирование старого превью
                    old_preview_path = video.get("video_preview_path")
                    if old_preview_path and Path(old_preview_path).exists():
                        backup_path = Path(old_preview_path).with_suffix(".jpg.backup")
                        shutil.copy2(old_preview_path, backup_path)
                        logger.info(f"Создан бэкап старого превью видео: {backup_path}")
                    
                    # Сохраняем новое превью
                    with open(new_preview_path, "wb") as f:
                        f.write(preview_content)
                    
                    # Обновляем путь в базе данных
                    database.update_video_preview(video_id, str(new_preview_path))
                    
                    old_size = Path(old_preview_path).stat().st_size if old_preview_path and Path(old_preview_path).exists() else 0
                    new_size = len(preview_content)
                    
                    logger.info(f"✅ Превью видео регенерировано для {video_id}: {old_size} -> {new_size} байт")
                    results["success"] += 1
                else:
                    logger.error(f"❌ Не удалось сгенерировать превью видео для {video_id}")
                    results["failed"] += 1
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при регенерации превью видео для портрета {portrait.get('id')}: {e}")
            results["failed"] += 1
    
    return results


def cleanup_backup_files():
    """Удаляет бэкап файлы после успешной регенерации"""
    logger.info("Очистка бэкап файлов...")
    
    storage_root = Path("storage")
    backup_files = list(storage_root.rglob("*.backup"))
    
    for backup_file in backup_files:
        try:
            backup_file.unlink()
            logger.info(f"Удален бэкап файл: {backup_file}")
        except Exception as e:
            logger.error(f"Ошибка при удалении бэкап файла {backup_file}: {e}")


def main():
    """Основная функция"""
    print("🚀 Начинаем регенерацию превью с оптимизированными параметрами...")
    print("=" * 60)
    
    try:
        # Инициализация базы данных
        db_path = Path("app_data.db")
        if not db_path.exists():
            print("❌ База данных не найдена!")
            return 1
        
        database = Database(db_path)
        
        start_time = time.time()
        
        # Регенерация превью портретов
        portrait_results = regenerate_portrait_previews(database)
        
        # Регенерация превью видео
        video_results = regenerate_video_previews(database)
        
        end_time = time.time()
        
        # Вывод результатов
        print("\n📊 Результаты регенерации:")
        print(f"🖼️  Портреты:")
        print(f"  ✅ Успешно: {portrait_results['success']}")
        print(f"  ❌ Ошибки: {portrait_results['failed']}")
        print(f"  ⏭️  Пропущено: {portrait_results['skipped']}")
        
        print(f"\n🎬 Видео:")
        print(f"  ✅ Успешно: {video_results['success']}")
        print(f"  ❌ Ошибки: {video_results['failed']}")
        print(f"  ⏭️  Пропущено: {video_results['skipped']}")
        
        total_success = portrait_results['success'] + video_results['success']
        total_failed = portrait_results['failed'] + video_results['failed']
        total_skipped = portrait_results['skipped'] + video_results['skipped']
        
        print(f"\n📈 Итого:")
        print(f"  ✅ Успешно: {total_success}")
        print(f"  ❌ Ошибки: {total_failed}")
        print(f"  ⏭️  Пропущено: {total_skipped}")
        print(f"  ⏱️  Время выполнения: {(end_time - start_time):.1f} сек")
        
        if total_failed == 0:
            print("\n🎉 Все превью успешно регенерированы!")
            
            # Предлагаем удалить бэкап файлы
            response = input("\n🗑️  Удалить бэкап файлы? (y/N): ").strip().lower()
            if response in ['y', 'yes', 'да']:
                cleanup_backup_files()
                print("✅ Бэкап файлы удалены")
        else:
            print(f"\n⚠️  {total_failed} превью не удалось регенерировать. Проверьте логи.")
        
        return 0 if total_failed == 0 else 1
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())