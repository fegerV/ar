# Deep Resource Diagnostics

## Overview

The Deep Resource Diagnostics system provides comprehensive performance profiling and resource monitoring to help identify bottlenecks, optimize performance, and detect memory leaks.

## Components

### 1. Process History Tracking

Maintains a time-series history of CPU and memory usage for monitored processes.

- **Metric**: CPU percentage and RSS (Resident Set Size) in MB
- **Storage**: Ring buffer of last N snapshots (default: 100)
- **Aggregation**: Calculates average, min, max values and trends
- **Use Case**: Identify processes with unusual resource consumption patterns

### 2. Slow Query Detection

Automatically captures database queries that exceed performance thresholds.

- **Threshold**: Configurable in milliseconds (default: 100ms)
- **Storage**: Top N slowest queries (default: 50)
- **Data**: Query text, duration, parameters, timestamp
- **Use Case**: Database optimization - add indexes, optimize JOINs

### 3. Slow Endpoint Detection

Tracks HTTP requests that exceed acceptable response times.

- **Threshold**: Configurable in milliseconds (default: 1000ms)
- **Storage**: Top N slowest endpoints (default: 50)
- **Data**: HTTP method, path, duration, status code, timestamp
- **Use Case**: API performance optimization, caching opportunities

### 4. Memory Snapshots (Tracemalloc)

Optional Python memory profiling for leak detection.

- **Threshold**: Triggers when memory exceeds limit (default: 100MB)
- **Storage**: Last 20 snapshots
- **Data**: Top N memory allocations by file/line (default: 10)
- **⚠️ Warning**: Adds ~10% overhead - use only for debugging

## Configuration

All settings are configured via environment variables in `.env`:

```bash
# Process history
MONITORING_PROCESS_HISTORY_SIZE=100

# Slow queries
MONITORING_SLOW_QUERY_THRESHOLD_MS=100
MONITORING_SLOW_QUERY_RING_SIZE=50

# Slow endpoints
MONITORING_SLOW_ENDPOINT_THRESHOLD_MS=1000
MONITORING_SLOW_ENDPOINT_RING_SIZE=50

# Memory profiling (disabled by default)
MONITORING_TRACEMALLOC_ENABLED=false
MONITORING_TRACEMALLOC_THRESHOLD_MB=100
MONITORING_TRACEMALLOC_TOP_N=10
```

## API Endpoints

### Get Hotspots

Returns all performance diagnostics data.

```bash
GET /api/monitoring/hotspots
Authorization: Cookie authToken=...
```

**Response**:
```json
{
  "success": true,
  "data": {
    "config": {
      "slow_query_threshold_ms": 100,
      "slow_endpoint_threshold_ms": 1000,
      "tracemalloc_enabled": false
    },
    "diagnostics": {
      "process_trends": { ... },
      "slow_queries": { ... },
      "slow_endpoints": { ... },
      "memory_snapshots": { ... }
    }
  }
}
```

### Get Memory Snapshots

Returns tracemalloc data for memory leak analysis.

```bash
GET /api/monitoring/memory-leaks
Authorization: Cookie authToken=...
```

### Trigger Memory Snapshot

Manually capture a memory snapshot (bypasses threshold).

```bash
POST /api/monitoring/memory-snapshot
Authorization: Cookie authToken=...
```

## Prometheus Metrics

The following metrics are automatically exported at `/metrics`:

```
# Slow queries
vertex_ar_slow_queries_count
vertex_ar_slow_queries_slowest_ms

# Slow endpoints  
vertex_ar_slow_endpoints_count
vertex_ar_slow_endpoints_slowest_ms

# Memory snapshots
vertex_ar_memory_snapshots_count

# Process trends
vertex_ar_process_history_count
vertex_ar_process_trend_cpu_avg{pid}
vertex_ar_process_trend_rss_mb{pid}
```

## Usage Scenarios

### 1. API Performance Optimization

```bash
# Get slow endpoints
curl -H "Cookie: authToken=..." \
  https://yourserver.com/api/monitoring/hotspots

# Analyze the results:
# - Which endpoints are consistently slow?
# - Are there patterns (time of day, specific parameters)?
# - Can results be cached?
```

### 2. Database Query Optimization

```bash
# Get slow queries
curl -H "Cookie: authToken=..." \
  https://yourserver.com/api/monitoring/hotspots

# Actions:
# - Add indexes on frequently filtered columns
# - Optimize N+1 query patterns
# - Use EXPLAIN to analyze query plans
# - Consider query result caching
```

### 3. Memory Leak Detection

```bash
# 1. Enable tracemalloc in .env
MONITORING_TRACEMALLOC_ENABLED=true
MONITORING_TRACEMALLOC_THRESHOLD_MB=50

# 2. Restart the application

# 3. Wait for memory to grow or trigger manually
curl -X POST -H "Cookie: authToken=..." \
  https://yourserver.com/api/monitoring/memory-snapshot

# 4. Analyze snapshots
curl -H "Cookie: authToken=..." \
  https://yourserver.com/api/monitoring/memory-leaks

# 5. Look for:
# - Files/functions with unusually high allocations
# - Growing allocation patterns over time
# - Unexpected objects in memory
```

## Best Practices

### Production Environment

- ✅ **Tracemalloc**: Disabled (`MONITORING_TRACEMALLOC_ENABLED=false`)
- ✅ **Query Threshold**: 100-200ms (balance overhead vs. detail)
- ✅ **Endpoint Threshold**: 1000-2000ms (user-impacting requests)
- ✅ **Ring Size**: Keep defaults (50) for moderate memory usage

### Development/Debugging

- 🔍 **Tracemalloc**: Enable temporarily for leak investigation
- 🔍 **Query Threshold**: Lower to 50ms for more detail
- 🔍 **Ring Size**: Increase to 100+ for more historical data
- 🔍 **Top N**: Increase to 20-50 for tracemalloc detail

### Monitoring Strategy

1. **Regular Reviews**: Check `/api/monitoring/hotspots` weekly
2. **Alerting**: Set up Grafana alerts on `vertex_ar_slow_*` metrics
3. **Trends**: Log historical data to detect performance degradation
4. **Thresholds**: Adjust based on your SLA requirements

## Overhead

The diagnostics system is designed to be lightweight:

- **Process History**: Negligible (<0.1%)
- **Slow Queries**: Minimal (<1%) - only tracks >50ms queries
- **Slow Endpoints**: Minimal (<1%) - automatic via middleware
- **Tracemalloc**: Significant (~10%) - use only when debugging

## Logging

All diagnostic events are logged via structlog:

```
[INFO] Slow query detected query="SELECT * FROM..." duration_ms=234.5
[INFO] Slow endpoint detected method=GET path=/api/users duration_ms=1523.2
[INFO] Memory snapshot taken memory_mb=158.2 threshold_mb=100 top_allocations_count=10
```

## Troubleshooting

### No slow queries/endpoints showing up

- Check thresholds are appropriate for your environment
- Verify application is receiving traffic
- Ensure monitoring is enabled (`ALERTING_ENABLED=true`)

### Tracemalloc not capturing snapshots

- Verify `MONITORING_TRACEMALLOC_ENABLED=true`
- Check current memory usage vs. threshold
- Try manually triggering via POST endpoint

### High memory usage from diagnostics

- Reduce ring buffer sizes
- Disable tracemalloc
- Lower retention periods

## See Also

- [Monitoring Implementation](./implementation.md) - Full monitoring system
- [Alert Stabilization](./alert-stabilization.md) - Alert configuration
- [Web Health Checks](./web-health-check.md) - Service health monitoring
