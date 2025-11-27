# Monitoring Alert Stabilization

## Overview

The monitoring alert system has been enhanced with deduplication, consecutive failure tracking, and degraded service detection to prevent alert spam from transient issues while ensuring sustained problems are properly escalated.

## Key Features

### 1. Consecutive Failure Tracking

Alerts are only escalated after a configurable number of consecutive failures. This prevents single noisy samples or transient spikes from triggering alerts.

**Configuration:**
```bash
MONITORING_CONSECUTIVE_FAILURES=3  # Default: 3 checks before alert
```

**Behavior:**
- Each metric/service tracks failures independently
- Failure count increments on each check that exceeds threshold
- Failure count resets to 0 when metric returns to healthy state
- Alert is only sent after reaching the consecutive failure threshold

### 2. Alert Deduplication Window

Once an alert is sent, the same alert type is suppressed within a configurable deduplication window to prevent alert spam.

**Configuration:**
```bash
MONITORING_DEDUP_WINDOW=300  # Default: 300 seconds (5 minutes)
```

**Behavior:**
- After sending an alert, subsequent alerts of the same type are suppressed for the dedup window
- Each alert type tracks its own dedup window independently
- Consecutive failures continue to be counted, but alerts are not re-sent

### 3. Degraded vs Failed Service Detection

Services are now classified with more granular severity levels based on their state:

**Severity Levels:**
- **Warning**: Metric just over threshold or transient issue (not yet escalated)
- **Medium**: Service degraded but still partially functional (e.g., slow response time)
- **High**: Service completely failed or metric critically high

**Severity Determination:**
- Just over threshold (<5% overshoot): `warning`
- Moderate degradation (5-15% overshoot): `medium`  
- Critical level (>15% overshoot or >95% absolute): `high`

**Service-Specific:**
- Slow response time (>5000ms) but still responding: `warning` → `medium` (degraded)
- Service not responding at all: `high` (failed)

### 4. Health Data Consistency

The `health_data["alerts"]` field returned by `check_system_health()` now mirrors what is sent through `alert_manager`, ensuring the Notification Center view is consistent with actual alerts sent.

**Alert Entry Types:**
- **Escalated Alerts**: Alerts that passed the consecutive failure threshold and were sent via `alert_manager`
  - Includes full severity (`warning`, `medium`, `high`)
  - Does not have `transient: true` flag
  
- **Transient Alerts**: Issues detected but not yet escalated
  - Marked with `transient: true`
  - Message prefixed with "Monitoring: ... (transient)"
  - Severity set to `warning`
  - Provides visibility without alert spam

## Tracked Metrics

The following metrics/services support consecutive failure tracking and deduplication:

### System Resources
- `high_cpu` - CPU usage above threshold
- `high_memory` - Memory usage above threshold
- `high_disk` - Disk usage above threshold

### Core Services
- `service_database` - Database connectivity failures
- `service_storage` - Storage system failures
- `service_minio` - MinIO/S3 failures (if configured)
- `service_web_server` - Web server health check failures
- `service_*_slow` - Slow response time for any service (degraded)

### External Services
- `external_email` - SMTP server failures
- `external_telegram` - Telegram API failures

### System Health
- `high_error_count` - High number of errors in logs
- `monitoring_failure` - Monitoring system itself failed

## Implementation Details

### Helper Methods

#### `_should_escalate_alert(alert_key: str) -> bool`
Checks if an alert should be escalated based on consecutive failures and deduplication window.

**Logic:**
1. Increment failure count for the alert key
2. Check if consecutive failure threshold is reached
3. Check if alert is within deduplication window
4. Update last alert timestamp if escalating
5. Return True to escalate, False to suppress

#### `_reset_failure_count(alert_key: str) -> None`
Resets the failure count for a metric/service that has recovered.

**Called when:**
- Metric returns below threshold
- Service becomes healthy
- Service response time becomes acceptable

#### `_determine_severity(metric_type: str, value: float, threshold: float) -> str`
Determines alert severity based on how much a metric exceeds its threshold.

**Returns:**
- `"warning"` - Just over threshold
- `"medium"` - Moderately degraded
- `"high"` - Critical level

### Data Structures

**Instance Variables in `SystemMonitor`:**
```python
self.last_alerts: Dict[str, datetime] = {}          # Last alert time per key
self.failure_counts: Dict[str, int] = {}            # Consecutive failure count per key
self.consecutive_failure_threshold: int = 3         # From config
self.dedup_window: int = 300                        # Seconds, from config
```

## Testing

Comprehensive tests in `test_monitoring_alert_dedup.py` verify:

1. ✅ Single spike does not trigger alert
2. ✅ Two consecutive spikes do not trigger alert  
3. ✅ Three consecutive spikes DO trigger alert
4. ✅ Failure count resets on recovery
5. ✅ Deduplication window prevents rapid re-alerts
6. ✅ Severity determination works correctly
7. ✅ Degraded services get warning/medium severity
8. ✅ Failed services get high severity
9. ✅ Multiple metrics track independently
10. ✅ `health_data["alerts"]` mirrors sent alerts

**Run tests:**
```bash
cd vertex-ar
python test_monitoring_alert_dedup.py
```

