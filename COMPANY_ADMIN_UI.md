# Company Admin UI - Implementation Guide

## Overview

A comprehensive admin interface for managing companies with integrated storage, folder management, content types, and backup configuration workflows.

## Features Implemented

### 1. Dedicated Companies Page (`/admin/companies`)
- **Template**: `templates/admin_companies.html`
- **JavaScript Module**: `static/js/admin-companies.js`
- **Route**: Added to `app/api/admin.py` as `/admin/companies`

### 2. Company Management Features

#### Company List Table
- Displays all companies with key information:
  - Company name with DEFAULT badge for default company
  - Storage type (LOCAL, LOCAL DISK, YANDEX, S3) with color-coded badges
  - Folder path (storage/yandex disk folder)
  - Client count
  - Content types count
  - Backup status with visual indicators
  - Creation date
- Action buttons for each company:
  - **Edit**: Modify company settings
  - **Backup**: Configure remote backup provider
  - **Delete**: Remove company (disabled for default company)

#### Create Company Workflow
Guided multi-step workflow ensuring proper configuration:

1. **Company Details**
   - Name (required, unique)
   - Storage type selection

2. **Storage Selection**
   - For remote storage (Yandex Disk):
     - Select from active, tested storage connections
     - Link to create new connection if none available
   - For local storage:
     - Automatically configured

3. **Folder Selection**
   - **Browse existing folders**: Lists folders from storage
   - **Create new folder**: Input field with validation
   - Shows current path for Yandex Disk navigation
   - Validates folder selection before proceeding

4. **Content Types Management**
   - Add/remove content type categories
   - Automatic slug generation from labels
   - Validation (minimum 1 content type required)
   - Default: "Portraits"

5. **Save and Verify**
   - Validation of all required fields
   - Storage connection testing
   - Folder existence verification
   - Toast notifications for success/errors

#### Edit Company
- Pre-populated form with current company data
- Cannot change company name or storage type (data integrity)
- Can update:
  - Storage connection
  - Folder path
  - Content types

#### Delete Company Protection
- Default company (`vertex-ar-default`) cannot be deleted
- Confirmation dialog warns about cascade deletion:
  - All clients
  - All portraits
  - All related data
- Server-side validation prevents default company deletion

### 3. Backup Configuration

#### Per-Company Backup Settings Modal
- **Provider Selection**:
  - None (disabled)
  - Local storage
  - Yandex Disk
  - Google Drive (if configured)
- **Remote Path**: Custom path for backups in remote storage
- **Status Indicator**: Visual feedback on backup configuration state
  - 🔴 Red: Not configured
  - 🟢 Green: Configured with provider name

#### Integration with Backend
- GET `/api/remote-storage/companies/{id}/backup-config`
- POST `/api/remote-storage/companies/{id}/backup-config`
- Providers list: GET `/api/remote-storage/providers`

### 4. Statistics Dashboard
Real-time statistics displayed as cards:
- **Total Companies**: Count of all companies
- **Total Clients**: Aggregate client count
- **Total Portraits**: Aggregate portrait count
- **Storage Connections**: Count of configured storage connections

### 5. UI/UX Features

#### Theme Support
- Dark mode (default)
- Light mode
- Theme toggle button
- Persistent theme selection (localStorage)
- CSS variables for consistent theming

#### Loading States
- Full-screen loading overlay with spinner
- Progress messages for long operations
- Disabled buttons during API calls

#### Toast Notifications
- Success ✅
- Error ❌
- Warning ⚠️
- Info ℹ️
- Auto-dismiss after 4 seconds
- Stacked for multiple notifications

#### Empty States
- Friendly messages when no data exists
- Call-to-action buttons (e.g., "Create first company")
- Icons for visual appeal

#### Responsive Design
- Mobile-optimized layout
- Collapsible navigation
- Flexible grid system
- Touch-friendly buttons

### 6. Modal Workflows

#### Company Modal
- Create/Edit company form
- Dynamic field visibility based on storage type
- Inline validation
- Close on ESC key or X button

#### Folder Selection Modal
- Browse folder tree
- Create new folders inline
- Current path display
- Confirm selection workflow

#### Backup Configuration Modal
- Provider dropdown
- Path input with validation
- Save/Cancel actions

### 7. Navigation Integration

