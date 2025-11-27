# Monitoring Alert Stabilization - Implementation Summary

## Ticket: Stabilize monitoring alerts

### Changes Completed ✅

#### 1. Configuration (`app/config.py`)
Added two new configuration settings:
- `MONITORING_CONSECUTIVE_FAILURES` (default: 3) - Number of consecutive failures before escalating to alert
- `MONITORING_DEDUP_WINDOW` (default: 300 seconds) - Deduplication window to suppress repeated alerts

#### 2. SystemMonitor Enhancement (`app/monitoring.py`)
**Instance Variables:**
- `failure_counts: Dict[str, int]` - Tracks consecutive failures per metric/service
- `consecutive_failure_threshold: int` - From config, defaults to 3
- `dedup_window: int` - From config, defaults to NOTIFICATION_DEDUP_WINDOW (300s)
- Enhanced `last_alerts: Dict[str, datetime]` - Now actively used for deduplication

**New Helper Methods:**
- `_should_escalate_alert(alert_key: str) -> bool`
  - Increments failure count
  - Checks consecutive failure threshold (3 by default)
  - Checks deduplication window (5 minutes by default)
  - Returns True only if alert should be sent
  
- `_reset_failure_count(alert_key: str) -> None`
  - Resets failure count when metric/service recovers
  - Called when values return below thresholds

- `_determine_severity(metric_type: str, value: float, threshold: float) -> str`
  - Calculates severity based on threshold overshoot
  - Returns "warning" (just over), "medium" (5-15% over), or "high" (>15% over or >95% absolute)

**Updated `check_system_health()` Method:**
Modified alert logic for all monitored resources:
- **CPU checks** - Track consecutive failures, reset on recovery
- **Memory checks** - Track consecutive failures, reset on recovery  
- **Disk checks** - Track consecutive failures, reset on recovery
- **Service health checks** - Track failures per service, distinguish degraded (slow) vs failed
- **External services** - Track consecutive failures per service
- **Error logs** - Track consecutive high error counts

**Alert Behavior Changes:**
- Before escalation: Adds transient alert to `health_data["alerts"]` with `transient: true` flag
- After escalation: Sends alert via `alert_manager` and adds non-transient alert to `health_data["alerts"]`
- Ensures Notification Center view matches actual alerts sent

#### 3. Environment Configuration (`.env.example`)
Added new section "System Monitoring and Alerting" with:
```bash
ALERTING_ENABLED=true
CPU_THRESHOLD=80.0
MEMORY_THRESHOLD=85.0
DISK_THRESHOLD=90.0
HEALTH_CHECK_INTERVAL=60
MONITORING_CONSECUTIVE_FAILURES=3
MONITORING_DEDUP_WINDOW=300
WEEKLY_REPORT_DAY=monday
WEEKLY_REPORT_TIME=09:00
```

#### 4. Comprehensive Tests (`test_monitoring_alert_dedup.py`)
Created full test suite with 12 test cases:
- ✅ Single spike doesn't escalate
- ✅ Two consecutive spikes don't escalate
- ✅ Three consecutive spikes DO escalate
- ✅ Failure count resets on recovery
- ✅ Deduplication window works correctly
- ✅ Severity levels (warning/medium/high) determined correctly
- ✅ Single CPU spike doesn't send alert
- ✅ Sustained CPU issue sends alert after 3 checks
- ✅ Degraded service gets warning, failed service gets high severity
- ✅ Multiple metrics track independently

All tests pass successfully.

#### 5. Documentation (`MONITORING_ALERT_STABILIZATION.md`)
Created comprehensive documentation including:
- Feature overview
- Configuration guide
- Implementation details
- Tracked metrics list
- Testing instructions
- Example scenarios
- Best practices
- Troubleshooting guide

### Key Features Implemented

#### 1. Consecutive Failure Tracking
- Single noisy samples or transient spikes no longer trigger alerts
- Alerts only sent after N consecutive failures (default: 3)
- Each metric/service tracks failures independently
- Failure counts reset when metrics return to healthy state

#### 2. Alert Deduplication
- Uses existing `NOTIFICATION_DEDUP_WINDOW` config (300 seconds by default)
- Can be overridden with `MONITORING_DEDUP_WINDOW`
- Prevents same alert type from being sent multiple times within window
- Dedup tracked per alert key (e.g., "high_cpu", "service_database")

#### 3. Degraded Service Detection
- Services now classified with granular severity:
  - **Warning**: Just over threshold, transient issue, or degraded but working
  - **Medium**: Moderately degraded (5-15% overshoot)
  - **High**: Critical failure (>15% overshoot or >95% absolute)
- Slow service response (>5000ms) gets "warning"→"medium" (degraded)
- Complete service failure gets "high" severity

#### 4. Health Data Consistency
- `health_data["alerts"]` now mirrors what's sent through `alert_manager`
- Transient issues (not yet escalated) marked with `transient: true` flag
- Escalated alerts include full severity and no transient flag
- Notification Center view stays consistent with actual alerts

### Tracked Metrics

**System Resources:**
- `high_cpu` - CPU usage
- `high_memory` - Memory usage
- `high_disk` - Disk usage

