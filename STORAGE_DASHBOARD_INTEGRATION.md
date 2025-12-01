# Storage Dashboard JavaScript Integration

## Summary

Extended `static/js/admin-dashboard.js` to manage storage-related state and integrate with backend storage API endpoints for comprehensive storage folder management in the admin dashboard.

## Changes Made

### 1. State Management Extension

Added new storage-related state properties to `AdminDashboard.state`:

```javascript
storageConfig: null,        // Current company storage configuration
storageFolders: [],         // List of storage folders
storageLoading: false       // Loading state for storage operations
```

### 2. New Functions Implemented

#### `loadCompanyStorageConfig(companyId)`
- Loads storage configuration for a specific company
- Calls `/api/companies/{company_id}/storage-info` endpoint
- Updates state with storage type, status, and configuration details
- Updates UI elements (storage type indicator, status, folder path)
- Handles errors gracefully with toast notifications

#### `updateStorageConfigDisplay(config)`
- Updates UI elements with storage configuration data
- Sets storage type indicator (`storageTypeIndicator`)
- Updates storage status message (`storageStatus`)
- Displays folder path if available (`storageFolderPath`)

#### `loadStorageFolders(companyId)`
- Loads list of folders for current company's storage
- Checks storage type and delegates to appropriate loader
- For local storage: sets empty folder list
- For Yandex Disk: calls `loadYandexDiskFolders()`
- For other types: logs message and sets empty list

#### `loadYandexDiskFolders(companyId)`
- Specifically loads folders from Yandex Disk
- Calls `/api/yandex-disk/folders?company_id={id}` endpoint
- Updates state and UI with folder list
- Handles pagination via API response (`items`, `total`, `has_more`)
- Shows toast notifications for errors

#### `updateStorageFoldersList(folders)`
- Renders folder list in the UI
- Creates folder items with name, path, and delete button
- Shows empty state when no folders exist
- Uses emoji icons for visual clarity (📁)

#### `validateFolderName(folderName)`
- Client-side validation for folder names
- Pattern: `/^[a-zA-Z0-9_-]+$/`
- Only allows letters, digits, dash, and underscore

#### `createStorageFolder()`
- Creates a new storage folder
- Validates folder name on client-side
- Implements optimistic UI updates (shows folder immediately)
- Calls `/api/companies/{company_id}/storage-folder` (POST) for local storage
- Shows warning for remote storage types (manual creation required)
- Reverts optimistic update on error
- Reloads folders and config after successful creation
- Toast notifications for success/error states

#### `deleteStorageFolder(folderPath)`
- Deletes a storage folder
- Shows confirmation dialog
- Implements optimistic UI updates
- For local/Yandex storage: shows warning about manual deletion
- Handles permission and non-empty folder errors gracefully
- Reverts optimistic update on error
- Reloads folders and config after operation

### 3. Integration Points

#### In `loadCompanyConfig(companyId)`
Added calls to:
- `await loadCompanyStorageConfig(companyId)`
- `await loadStorageFolders(companyId)`

This ensures storage config loads when:
- Dashboard initializes
- User switches companies
- Company config is refreshed

#### In `refreshData()`
Added storage refresh logic:
```javascript
const currentCompanyId = AdminDashboard.state.currentCompany?.id;
if (currentCompanyId) {
    loadCompanyStorageConfig(currentCompanyId);
    loadStorageFolders(currentCompanyId);
}
```

This ensures storage data refreshes during:
- Auto-refresh intervals (every 30 seconds)
- Manual refresh button clicks

#### In `initializeEventListeners()`
Added event listeners for storage folder input:
- Input validation (enable/disable button based on input)
- Enter key handler to trigger `createStorageFolder()`
- Pattern matching validation on input

### 4. UI Integration Points

The implementation expects these HTML elements (to be added in template):

```html
<!-- Storage Configuration Display -->
<div id="storageTypeIndicator"></div>
<div id="storageStatus"></div>
<div id="storageFolderPath"></div>

<!-- Storage Folder Management -->
<div id="storageFoldersList"></div>
<input type="text" id="newStorageFolderInput" />
<button id="addStorageFolderBtn" onclick="createStorageFolder()">Add Folder</button>
```

### 5. Features Implemented

✅ **Client-side validation**: Folder names validated against pattern before API call  
✅ **Optimistic UI updates**: Folders appear immediately, revert on error  
✅ **Toast notifications**: Success, error, and warning messages for all operations  
✅ **Error handling**: Graceful handling of permission and non-empty folder errors  
✅ **Loading states**: `storageLoading` flag prevents concurrent operations  
✅ **Auto-refresh**: Storage data refreshes with other dashboard data  
✅ **Company context**: All operations scoped to current company  
✅ **Storage type awareness**: Different behavior for local/remote storage  

### 6. API Endpoints Used

1. **GET** `/api/companies/{company_id}/storage-info`
   - Returns: storage_type, storage_folder_path, status_message, is_configured

2. **GET** `/api/yandex-disk/folders?company_id={id}`
   - Returns: items (array of folders), total, has_more

3. **POST** `/api/companies/{company_id}/storage-folder`
   - Body: `{ folder_path: string }`
   - Creates folder for local storage

### 7. Error Handling

The implementation handles:
- Network errors (fetch failures)
- HTTP errors (4xx, 5xx responses)
- Permission errors (403 responses)
- Non-empty folder errors (specific message detection)
- Missing company ID (validation)
- Invalid folder names (client-side validation)

All errors show user-friendly toast messages and log details to console.

### 8. Validation Rules

**Folder Name Validation:**
- Required: not empty
- Pattern: `^[a-zA-Z0-9_-]+$`
- Error message: "Название папки может содержать только буквы, цифры, дефис и подчёркивание"

### 9. State Persistence

Storage state is **not** persisted to localStorage (unlike theme/page state) because:
- Storage config can change server-side
- Folders list should always reflect current backend state
- Reduces stale data issues

### 10. Future Enhancements

Potential improvements for future tickets:
- MinIO folder creation/deletion support
- Folder search/filter functionality
- Folder size/usage statistics
- Drag-and-drop folder reorganization
- Bulk folder operations
- Folder permissions management

## Testing Checklist

- [x] No JavaScript syntax errors (verified with `node -c`)
- [ ] Functions are called on page load
- [ ] Functions are called on company switch
- [ ] Functions are called on auto-refresh
- [ ] Create folder validates input
- [ ] Create folder shows optimistic UI update
- [ ] Create folder reverts on error
- [ ] Delete folder shows confirmation
- [ ] Delete folder handles permission errors
- [ ] Delete folder handles non-empty errors
- [ ] Toast notifications appear for all operations
- [ ] Event listeners wire correctly to UI elements

## Files Modified

- `vertex-ar/static/js/admin-dashboard.js` (~300 lines added)
  - Added state properties
  - Added 9 new functions
  - Updated 3 existing functions
  - Added event listeners

## Related Documentation

- Backend API: `vertex-ar/app/api/companies.py` (storage endpoints)
- Backend API: `vertex-ar/app/api/yandex_disk.py` (Yandex folder endpoints)
- Storage config: `vertex-ar/app/api/storage_config.py`
- Memory notes: YANDEX DISK ORDER STORAGE, YANDEX DISK FOLDERS & CONTENT TYPES API

## Notes

- Local storage folder creation uses filesystem operations (actual folder created on disk)
- Remote storage (Yandex, MinIO) currently requires manual folder creation in storage interface
- Folder deletion for remote storage also requires manual operation (by design for safety)
- All storage operations are scoped to the current company context
- Storage config automatically refreshes when switching companies or during auto-refresh
