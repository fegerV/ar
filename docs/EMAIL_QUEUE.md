# Email Queue Architecture

## Overview

Vertex AR implements a **durable async email queue** that ensures email delivery never blocks request paths. The system uses database persistence to survive application restarts and employs a configurable worker pool for concurrent processing.

## Architecture

### Components

1. **EmailQueue** (`app/services/email_queue.py`)
   - Manages persistent email jobs
   - Runs async worker pool
   - Coordinates with database for persistence
   - Handles retry logic and failure tracking

2. **Database Layer** (`app/database.py`)
   - `email_queue` table for job persistence
   - CRUD operations for email jobs
   - Statistics and cleanup utilities

3. **EmailService Integration** (`app/email_service.py`)
   - Routes non-urgent emails to persistent queue
   - Provides `urgent=True` escape hatch for synchronous flows
   - Falls back to in-memory queue if persistent queue unavailable

4. **CLI Tool** (`scripts/process_email_queue.py`)
   - Manual queue management
   - Drain/retry/stats/cleanup commands
   - Operational troubleshooting

## Database Schema

### `email_queue` Table

```sql
CREATE TABLE email_queue (
    id TEXT PRIMARY KEY,                  -- UUID
    recipient_to TEXT NOT NULL,           -- Comma-separated email addresses
    subject TEXT NOT NULL,                -- Email subject
    body TEXT NOT NULL,                   -- Plain text body
    html TEXT,                            -- Optional HTML body
    template_id TEXT,                     -- Optional template reference
    variables TEXT,                       -- JSON-encoded template variables
    status TEXT NOT NULL DEFAULT 'pending', -- pending|sending|sent|failed
    attempts INTEGER NOT NULL DEFAULT 0,   -- Number of send attempts
    last_error TEXT,                      -- Last error message
    created_at TIMESTAMP NOT NULL,        -- Job creation timestamp
    updated_at TIMESTAMP NOT NULL         -- Last update timestamp
);

-- Indexes for performance
CREATE INDEX idx_email_queue_status ON email_queue(status);
CREATE INDEX idx_email_queue_created_at ON email_queue(created_at);
CREATE INDEX idx_email_queue_status_created ON email_queue(status, created_at);
```

### Job Lifecycle

```
   ┌─────────┐
   │ PENDING │◄──────────────────┐
   └────┬────┘                   │
        │                        │
        │  dequeue               │  retry
        v                        │  (attempts < 3)
   ┌─────────┐                   │
   │ SENDING │                   │
   └────┬────┘                   │
        │                        │
        ├─► Success ──► SENT     │
        │                        │
        └─► Failure ─────────────┘
                 │
                 │ (attempts >= 3)
                 v
            ┌────────┐
            │ FAILED │
            └────────┘
```

## Worker Lifecycle

### Startup

1. Application starts → FastAPI `startup` event
2. `EmailQueue` initialized with:
   - `EmailService` instance
   - `Database` instance
   - Worker count (default: 3, configurable via `EMAIL_QUEUE_WORKERS`)
3. Pending jobs reloaded from database into memory queue
4. Worker pool started as async tasks

### Processing

Each worker:
1. Continuously polls for jobs (`dequeue()`)
2. Checks in-memory queue first (fast path)
3. Falls back to database query if memory queue empty
4. Updates job status to `sending`
5. Invokes `EmailService._send_email_sync()`
6. On success: marks as `sent`
7. On failure: increments attempts, sets error, requeues if under max attempts

### Shutdown

1. Application shutdown → FastAPI `shutdown` event
2. `stop_workers()` called
3. Workers cancelled gracefully
4. In-flight jobs remain in database with `sending` status
5. Next startup reloads unfinished jobs

## Configuration

### Environment Variables

```bash
# Worker pool size (default: 3)
EMAIL_QUEUE_WORKERS=3

# SMTP configuration (inherited from EmailService)
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=user@example.com
SMTP_PASSWORD=password
```

### Code Configuration