**Core Services:**
- `service_database` - Database connectivity
- `service_storage` - Storage system
- `service_minio` - MinIO/S3 (if configured)
- `service_web_server` - Web server health
- `service_*_slow` - Degraded performance

**External Services:**
- `external_email` - SMTP server
- `external_telegram` - Telegram API

**System Health:**
- `high_error_count` - Error log volume
- `monitoring_failure` - Monitoring system itself

### Testing Results

All tests pass successfully:
```bash
cd vertex-ar
python test_monitoring_alert_dedup.py
```

Output confirms:
- Single noisy samples do not trigger alerts ✅
- Sustained issues (3+ consecutive failures) do trigger alerts ✅
- Deduplication window prevents alert spam ✅
- Degraded services get warning severity ✅
- Failed services get high severity ✅
- Multiple metrics track independently ✅
- health_data["alerts"] mirrors sent alerts ✅

### Example Scenarios

**Scenario 1: Transient CPU Spike (No Alert)**
```
Check 1: CPU 85% → failure_count=1, no alert sent
Check 2: CPU 75% → failure_count=0 (reset), no alert
Result: No alerts sent ✅
```

**Scenario 2: Sustained CPU Issue (Alert Sent)**
```
Check 1: CPU 85% → failure_count=1, no alert
Check 2: CPU 88% → failure_count=2, no alert
Check 3: CPU 90% → failure_count=3, ALERT SENT ✅
Check 4: CPU 91% → suppressed (dedup window)
Result: One alert sent, spam prevented ✅
```

**Scenario 3: Service Degraded Then Failed**
```
Checks 1-3: DB slow (6-8s) → ALERT "degraded" (medium)
... (5 min passes)
Checks 10-12: DB fails → ALERT "failed" (high)
Result: Two distinct alerts - degraded, then failed ✅
```

### Log Output

The system provides helpful debug and info logs:
```
DEBUG: Alert high_cpu not escalated: 2/3 failures
DEBUG: Alert high_cpu within dedup window (120.5s < 300s)
DEBUG: Resetting failure count for high_cpu (was 2)
INFO:  Escalating alert high_cpu after 3 consecutive failures
INFO:  System health check completed: warning
```

### Configuration Recommendations

**Development:**
```bash
MONITORING_CONSECUTIVE_FAILURES=2  # Faster detection
MONITORING_DEDUP_WINDOW=120        # 2 minutes
HEALTH_CHECK_INTERVAL=30           # Check every 30s
```

**Production:**
```bash
MONITORING_CONSECUTIVE_FAILURES=3  # Default
MONITORING_DEDUP_WINDOW=300        # 5 minutes
HEALTH_CHECK_INTERVAL=60           # Check every minute
```

**High-Traffic Systems:**
```bash
MONITORING_CONSECUTIVE_FAILURES=5  # More tolerance
MONITORING_DEDUP_WINDOW=600        # 10 minutes
HEALTH_CHECK_INTERVAL=120          # Check every 2 minutes
```

### Acceptance Criteria Met ✅

1. ✅ Used `SystemMonitor.last_alerts` field for deduplication
2. ✅ Implemented rolling counter via `failure_counts` dictionary
3. ✅ Track consecutive failures per service/metric
4. ✅ Only escalate after N consecutive failures
5. ✅ Honor configurable deduplication window (NOTIFICATION_DEDUP_WINDOW)
6. ✅ Downgrade alerts to "warning" when degraded but not failed
7. ✅ Ensure `health_data["alerts"]` mirrors `alert_manager` sends
8. ✅ Added targeted tests with stubbed `alert_manager.send_alert`
9. ✅ Confirmed single noisy sample doesn't produce alerts
10. ✅ Confirmed sustained issues still do produce alerts
11. ✅ Alert entries in Notification Center correspond to sustained problems only
12. ✅ Log output shows deduplication behavior per threshold

### Files Changed

1. `/home/engine/project/vertex-ar/app/monitoring.py` - Core implementation
2. `/home/engine/project/vertex-ar/app/config.py` - Configuration settings
3. `/home/engine/project/vertex-ar/.env.example` - Environment template
4. `/home/engine/project/vertex-ar/test_monitoring_alert_dedup.py` - Comprehensive tests
5. `/home/engine/project/vertex-ar/MONITORING_ALERT_STABILIZATION.md` - Full documentation
6. `/home/engine/project/vertex-ar/MONITORING_ALERT_STABILIZATION_SUMMARY.md` - This file

### Next Steps

The implementation is complete and tested. To deploy:

1. Update `.env` file with new configuration values
2. Restart the application to load new settings
3. Monitor logs for "Escalating alert" messages
4. Adjust thresholds based on actual system behavior
5. Review Notification Center to verify transient vs escalated alerts

### Benefits

- **Reduced Alert Noise**: Single spikes no longer trigger alerts
- **Improved Signal-to-Noise**: Only sustained issues generate alerts
- **Better Severity Levels**: Warning vs medium vs high based on actual impact
- **Consistent UI**: Notification Center matches alert_manager behavior
- **Configurable Behavior**: Easy to tune via environment variables
- **Comprehensive Testing**: Full test coverage ensures reliability
- **Well Documented**: Clear documentation for operators and developers

### Version

This feature is part of version **v1.4.0** of Vertex AR.
