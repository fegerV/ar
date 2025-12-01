# Company Admin UI - Manual Test Scenarios

## Prerequisites
- Access to admin panel with credentials
- At least one storage connection configured (for Yandex Disk testing)
- Browser with developer console open for debugging

## Test Scenario 1: Page Load and Navigation

### Steps:
1. Navigate to http://localhost:8000/admin
2. Log in with admin credentials
3. Verify navigation bar displays "🏢 Компании" tab
4. Click on "Компании" tab

### Expected Results:
- ✅ Page loads successfully
- ✅ Navigation tabs visible with "Компании" between "Dashboard" and "Клиенты"
- ✅ Four statistics cards displayed (Companies, Clients, Portraits, Storage Connections)
- ✅ Company list table visible
- ✅ "Create Company" and "Refresh" buttons present
- ✅ Theme toggle button works (dark ↔ light)
- ✅ No console errors

---

## Test Scenario 2: Create Company - Local Storage

### Steps:
1. Click "➕ Создать компанию" button
2. Enter company name: "Test Local Company"
3. Select storage type: "Локальное хранилище"
4. Verify storage connection dropdown is hidden
5. Click "📁 Выбрать папку" button
6. Enter folder path: "/test_company"
7. Add content type: "Certificates"
8. Click "Сохранить"

### Expected Results:
- ✅ Modal opens with form fields
- ✅ Storage connection field not shown for local storage
- ✅ Folder selection field appears
- ✅ Content types list shows default "Portraits"
- ✅ New content type added successfully
- ✅ Success toast: "Компания успешно создана"
- ✅ Modal closes
- ✅ Company appears in table with:
  - Name: "Test Local Company"
  - Storage type badge: "LOCAL"
  - Client count: 0
  - Content types: 2 типов
  - Backup status: Red indicator "Не настроено"
- ✅ Statistics updated (Total Companies +1)

---

## Test Scenario 3: Create Company - Yandex Disk (Full Workflow)

### Prerequisites:
- At least one active, tested Yandex Disk storage connection exists

### Steps:
1. Click "➕ Создать компанию"
2. Enter company name: "Test Yandex Company"
3. Select storage type: "Яндекс.Диск"
4. Verify storage connection dropdown appears
5. Select a Yandex Disk connection from dropdown
6. Click "📁 Выбрать папку"
7. In folder modal:
   - Verify folder list loads
   - Click on a folder to select it (should highlight)
   - OR create new folder:
     - Enter name: "vertex_ar_test"
     - Click "Создать"
   - Click "Выбрать" to confirm
8. Verify selected folder path appears in form
9. Remove default "Portraits" content type
10. Add two content types:
    - "Diplomas"
    - "Certificates"
11. Click "Сохранить"

### Expected Results:
- ✅ Storage connection dropdown populated with connections
- ✅ "Select Folder" button enabled only after connection selected
- ✅ Folder modal opens with loading state
- ✅ Folder list displays available folders
- ✅ Selected folder highlighted with blue background
- ✅ New folder name validated (no special characters warning)
- ✅ Folder path populated in main form
- ✅ Content types validation: Cannot remove last type
- ✅ Warning if trying to save with 0 content types
- ✅ Success toast after creation
- ✅ Company in table with:
  - Storage badge: "YANDEX" (red background)
  - Folder path displayed
  - Content types: 2 типов

---

## Test Scenario 4: Edit Company

### Steps:
1. Find "Test Local Company" in table
2. Click "✏️ Редактировать" button
3. Verify form fields pre-populated
4. Try to change company name (should be disabled)
5. Try to change storage type (should be disabled)
6. Update folder path to: "/test_company/updated"
7. Add new content type: "ID Cards"
8. Click "Сохранить"

### Expected Results:
- ✅ Modal opens with title "Редактировать компанию"
- ✅ Company name field is disabled
- ✅ Storage type field is disabled
- ✅ Folder path can be edited
- ✅ Content types can be modified
- ✅ Success toast: "Компания успешно обновлена"
- ✅ Table reflects changes (3 типов)

---

## Test Scenario 5: Backup Configuration

