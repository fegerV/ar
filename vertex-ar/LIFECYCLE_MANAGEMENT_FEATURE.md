# Lifecycle Management Feature

## Overview

The Lifecycle Management feature provides visual status indicators and filtering capabilities in the admin interface to help operators track portrait subscription status and manage content lifecycle effectively.

## Features

### 1. Status Types

Three lifecycle statuses are available:

- **🟢 Активен (Active)**: Portrait subscription is valid (more than 30 days remaining or no expiration date)
- **🔴 Истекает (Expiring)**: Portrait subscription is about to expire (30 days or less remaining)
- **⚫️ Архив (Archived)**: Portrait subscription has expired or has been explicitly archived

### 2. Database Schema

New columns added to the `portraits` table:

```sql
subscription_end TIMESTAMP           -- Subscription end date
lifecycle_status TEXT DEFAULT 'active' CHECK (lifecycle_status IN ('active', 'expiring', 'archived'))
```

### 3. API Enhancements

#### GET `/admin/stats`
Returns status counts for dashboard display:
```json
{
  "status_counts": {
    "active": 120,
    "expiring": 15,
    "archived": 8
  },
  ...
}
```

#### GET `/admin/records`
Returns portrait records with lifecycle information:
```json
{
  "records": [
    {
      "id": "portrait-id",
      "status": "active",
      "subscription_end": "2025-06-15T00:00:00",
      "days_remaining": 180,
      ...
    }
  ]
}
```

#### GET `/admin/search?status=expiring`
Supports filtering by lifecycle status:
- `status=active` - Show only active portraits
- `status=expiring` - Show only expiring portraits  
- `status=archived` - Show only archived portraits
- No status parameter - Show all portraits

### 4. Admin UI Components

#### Status Legend
Located below the statistics cards, displays:
- Current count for each status
- Clickable items for quick filtering
- Visual indicators matching table display

#### Records Table
New "Статус" column shows:
- Status icon (🟢/🔴/⚫️)
- Hover tooltip with days remaining information
- For expiring: "Истекает: X дней"
- For archived: "Архив: истек X дней назад"

### 5. Status Calculation Logic

Status is calculated dynamically based on `subscription_end` date:

```javascript
if (!subscription_end) {
  status = 'active'
} else if (days_remaining < 0) {
  status = 'archived'
} else if (days_remaining <= 30) {
  status = 'expiring'
} else {
  status = 'active'
}
```

## Usage Examples

### Setting Subscription End Date

When creating or updating a portrait (future enhancement):
```python
portrait = database.create_portrait(
    portrait_id="...",
    subscription_end=datetime.now() + timedelta(days=365)
)
```

### Filtering by Status

Using the admin interface:
1. Click on status legend item (e.g., "🔴 Истекает")
2. Table automatically filters to show only matching records
3. Click "🔘 Все" to clear filter

Using the API:
```bash
curl "/admin/search?status=expiring&company_id=..."
```

### Monitoring Status Counts

Dashboard automatically displays:
- Count of active portraits
- Count of expiring portraits (attention needed)
- Count of archived portraits

## Implementation Details

### Backend Components

1. **Database** (`app/database.py`):
   - `count_portraits_by_status()` - Count portraits grouped by status
   - Updated `get_admin_records()` - Include status filtering

2. **Admin API** (`app/api/admin.py`):
   - `_calculate_lifecycle_info()` - Calculate status and days remaining
   - Updated `_serialize_records()` - Include lifecycle fields
   - Updated `/admin/stats` - Include status counts
   - Updated `/admin/search` - Support status filtering

### Frontend Components

1. **JavaScript** (`static/js/admin-dashboard.js`):
   - `getStatusIndicator()` - Generate status icon and tooltip
   - `filterByStatus()` - Handle status filtering
   - Updated `createRecordRow()` - Render status column
   - Updated `updateStatistics()` - Display status counts

2. **HTML/CSS** (`templates/admin_dashboard.html`):
   - Status legend section with interactive items
   - Status column in records table
   - Responsive styling for status indicators

## Configuration

No additional configuration required. The feature works with default thresholds:
- Expiring threshold: 30 days
- Automatic status calculation based on `subscription_end`

## Future Enhancements

Potential improvements for future versions:
1. Configurable expiring threshold (env variable)
2. Email notifications for expiring subscriptions
3. Bulk subscription renewal interface
4. Subscription history tracking
5. Client-facing subscription status
6. Integration with payment systems

## Troubleshooting

### Status not showing correctly
- Verify `subscription_end` is set correctly in database
- Check browser console for JavaScript errors
- Ensure backend is returning status fields

### Filter not working
- Clear browser cache
- Check network tab for API errors
- Verify company_id is set correctly

## Related Features

- **Video Scheduler**: Similar status management for videos
- **Projects & Folders**: Organizational hierarchy for portraits
- **Client Management**: Associated with portrait lifecycle

## Database Migration

The feature includes automatic migration via `ALTER TABLE` statements in `database.py`. No manual migration needed for existing installations.

Legacy portraits without `lifecycle_status` will default to 'active'.
