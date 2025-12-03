#!/usr/bin/env python3
"""
Script to fix path separators in the database.
This script converts backslashes to forward slashes in stored paths.
"""

import sqlite3
from pathlib import Path
import sys

def fix_database_paths(db_path='app_data.db'):
    """Fix path separators in the database."""
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fix paths in portraits table
    print("Fixing paths in portraits table...")
    cursor.execute("SELECT id, image_path, image_preview_path, marker_fset, marker_fset3, marker_iset FROM portraits")
    portraits = cursor.fetchall()

    updated_portraits = 0
    for portrait in portraits:
        portrait_id, image_path, image_preview_path, marker_fset, marker_fset3, marker_iset = portrait

        # Fix each path field
        updates = {}
        if image_path and '\\' in image_path:
            updates['image_path'] = image_path.replace('\\', '/')
        if image_preview_path and '\\' in image_preview_path:
            updates['image_preview_path'] = image_preview_path.replace('\\', '/')
        if marker_fset and '\\' in marker_fset:
            updates['marker_fset'] = marker_fset.replace('\\', '/')
        if marker_fset3 and '\\' in marker_fset3:
            updates['marker_fset3'] = marker_fset3.replace('\\', '/')
        if marker_iset and '\\' in marker_iset:
            updates['marker_iset'] = marker_iset.replace('\\', '/')

        # Update if any paths were fixed
        if updates:
            update_query = ", ".join([f"{key} = ?" for key in updates.keys()])
            update_values = list(updates.values()) + [portrait_id]
            cursor.execute(f"UPDATE portraits SET {update_query} WHERE id = ?", update_values)
            updated_portraits += 1
            print(f"  Updated portrait {portrait_id}")

    print(f"Fixed {updated_portraits} portraits")

    # Fix paths in videos table
    print("Fixing paths in videos table...")
    cursor.execute("SELECT id, video_path, video_preview_path FROM videos")
    videos = cursor.fetchall()

    updated_videos = 0
    for video in videos:
        video_id, video_path, video_preview_path = video

        # Fix each path field
        updates = {}
        if video_path and '\\' in video_path:
            updates['video_path'] = video_path.replace('\\', '/')
        if video_preview_path and '\\' in video_preview_path:
            updates['video_preview_path'] = video_preview_path.replace('\\', '/')

        # Update if any paths were fixed
        if updates:
            update_query = ", ".join([f"{key} = ?" for key in updates.keys()])
            update_values = list(updates.values()) + [video_id]
            cursor.execute(f"UPDATE videos SET {update_query} WHERE id = ?", update_values)
            updated_videos += 1
            print(f"  Updated video {video_id}")

    print(f"Fixed {updated_videos} videos")

    # Commit changes
    conn.commit()
    conn.close()

    print("Path fixing completed!")

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'app_data.db'
    print(f"Fixing paths in database: {db_path}")
    fix_database_paths(db_path)
