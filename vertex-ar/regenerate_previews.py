#!/usr/bin/env python3
"""
Скрипт для регенерации всех существующих превью с улучшенными параметрами.
"""

import os
import sys
from pathlib import Path
from logging_setup import get_logger

# Добавляем путь к приложению
sys.path.insert(0, str(Path(__file__).parent))

logger = get_logger(__name__)

def regenerate_previews():
    """Регенерирует все превью с новыми параметрами."""
    from app.database import Database
    from preview_generator import PreviewGenerator
    from app.main import get_current_app
    
    # Инициализация приложения
    try:
        app = get_current_app()
        if not app:
            from app.config import settings
            from app.main import create_app
            app = create_app()
    except:
        from app.config import settings
        from app.main import create_app
        app = create_app()
    
    database = app.state.database
    storage_root = app.state.config["STORAGE_ROOT"]
    
    # Получаем все портреты
    portraits = database.list_portraits()
    logger.info(f"Found {len(portraits)} portraits to regenerate previews for")
    
    # Регенерируем превью портретов
    for portrait in portraits:
        try:
            portrait_id = portrait["id"]
            image_path = portrait.get("image_path")
            
            if not image_path or not Path(image_path).exists():
                logger.warning(f"Image file not found for portrait {portrait_id}: {image_path}")
                continue
            
            # Читаем оригинальное изображение
            with open(image_path, "rb") as f:
                image_content = f.read()
            
            # Генерируем новое превью
            new_preview = PreviewGenerator.generate_image_preview(
                image_content, 
                size=(300, 300), 
                format='webp'
            )
            
            if new_preview:
                # Определяем путь для нового превью
                client_id = portrait["client_id"]
                preview_dir = storage_root / "portraits" / client_id
                preview_dir.mkdir(parents=True, exist_ok=True)
                
                new_preview_path = preview_dir / f"{portrait_id}_preview.webp"
                
                # Сохраняем новое превью
                with open(new_preview_path, "wb") as f:
                    f.write(new_preview)
                
                # Обновляем путь в базе данных
                database.update_portrait_preview(portrait_id, str(new_preview_path))
                
                # Удаляем старое превью если существует
                old_preview_path = portrait.get("image_preview_path")
                if old_preview_path and Path(old_preview_path).exists():
                    os.remove(old_preview_path)
                
                logger.info(f"Regenerated preview for portrait {portrait_id}")
            else:
                logger.error(f"Failed to generate preview for portrait {portrait_id}")
                
        except Exception as e:
            logger.error(f"Error regenerating preview for portrait {portrait.get('id')}: {e}")
    
    # Регенерируем превью видео
    videos = []
    for portrait in portraits:
        portrait_videos = database.list_videos(portrait["id"])
        videos.extend(portrait_videos)
    
    logger.info(f"Found {len(videos)} videos to regenerate previews for")
    
    for video in videos:
        try:
            video_id = video["id"]
            video_path = video.get("video_path")
            
            if not video_path or not Path(video_path).exists():
                logger.warning(f"Video file not found for video {video_id}: {video_path}")
                continue
            
            # Читаем оригинальное видео
            with open(video_path, "rb") as f:
                video_content = f.read()
            
            # Генерируем новое превью
            new_preview = PreviewGenerator.generate_video_preview(
                video_content, 
                size=(300, 300), 
                format='webp'
            )
            
            if new_preview:
                # Определяем путь для нового превью
                portrait_id = video["portrait_id"]
                portrait_info = database.get_portrait(portrait_id)
                client_id = portrait_info["client_id"] if portrait_info else "unknown"
                
                preview_dir = storage_root / "portraits" / client_id / portrait_id
                preview_dir.mkdir(parents=True, exist_ok=True)
                
                new_preview_path = preview_dir / f"{video_id}_preview.webp"
                
                # Сохраняем новое превью
                with open(new_preview_path, "wb") as f:
                    f.write(new_preview)
                
                # Обновляем путь в базе данных
                database.update_video_preview(video_id, str(new_preview_path))
                
                # Удаляем старое превью если существует
                old_preview_path = video.get("video_preview_path")
                if old_preview_path and Path(old_preview_path).exists():
                    os.remove(old_preview_path)
                
                logger.info(f"Regenerated preview for video {video_id}")
            else:
                logger.error(f"Failed to generate preview for video {video_id}")
                
        except Exception as e:
            logger.error(f"Error regenerating preview for video {video.get('id')}: {e}")
    
    logger.info("Preview regeneration completed")

if __name__ == "__main__":
    regenerate_previews()