```python
from app.services.email_queue import get_email_queue

# Get queue instance
queue = get_email_queue()

# Get statistics
stats = await queue.get_stats()
print(f"Pending: {stats['pending']}, Failed: {stats['failed']}")

# Manually retry failed jobs
count = await queue.retry_failed_jobs(max_jobs=10)
```

## Usage

### Sending Emails

#### Non-Urgent (Default - Persistent Queue)

```python
from app.email_service import email_service

# Email is persisted to database and processed by workers
await email_service.send_email(
    to_addresses=["user@example.com"],
    subject="Welcome!",
    body="Welcome to Vertex AR",
    html_body="<p>Welcome to Vertex AR</p>",
    urgent=False,  # Default - uses persistent queue
)
```

#### Urgent (Bypass Persistent Queue)

```python
# For tests, admin actions, or time-sensitive emails
# Uses in-memory queue for immediate processing
await email_service.send_email(
    to_addresses=["admin@example.com"],
    subject="Critical Alert",
    body="System error detected",
    urgent=True,  # Bypasses persistent queue
)
```

### CLI Management

#### Show Statistics

```bash
python scripts/process_email_queue.py stats
```

Output:
```
============================================================
EMAIL QUEUE STATISTICS
============================================================
Pending:       15
Sending:       2
Sent:          1024
Failed:        3
Total:         1044
Memory Queue:  5
Workers:       0  # (not running in CLI mode)
Running:       False
============================================================
```

#### Drain Queue

Process all pending jobs (or up to max):

```bash
# Process all pending jobs
python scripts/process_email_queue.py drain

# Process up to 100 jobs
python scripts/process_email_queue.py drain --max 100
```

#### Retry Failed Jobs

```bash
# Retry up to 10 failed jobs
python scripts/process_email_queue.py retry --max 10
```

#### List Failed Jobs

```bash
# Show 20 most recent failed jobs
python scripts/process_email_queue.py failed --limit 20
```

#### Clean Up Old Jobs

```bash
# Delete sent/failed jobs older than 30 days
python scripts/process_email_queue.py cleanup --days 30

# Delete jobs older than 7 days
python scripts/process_email_queue.py cleanup --days 7
```

## Monitoring

### Queue Statistics

```python
from app.services.email_queue import get_email_queue

queue = get_email_queue()
stats = await queue.get_stats()

# Available metrics:
# - pending: Jobs waiting to be processed
# - sending: Jobs currently being processed
# - sent: Successfully sent jobs
# - failed: Permanently failed jobs (3+ attempts)
# - total: Total jobs in database
# - memory_queue_size: Jobs in memory queue
# - workers: Number of active workers
# - running: Whether workers are running
```

### Database Queries

Check queue health directly:

```sql
-- Current queue status
SELECT status, COUNT(*) as count
FROM email_queue
GROUP BY status;

-- Recent failed jobs
SELECT id, to, subject, attempts, last_error, updated_at
FROM email_queue
WHERE status = 'failed'
ORDER BY updated_at DESC
LIMIT 10;

-- Jobs stuck in 'sending' (possible worker crash)
SELECT id, to, subject, attempts, updated_at
FROM email_queue
WHERE status = 'sending'
  AND updated_at < datetime('now', '-10 minutes')
ORDER BY updated_at ASC;
```

### Prometheus Metrics

Email metrics are exposed at `/metrics`:

```
# Success/failure counters
vertex_ar_email_sent_total{priority="5"} 1024
vertex_ar_email_failed_total{priority="5",error_type="SMTPException"} 3

# Queue depth
vertex_ar_email_queue_depth 15
vertex_ar_email_pending_count 15
vertex_ar_email_failed_count 3

# Send duration histogram
vertex_ar_email_send_duration_seconds_bucket{le="1.0"} 950
vertex_ar_email_send_duration_seconds_bucket{le="5.0"} 1020
```

## Failure Recovery

### Scenario 1: Worker Crash During Processing

**Problem**: Workers crash, leaving jobs in `sending` status.

**Detection**:
```sql
SELECT * FROM email_queue
WHERE status = 'sending'
  AND updated_at < datetime('now', '-10 minutes');
```

