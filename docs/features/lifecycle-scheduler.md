# Lifecycle Scheduler & Notifications

## Overview

The Lifecycle Scheduler is an automated system that manages portrait subscription lifecycle and sends timely notifications to clients and administrators when subscriptions are approaching expiration or have expired.

## Features

### 1. Automatic Status Transitions

The system automatically updates portrait lifecycle statuses based on subscription end dates:

- **Active (🟢)**: More than 7 days remaining until expiration
- **Expiring (🔴)**: 7 days or less remaining until expiration
- **Archived (⚫)**: Subscription has expired

### 2. Multi-Stage Notifications

The system sends notifications at three critical milestones:

#### 7-Day Warning
- Triggered when ≤7 days remain before expiration
- Sent once per portrait (tracked to avoid duplicates)
- Includes days remaining and expiration date
- Sent via Telegram (admin) and Email (client, if email exists)

#### 24-Hour Warning
- Triggered when ≤24 hours remain before expiration
- Sent once per portrait (tracked to avoid duplicates)
- Final reminder before expiration
- Sent via Telegram (admin) and Email (client, if email exists)

#### Post-Expiry Notification
- Triggered immediately after subscription expires
- Notifies that portrait has been archived
- Includes renewal instructions
- Sent via Telegram (admin) and Email (client, if email exists)

### 3. Notification Tracking

The system tracks when each notification has been sent to prevent duplicates:

- `notification_7days_sent`: Timestamp of 7-day warning
- `notification_24hours_sent`: Timestamp of 24-hour warning
- `notification_expired_sent`: Timestamp of post-expiry notification

### 4. Bilingual Support

All client notifications include both Russian and English versions:

**7-Day Warning:**
```
Subject RU: Подписка истекает через 7 дней
Subject EN: Subscription expires in 7 days
```

**24-Hour Warning:**
```
Subject RU: Подписка истекает через 24 часа
Subject EN: Subscription expires in 24 hours
```

**Post-Expiry:**
```
Subject RU: Подписка истекла
Subject EN: Subscription expired
```

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Enable lifecycle scheduler (default: true)
LIFECYCLE_SCHEDULER_ENABLED=true

# Check interval in seconds (default: 3600 = 1 hour)
LIFECYCLE_CHECK_INTERVAL_SECONDS=3600

# Enable notifications (default: true)
LIFECYCLE_NOTIFICATIONS_ENABLED=true
```

### Email Configuration

For client email notifications to work, configure SMTP settings:

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
```

### Telegram Configuration

For admin notifications via Telegram:

```bash
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

## Database Schema

### Portraits Table Extensions

```sql
-- Lifecycle status tracking
ALTER TABLE portraits ADD COLUMN subscription_end TIMESTAMP;
ALTER TABLE portraits ADD COLUMN lifecycle_status TEXT DEFAULT 'active';

-- Notification tracking
ALTER TABLE portraits ADD COLUMN notification_7days_sent TIMESTAMP;
ALTER TABLE portraits ADD COLUMN notification_24hours_sent TIMESTAMP;
ALTER TABLE portraits ADD COLUMN notification_expired_sent TIMESTAMP;
```

### Clients Table Extension

```sql
-- Client email for notifications
ALTER TABLE clients ADD COLUMN email TEXT;
```

## API Usage

### Setting Subscription End Date

When creating or updating a portrait, set the `subscription_end` field:

```python
# Example: Set subscription to expire in 30 days
from datetime import datetime, timedelta

subscription_end = datetime.utcnow() + timedelta(days=30)

# Update portrait
database.execute(
    "UPDATE portraits SET subscription_end = ? WHERE id = ?",
    (subscription_end.isoformat(), portrait_id)
)
```

### Resetting Notifications

If you need to reset notification tracking (e.g., after renewing a subscription):

```python
database.reset_lifecycle_notifications(portrait_id)
```

### Getting Scheduler Status

```python
from app.project_lifecycle import project_lifecycle_scheduler

status = await project_lifecycle_scheduler.get_scheduler_status()
# Returns:
# {
#     "scheduler_enabled": true,
#     "notifications_enabled": true,
#     "check_interval_seconds": 3600,
#     "last_check": "2024-01-15T10:30:00",
#     "status_counts": {
#         "active": 150,
#         "expiring": 10,
#         "archived": 5
#     },
#     "expiring_soon_count": 10,
#     "expired_count": 5
# }
```

## Architecture

### Service Module: `app/project_lifecycle.py`

The `ProjectLifecycleScheduler` class manages:

1. **Status Calculation**: Determines lifecycle status based on subscription end date
2. **Notification Logic**: Decides when notifications should be sent
3. **Email Sending**: Sends transactional emails to clients
4. **Telegram Alerts**: Sends admin notifications via Telegram
5. **Database Updates**: Updates statuses and tracks notifications

### Database Methods

New methods in `app/database.py`:

- `get_portraits_for_lifecycle_check()`: Get all portraits with subscription_end
- `update_portrait_lifecycle_status(portrait_id, status)`: Update status
- `record_lifecycle_notification(portrait_id, type)`: Track notification sent
- `reset_lifecycle_notifications(portrait_id)`: Reset notification flags

### Startup Integration

The scheduler is registered in `app/main.py` as a background task:

```python
if settings.LIFECYCLE_SCHEDULER_ENABLED:
    from app.project_lifecycle import project_lifecycle_scheduler
    
    @app.on_event("startup")
    async def start_lifecycle_scheduler():
        asyncio.create_task(project_lifecycle_scheduler.start_lifecycle_scheduler())
        logger.info("Lifecycle scheduler started")
