# Email Monitoring Documentation

## Overview

The Vertex AR email monitoring system provides comprehensive observability for the email pipeline, including Prometheus metrics, failure rate tracking, automated alerting, and a REST API for monitoring email service health.

## Architecture

### Components

1. **EmailService** (`app/email_service.py`)
   - Core email delivery service with queue management
   - Prometheus metrics instrumentation
   - Failure rate tracking and alerting
   - SMTP integration with retry logic

2. **EmailQueue** (`app/email_service.py`)
   - Priority-based message queuing
   - Exponential backoff retry mechanism
   - Failed message tracking

3. **Monitoring API** (`app/api/monitoring.py`)
   - `/api/monitoring/email-stats` endpoint
   - Admin-protected access
   - Real-time statistics

4. **Background Processor** (`app/main.py`)
   - Async queue processing every 30 seconds
   - Automatic metric updates
   - Failure rate monitoring

## Prometheus Metrics

All email metrics are automatically exported at `/metrics` in Prometheus format.

### Counter Metrics

#### `vertex_ar_email_sent_total`
Total number of emails successfully sent.

**Labels:**
- `priority`: Email priority (1-10, where 1 is highest)

**Example:**
```promql
# Total emails sent
sum(vertex_ar_email_sent_total)

# Emails sent by priority
sum by (priority) (vertex_ar_email_sent_total)
```

#### `vertex_ar_email_failed_total`
Total number of emails that failed to send.

**Labels:**
- `priority`: Email priority (1-10)
- `error_type`: Type of error encountered (e.g., `SMTPException`, `ConnectionError`)

**Example:**
```promql
# Total failed emails
sum(vertex_ar_email_failed_total)

# Failed emails by error type
sum by (error_type) (vertex_ar_email_failed_total)
```

#### `vertex_ar_email_retry_attempts_total`
Total number of email retry attempts.

**Labels:**
- `attempt_number`: Retry attempt number (1, 2, 3)

**Example:**
```promql
# Total retry attempts
sum(vertex_ar_email_retry_attempts_total)

# Retries by attempt number
sum by (attempt_number) (vertex_ar_email_retry_attempts_total)
```

### Gauge Metrics

#### `vertex_ar_email_queue_depth`
Current total depth of email queue (pending + retry queue).

**Example:**
```promql
# Current queue depth
vertex_ar_email_queue_depth

# Alert if queue depth > 100
vertex_ar_email_queue_depth > 100
```

#### `vertex_ar_email_pending_count`
Number of emails currently pending in queue.

**Example:**
```promql
# Pending emails
vertex_ar_email_pending_count
```

#### `vertex_ar_email_failed_count`
Number of emails in permanently failed state.

**Example:**
```promql
# Permanently failed emails
vertex_ar_email_failed_count
```

### Histogram Metrics

#### `vertex_ar_email_send_duration_seconds`
Email send duration distribution in seconds.

**Buckets:** `[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]`

**Example:**
```promql
# Average send duration (last 5 minutes)
rate(vertex_ar_email_send_duration_seconds_sum[5m]) / 
rate(vertex_ar_email_send_duration_seconds_count[5m])

# 95th percentile send duration
histogram_quantile(0.95, 
  rate(vertex_ar_email_send_duration_seconds_bucket[5m])
)

# Emails taking > 10 seconds
rate(vertex_ar_email_send_duration_seconds_bucket{le="10.0"}[5m])
```

## REST API

### GET `/api/monitoring/email-stats`

Get comprehensive email service statistics.

**Authentication:** Admin session required

**Response Structure:**
```json
{
  "success": true,
  "data": {
    "service": {
      "enabled": true,
      "processing": false
    },
    "queue": {
      "pending": 5,
      "retry_queue": 2,
      "permanent_failed": 1,
      "total_sent": 142,
      "total_failed": 8,
      "queue_depth": 7
    },
    "performance": {
      "failure_rate_1h_percent": 5.2,
      "recent_attempts_1h": 25
    },
    "retry_histogram": {
      "1": 3,
      "2": 2,
      "3": 1
    },
    "errors": {
      "last_error": {
        "id": "1234567890_hash",
        "to": ["user@example.com"],
        "subject": "Test Email",
        "error": "SMTP Authentication failed",
        "attempts": 3,
        "created_at": "2025-01-15T10:30:00",
        "next_retry": null
      },
      "recent_errors": [
        // ... list of recent errors
      ]
    },
    "prometheus_metrics": {
      "email_sent_total": 142,
      "email_failed_total": 8,
      "email_queue_depth": 7,
      "email_pending_count": 5,
      "email_failed_count": 1
    }
  },
  "message": "Email service statistics retrieved successfully"
}
```

**Field Descriptions:**

- **service.enabled**: Whether email service is enabled
- **service.processing**: Whether queue is currently being processed
- **queue.pending**: Emails waiting to be sent
- **queue.retry_queue**: Emails scheduled for retry
- **queue.permanent_failed**: Emails that exceeded max retry attempts
- **queue.total_sent**: Total successful sends (lifetime)
- **queue.total_failed**: Total permanent failures (lifetime)
- **queue.queue_depth**: Total queue size (pending + retry)
- **performance.failure_rate_1h_percent**: Failure rate over last hour as percentage
- **performance.recent_attempts_1h**: Number of send attempts in last hour
- **retry_histogram**: Distribution of retry attempts
- **errors.last_error**: Most recent error details
- **errors.recent_errors**: Last 5 errors
- **prometheus_metrics**: Snapshot of current metric values