**Recovery**:
```sql
-- Reset stuck jobs to pending
UPDATE email_queue
SET status = 'pending', updated_at = CURRENT_TIMESTAMP
WHERE status = 'sending'
  AND updated_at < datetime('now', '-10 minutes');
```

Or restart the application (workers will reload pending jobs).

### Scenario 2: SMTP Server Down

**Problem**: SMTP server unreachable, causing cascading failures.

**Detection**: Spike in `failed` count, similar error messages.

**Recovery**:
1. Fix SMTP configuration/server
2. Retry failed jobs:
   ```bash
   python scripts/process_email_queue.py retry --max 100
   ```

### Scenario 3: Database Growth

**Problem**: Queue table grows large with old sent/failed jobs.

**Detection**: Query performance degradation, large table size.

**Recovery**:
```bash
# Clean up jobs older than 30 days
python scripts/process_email_queue.py cleanup --days 30
```

Set up periodic cleanup (cron job):
```bash
# Daily cleanup at 2 AM
0 2 * * * cd /path/to/vertex-ar && python scripts/process_email_queue.py cleanup --days 30
```

### Scenario 4: Queue Backlog

**Problem**: Jobs accumulating faster than workers can process.

**Detection**: Growing `pending` count.

**Recovery**:
1. Increase worker count:
   ```bash
   # In .env
   EMAIL_QUEUE_WORKERS=5
   ```
2. Manually drain queue:
   ```bash
   python scripts/process_email_queue.py drain
   ```
3. Investigate slow SMTP server or network issues

## Best Practices

### 1. Use Non-Urgent by Default

```python
# ✅ Good - Uses persistent queue
await email_service.send_email(to=["user@example.com"], ...)

# ❌ Avoid unless necessary
await email_service.send_email(to=["user@example.com"], ..., urgent=True)
```

### 2. Monitor Queue Depth

Set up alerts for:
- `pending > 100` (backlog building)
- `failed > 10` (systematic issues)
- `sending > workers * 2` (stuck jobs)

### 3. Regular Cleanup

Schedule periodic cleanup to prevent database growth:

```bash
# Keep 30 days of history
0 2 * * * python scripts/process_email_queue.py cleanup --days 30
```

### 4. Graceful Degradation

EmailService automatically falls back to in-memory queue if persistent queue unavailable:

```python
# If persistent queue fails, email still queued in-memory
await email_service.send_email(...)  # Never blocks, always succeeds
```

### 5. Retry Budget

Jobs retry up to 3 times with exponential backoff:
- Attempt 1: immediate
- Attempt 2: +2 minutes (if persistent queue worker picks it up)
- Attempt 3: +4 minutes
- After 3: permanently failed

For critical emails, manually retry:
```bash
python scripts/process_email_queue.py retry
```

## Testing

### Unit Tests

Run email queue unit tests:

```bash
pytest test_files/unit/test_email_queue.py -v
```

Tests cover:
- Job creation/serialization
- Enqueue/dequeue logic
- Retry increments
- DB persistence
- Error handling
- Worker behavior

### Integration Testing

Test end-to-end flow:

```python
# Send test email
await email_service.send_email(
    to_addresses=["test@example.com"],
    subject="Test Email",
    body="This is a test",
)

# Check queue stats
queue = get_email_queue()
stats = await queue.get_stats()
assert stats["pending"] > 0

# Wait for processing
await asyncio.sleep(5)

# Verify sent
stats = await queue.get_stats()
assert stats["sent"] > 0
```

## Troubleshooting

### Queue Not Processing

**Symptoms**: Jobs stay in `pending`, never transition to `sent`.

**Checks**:
1. Are workers running?
   ```python
   stats = await queue.get_stats()
   print(stats["workers"], stats["running"])
   ```
2. Are workers stuck?
   ```bash
   # Check logs for errors
   tail -f vertex-ar/app.log | grep -i "email"
   ```
3. Is SMTP configured?
   ```bash
   # Check environment variables
   env | grep SMTP
   ```

