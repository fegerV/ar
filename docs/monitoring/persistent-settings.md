# Persistent Monitoring Settings & Concurrency Guards

## Overview

The monitoring system now persists all configuration settings to the database and includes robust concurrency guards to prevent overlapping health checks and notification loops.

## Key Features

### 1. **Persistent Settings Storage**
All monitoring configuration is stored in the `monitoring_settings` table and survives application restarts.

### 2. **Concurrency Guards**
- **AsyncIO Lock**: Prevents overlapping health checks
- **Cooldown Period**: Enforces minimum time between checks
- **Max Runtime**: Optional timeout for runaway checks

### 3. **Runtime Observability**
- View active settings via `/monitoring/status` API
- Track lock status and check timing
- Compare persisted vs runtime configuration

## Database Schema

### `monitoring_settings` Table

```sql
CREATE TABLE monitoring_settings (
    id TEXT PRIMARY KEY,
    cpu_threshold REAL NOT NULL DEFAULT 80.0,
    memory_threshold REAL NOT NULL DEFAULT 85.0,
    disk_threshold REAL NOT NULL DEFAULT 90.0,
    health_check_interval INTEGER NOT NULL DEFAULT 60,
    consecutive_failures INTEGER NOT NULL DEFAULT 3,
    dedup_window_seconds INTEGER NOT NULL DEFAULT 300,
    max_runtime_seconds INTEGER DEFAULT NULL,
    health_check_cooldown_seconds INTEGER NOT NULL DEFAULT 30,
    alert_recovery_minutes INTEGER NOT NULL DEFAULT 60,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Fields Explained

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `cpu_threshold` | REAL | 80.0 | CPU usage % threshold for alerts |
| `memory_threshold` | REAL | 85.0 | Memory usage % threshold for alerts |
| `disk_threshold` | REAL | 90.0 | Disk usage % threshold for alerts |
| `health_check_interval` | INTEGER | 60 | Seconds between health checks |
| `consecutive_failures` | INTEGER | 3 | Failures before escalating to alert |
| `dedup_window_seconds` | INTEGER | 300 | Suppress duplicate alerts (5 min) |
| `max_runtime_seconds` | INTEGER | NULL | Max duration for a check (NULL = no limit) |
| `health_check_cooldown_seconds` | INTEGER | 30 | Minimum time between checks |
| `alert_recovery_minutes` | INTEGER | 60 | Time before alert can re-fire |

## Configuration Methods

### 1. Environment Variables (Initial Defaults)

Configuration values can be set via environment variables which are used as defaults when seeding the database:

```bash
# .env or environment
CPU_THRESHOLD=80.0
MEMORY_THRESHOLD=85.0
DISK_THRESHOLD=90.0
HEALTH_CHECK_INTERVAL=60
MONITORING_CONSECUTIVE_FAILURES=3
MONITORING_DEDUP_WINDOW=300
MONITORING_MAX_RUNTIME=120
HEALTH_CHECK_COOLDOWN=30
ALERT_RECOVERY_MINUTES=60
```

**Note**: Environment variables are only used for initial database seeding. Once settings exist in the database, they take precedence.

### 2. API Endpoints (Runtime & Persisted)

#### Update Thresholds
```bash
PUT /admin/monitoring/thresholds
```

**Request Body:**
```json
{
  "cpu_threshold": 85.0,
  "memory_threshold": 90.0,
  "disk_threshold": 95.0
}
```

**Response:**
```json
{
  "success": true,
  "message": "Thresholds updated and persisted: CPU: 85.0%, Memory: 90.0%, Disk: 95.0%",
  "current_thresholds": {
    "cpu": 85.0,
    "memory": 90.0,
    "disk": 95.0
  },
  "persisted": true
}
```

#### Update Settings
```bash
PUT /admin/monitoring/settings
```

**Request Body:**
```json
{
  "cpu_threshold": 85,
  "memory_threshold": 90,
  "disk_threshold": 95,
  "response_threshold": 3000
}
```

**Response:**
```json
{
  "success": true,
  "message": "Settings updated and persisted: CPU threshold: 85%, Memory threshold: 90%, Disk threshold: 95%",
  "settings": {
    "cpu_threshold": 85.0,
    "memory_threshold": 90.0,
    "disk_threshold": 95.0
  },
  "persisted": true
}
```

#### Get Status (with Runtime Settings)
```bash
GET /admin/monitoring/status
```

**Response:**
```json
{
  "enabled": true,
  "status": "Активен",
  "check_interval": 60,
  "thresholds": {
    "cpu": 80.0,
    "memory": 85.0,
    "disk": 90.0
  },
  "channels": {
    "telegram": true,
    "email": true
  },
  "recent_alerts": [...],
  "runtime_settings": {
    "cpu_threshold": 80.0,
    "memory_threshold": 85.0,
    "disk_threshold": 90.0,
    "health_check_interval": 60,
    "consecutive_failures": 3,
    "dedup_window_seconds": 300,
    "max_runtime_seconds": 120,
    "health_check_cooldown_seconds": 30,
    "alert_recovery_minutes": 60
  },
  "persisted_settings": {
    "id": "uuid",
    "cpu_threshold": 80.0,
    ...
    "created_at": "2025-01-21T10:00:00",
    "updated_at": "2025-01-21T10:30:00"
  },
  "lock_status": {
    "is_locked": false,
    "last_check_start": "2025-01-21T10:29:45",
    "last_check_end": "2025-01-21T10:29:50"
  }
}
```

### 3. Database Methods

```python
from app.main import database