**Example Usage:**
```bash
curl -X GET "https://your-domain.com/api/monitoring/email-stats" \
  -H "Cookie: authToken=your_session_token"
```

## Automated Alerting

### Failure Rate Alert

The email service automatically monitors failure rate over a rolling 1-hour window. An alert is triggered when:

- **Threshold:** >10% failure rate
- **Minimum Sample:** At least 10 email attempts in the last hour
- **Cooldown:** 1 hour between alerts
- **Alert Type:** `email_failure_rate`
- **Severity:** `high`

The alert is sent via the existing alerting system (Telegram + Email) and includes:
- Current failure rate percentage
- Total attempts
- Number of failures
- Guidance to check SMTP configuration

**Alert Example:**
```
🔴 HIGH

Email delivery failure rate is 15.2% over the last hour.
Total attempts: 65
Failed: 10
Threshold: 10%

Check SMTP configuration and email service logs.
```

## Grafana Dashboards

### Recommended Panels

#### 1. Email Send Rate
```promql
# Send rate (emails/second)
rate(vertex_ar_email_sent_total[5m])
```
**Visualization:** Time series graph

#### 2. Email Failure Rate
```promql
# Failure rate (%)
100 * (
  rate(vertex_ar_email_failed_total[5m]) / 
  (rate(vertex_ar_email_sent_total[5m]) + rate(vertex_ar_email_failed_total[5m]))
)
```
**Visualization:** Time series graph with threshold line at 10%

#### 3. Queue Depth
```promql
# Queue depth over time
vertex_ar_email_queue_depth
```
**Visualization:** Time series graph

#### 4. Email Send Duration (p50, p95, p99)
```promql
# 50th percentile
histogram_quantile(0.50, rate(vertex_ar_email_send_duration_seconds_bucket[5m]))

# 95th percentile
histogram_quantile(0.95, rate(vertex_ar_email_send_duration_seconds_bucket[5m]))

# 99th percentile
histogram_quantile(0.99, rate(vertex_ar_email_send_duration_seconds_bucket[5m]))
```
**Visualization:** Time series graph

#### 5. Failures by Error Type
```promql
# Failures by error type
sum by (error_type) (rate(vertex_ar_email_failed_total[5m]))
```
**Visualization:** Stacked bar chart

#### 6. Retry Attempts
```promql
# Retry attempts by attempt number
sum by (attempt_number) (rate(vertex_ar_email_retry_attempts_total[5m]))
```
**Visualization:** Stacked area chart

#### 7. Service Status
```promql
# Queue depth gauge
vertex_ar_email_queue_depth

# Failed count gauge
vertex_ar_email_failed_count

# Pending count gauge
vertex_ar_email_pending_count
```
**Visualization:** Stat panels

### Complete Dashboard JSON

A complete Grafana dashboard template is available in `docs/grafana/email-monitoring-dashboard.json`.

## PromQL Alert Rules

### High Failure Rate Alert
```yaml
groups:
  - name: email_alerts
    interval: 1m
    rules:
      - alert: HighEmailFailureRate
        expr: |
          100 * (
            rate(vertex_ar_email_failed_total[1h]) / 
            (rate(vertex_ar_email_sent_total[1h]) + rate(vertex_ar_email_failed_total[1h]))
          ) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High email failure rate detected"
          description: "Email failure rate is {{ $value | humanizePercentage }} over the last hour (threshold: 10%)"
```

### Queue Growing Alert
```yaml
      - alert: EmailQueueGrowing
        expr: |
          vertex_ar_email_queue_depth > 50
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Email queue is growing"
          description: "Email queue depth is {{ $value }} (threshold: 50)"
```

### Email Send Slow Alert
```yaml
      - alert: EmailSendSlow
        expr: |
          histogram_quantile(0.95, 
            rate(vertex_ar_email_send_duration_seconds_bucket[5m])
          ) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Email sending is slow"
          description: "95th percentile email send duration is {{ $value }}s (threshold: 10s)"
```

### Emails Permanently Failed Alert
```yaml
      - alert: EmailsPermanentlyFailed
        expr: |
          vertex_ar_email_failed_count > 10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Multiple emails permanently failed"
          description: "{{ $value }} emails have permanently failed"
```

## Configuration

### Environment Variables

```bash
# SMTP Configuration (required for email service)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@your-domain.com

# Admin emails for alerts
ADMIN_EMAILS=admin1@example.com,admin2@example.com
```

### Service Settings

The email service is automatically enabled if SMTP credentials are configured. No additional configuration is required.

**Queue Configuration** (in `email_service.py`):
- `max_size`: 1000 (maximum queue size)
- `max_attempts`: 3 (retry attempts per email)
- `processing_interval`: 30 seconds
- `failure_threshold`: 10% (alert threshold)
- `alert_cooldown`: 1 hour