### Steps:
1. Find "Test Local Company" in table
2. Click "🔒 Backup" button
3. In backup modal:
   - Verify current provider is "Не настроено"
   - Select provider: "local"
   - Enter remote path: "/backups/test_local_company"
   - Click "Сохранить"
4. Verify table updates
5. Click "🔒 Backup" again
6. Verify settings persisted

### Expected Results:
- ✅ Backup modal opens
- ✅ Provider dropdown shows options
- ✅ Remote path field accepts input
- ✅ Success toast: "Настройки резервного копирования сохранены"
- ✅ Backup status in table changes to:
  - Green indicator 🟢
  - Provider name "local"
- ✅ Reopening modal shows saved values

---

## Test Scenario 6: Delete Company - Protection

### Steps:
1. Find default company "Vertex AR" in table
2. Verify "Удалить" button is NOT present (or disabled)
3. Find "Test Local Company"
4. Click "🗑️ Удалить"
5. Read confirmation dialog
6. Click "Cancel"
7. Click "Удалить" again
8. Click "OK" to confirm

### Expected Results:
- ✅ Default company has no delete button or it's disabled
- ✅ Badge shows "DEFAULT" for default company
- ✅ Confirmation dialog appears with warning:
  - Lists data that will be deleted (clients, portraits, etc.)
  - States action is irreversible
- ✅ First cancel: company remains
- ✅ After confirmation: Success toast "Компания успешно удалена"
- ✅ Company removed from table
- ✅ Statistics updated (Total Companies -1)

---

## Test Scenario 7: Validation Errors

### Steps:
1. Click "Создать компанию"
2. Leave name empty, click "Сохранить"
3. Enter name: "Validation Test"
4. Leave storage type empty, click "Сохранить"
5. Select storage type: "Яндекс.Диск"
6. Leave connection empty, click "Сохранить"

### Expected Results:
- ✅ Empty name → Error toast: "Введите название компании"
- ✅ Empty storage type → Error toast: "Выберите тип хранилища"
- ✅ Yandex without connection → Error toast: "Выберите подключение к хранилищу"
- ✅ Form remains open with user input preserved
- ✅ No API calls made for invalid data

---

## Test Scenario 8: Empty States

### Steps:
1. If companies exist, temporarily rename database or use fresh install
2. Navigate to /admin/companies
3. Observe empty state

### Expected Results:
- ✅ Table shows centered empty state with:
  - 🏢 Icon
  - Message: "Нет компаний"
  - Button: "Создать первую компанию"
- ✅ Clicking button opens create modal
- ✅ Statistics show 0 for all cards

---

## Test Scenario 9: Theme Persistence

### Steps:
1. Navigate to /admin/companies
2. Verify current theme (default: dark)
3. Click theme toggle button (🌙 or ☀️)
4. Observe theme change
5. Refresh page (F5)
6. Navigate to different admin page (e.g., /admin/clients)
7. Navigate back to /admin/companies

### Expected Results:
- ✅ Theme toggles instantly
- ✅ All colors, backgrounds, borders adapt
- ✅ Theme persists after refresh
- ✅ Theme consistent across admin pages
- ✅ Toggle icon changes (🌙 for dark mode, ☀️ for light mode)

---

## Test Scenario 10: Responsive Design - Mobile

### Steps:
1. Open browser DevTools (F12)
2. Enable device toolbar / responsive mode
3. Set viewport to iPhone 12 (390x844)
4. Navigate to /admin/companies
5. Test all interactions:
   - Open create modal
   - Fill form
   - Open folder modal
   - Scroll table horizontally

### Expected Results:
- ✅ Navigation collapses appropriately
- ✅ Statistics cards stack (2 per row)
- ✅ Table scrolls horizontally
- ✅ Modals fit screen (95% width)
- ✅ Buttons are touch-friendly (min 44x44px)
- ✅ Text readable without zooming
- ✅ Action buttons in table stack vertically

---

## Test Scenario 11: Multiple Content Types

### Steps:
1. Create company with multiple content types
2. Add 5 content types:
   - "Portraits"
   - "Certificates"
   - "Diplomas"
   - "ID Cards"
   - "Business Cards"