# Get active settings
settings = database.get_monitoring_settings()

# Update settings
success = database.update_monitoring_settings(
    cpu_threshold=85.0,
    memory_threshold=90.0,
    max_runtime_seconds=180
)
```

## Concurrency Control

### AsyncIO Lock

The `SystemMonitor` uses `asyncio.Lock()` to prevent overlapping health checks:

```python
async with self._monitoring_lock:
    await self.check_system_health()
```

**Behavior:**
- If a health check is already running, subsequent checks are skipped
- Logs warning: "Previous health check still running, skipping this iteration"
- Prevents resource exhaustion from stacked checks

### Health Check Cooldown

Enforces minimum time between consecutive checks:

```python
if self._last_check_end:
    time_since_last = (datetime.utcnow() - self._last_check_end).total_seconds()
    if time_since_last < self.health_check_cooldown:
        remaining = self.health_check_cooldown - time_since_last
        await asyncio.sleep(remaining)
```

**Default**: 30 seconds

**Purpose**: Prevents rapid-fire checks that could mask transient issues or spam alerts

### Max Runtime (Timeout)

Optional timeout for health checks:

```python
if self.max_runtime_seconds:
    await asyncio.wait_for(
        self.check_system_health(),
        timeout=self.max_runtime_seconds
    )
```

**Default**: None (no limit)

**Purpose**: 
- Prevents runaway checks from blocking the monitoring loop
- Sends alert if timeout is exceeded
- Useful for detecting slow/hung health checks

## Alert Deduplication

### Consecutive Failures Threshold

Alerts only escalate after N consecutive failures:

```python
self.failure_counts[alert_key] = self.failure_counts.get(alert_key, 0) + 1

if self.failure_counts[alert_key] >= self.consecutive_failure_threshold:
    # Escalate to alert
```

**Default**: 3 failures

**Purpose**: Prevents alerts from transient spikes (e.g., brief CPU spike during backup)

### Deduplication Window

Suppresses duplicate alerts within a time window:

```python
if alert_key in self.last_alerts:
    time_since_last = (datetime.utcnow() - self.last_alerts[alert_key]).total_seconds()
    if time_since_last < self.dedup_window:
        return False  # Don't send duplicate
```

**Default**: 300 seconds (5 minutes)

**Purpose**: Prevents notification spam for sustained issues

### Alert Recovery

Tracks recovery time before an alert can re-fire:

**Default**: 60 minutes

**Purpose**: Prevents alert fatigue from oscillating metrics

## Monitoring Loop Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Start Monitoring Loop                                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Check: Is cooldown period elapsed?                         │
│ • If not, wait for remaining cooldown time                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Check: Is lock available?                                   │
│ • If locked, skip this iteration                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Acquire Lock                                                │
│ • Record start time                                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Run Health Check (with timeout if configured)              │
│ • Collect metrics                                           │
│ • Check thresholds                                          │
│ • Evaluate alerts (consecutive failures + dedup)           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Release Lock                                                │
│ • Record end time                                           │
│ • Log check duration                                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Sleep for check_interval                                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            └──────────────────────────┐
                                                       │
                                                       ▼
                                                 (repeat)
```

## Tuning Recommendations

### Conservative (Low Alert Volume)
```env
MONITORING_CONSECUTIVE_FAILURES=5
MONITORING_DEDUP_WINDOW=600
HEALTH_CHECK_COOLDOWN=60
ALERT_RECOVERY_MINUTES=120
```

### Balanced (Default)
```env
MONITORING_CONSECUTIVE_FAILURES=3
MONITORING_DEDUP_WINDOW=300
HEALTH_CHECK_COOLDOWN=30
ALERT_RECOVERY_MINUTES=60
```

### Aggressive (High Sensitivity)
```env
MONITORING_CONSECUTIVE_FAILURES=2
MONITORING_DEDUP_WINDOW=180
HEALTH_CHECK_COOLDOWN=15
ALERT_RECOVERY_MINUTES=30
MONITORING_MAX_RUNTIME=60
```

### Production Best Practices

