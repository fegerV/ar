# Web Server Health Check Improvements

## Overview

Enhanced the web server health monitoring system to eliminate false alerts when the FastAPI application is healthy but `BASE_URL` points to an external domain with TLS/host mismatch issues.

## Problem Statement

Previously, the monitoring system would raise "web_server not responding" alerts even when the FastAPI application was running and healthy. This occurred when:

- `BASE_URL` pointed to an external domain (e.g., `https://yourdomain.com`)
- TLS/SSL certificate verification failed
- Host mismatch prevented the health check from reaching the local server
- Rate limiting blocked health check requests
- DNS resolution issues prevented connection

## Solution

Implemented a comprehensive fallback and diagnostic system that:

1. **Attempts Multiple URLs**: Tries configured URLs in priority order before declaring service down
2. **Records Detailed Diagnostics**: Captures exception messages and response times for each attempt
3. **Uses Process/Port Diagnostics**: Leverages psutil and socket to verify service status independently of HTTP
4. **Provides Actionable Information**: Returns structured data to help diagnose the actual issue

## Configuration

### Health Check Environment Variables

Added to `.env.example`:

```bash
# Internal health check URL (optional)
# Used for web server health monitoring when BASE_URL points to an external domain
# If blank, system will auto-build from APP_HOST/APP_PORT (e.g., http://localhost:8000)
INTERNAL_HEALTH_URL=

# Health check request timeout in seconds (default: 5)
# Max time to wait for /health endpoint response
WEB_HEALTH_CHECK_TIMEOUT=5

# Use HEAD requests for health checks (default: false)
# HEAD requests are lighter than GET (no response body)
# Enable to reduce monitoring load on high-traffic systems
WEB_HEALTH_CHECK_USE_HEAD=false

# Cooldown between health checks in seconds (default: 30)
# Minimum time between consecutive health check attempts
# Prevents monitoring from overwhelming the server
WEB_HEALTH_CHECK_COOLDOWN=30
```

### Configuration in `app/config.py`

```python
self.INTERNAL_HEALTH_URL = os.getenv("INTERNAL_HEALTH_URL", "")
self.APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
self.APP_PORT = int(os.getenv("APP_PORT", "8000"))

# Web server health check tuning
self.WEB_HEALTH_CHECK_TIMEOUT = int(os.getenv("WEB_HEALTH_CHECK_TIMEOUT", "5"))
self.WEB_HEALTH_CHECK_USE_HEAD = os.getenv("WEB_HEALTH_CHECK_USE_HEAD", "false").lower() == "true"
self.WEB_HEALTH_CHECK_COOLDOWN = int(os.getenv("WEB_HEALTH_CHECK_COOLDOWN", "30"))
```

## Implementation Details

### URL Attempt Priority

The health check attempts URLs in this order:

1. **INTERNAL_HEALTH_URL** (if configured) - e.g., `http://localhost:8000/health`
2. **BASE_URL** (public URL) - e.g., `https://yourdomain.com/health`
3. **localhost fallback** - `http://localhost:{APP_PORT}/health`
4. **127.0.0.1 fallback** - `http://127.0.0.1:{APP_PORT}/health`

Stops at first successful response (HTTP 200).

### Structured Diagnostics

Each attempt records:

```json
{
  "type": "localhost",
  "url": "http://localhost:8000/health",
  "success": true,
  "error": null,
  "response_time_ms": 45.23,
  "status_code": 200
}
```

### Process Diagnostics (psutil)

Checks if uvicorn/gunicorn process is running:

```json
{
  "running": true,
  "pid": 12345,
  "name": "uvicorn",
  "cpu_percent": 5.2,
  "memory_mb": 150.5,
  "num_threads": 4,
  "create_time": "2025-01-27T10:30:00"
}
```

### Port Diagnostics (socket)

Checks if the configured port is accepting connections:

```json
{
  "port": 8000,
  "accepting_connections": true,
  "status": "open"
}
```

### Complete Response Structure

```json
{
  "healthy": true,
  "response_time_ms": 45.23,
  "status": "operational",
  "status_code": 200,
  "check_method": "GET",
  "successful_url": "http://localhost:8000/health",
  "successful_url_type": "localhost",
  "attempts": [
    {
      "type": "public",
      "url": "https://yourdomain.com/health",
      "success": false,
      "error": "SSL/TLS error: certificate verify failed",
      "response_time_ms": null,
      "status_code": null,
      "method": "GET"
    },
    {
      "type": "localhost",
      "url": "http://localhost:8000/health",
      "success": true,
      "error": null,
      "response_time_ms": 45.23,
      "status_code": 200,
      "method": "GET"
    }
  ],
  "process_info": {
    "running": true,
    "pid": 12345,
    "name": "uvicorn"
  },
  "port_info": {
    "port": 8000,
    "accepting_connections": true,
    "status": "open"
  }
}
```

**New Fields:**
- `check_method`: The HTTP method used for health checks ("GET" or "HEAD")
- `method` in each attempt: Shows which method was used for that specific attempt

## Status Determination

### Healthy (`status: "operational"`)

- At least one URL returned HTTP 200
- Response time recorded from successful attempt

### Degraded (`status: "degraded"`)

- All HTTP attempts failed
- BUT process is running AND port is accepting connections
- Indicates service is up but health endpoint not responding