## Configuration Example

`.env` file:
```bash
# Monitoring alert stabilization
MONITORING_CONSECUTIVE_FAILURES=3    # Require 3 consecutive failures before alert
MONITORING_DEDUP_WINDOW=300          # 5 minutes between same alert type

# Existing monitoring settings
ALERTING_ENABLED=true
CPU_THRESHOLD=80.0
MEMORY_THRESHOLD=85.0
DISK_THRESHOLD=90.0
HEALTH_CHECK_INTERVAL=60            # Check every 60 seconds
```

## Logging

The system logs debug and info messages for troubleshooting:

**Debug logs:**
```
Alert {key} not escalated: 2/3 failures
Alert {key} within dedup window (120.5s < 300s)
Resetting failure count for {key} (was 2)
```

**Info logs:**
```
Escalating alert {key} after 3 consecutive failures
System health check completed: warning
```

## Example Scenarios

### Scenario 1: CPU Transient Spike
```
Check 1: CPU 85% → failure_count=1, no alert (transient warning in health_data)
Check 2: CPU 75% → failure_count=0 (reset), no alert
Check 3: CPU 70% → no issues
```
**Result**: No alerts sent ✅

### Scenario 2: CPU Sustained High Usage
```
Check 1: CPU 85% → failure_count=1, no alert
Check 2: CPU 88% → failure_count=2, no alert  
Check 3: CPU 90% → failure_count=3, ALERT SENT (high severity)
Check 4: CPU 91% → failure_count=4, suppressed (dedup window)
```
**Result**: One alert sent, subsequent checks suppressed ✅

### Scenario 3: Service Degraded Then Failed
```
Check 1: DB response 6000ms → failure_count=1, no alert
Check 2: DB response 7000ms → failure_count=2, no alert
Check 3: DB response 8000ms → failure_count=3, ALERT SENT (medium severity, degraded)
... (5 minutes pass, within dedup window)
Check 10: DB fails → failure_count=1 (new key), no alert
Check 11: DB fails → failure_count=2, no alert
Check 12: DB fails → failure_count=3, ALERT SENT (high severity, failed)
```
**Result**: Two distinct alerts - degraded then failed ✅

## Monitoring Dashboard Integration

The admin dashboard at `/admin/monitoring` will show:

- **Active Alerts**: Only escalated alerts (passed consecutive failure threshold)
- **Transient Issues**: Shown separately or with warning icon
- **Failure Counts**: Display "2/3" for metrics approaching threshold
- **Next Alert Time**: Show when dedup window expires for each alert type

## Best Practices

1. **Tune Thresholds**: Adjust `MONITORING_CONSECUTIVE_FAILURES` based on your check interval
   - 60s interval × 3 checks = 3 minutes to detect sustained issues
   - For faster detection, reduce to 2 checks or decrease interval

2. **Balance Dedup Window**: Balance between preventing spam and staying informed
   - Too short (<5 min): May still get too many alerts
   - Too long (>30 min): May miss escalating issues

3. **Review Transient Alerts**: Check health data for transient alerts to identify intermittent issues

4. **Service-Specific Tuning**: Consider separate thresholds for critical vs non-critical services

5. **Alert Routing**: Use severity levels to route alerts appropriately
   - `high` → Telegram + Email + PagerDuty
   - `medium` → Email only  
   - `warning` → Dashboard only

## Troubleshooting

### Too Many Alerts Still Being Sent

1. Check failure counts are resetting properly when metrics recover
2. Increase `MONITORING_CONSECUTIVE_FAILURES` to 4 or 5
3. Increase `MONITORING_DEDUP_WINDOW` to 600 (10 minutes)
4. Review logs for "Escalating alert" messages

### Important Issues Not Being Alerted

1. Check that consecutive failure threshold isn't too high
2. Verify `ALERTING_ENABLED=true` in config
3. Review failure counts in health data
4. Check alert dedup windows haven't suppressed important alerts
5. Ensure monitoring loop is running (`Health check interval` in logs)

### Inconsistent Health Data

1. Verify `health_data["alerts"]` includes both escalated and transient alerts
2. Check that transient alerts have `transient: true` flag
3. Ensure `_reset_failure_count()` is called when metrics recover

## Future Enhancements

Potential improvements for future versions:

1. **Adaptive Thresholds**: Automatically adjust based on historical patterns
2. **Weighted Severity**: Consider multiple factors (CPU + memory) together
3. **Time-of-Day Awareness**: Different thresholds for peak vs off-peak hours
4. **Alert Correlation**: Detect cascading failures and send single aggregated alert
5. **Self-Healing**: Automatically attempt recovery actions before alerting
6. **Machine Learning**: Predict issues before they reach critical thresholds

## Related Documentation

- [MONITORING.md](MONITORING.md) - Main monitoring system documentation
- [ALERTING.md](ALERTING.md) - Alert routing and notification configuration
- [NOTIFICATION_CENTER.md](NOTIFICATION_CENTER.md) - Notification center UI

## Version History

- **v1.4.0** (2025-01-27): Initial implementation of alert stabilization
  - Added consecutive failure tracking
  - Added deduplication window
  - Added degraded service detection
  - Added comprehensive tests