1. **Start Conservative**: Begin with high thresholds and gradually tighten
2. **Monitor Lock Status**: Check `/monitoring/status` for `lock_status.is_locked`
3. **Set Max Runtime**: Prevent runaway checks with `MONITORING_MAX_RUNTIME=120`
4. **Review Logs**: Check for "skipping iteration" warnings indicating overlaps
5. **Adjust Based on Load**: Higher traffic systems may need longer cooldowns
6. **Test Changes**: Use `/monitoring/test-alert` to verify alert routing

## Troubleshooting

### Issue: Settings not persisting

**Symptoms**: Changes reset after restart

**Diagnosis**:
```bash
curl http://localhost:8000/admin/monitoring/status | jq '.persisted'
```

**Solution**:
- Verify database migration ran successfully
- Check logs for "Seeded default monitoring settings"
- Manually call `database._seed_default_monitoring_settings()`

### Issue: Health checks overlapping

**Symptoms**: Multiple "still running" warnings in logs

**Diagnosis**:
```bash
curl http://localhost:8000/admin/monitoring/status | jq '.lock_status'
```

**Solution**:
1. Increase `MONITORING_MAX_RUNTIME` to timeout slow checks
2. Increase `HEALTH_CHECK_COOLDOWN` to space out checks
3. Reduce `HEALTH_CHECK_INTERVAL` frequency

### Issue: Too many alerts

**Symptoms**: Alert fatigue from frequent notifications

**Diagnosis**: Check alert history
```bash
curl http://localhost:8000/admin/monitoring/alerts?hours=1
```

**Solution**:
1. Increase `MONITORING_CONSECUTIVE_FAILURES` (e.g., 5 instead of 3)
2. Increase `MONITORING_DEDUP_WINDOW` (e.g., 600 instead of 300)
3. Increase `ALERT_RECOVERY_MINUTES` (e.g., 120 instead of 60)
4. Raise resource thresholds if alerts are false positives

### Issue: No alerts when expected

**Symptoms**: System issues not triggering alerts

**Diagnosis**:
```bash
# Check runtime settings
curl http://localhost:8000/admin/monitoring/status | jq '.runtime_settings'

# Check recent metrics
curl http://localhost:8000/admin/monitoring/metrics
```

**Solution**:
1. Verify `ALERTING_ENABLED=true`
2. Lower `MONITORING_CONSECUTIVE_FAILURES` (e.g., 2 instead of 3)
3. Lower resource thresholds if they're too high
4. Check notification channels configured correctly
5. Test alert system: `POST /admin/monitoring/test-alert`

## Migration from Legacy Config

### Before (Config-only)
```python
# Settings only from environment variables
# Lost on restart if changed via API
system_monitor.alert_thresholds["cpu"] = 85.0
```

### After (Persistent)
```python
# Settings persisted to database
database.update_monitoring_settings(cpu_threshold=85.0)
system_monitor.reload_settings()
```

### Automatic Migration

On first startup after upgrade:
1. Database table `monitoring_settings` is created automatically
2. Default row seeded with values from environment variables
3. `SystemMonitor.__init__()` loads persisted settings
4. API endpoints update both runtime and database

**No manual migration required!**

## API Reference Summary

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/monitoring/status` | GET | Admin | View runtime + persisted settings |
| `/monitoring/thresholds` | PUT | Admin | Update & persist thresholds |
| `/monitoring/settings` | GET | Admin | Get alert settings |
| `/monitoring/settings` | PUT | Admin | Update & persist settings |
| `/monitoring/health-check` | POST | Admin | Trigger manual check |
| `/monitoring/metrics` | GET | Admin | Get current metrics |
| `/monitoring/test-alert` | POST | Admin | Test alert channels |

## Logging

### Key Log Events

```python
# Settings loaded
logger.info("Loaded monitoring settings from database", settings=db_settings)

# Settings updated
logger.info("Reloaded monitoring settings from database", settings=db_settings)

# Lock contention
logger.warning("Previous health check still running, skipping this iteration")

# Cooldown active
logger.debug("Health check cooldown active, waiting {remaining:.1f}s")

# Timeout exceeded
logger.error("Health check exceeded max runtime of {max_runtime_seconds}s")

# Check completed
logger.debug("Health check completed in {check_duration:.1f}s")
```

### Monitoring Logs

```bash
# Tail logs for monitoring events
tail -f /var/log/vertex-ar/app.log | grep -E "monitoring|health_check|alert"

# Check for overlaps
grep "still running" /var/log/vertex-ar/app.log

# Check for timeouts
grep "exceeded max runtime" /var/log/vertex-ar/app.log

# View check duration stats
grep "completed in" /var/log/vertex-ar/app.log | awk '{print $NF}' | sort -n
```

## See Also

- [Monitoring Implementation](./implementation.md) - Core monitoring features
- [Alert Stabilization](./alert-stabilization.md) - Deduplication details
- [Web Health Check](./web-health-check.md) - Web server monitoring
- [Setup Guide](./setup.md) - Initial configuration