3. Try to remove all content types
4. Remove content types one by one until only 1 remains
5. Try to remove the last one

### Expected Results:
- ✅ All 5 content types added successfully
- ✅ Each has label input and remove button (✕)
- ✅ Can remove freely until only 1 remains
- ✅ Attempting to remove last one → Warning toast: "Должен остаться хотя бы один тип контента"
- ✅ Content types saved to database correctly
- ✅ Table shows "5 типов" → "4 типов" → ... → "1 тип"

---

## Test Scenario 12: Network Error Handling

### Prerequisites:
- Browser DevTools open
- Network tab active

### Steps:
1. Navigate to /admin/companies
2. In DevTools, enable "Offline" mode (Network → Offline)
3. Click "Refresh" button
4. Observe behavior
5. Re-enable network
6. Try to create company with invalid data (to trigger 400 error)

### Expected Results:
- ✅ While offline:
  - Error toast: "Ошибка загрузки компаний"
  - Table shows previous data or empty state
  - No crash, app remains usable
  - Console logs error details
- ✅ After network restored:
  - Next action works normally
  - Data refreshes successfully
- ✅ Validation errors (400):
  - Specific error message shown
  - Form stays open for correction
  - No generic "Network Error"

---

## Test Scenario 13: Toast Notifications

### Steps:
1. Perform actions that trigger different toast types:
   - Success: Create company
   - Error: Try to delete default company
   - Warning: Try to remove all content types
   - Info: Note about folder selection
2. Trigger multiple toasts rapidly (e.g., click Save button 3 times quickly)

### Expected Results:
- ✅ Success toast:
  - Green left border
  - ✅ icon
  - Auto-dismiss after 4 seconds
- ✅ Error toast:
  - Red left border
  - ❌ icon
- ✅ Warning toast:
  - Yellow left border
  - ⚠️ icon
- ✅ Info toast:
  - Blue left border
  - ℹ️ icon
- ✅ Multiple toasts stack vertically
- ✅ Each toast dismisses independently
- ✅ Toasts slide in from right
- ✅ No toast overlaps another

---

## Test Scenario 14: Loading States

### Steps:
1. Click "Создать компанию"
2. Fill form completely
3. Open Network tab in DevTools
4. Throttle network to "Slow 3G"
5. Click "Сохранить"
6. Observe loading overlay

### Expected Results:
- ✅ Full-screen overlay appears
- ✅ Spinner animation visible
- ✅ Loading text: "Создание компании..." or similar
- ✅ Cannot interact with page behind overlay
- ✅ Overlay dismisses after API completes
- ✅ Success/error toast appears after overlay closes

---

## Test Scenario 15: Cross-Page Integration

### Steps:
1. Create a new company: "Integration Test Company"
2. Navigate to /admin/clients
3. Create a new client
4. Verify company appears in dropdown
5. Navigate to /admin (dashboard)
6. Verify company statistics updated
7. Navigate to /admin/storage
8. Verify company can select storage connection
9. Navigate back to /admin/companies
10. Verify company still listed

### Expected Results:
- ✅ New company available in clients page dropdown
- ✅ Dashboard statistics reflect new company
- ✅ Storage page recognizes company
- ✅ Navigation preserves state
- ✅ No data inconsistencies
- ✅ Theme persists across navigation

---

## Test Scenario 16: Folder Selection - Yandex Disk Pagination

### Prerequisites:
- Yandex Disk connection configured
- Folder with many subfolders

### Steps:
1. Create company with Yandex storage
2. Click "Select Folder"
3. Navigate to folder with many items
4. Scroll folder list
5. Select deeply nested folder

### Expected Results:
- ✅ Folders load with pagination if available
- ✅ Scroll works smoothly
- ✅ Selected folder path builds correctly (/parent/child/grandchild)
- ✅ Current path display updates during navigation
- ✅ No duplicate folders shown

---

## Test Scenario 17: Performance with Many Companies

### Prerequisites:
- Database with 20+ companies

### Steps:
1. Navigate to /admin/companies
2. Note initial load time
3. Scroll through company list
4. Perform search/filter (if implemented)
5. Create new company
6. Verify table updates