Updated all admin pages with Companies tab:
- `/admin` (Dashboard) - updated ✅
- `/admin/companies` (NEW) - active when on page ✅
- `/admin/clients` - updated ✅
- `/admin/schedule` - updated ✅
- `/admin/storage` - updated ✅
- `/admin/backups` - updated ✅
- `/admin/notifications` - updated ✅
- `/admin/settings` - updated ✅

## API Endpoints Used

### Companies
- `GET /api/companies` - List all companies with pagination
- `POST /api/companies` - Create new company
- `GET /api/companies/{id}` - Get company details
- `DELETE /api/companies/{id}` - Delete company
- `POST /api/companies/{id}/select` - Switch active company
- `POST /api/companies/{id}/yandex-disk-folder` - Set Yandex folder
- `POST /api/companies/{id}/content-types` - Update content types

### Storage
- `GET /api/storage/connections` - List storage connections
- `GET /api/yandex-disk/folders` - Browse Yandex Disk folders

### Backup
- `GET /api/remote-storage/providers` - List available backup providers
- `GET /api/remote-storage/companies/{id}/backup-config` - Get backup config
- `POST /api/remote-storage/companies/{id}/backup-config` - Update backup config

### Statistics
- `GET /admin/stats` - Get dashboard statistics

## State Management

### CompanyManager.state
```javascript
{
    companies: [],              // All companies
    storageConnections: [],     // Available storage connections
    currentCompany: null,       // Company being edited
    currentFolders: [],         // Folders in current path
    currentPath: '/',           // Current folder path
    selectedFolder: null,       // Selected folder for company
    contentTypes: [],           // Content types being configured
    backupProviders: [],        // Available backup providers
    isLoading: false            // Loading state flag
}
```

## Validation Rules

### Company Creation
- **Name**: Required, must be unique
- **Storage Type**: Required, one of: local, local_disk, yandex_disk
- **Storage Connection**: Required for remote storage types
- **Folder Path**: Optional but recommended
- **Content Types**: Optional, defaults to [{ label: 'Portraits', slug: 'portraits' }]

### Company Deletion
- Cannot delete default company
- Requires confirmation
- Shows warning about cascading deletions

### Backup Configuration
- Provider: Optional
- Remote Path: Optional (auto-generated if not provided)

## Error Handling

### Network Errors
- Graceful degradation with user-friendly messages
- Retry suggestions for transient failures
- Detailed error logging to console

### Validation Errors
- Inline field validation
- Toast notifications for form errors
- Server-side validation feedback

### Permission Errors
- Redirect to login if session expired
- 403 Forbidden handled with appropriate messaging

## Testing Recommendations

### Manual Testing Scenarios

1. **Create Company - Happy Path**
   - Navigate to /admin/companies
   - Click "Create Company"
   - Fill name, select storage type
   - Select storage connection (for remote)
   - Browse and select folder
   - Add/edit content types
   - Save
   - Verify company appears in table

2. **Create Company - Validation**
   - Try to submit without name → Error
   - Try to submit Yandex storage without connection → Error
   - Try to save with empty content types list → Warning

3. **Edit Company**
   - Click Edit on existing company
   - Modify folder path
   - Add new content type
   - Save
   - Verify changes reflected

4. **Delete Company - Protection**
   - Try to delete default company → Button disabled
   - Delete non-default company → Confirmation dialog
   - Confirm deletion → Company removed

5. **Backup Configuration**
   - Click Backup button
   - Select provider
   - Enter remote path
   - Save
   - Verify green status indicator

6. **Folder Workflow**
   - Create company with Yandex storage
   - Click "Select Folder"
   - Browse folders
   - Create new folder
   - Select folder
   - Verify path populated

7. **Theme Toggle**
   - Toggle between dark/light mode
   - Verify all colors adjust appropriately
   - Refresh page → Theme persists

8. **Responsive Design**
   - Test on mobile viewport (< 768px)
   - Verify navigation collapses
   - Check table scrolls horizontally
   - Verify modals fit screen

### Integration Testing

```python
# Test company creation workflow
async def test_create_company_full_workflow():
    # Create storage connection
    connection = await create_storage_connection("yandex_test")
    
    # Create company
    company = await create_company({
        "name": "Test Company",
        "storage_type": "yandex_disk",
        "storage_connection_id": connection["id"],
        "yandex_disk_folder_id": "/test_folder",
        "content_types": [
            {"label": "Portraits", "slug": "portraits"},
            {"label": "Certificates", "slug": "certificates"}
        ]
    })
    
    assert company["id"]
    assert company["name"] == "Test Company"
    
    # Configure backup
    backup = await set_backup_config(company["id"], {
        "backup_provider": "yandex_disk",
        "backup_remote_path": "/backups/test_company"
    })
    
    assert backup["backup_provider"] == "yandex_disk"
    
    # Verify company in list
    companies = await list_companies()
    assert any(c["id"] == company["id"] for c in companies["items"])
    
    # Clean up
    await delete_company(company["id"])
```

