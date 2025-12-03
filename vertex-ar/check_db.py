import sqlite3

# Connect to database
conn = sqlite3.connect('app_data.db')
cursor = conn.cursor()

# Check portraits
cursor.execute('SELECT id, image_path, image_preview_path FROM portraits')
portraits = cursor.fetchall()
print('Portraits:')
for portrait in portraits:
    print(f'  ID: {portrait[0]}')
    print(f'    Image: {portrait[1]}')
    print(f'    Preview: {portrait[2]}')

# Check videos
cursor.execute('SELECT id, video_path, video_preview_path FROM videos')
videos = cursor.fetchall()
print('\nVideos:')
for video in videos:
    print(f'  ID: {video[0]}')
    print(f'    Video: {video[1]}')
    print(f'    Preview: {video[2]}')

conn.close()