**Fix**: Restart application or manually drain queue.

### High Failure Rate

**Symptoms**: Many jobs in `failed` status.

**Checks**:
1. Check error messages:
   ```bash
   python scripts/process_email_queue.py failed --limit 10
   ```
2. Test SMTP connectivity:
   ```python
   import smtplib
   server = smtplib.SMTP("smtp.example.com", 587)
   server.starttls()
   server.login("user", "pass")
   server.quit()
   ```

**Fix**: Correct SMTP configuration, retry failed jobs.

### Database Lock Errors

**Symptoms**: Workers timeout waiting for database lock.

**Checks**: SQLite has limited concurrency. Consider:
1. Reduce worker count
2. Increase SQLite timeout
3. Migrate to PostgreSQL for production

## Performance Tuning

### Worker Count

- **Low traffic** (< 100 emails/hour): 1-2 workers
- **Medium traffic** (100-1000 emails/hour): 3-5 workers
- **High traffic** (> 1000 emails/hour): 5-10 workers

SQLite performs best with 3-5 concurrent workers. For higher concurrency, migrate to PostgreSQL.

### Memory Queue Size

In-memory queue buffers pending jobs for fast dequeue:

```python
# Default: unlimited
queue = EmailQueue(email_service, database, worker_count=3)

# To limit memory usage, jobs load from DB on demand
```

### Database Cleanup

Regular cleanup prevents performance degradation:

```bash
# Daily cleanup, keep 30 days
0 2 * * * python scripts/process_email_queue.py cleanup --days 30
```

## Migration Guide

### From In-Memory Queue

**Before** (in-memory only):
```python
await email_service.send_email(to=["user@example.com"], ...)
# Email lost on restart
```

**After** (persistent queue):
```python
await email_service.send_email(to=["user@example.com"], ...)
# Email persists across restarts
```

**Transition**: Existing `send_email()` calls automatically use persistent queue. No code changes required.

### Backward Compatibility

- `urgent=True` maintains synchronous behavior for tests/admin
- In-memory queue still runs for fallback
- If persistent queue unavailable, degrades gracefully

## API Reference

### EmailQueue Class

#### `__init__(email_service, database, worker_count=3)`

Initialize email queue.

**Parameters:**
- `email_service`: EmailService instance
- `database`: Database instance
- `worker_count`: Number of concurrent workers

#### `async enqueue(to, subject, body, html=None, template_id=None, variables=None) -> str`

Enqueue an email job.

**Returns:** Job ID (UUID string)

#### `async dequeue() -> Optional[EmailQueueJob]`

Dequeue next pending job.

**Returns:** EmailQueueJob or None

#### `async start_workers()`

Start worker pool. Reloads pending jobs from database.

#### `async stop_workers()`

Stop worker pool gracefully.

#### `async get_stats() -> Dict[str, Any]`

Get queue statistics.

**Returns:** Dictionary with keys: `pending`, `sending`, `sent`, `failed`, `total`, `memory_queue_size`, `workers`, `running`

#### `async retry_failed_jobs(max_jobs=10) -> int`

Retry failed jobs.

**Returns:** Number of jobs requeued

### Database Methods

#### `create_email_job(job) -> str`

Persist email job to database.

**Returns:** Job ID

#### `update_email_job(job) -> bool`

Update existing job status/attempts/error.

#### `get_next_pending_email_job() -> Optional[Dict]`

Get next pending job from database.

#### `get_all_pending_email_jobs() -> List[Dict]`

Get all pending jobs.

#### `get_failed_email_jobs(limit=10) -> List[Dict]`

Get recent failed jobs.

#### `get_email_queue_stats() -> Dict[str, int]`

Get queue statistics from database.

#### `delete_old_email_jobs(days=30) -> int`

Delete old sent/failed jobs.

**Returns:** Number of jobs deleted

## See Also

- [Email Monitoring Documentation](EMAIL_MONITORING.md)
- [Notification System](../NOTIFICATIONS_MIGRATION_REPORT.md)
- [Database Schema](../vertex-ar/app/database.py)
