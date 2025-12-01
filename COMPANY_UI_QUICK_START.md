# Company Admin UI - Quick Start Guide

## 🚀 What Was Built

A comprehensive company management interface at `/admin/companies` that provides:
- **Visual company list** with storage types, folder paths, client counts, and backup status
- **Guided workflows** for creating companies with storage selection and folder management
- **Content type management** for organizing portrait categories
- **Backup configuration** per company
- **Protection** against deleting the default company
- **Responsive design** that works on desktop and mobile

## 📋 Files Created/Modified

### New Files
```
templates/admin_companies.html          (32KB, 1000+ lines)
static/js/admin-companies.js            (31KB, 800+ lines)
COMPANY_ADMIN_UI.md                     (Comprehensive documentation)
COMPANY_UI_MANUAL_TEST_SCENARIOS.md     (20 test scenarios)
COMPANY_UI_QUICK_START.md               (This file)
```

### Modified Files
```
app/api/admin.py                        (+13 lines for /companies route)
templates/admin_dashboard.html          (Navigation update)
templates/admin_clients.html            (Navigation update)
templates/admin_backups.html            (Navigation update)
templates/admin_storage.html            (Navigation update)
templates/admin_notifications.html      (Navigation update)
templates/admin_settings.html           (Navigation update)
templates/admin_video_schedule.html     (Navigation update)
```

## 🎯 Key Features

### 1. Create Company Workflow
```
Click "Create Company" 
  ↓
Enter name + select storage type
  ↓
[If Yandex] Select storage connection
  ↓
Select or create folder
  ↓
Configure content types
  ↓
Save → Company created ✅
```

### 2. Storage Type Support
- **Local Storage**: For files on server disk
- **Local Disk**: Alternative local storage option
- **Yandex Disk**: Cloud storage with folder browser

### 3. Backup Configuration
Each company can have independent backup settings:
- Provider selection (local, Yandex Disk, etc.)
- Custom remote path
- Visual status indicators (🔴 not configured, 🟢 configured)

### 4. Content Types
Flexible categorization system:
- Add/remove types (e.g., Portraits, Certificates, Diplomas)
- Auto-generated slugs from labels
- Minimum 1 type required

### 5. Default Company Protection
The system default company "Vertex AR" cannot be deleted to maintain data integrity.

## 🔗 API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/companies` | GET | List all companies |
| `/api/companies` | POST | Create company |
| `/api/companies/{id}` | GET | Get company details |
| `/api/companies/{id}` | DELETE | Delete company |
| `/api/companies/{id}/yandex-disk-folder` | POST | Set Yandex folder |
| `/api/companies/{id}/content-types` | POST | Update content types |
| `/api/storage/connections` | GET | List storage connections |
| `/api/yandex-disk/folders` | GET | Browse Yandex folders |
| `/api/remote-storage/providers` | GET | List backup providers |
| `/api/remote-storage/companies/{id}/backup-config` | GET/POST | Backup settings |

## 🎨 UI Components

### Modals
1. **Company Modal**: Create/edit company form with dynamic fields
2. **Folder Modal**: Browse and select storage folders
3. **Backup Modal**: Configure backup provider and path

### Tables
- Sortable columns (future enhancement)
- Action buttons per row
- Responsive horizontal scroll on mobile
- Empty states with helpful CTAs

### Notifications
- **Toast System**: Success ✅, Error ❌, Warning ⚠️, Info ℹ️
- Auto-dismiss after 4 seconds
- Stackable for multiple messages

### Theme Support
- Dark mode (default)
- Light mode
- Persistent across sessions
- Toggle via 🌙/☀️ button

## 🧪 Quick Smoke Test

```bash
# 1. Start the server
cd /home/engine/project/vertex-ar
python -m uvicorn app.main:app --reload

# 2. Open browser
open http://localhost:8000/admin

# 3. Login and navigate to Companies
# Click: 🏢 Компании

# 4. Verify:
✓ Page loads
✓ Statistics cards show
✓ Companies table displays
✓ "Create Company" button present

# 5. Create test company:
Name: "Test Company"
Storage: "Local Storage"
Folder: "/test"
Content Type: "Portraits" (default)

# 6. Verify company appears in table
# 7. Test backup configuration
# 8. Test deletion (should confirm)
```

## 🐛 Common Issues & Solutions

### Issue: Modal doesn't open
**Solution**: Check console for JS errors, ensure admin-companies.js loaded

### Issue: Storage connections dropdown empty
**Solution**: Navigate to /admin/storage and create a storage connection first

### Issue: Folder list doesn't load
**Solution**: Verify storage connection is active and tested

### Issue: Cannot delete company
**Solution**: Check if it's the default company (has DEFAULT badge)

### Issue: Theme doesn't persist
**Solution**: Check localStorage permissions in browser

### Issue: 401 Unauthorized errors
**Solution**: Session expired, log in again

## 📊 Statistics Card Values

