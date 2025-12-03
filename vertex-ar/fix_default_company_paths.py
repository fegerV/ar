#!/usr/bin/env python3
"""
Script to fix existing database paths for the default company.
This script updates paths in the database to use the new simplified structure
without the redundant 'vertex-ar-default' segment and with the shortened folder name.
"""

import sqlite3
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

def fix_database_paths(db_path='app_data.db'):
    """Fix path separators and structure in the database for the default company."""
    print(f"Fixing database paths in {db_path}...")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Fix paths in portraits table
        print("Updating portraits table...")
        cursor.execute("SELECT id, image_path FROM portraits")
        portraits = cursor.fetchall()

        updated_portraits = 0
        for portrait_id, image_path in portraits:
            if image_path:
                new_path = image_path
                # Remove the redundant vertex-ar-default segment
                # Convert: vertex_ar_content/vertex-ar-default/portraits/...
                # To:      content/portraits/...
                new_path = new_path.replace('vertex_ar_content/vertex-ar-default/', 'content/')
                # Also handle cases where vertex-ar-default might not be present
                new_path = new_path.replace('vertex_ar_content/', 'content/')

                if new_path != image_path:
                    cursor.execute(
                        "UPDATE portraits SET image_path = ? WHERE id = ?",
                        (new_path, portrait_id)
                    )
                    updated_portraits += 1
                    print(f"  Updated portrait {portrait_id}: {image_path} -> {new_path}")

        print(f"Updated {updated_portraits} portraits")

        # Fix paths in videos table
        print("Updating videos table...")
        cursor.execute("SELECT id, video_path FROM videos")
        videos = cursor.fetchall()

        updated_videos = 0
        for video_id, video_path in videos:
            if video_path:
                new_path = video_path
                # Remove the redundant vertex-ar-default segment
                new_path = new_path.replace('vertex_ar_content/vertex-ar-default/', 'content/')
                # Also handle cases where vertex-ar-default might not be present
                new_path = new_path.replace('vertex_ar_content/', 'content/')

                if new_path != video_path:
                    cursor.execute(
                        "UPDATE videos SET video_path = ? WHERE id = ?",
                        (new_path, video_id)
                    )
                    updated_videos += 1
                    print(f"  Updated video {video_id}: {video_path} -> {new_path}")

        print(f"Updated {updated_videos} videos")

        # Commit changes
        conn.commit()
        print("Database update completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"Error updating database: {e}")
        raise
    finally:
        conn.close()

def check_database_paths(db_path='app_data.db'):
    """Check current database paths for the default company."""
    print(f"Checking database paths in {db_path}...")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check portraits table
        print("\nPortraits with vertex-ar-default in path:")
        cursor.execute("SELECT id, image_path FROM portraits WHERE image_path LIKE '%vertex-ar-default%'")
        portraits = cursor.fetchall()

        for portrait_id, image_path in portraits:
            print(f"  Portrait {portrait_id}: {image_path}")

        print(f"Found {len(portraits)} portraits with redundant path segments")

        # Check videos table
        print("\nVideos with vertex-ar-default in path:")
        cursor.execute("SELECT id, video_path FROM videos WHERE video_path LIKE '%vertex-ar-default%'")
        videos = cursor.fetchall()

        for video_id, video_path in videos:
            print(f"  Video {video_id}: {video_path}")

        print(f"Found {len(videos)} videos with redundant path segments")

        # Also check for old vertex_ar_content paths
        print("\nEntries with old vertex_ar_content paths:")
        cursor.execute("SELECT id, image_path FROM portraits WHERE image_path LIKE '%vertex_ar_content%'")
        portraits_old = cursor.fetchall()

        for portrait_id, image_path in portraits_old:
            print(f"  Portrait {portrait_id}: {image_path}")

        cursor.execute("SELECT id, video_path FROM videos WHERE video_path LIKE '%vertex_ar_content%'")
        videos_old = cursor.fetchall()

        for video_id, video_path in videos_old:
            print(f"  Video {video_id}: {video_path}")

        total_old = len(portraits_old) + len(videos_old)
        print(f"Found {total_old} entries with old path structure")

    except Exception as e:
        print(f"Error checking database: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    db_path = 'app_data.db'
    if len(sys.argv) > 1:
        db_path = sys.argv[1]

    # First check what needs to be fixed
    check_database_paths(db_path)

    # Ask for confirmation before making changes
    response = input("\nDo you want to fix these paths? (y/N): ")
    if response.lower() in ['y', 'yes']:
        fix_database_paths(db_path)
    else:
        print("Operation cancelled.")