## Usage Examples

### Send Email via Service

```python
from app.email_service import email_service

# Queue an email
await email_service.send_email(
    to_addresses=["user@example.com"],
    subject="Test Email",
    body="Plain text body",
    html_body="<p>HTML body</p>",  # Optional
    priority=5  # 1-10, lower = higher priority
)
```

### Get Service Statistics

```python
from app.email_service import email_service

stats = await email_service.get_stats()
print(f"Queue depth: {stats['queue']['queue_depth']}")
print(f"Failure rate: {stats['failure_rate_1h']}%")
```

### Check Prometheus Metrics

```python
from app.email_service import email_service

metrics = await email_service.get_prometheus_metrics_snapshot()
print(f"Total sent: {metrics['email_sent_total']}")
print(f"Total failed: {metrics['email_failed_total']}")
```

## Troubleshooting

### High Failure Rate

**Symptoms:**
- Failure rate >10%
- Alerts being sent
- Emails in retry queue

**Possible Causes:**
1. **SMTP Authentication Issues**
   - Check SMTP credentials
   - Verify app passwords are correctly configured
   - Check 2FA settings on email provider

2. **Network Issues**
   - Check DNS resolution
   - Verify firewall allows SMTP port
   - Check network connectivity

3. **Rate Limiting**
   - Email provider may be rate limiting
   - Check daily/hourly sending limits
   - Consider using dedicated email service (SendGrid, SES)

4. **Invalid Recipients**
   - Check recipient email addresses
   - Verify domain DNS records
   - Check for typos in addresses

**Resolution:**
```bash
# Check SMTP connectivity
curl -v telnet://smtp.gmail.com:587

# View recent errors via API
curl -X GET "https://your-domain.com/api/monitoring/email-stats" \
  -H "Cookie: authToken=your_token" | jq '.data.errors.recent_errors'

# Check logs
tail -f vertex-ar/logs/app.log | grep -i email
```

### Queue Growing

**Symptoms:**
- Queue depth increasing
- Emails not being sent
- Processing stuck

**Possible Causes:**
1. **SMTP Server Down**
   - Provider outage
   - Maintenance window

2. **Credentials Expired**
   - App password revoked
   - Account locked

3. **Service Disabled**
   - SMTP settings missing
   - Service not enabled

**Resolution:**
```bash
# Check service status via API
curl -X GET "https://your-domain.com/api/monitoring/email-stats" \
  -H "Cookie: authToken=your_token" | jq '.data.service'

# Check queue depth
curl -X GET "https://your-domain.com/api/monitoring/email-stats" \
  -H "Cookie: authToken=your_token" | jq '.data.queue'

# Restart service if needed
systemctl restart vertex-ar
```

### Slow Email Sending

**Symptoms:**
- High p95/p99 send duration
- Timeouts in logs
- Queue processing slow

**Possible Causes:**
1. **Slow SMTP Server**
   - Provider performance issues
   - Network latency

2. **Large Emails**
   - Heavy HTML content
   - Attachments (if added)

3. **TLS Negotiation**
   - SSL/TLS handshake slow

**Resolution:**
- Monitor send duration metrics
- Consider connection pooling (future enhancement)
- Use dedicated email service for high volume

## Maintenance

### Regular Checks

1. **Daily:**
   - Check failure rate via dashboard
   - Verify queue depth is reasonable (<10)
   - Review recent errors

2. **Weekly:**
   - Review total sent/failed trends
   - Check for retry patterns
   - Verify alerts are working

3. **Monthly:**
   - Review email provider limits
   - Check for credential expiration
   - Update SMTP settings if needed

### Metric Retention

- **Prometheus:** Configure retention based on your setup (default: 15 days)
- **Service History:** Last 1000 send attempts kept in memory
- **Failed Queue:** Cleaned up after 24 hours

## Security Considerations

1. **API Access:**
   - Email stats endpoint requires admin authentication
   - Session-based access control

2. **SMTP Credentials:**
   - Stored in environment variables
   - Never exposed in API responses
   - Use app-specific passwords

3. **Email Content:**
   - No email content logged
   - Only metadata tracked
   - Sensitive data not stored in metrics

4. **Prometheus Metrics:**
   - `/metrics` endpoint is public by default
   - Consider access restrictions in production
   - No sensitive data in metric labels

## Future Enhancements

1. **Connection Pooling:** Reuse SMTP connections
2. **Batch Sending:** Group emails for efficiency
3. **Template System:** Email templates with variables
4. **Attachment Support:** Send files with emails
5. **Delivery Tracking:** Track open/click rates
6. **Bounce Handling:** Process bounce notifications
7. **Priority Lanes:** Separate queues by priority

## Support

For issues or questions:
1. Check logs: `vertex-ar/logs/app.log`
2. Review Prometheus metrics: `/metrics`
3. Check service stats: `/api/monitoring/email-stats`
4. Contact system administrator

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/)
- [SMTP RFC 5321](https://tools.ietf.org/html/rfc5321)
- [Email Best Practices](https://tools.ietf.org/html/rfc5321)
