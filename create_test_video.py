#!/usr/bin/env python3
"""
Создание тестового видеофайла для проверки генерации превью
"""
import cv2
import numpy as np
import sys
from pathlib import Path

def create_test_video(output_path="test_video.mp4", duration=5, fps=30):
    """Создает тестовое видео с изменяющимися кадрами"""
    
    # Параметры видео
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    total_frames = duration * fps
    print(f"Создание видео: {duration} секунд, {fps} FPS, всего {total_frames} кадров")
    
    for i in range(total_frames):
        # Создаем кадр с изменяющимся цветом
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Изменяем цвет от синего к красному
        progress = i / total_frames
        blue = int(255 * (1 - progress))
        red = int(255 * progress)
        green = int(128 * (0.5 + 0.5 * np.sin(2 * np.pi * progress)))
        
        # Заполняем фон
        frame[:, :] = [blue, green, red]
        
        # Добавляем номер кадра
        cv2.putText(frame, f"Frame {i+1}/{total_frames}", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Добавляем временной код
        seconds = i / fps
        cv2.putText(frame, f"Time: {seconds:.2f}s", (50, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Добавляем движущийся круг
        center_x = int(width * (0.2 + 0.6 * progress))
        center_y = int(height * 0.7)
        cv2.circle(frame, (center_x, center_y), 30, (255, 255, 0), -1)
        
        out.write(frame)
        
        if (i + 1) % fps == 0:
            print(f"Создано {i+1}/{total_frames} кадров...")
    
    out.release()
    print(f"Видео сохранено: {output_path}")
    return output_path

if __name__ == "__main__":
    video_path = create_test_video()
    print(f"Тестовое видео создано: {video_path}")
    
    # Проверяем размер файла
    file_size = Path(video_path).stat().st_size
    print(f"Размер файла: {file_size} байт")