### Smoke Test Script

```bash
#!/bin/bash
# smoke_test_companies_ui.sh

echo "Starting Companies UI smoke test..."

# 1. Check page loads
echo "Test 1: Page loads"
curl -f http://localhost:8000/admin/companies > /dev/null
if [ $? -eq 0 ]; then
    echo "✓ Companies page loads"
else
    echo "✗ Companies page failed to load"
    exit 1
fi

# 2. Check API endpoints
echo "Test 2: API endpoints"
curl -f http://localhost:8000/api/companies > /dev/null
if [ $? -eq 0 ]; then
    echo "✓ Companies API responds"
else
    echo "✗ Companies API failed"
    exit 1
fi

# 3. Check JavaScript loads
echo "Test 3: JavaScript module"
curl -f http://localhost:8000/static/js/admin-companies.js > /dev/null
if [ $? -eq 0 ]; then
    echo "✓ JavaScript module loads"
else
    echo "✗ JavaScript module failed to load"
    exit 1
fi

echo "All smoke tests passed!"
```

## Performance Considerations

- **Lazy Loading**: Companies loaded on page mount, not on tab switch
- **Debouncing**: Search/filter inputs debounced 300ms
- **Optimistic UI**: Folder selection updates UI before API confirmation
- **Caching**: Theme and state stored in localStorage
- **Pagination**: Large company lists paginated (future enhancement)

## Security Considerations

- **Authentication**: All endpoints require admin session
- **Authorization**: Server-side validation of company ownership
- **Input Sanitization**: All user inputs validated and escaped
- **CSRF Protection**: Cookie-based auth with SameSite
- **Default Company Protection**: Hardcoded ID check in backend and frontend

## Future Enhancements

1. **Search and Filtering**
   - Search companies by name
   - Filter by storage type
   - Filter by backup status

2. **Bulk Operations**
   - Multi-select companies
   - Bulk backup configuration
   - Bulk content type updates

3. **Company Statistics**
   - Per-company dashboard
   - Storage usage charts
   - Activity timeline

4. **Advanced Folder Management**
   - Create nested folders
   - Move folders
   - Delete empty folders
   - Folder permissions

5. **Audit Trail**
   - Company creation/modification log
   - User action tracking
   - Change history with rollback

6. **Import/Export**
   - Export company configuration as JSON
   - Import companies from CSV
   - Clone company settings

## Files Modified/Created

### Created
- `templates/admin_companies.html` (1000+ lines)
- `static/js/admin-companies.js` (800+ lines)

### Modified
- `app/api/admin.py` (+13 lines) - Added `/companies` route
- `templates/admin_dashboard.html` (Navigation update)
- `templates/admin_clients.html` (Navigation update)
- `templates/admin_backups.html` (Navigation update)
- `templates/admin_storage.html` (Navigation update)
- `templates/admin_notifications.html` (Navigation update)
- `templates/admin_settings.html` (Navigation update)
- `templates/admin_video_schedule.html` (Navigation update)

### Dependencies
None - uses existing libraries and frameworks

## Deployment Checklist

- [ ] Verify all admin pages have Companies tab
- [ ] Test company creation workflow end-to-end
- [ ] Test company deletion protection
- [ ] Verify backup configuration works
- [ ] Test folder selection for Yandex Disk
- [ ] Validate responsive design on mobile
- [ ] Check theme toggle persistence
- [ ] Test with multiple storage connections
- [ ] Verify default company cannot be deleted
- [ ] Check toast notifications appear correctly
- [ ] Test empty states render properly
- [ ] Validate all modals open/close correctly
- [ ] Check navigation between admin pages
- [ ] Test with existing companies in database
- [ ] Verify statistics update after company changes

## Summary

This implementation provides a comprehensive, user-friendly interface for company management that integrates seamlessly with the existing Vertex AR admin system. It follows established patterns for UI/UX, state management, and API integration while adding significant value through guided workflows, validation, and error handling. The modular JavaScript architecture allows for easy maintenance and future enhancements.