```

## Notification Flow

```
┌─────────────────────────────────────────────┐
│         Lifecycle Scheduler Loop            │
│        (runs every check_interval)          │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│    Get all portraits with subscription_end  │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
         ┌────────────────────┐
         │ For each portrait  │
         └────────┬───────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│    Calculate lifecycle status               │
│    - Active: >7 days remaining              │
│    - Expiring: ≤7 days remaining            │
│    - Archived: expired                      │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│    Update status if changed                 │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│    Check notification conditions            │
│    - 7 days: ≤7 days & not sent             │
│    - 24 hours: ≤24 hours & not sent         │
│    - Expired: past date & not sent          │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
         ┌────────────────────┐
         │  Send notifications │
         └────────┬───────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
        ▼                   ▼
┌─────────────┐    ┌─────────────┐
│   Telegram  │    │    Email    │
│   (Admin)   │    │  (Client)   │
└─────────────┘    └─────────────┘
        │                   │
        └─────────┬─────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│    Record notification sent timestamp       │
└─────────────────────────────────────────────┘
```

## Monitoring

### Logs

The scheduler logs all operations:

```
INFO: Starting lifecycle scheduler - checking every 3600 seconds
INFO: Updated lifecycle status for portrait abc123: active -> expiring
INFO: Sent 7-day notification for portrait abc123
INFO: Updated 5 portrait lifecycle statuses
```

### Prometheus Metrics

Lifecycle metrics can be exposed via Prometheus:

- `lifecycle_portraits_active`: Number of active portraits
- `lifecycle_portraits_expiring`: Number of expiring portraits
- `lifecycle_portraits_archived`: Number of archived portraits
- `lifecycle_notifications_sent_total`: Counter of sent notifications

### Notification History

All sent notifications are logged to the `notification_history` table:

```sql
SELECT * FROM notification_history 
WHERE notification_type = 'email' 
  AND message LIKE '%subscription%'
ORDER BY sent_at DESC;
```

## Testing

### Unit Tests

Run the lifecycle scheduler tests:

```bash
cd vertex-ar
pytest tests/test_lifecycle_scheduler.py -v
```

### Manual Testing

1. Create a test portrait with a subscription end date:

```python
from datetime import datetime, timedelta

# Set subscription to expire in 6 days
subscription_end = datetime.utcnow() + timedelta(days=6)
db.execute(
    "UPDATE portraits SET subscription_end = ? WHERE id = ?",
    (subscription_end.isoformat(), portrait_id)
)
```

2. Wait for the scheduler to run (or trigger manually)
3. Check logs for notification messages
4. Verify email and Telegram notifications received
5. Check database for notification timestamps

### Testing Notification Logic

```python
from app.project_lifecycle import project_lifecycle_scheduler

# Test status calculation
status = scheduler.calculate_lifecycle_status(subscription_end)
print(f"Status: {status}")

# Test notification conditions
should_send = scheduler.should_send_7day_notification(portrait, subscription_end)
print(f"Should send 7-day notification: {should_send}")
```

## Troubleshooting

### Notifications Not Being Sent

1. **Check scheduler is enabled:**
   ```bash
   grep LIFECYCLE_SCHEDULER_ENABLED .env
   ```

2. **Check email configuration:**
   ```bash
   grep SMTP_ .env
   ```

3. **Check logs for errors:**
   ```bash
   tail -f logs/vertex-ar.log | grep lifecycle
   ```

4. **Verify portrait has subscription_end:**
   ```sql
   SELECT id, subscription_end, lifecycle_status 
   FROM portraits 
   WHERE subscription_end IS NOT NULL;
   ```

### Duplicate Notifications

- The system tracks sent notifications in the database
- Check `notification_*_sent` fields in portraits table
- To reset: `database.reset_lifecycle_notifications(portrait_id)`

### Status Not Updating

- Verify scheduler is running: check startup logs
- Check check interval: default is 1 hour
- Manually trigger: `await scheduler.check_and_update_lifecycle_statuses()`

## Best Practices

1. **Set Subscription Dates**: Always set `subscription_end` when creating portraits
2. **Collect Client Emails**: Encourage collecting client emails for notifications
3. **Monitor Logs**: Regularly check logs for scheduler operation
4. **Test Notifications**: Test email/Telegram delivery before production
5. **Configure Intervals**: Adjust check interval based on your needs
6. **Handle Renewals**: Reset notification flags when renewing subscriptions

## Future Enhancements

Potential improvements:

- [ ] Customizable notification templates
- [ ] SMS notifications
- [ ] Web push notifications
- [ ] Admin dashboard for lifecycle overview
- [ ] Bulk subscription renewal operations
- [ ] Grace period configuration
- [ ] Multiple reminder schedules
- [ ] Client self-service renewal portal

## Related Features

- **Video Scheduler**: Automated video activation/deactivation
- **Alert Manager**: System monitoring and alerting
- **Notification Center**: Centralized notification management
- **Admin Panel**: Manual status management and overrides

## Support

For issues or questions:

1. Check this documentation
2. Review logs: `logs/vertex-ar.log`
3. Check database: verify schema and data
4. Test configuration: verify SMTP/Telegram settings
5. Contact development team

---

**Version**: 1.0.0  
**Last Updated**: 2024-01-15  
**Author**: Vertex AR Development Team