### Expected Results:
- ✅ Page loads in < 2 seconds
- ✅ Table renders smoothly without jank
- ✅ Scroll is fluid
- ✅ Creating company doesn't reload all data unnecessarily
- ✅ Statistics calculate correctly with large datasets

---

## Test Scenario 18: Concurrent User Actions

### Setup:
- Two browser windows/tabs open
- Both logged in as admin
- Both on /admin/companies

### Steps:
1. Window 1: Start editing "Test Company"
2. Window 2: Delete "Test Company"
3. Window 1: Try to save changes
4. Window 2: Create new company
5. Window 1: Refresh page

### Expected Results:
- ✅ Window 1 save fails gracefully:
  - Error toast: "Company not found" or similar
  - No data corruption
- ✅ Window 2 operations succeed normally
- ✅ After refresh, both windows show consistent state
- ✅ No stale data displayed
- ✅ No race conditions or deadlocks

---

## Test Scenario 19: Security - Authorization

### Steps:
1. Log out of admin panel
2. Try to navigate directly to /admin/companies
3. Verify redirect to login
4. Try to access API endpoint directly:
   ```
   curl http://localhost:8000/api/companies
   ```
5. Log in as non-admin user (if available)
6. Try to access /admin/companies

### Expected Results:
- ✅ Unauthenticated users redirected to /admin?error=unauthorized
- ✅ Direct API access returns 401 Unauthorized
- ✅ Non-admin users see 403 Forbidden or redirect
- ✅ No sensitive data exposed in errors
- ✅ Session timeout redirects to login

---

## Test Scenario 20: Edge Cases

### Test 20.1: Very Long Company Name
- Create company with 100+ character name
- Expected: Validation error or name truncated gracefully

### Test 20.2: Special Characters in Name
- Try names with: ", ', <, >, &, emoji 🎉
- Expected: Sanitized or validation error

### Test 20.3: Duplicate Company Name
- Create company "Duplicate Test"
- Create another company "Duplicate Test"
- Expected: Error toast "Company already exists"

### Test 20.4: Empty Content Type Label
- Add content type with empty label
- Expected: Warning or auto-remove on save

### Test 20.5: Rapid Button Clicks
- Click "Create Company" button 10 times rapidly
- Expected: Only one modal opens, button disabled during operation

---

## Regression Checklist

After any changes to the code, verify:
- [ ] All 20 test scenarios pass
- [ ] No console errors on page load
- [ ] No console warnings related to React/Vue (if applicable)
- [ ] Theme toggle works
- [ ] Navigation links work
- [ ] All modals open/close correctly
- [ ] Toast notifications appear and dismiss
- [ ] Loading overlays show and hide
- [ ] Form validation works
- [ ] API calls succeed
- [ ] Data persists correctly
- [ ] Statistics update accurately
- [ ] Responsive design intact
- [ ] No memory leaks (DevTools → Memory → Take Snapshot)
- [ ] No network request failures

---

## Bug Report Template

If you encounter an issue:

```markdown
### Bug Report

**Test Scenario:** [Number and name]

**Steps to Reproduce:**
1. 
2. 
3. 

**Expected Result:**
[What should happen]

**Actual Result:**
[What actually happened]

**Screenshots/Videos:**
[Attach if available]

**Console Errors:**
[Copy any errors from DevTools console]

**Environment:**
- Browser: [e.g., Chrome 120]
- OS: [e.g., macOS 14.1]
- Screen Size: [e.g., 1920x1080]
- Theme: [Dark/Light]

**Additional Context:**
[Any other relevant information]
```

---

## Success Criteria

All tests pass when:
- ✅ All 20 test scenarios execute without critical errors
- ✅ All expected results match actual results
- ✅ No console errors during normal operations
- ✅ Performance is acceptable (page loads < 3s, interactions < 500ms)
- ✅ UI is responsive and accessible
- ✅ Data integrity maintained across all operations
- ✅ Security checks pass (authentication, authorization)
- ✅ Edge cases handled gracefully
- ✅ Error messages are user-friendly and actionable