The dashboard shows real-time statistics:
- **Total Companies**: Count from database
- **Total Clients**: Aggregate across all companies
- **Total Portraits**: Aggregate across all companies
- **Storage Connections**: Count of configured storage

Statistics update automatically after:
- Creating a company
- Deleting a company
- Creating a client (updates on next refresh)

## 🔒 Security Features

1. **Authentication Required**: All endpoints require admin session
2. **Authorization Checks**: Server validates admin role
3. **Default Company Protection**: Cannot delete system default
4. **Input Validation**: Client-side and server-side
5. **CSRF Protection**: Cookie-based auth with SameSite
6. **Sanitization**: All user inputs sanitized

## 🚦 Next Steps

After deployment:

1. **Test Basic Flow**:
   - Create company with local storage
   - Verify it appears in table
   - Edit and add content types
   - Delete (if not default)

2. **Test Yandex Integration**:
   - Configure Yandex storage connection in /admin/storage
   - Create company with Yandex storage
   - Browse and select folder
   - Verify files upload to correct location

3. **Configure Backups**:
   - For each company, click "Backup"
   - Select backup provider
   - Test backup sync (use /admin/backups page)

4. **Monitor Logs**:
   ```bash
   tail -f logs/app.log | grep -i company
   ```

5. **Check Performance**:
   - Open DevTools → Performance
   - Record page load and interactions
   - Verify no long tasks (>50ms)

## 📚 Documentation Links

- **Full Documentation**: `COMPANY_ADMIN_UI.md`
- **Test Scenarios**: `COMPANY_UI_MANUAL_TEST_SCENARIOS.md`
- **API Docs**: Check existing `app/api/companies.py` docstrings
- **Backend Config**: Refer to COMPANY_BACKUP_PROVIDERS.md

## 🤝 Integration with Existing Features

### Orders Workflow
When creating orders in `/admin`:
1. Select company from dropdown (now includes new companies)
2. Content type dropdown populated from company's configured types
3. Files uploaded to company's storage folder

### Clients Management
In `/admin/clients`:
- Company filter includes new companies
- Client creation auto-associates with selected company

### Storage Management
In `/admin/storage`:
- Storage connections used by companies shown
- Cannot delete connection in use by a company

### Backup System
In `/admin/backups`:
- Per-company backup configs reflected in backup operations
- Backup files organized by company ID

## 💡 Pro Tips

1. **Always configure storage first**: Create storage connections before companies
2. **Use descriptive folder paths**: e.g., `/companies/company-name/portraits`
3. **Organize content types**: Match your business workflow (e.g., separate certificates and diplomas)
4. **Set up backups early**: Configure backup provider when creating company
5. **Test with dummy data**: Create test company, upload test files, verify workflow before production
6. **Monitor statistics**: Watch for unexpected counts (may indicate data issues)
7. **Use theme that matches time of day**: Dark mode for evening/night work

## 🎓 Training Guide for Admins

### Beginner (First time user)
1. Watch company list populate on page load
2. Click through different admin pages to see navigation
3. Create one local storage company
4. Observe statistics update

### Intermediate (Regular use)
1. Create company with Yandex storage
2. Browse folders and select appropriate path
3. Configure 3+ content types
4. Set up backup configuration
5. Test creating order with new company

### Advanced (Power user)
1. Manage multiple companies with different storage types
2. Organize folder hierarchies for scalability
3. Implement backup rotation strategy
4. Monitor statistics for capacity planning
5. Integrate with external storage providers

## 📞 Support

If you encounter issues:
1. Check browser console for errors (F12 → Console)
2. Verify network requests (F12 → Network)
3. Review server logs for backend errors
4. Consult test scenarios document for expected behavior
5. File detailed bug report using template in test scenarios doc

## ✅ Deployment Checklist

Before going live:
- [ ] Run all 20 test scenarios from manual test doc
- [ ] Verify theme toggle works in all browsers
- [ ] Test on mobile device (not just DevTools emulation)
- [ ] Check all admin navigation links work
- [ ] Confirm default company cannot be deleted
- [ ] Validate storage connections are configured
- [ ] Test backup configuration end-to-end
- [ ] Verify statistics calculate correctly
- [ ] Check console for any warnings or errors
- [ ] Test with production data (not just test data)
- [ ] Ensure loading states appear during slow network
- [ ] Validate all toast notifications appear correctly
- [ ] Test concurrent user access (two browser windows)
- [ ] Verify API rate limiting doesn't block normal use
- [ ] Check error handling for network failures
- [ ] Confirm responsive design on all screen sizes

## 🎉 Success!

You now have a fully functional company management interface. The system is designed to be:
- **Intuitive**: Guided workflows with clear labels
- **Robust**: Validation and error handling at every step
- **Flexible**: Supports multiple storage types and configurations
- **Scalable**: Handles growth from few to many companies
- **Maintainable**: Clean code with comprehensive documentation

Enjoy managing your companies! 🏢✨
