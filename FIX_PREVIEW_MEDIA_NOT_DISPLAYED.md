# Fix: Preview Media Not Displayed in Admin

## Problem
Preview images and videos were created in the storage directory but were not displayed in the admin panel at `/admin/orders`.

## Root Causes
1. **Missing Video Preview in API Response**: The `/portraits/admin/list-with-preview` endpoint only returned image preview data but not video preview data
2. **Missing Video Preview Display**: The admin template did not display video preview images even though the code was partially prepared for it

## Solution Implemented

### 1. Updated API Endpoint (portraits.py)
**File**: `vertex-ar/app/api/portraits.py`

Modified the `/admin/list-with-preview` endpoint to:
- Read video preview file paths from the database for each video
- Load video preview files from disk and encode to base64
- Include preview data in the API response for each video object
- Added comprehensive logging for debugging file access and encoding

**Key Changes**:
```python
videos_with_previews = []
for v in videos:
    video_preview_data = None
    video_preview_path = v.get("video_preview_path")
    if video_preview_path:
        try:
            preview_path = Path(video_preview_path)
            if preview_path.exists():
                with open(preview_path, "rb") as f:
                    video_preview_data = base64.b64encode(f.read()).decode()
        except Exception as e:
            logger.warning(f"Failed to read video preview: {e}")
    
    videos_with_previews.append({
        "id": v["id"],
        "is_active": bool(v["is_active"]),
        "created_at": v.get("created_at"),
        "preview": video_preview_data or ""
    })
```

### 2. Updated Admin Template (admin_orders.html)
**File**: `vertex-ar/templates/admin_orders.html`

Enhanced the video display section to:
- Show video preview images inline with video information
- Display video status (active/inactive) and preview image
- Show placeholder when preview is unavailable
- Improved layout with flexbox for better alignment

**Key Changes**:
```html
<div class="video-item ${v.is_active ? 'active' : ''}" style="flex-direction: column; align-items: flex-start; gap: 8px;">
    <div style="display: flex; justify-content: space-between; width: 100%; align-items: center;">
        <span>Видео #${i + 1}</span>
        <span>${v.is_active ? '✅' : '⭕'}</span>
    </div>
    ${v.preview ? `<img src="data:image/jpeg;base64,${v.preview}" alt="Video Preview" style="width: 100%; height: auto; border-radius: 3px; max-height: 100px;">` : '<div style="width: 100%; height: 60px; background: #e0e0e0; border-radius: 3px; display: flex; align-items: center; justify-content: center; font-size: 11px; color: #999;">Нет превью</div>'}
</div>
```

### 3. Enhanced Logging (orders.py)
**File**: `vertex-ar/app/api/orders.py`

Added detailed logging when creating previews:
- Logs success when portrait preview is created (includes path and file size)
- Logs success when video preview is created (includes path and file size)
- Logs warnings when preview generation returns None
- Maintains error logging for failed preview generation

## Data Flow

### Storage
```
storage/
└── portraits/
    └── {client_id}/
        └── {portrait_id}/
            ├── {portrait_id}.jpg                 (original portrait image)
            ├── {portrait_id}_preview.jpg         (120x120 portrait preview)
            ├── {video_id}.mp4                    (original video)
            └── {video_id}_preview.jpg            (video frame thumbnail)
```

### Database
```
portraits table:
  - id
  - image_preview_path  → Points to {portrait_id}_preview.jpg

videos table:
  - id
  - video_preview_path  → Points to {video_id}_preview.jpg
```

### API Response
```json
{
  "id": "portrait-123",
  "client_id": "client-456",
  "preview": "base64_encoded_image_data",
  "videos": [
    {
      "id": "video-789",
      "is_active": true,
      "preview": "base64_encoded_video_preview_data"
    }
  ]
}
```

### Admin Display
- Portrait preview shown as inline image with fallback placeholder
- Video preview shown as inline image with fallback gray placeholder
- Video status (active/inactive) displayed with emoji indicators

## Error Handling
- **Missing preview file**: Logs warning, shows placeholder
- **Failed file read**: Logs exception, shows placeholder
- **Invalid video**: Uses PreviewGenerator stub (play button on dark background)
- **No database path**: Shows placeholder without errors

## Testing
The fix includes:
- Comprehensive logging for debugging
- Base64 encoding test verification
- Structure validation for API responses
- Fallback mechanisms for all error cases

## Files Modified
1. `vertex-ar/app/api/orders.py` - Added preview creation logging
2. `vertex-ar/app/api/portraits.py` - Added video preview loading logic
3. `vertex-ar/templates/admin_orders.html` - Added video preview display

## Status
✅ Complete - Preview images and videos now display correctly in the admin panel
