# Lifecycle Fields Implementation

## Overview

This document describes the lifecycle management fields added to both **projects** and **portraits** (orders) to track subscription end dates and statuses.

## Database Schema Changes

### Projects Table

Added columns to the `projects` table:

- `status` TEXT - Lifecycle status (CHECK constraint: 'active', 'expiring', 'archived')
  - Default: 'active'
  - Managed automatically or manually
- `subscription_end` TIMESTAMP - Subscription expiration date (ISO format)
  - NULL means no expiration
- `last_status_change` TIMESTAMP - When status was last updated
  - Automatically set when status changes
- `notified_7d` TIMESTAMP - Timestamp of 7-day warning notification
- `notified_24h` TIMESTAMP - Timestamp of 24-hour warning notification  
- `notified_expired` TIMESTAMP - Timestamp of expiration notification

### Portraits Table

Added columns to the `portraits` table (in addition to existing lifecycle columns):

- `subscription_end` TIMESTAMP - Already existed
- `lifecycle_status` TEXT - Already existed (CHECK constraint: 'active', 'expiring', 'archived')
- `last_status_change` TIMESTAMP - When status was last updated (newly added)
- `notification_7days_sent` TIMESTAMP - Already existed
- `notification_24hours_sent` TIMESTAMP - Already existed
- `notification_expired_sent` TIMESTAMP - Already existed

## Status Values

### Status Enum

- **active** 🟢: More than 30 days remaining (or no expiration date)
- **expiring** 🔴: 30 days or less remaining
- **archived** ⚫️: Past expiration date

Status can be:
1. Automatically calculated based on `subscription_end` date
2. Manually set via API
3. Updated by background lifecycle scheduler

## API Changes

### Project Endpoints

#### POST /api/projects
Create a new project with lifecycle fields:

```json
{
  "name": "Project Name",
  "description": "Optional description",
  "company_id": "company-uuid",
  "status": "active",
  "subscription_end": "2024-12-31T23:59:59Z"
}
```

#### PUT /api/projects/{project_id}
Update project lifecycle fields:

```json
{
  "name": "Updated Name",
  "status": "expiring",
  "subscription_end": "2024-06-30T23:59:59Z"
}
```

#### GET /api/projects/{project_id}
Response includes lifecycle fields:

```json
{
  "id": "project-uuid",
  "name": "Project Name",
  "description": "Description",
  "company_id": "company-uuid",
  "created_at": "2024-01-01T00:00:00Z",
  "status": "active",
  "subscription_end": "2024-12-31T23:59:59Z",
  "last_status_change": "2024-01-01T00:00:00Z"
}
```

### Order/Portrait Endpoints

#### POST /orders/create
Create order with subscription end date:

```
POST /orders/create
Content-Type: multipart/form-data

phone: "+1234567890"
name: "Client Name"
image: <file>
video: <file>
description: "Optional description"
company_id: "company-uuid"
subscription_end: "2024-12-31T23:59:59Z"
```

#### Portrait Response
All portrait responses now include:

```json
{
  "id": "portrait-uuid",
  "client_id": "client-uuid",
  "permanent_link": "portrait_xxx",
  "created_at": "2024-01-01T00:00:00Z",
  "view_count": 0,
  "subscription_end": "2024-12-31T23:59:59Z",
  "lifecycle_status": "active",
  "last_status_change": "2024-01-01T00:00:00Z"
}
```

## Database API Methods

### Projects

```python
# Create project with lifecycle
db.create_project(
    project_id=uuid,
    company_id=company_id,
    name="Project",
    description="Description",
    status="active",
    subscription_end="2024-12-31T23:59:59Z"
)

# Update project lifecycle
db.update_project(
    project_id=uuid,
    status="expiring",
    subscription_end="2024-06-30T23:59:59Z"
)

# Set status and record timestamp
db.set_project_status(project_id, "archived")

# Get projects for lifecycle checking
projects = db.list_projects_for_lifecycle_check()

# Count projects by status
counts = db.count_projects_by_status(company_id=company_id)
# Returns: {"active": 10, "expiring": 3, "archived": 2}
```

### Portraits

```python
# Create portrait with subscription
db.create_portrait(
    portrait_id=uuid,
    client_id=client_id,
    image_path="path/to/image.jpg",
    marker_fset="path/to/marker.fset",
    marker_fset3="path/to/marker.fset3",
    marker_iset="path/to/marker.iset",
    permanent_link="portrait_xxx",
    subscription_end="2024-12-31T23:59:59Z",
    lifecycle_status="active"
)

# Update lifecycle status
db.update_portrait_lifecycle_status(portrait_id, "expiring")

# Get portraits for lifecycle checking
portraits = db.get_portraits_for_lifecycle_check()

# Record notification sent
db.record_lifecycle_notification(portrait_id, "7days")

# Count portraits by status
counts = db.count_portraits_by_status(company_id=company_id)
# Returns: {"active": 50, "expiring": 10, "archived": 5}
```

## Admin Dashboard Integration

### Dashboard Stats

The `/admin/stats` endpoint now includes status counts:

```json
{
  "total_portraits": 65,
  "active_portraits": 50,
  "status_counts": {
    "active": 50,
    "expiring": 10,
    "archived": 5
  }
}
```

### Order Form

The admin order creation form should include:

```html
<input type="datetime-local" name="subscription_end" 
       placeholder="Subscription End Date (optional)">
```

When creating an order, the `subscription_end` field will be passed to the API and stored in the database.

## Validation

### Status Validation

- Must be one of: 'active', 'expiring', 'archived'
- Enforced by CHECK constraint in database
- Validated in Pydantic models

### Date Validation

- `subscription_end` must be valid ISO 8601 format
- Accepts formats: 
  - `2024-12-31T23:59:59Z`
  - `2024-12-31T23:59:59+00:00`
  - `2024-12-31T23:59:59`
- NULL/None is valid (no expiration)

## Migration Notes

### Existing Data

All existing records receive safe defaults:
- `status` = 'active'
- `subscription_end` = NULL (no expiration)
- `last_status_change` = NULL
- Notification fields = NULL

### Backward Compatibility

- All new fields are optional/nullable
- Existing API calls continue to work without modifications
- Default values ensure no breaking changes
- Legacy data remains accessible and functional

## Future Enhancements

This implementation provides the foundation for:

1. **Automated Lifecycle Scheduler**
   - Scan records with `subscription_end` dates
   - Update `status` based on time remaining
   - Send notifications at key milestones
   - Track notifications via timestamp fields

2. **Admin Dashboard Enhancements**
   - Visual status indicators
   - Filter by lifecycle status
   - Status change history
   - Bulk status updates

3. **Client Notifications**
   - Email notifications at 7 days, 24 hours, and expiration
   - Telegram admin alerts
   - Customizable notification templates

## Documentation Status Meanings

For end users and administrators:

### Active 🟢
- Subscription has more than 30 days remaining
- All features are fully available
- No action required

### Expiring 🔴  
- Subscription expires within 30 days
- Renewal recommended
- Contact administrator before expiration

### Archived ⚫️
- Subscription has expired
- Content may be restricted or inaccessible
- Renewal required to restore access

## Support

For questions or issues related to lifecycle management:
- Review existing lifecycle documentation in `LIFECYCLE_MANAGEMENT_FEATURE.md`
- Check lifecycle scheduler documentation in `LIFECYCLE_SCHEDULER_NOTIFICATIONS.md`
- Review projects/folders documentation in `PROJECTS_FOLDERS_FEATURE.md`