### Failed (`status: "failed"`)

- All HTTP attempts failed
- Process not running OR port not accepting connections
- Service is genuinely down

## API Exposure

The enhanced diagnostics are automatically exposed through existing monitoring endpoints:

### `/api/monitoring/metrics`

Returns full service health including web_server diagnostics:

```json
{
  "success": true,
  "data": {
    "services": {
      "web_server": {
        "healthy": true,
        "attempts": [...],
        "process_info": {...},
        "port_info": {...}
      }
    }
  }
}
```

### `/api/monitoring/detailed-metrics`

Includes web_server status in comprehensive system overview.

## Testing

### Unit Tests

Comprehensive unit tests in `tests/test_monitoring.py` verify:

- ✅ Successful health check on public URL (no fallback needed)
- ✅ Fallback to localhost when public URL fails (SSL error)
- ✅ All attempts fail but diagnostics show service running (degraded)
- ✅ All attempts fail and service is down (failed)
- ✅ INTERNAL_HEALTH_URL takes priority when configured
- ✅ Timeout errors are properly recorded
- ✅ HTTP error status codes are captured
- ✅ Process detection (uvicorn/gunicorn)
- ✅ Port status checking (open/closed)
- ✅ Structured error output for all attempts
- ✅ No duplicate localhost URLs in attempts list

Run tests:

```bash
cd vertex-ar
python -m pytest tests/test_monitoring.py -v
```

### Manual Testing

Test script to reproduce and verify the fix:

```bash
cd vertex-ar
python test_web_health_check.py
```

This script:
- Shows current configuration
- Calls `system_monitor.get_service_health()`
- Displays formatted diagnostics
- Provides interpretation and recommendations
- Outputs raw JSON for debugging

## Usage Scenarios

### Scenario 1: Production with External Domain

**Configuration:**
```env
BASE_URL=https://yourdomain.com
INTERNAL_HEALTH_URL=http://localhost:8000
```

**Result:**
- INTERNAL_HEALTH_URL checked first (fast, reliable)
- Public URL checked second (may fail with TLS but won't false-alert)
- No false alerts even if public URL has certificate issues

### Scenario 2: Development/Staging

**Configuration:**
```env
BASE_URL=http://localhost:8000
INTERNAL_HEALTH_URL=
```

**Result:**
- BASE_URL checked (works fine for localhost)
- No duplicates in attempts list
- Fast health checks

### Scenario 3: Docker with External Load Balancer

**Configuration:**
```env
BASE_URL=https://api.example.com
INTERNAL_HEALTH_URL=http://127.0.0.1:8000
```

**Result:**
- Internal check hits container directly
- External check validates load balancer path
- Both metrics available for monitoring

## Notification Center Integration

The Notification Center automatically displays:

1. **Real-time Health Status**: Shows web_server as healthy/degraded/failed
2. **Diagnostic Details**: Expands to show all attempt results
3. **Process/Port Info**: Shows whether service is actually running
4. **Actionable Errors**: Displays specific error messages (SSL, timeout, etc.)

**No false alerts** when service is healthy but external URL unreachable.

## Best Practices

1. **Set INTERNAL_HEALTH_URL in production** to skip unnecessary external URL attempts
2. **Monitor degraded status** - indicates service is running but HTTP health check failed
3. **Review attempt diagnostics** to identify root cause of failures
4. **Check process_info and port_info** when troubleshooting
5. **Use structured logs** - all diagnostics are logged with exception details

## Monitoring & Alerting

The alert system respects the new diagnostics:

- **No alert** if any URL succeeds (even via fallback)
- **Degraded alert** if HTTP fails but process is running
- **Critical alert** only if service is genuinely down

Alert deduplication and consecutive failure tracking still apply (see MONITORING_ALERT_STABILIZATION.md).

## Backward Compatibility

All changes are backward compatible:

- ✅ Existing health checks continue to work
- ✅ INTERNAL_HEALTH_URL is optional
- ✅ API responses include new fields but don't break existing consumers
- ✅ Old simple health status still available in `healthy` field

## Files Changed

### Core Implementation
- `vertex-ar/app/config.py` - Added INTERNAL_HEALTH_URL, APP_HOST, APP_PORT config
- `vertex-ar/app/monitoring.py` - Enhanced `_check_web_server_health()` with fallback and diagnostics
- `.env.example` - Documented INTERNAL_HEALTH_URL setting

### Testing
- `vertex-ar/tests/test_monitoring.py` - Comprehensive unit tests (13 tests)
- `vertex-ar/test_web_health_check.py` - Manual reproduction/verification script

### Documentation
- `vertex-ar/WEB_HEALTH_CHECK_IMPROVEMENTS.md` - This file

## Related Documentation

- `MONITORING_ALERT_STABILIZATION.md` - Alert deduplication and consecutive failure tracking
- `DEPENDENCIES.md` - Dependencies including psutil for process diagnostics

## Future Enhancements

Potential improvements for future versions:

1. **Configurable timeout per URL** - Allow different timeouts for external vs internal checks
2. **Health check result caching** - Cache successful results briefly to reduce overhead
3. **Custom health endpoints** - Support different health endpoints for different services
4. **Metrics export** - Export health check metrics to Prometheus
5. **WebSocket health** - Check WebSocket connections in addition to HTTP
