# Uvicorn Server Tuning

<cite>
**Referenced Files in This Document**   
- [uvicorn-tuning.md](file://docs/deployment/uvicorn-tuning.md)
- [UVICORN_TUNING_IMPLEMENTATION.md](file://docs/releases/UVICORN_TUNING_IMPLEMENTATION.md)
- [config.py](file://vertex-ar/app/config.py)
- [start.sh](file://vertex-ar/start.sh)
- [app.env.example](file://vertex-ar/.env.example)
- [app.env.production.example](file://vertex-ar/.env.production.example)
- [monitoring.py](file://vertex-ar/app/monitoring.py)
- [api/monitoring.py](file://vertex-ar/app/api/monitoring.py)
- [test_uvicorn_config.py](file://test_files/unit/test_uvicorn_config.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Configuration Reference](#configuration-reference)
3. [Worker Sizing](#worker-sizing)
4. [Connection Management](#connection-management)
5. [Graceful Shutdown and Proxy Headers](#graceful-shutdown-and-proxy-headers)
6. [Health Check Optimization](#health-check-optimization)
7. [Deployment Integration](#deployment-integration)
8. [Tuning Scenarios](#tuning-scenarios)
9. [Performance Benchmarks](#performance-benchmarks)
10. [Monitoring & Validation](#monitoring--validation)
11. [Troubleshooting](#troubleshooting)
12. [Conclusion](#conclusion)

## Introduction
This document provides comprehensive guidance for tuning Uvicorn server settings in the Vertex AR application. The configuration covers critical parameters such as worker count, connection persistence, concurrency limits, connection queuing, proxy header handling, and graceful shutdown behavior. The tuning framework enables optimization across various deployment scales—from development environments to high-traffic production systems—while balancing throughput, resource consumption, and reliability. This documentation details configuration options, real-world scenarios, performance benchmarks, monitoring strategies, and troubleshooting guidance to ensure optimal Uvicorn performance.

**Section sources**
- [uvicorn-tuning.md](file://docs/deployment/uvicorn-tuning.md#L1-L623)
- [UVICORN_TUNING_IMPLEMENTATION.md](file://docs/releases/UVICORN_TUNING_IMPLEMENTATION.md#L1-L269)

## Configuration Reference
The Vertex AR application exposes several Uvicorn-specific environment variables that control server behavior. These settings are loaded via the application's configuration layer and applied during startup.

| Setting | Default | Description |
|---------|---------|-------------|
| `UVICORN_WORKERS` | `(2 * CPU cores) + 1` | Number of worker processes |
| `UVICORN_KEEPALIVE_TIMEOUT` | `5` | Keep-alive timeout in seconds |
| `UVICORN_TIMEOUT_KEEP_ALIVE` | `5` | Alternative keep-alive setting |
| `UVICORN_LIMIT_CONCURRENCY` | `0` (unlimited) | Max concurrent connections per worker |
| `UVICORN_BACKLOG` | `2048` | Connection queue size |
| `UVICORN_PROXY_HEADERS` | `true` | Enable X-Forwarded-* header parsing |
| `UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN` | `30` | Graceful shutdown timeout in seconds |

Additional health check tuning parameters include:
- `WEB_HEALTH_CHECK_TIMEOUT`: Health check request timeout in seconds (default: 5)
- `WEB_HEALTH_CHECK_USE_HEAD`: Use HEAD instead of GET for health checks (default: false)
- `WEB_HEALTH_CHECK_COOLDOWN`: Minimum seconds between health checks (default: 30)

These settings are implemented in the application's configuration module and respected across all deployment methods including direct execution, Docker, systemd, and orchestration platforms.

**Section sources**
- [config.py](file://vertex-ar/app/config.py#L209-L225)
- [uvicorn-tuning.md](file://docs/deployment/uvicorn-tuning.md#L20-L31)
- [UVICORN_TUNING_IMPLEMENTATION.md](file://docs/releases/UVICORN_TUNING_IMPLEMENTATION.md#L19-L30)

## Worker Sizing
Worker sizing is critical for balancing CPU utilization, memory consumption, and request throughput. The Vertex AR application implements an intelligent default calculation while allowing explicit overrides.

### Default Calculation
The default worker count follows the industry-standard formula:
```
workers = (2 * CPU_cores) + 1
```

This formula is implemented in both the configuration layer and startup scripts:
```python
import psutil
cpu_count = psutil.cpu_count() or 1
default_workers = (2 * cpu_count) + 1
```

**Rationale:**
- 2× cores handles both CPU-bound and I/O-bound tasks effectively
- +1 ensures at least one worker is available during reloads or restarts
- Validated across systems with 1-64 cores

### CPU Core Examples
| CPU Cores | Default Workers | Memory Usage (est.) |
|-----------|----------------|---------------------|
| 1 | 3 | ~600 MB |
| 2 | 5 | ~1 GB |
| 4 | 9 | ~1.8 GB |
| 8 | 17 | ~3.4 GB |
| 16 | 33 | ~6.6 GB |

*Memory estimates assume ~200 MB per worker under typical load*

### Override Configuration
The worker count can be explicitly set via environment variable:
```bash
# .env file
UVICORN_WORKERS=12  # Explicit worker count
```

### Adjustment Guidelines
**Increase workers when:**
- CPU utilization < 70% but request queue growing
- High throughput requirements (1000+ req/sec)
- Sufficient RAM available (200-300 MB per worker)
- Horizontal scaling is not feasible

**Decrease workers when:**
- Memory constrained environments
- Low traffic sites (< 100 req/sec)
- Database connection pool limits
- Development/testing environments

The deployment script includes safeguards to cap worker counts on large machines to prevent resource exhaustion.

**Section sources**
- [config.py](file://vertex-ar/app/config.py#L210-L214)
- [start.sh](file://vertex-ar/start.sh#L34-L35)
- [uvicorn-tuning.md](file://docs/deployment/uvicorn-tuning.md#L40-L86)
- [test_uvicorn_config.py](file://test_files/unit/test_uvicorn_config.py#L42-L109)

## Connection Management
Effective connection management ensures optimal resource utilization and prevents service degradation under load.

### Keep-Alive Timeout
Controls how long idle connections are kept open:
```bash
UVICORN_KEEPALIVE_TIMEOUT=5     # Default: 5 seconds
UVICORN_TIMEOUT_KEEP_ALIVE=5    # Same setting (use either)
```

**Tuning Guidelines:**
- **High-traffic sites (5-15s):** Reduce connection overhead for frequent clients
- **Low-traffic sites (2-3s):** Free resources quickly
- **Behind load balancer (30-60s):** Match LB timeout to prevent premature closure

### Concurrency Limits
Limits concurrent connections per worker:
```bash
UVICORN_LIMIT_CONCURRENCY=1000  # 0 = unlimited
```

**Use Cases:**
- **API rate limiting:** Prevent overload from burst traffic
- **Resource protection:** Cap connections to prevent memory exhaustion
- **SLA enforcement:** Ensure fair resource distribution

**Capacity Calculation:**
```
total_capacity = UVICORN_WORKERS * UVICORN_LIMIT_CONCURRENCY
```

Example: 8 workers × 500 concurrency = 4000 max concurrent requests

### Connection Backlog
Queue size for pending connections:
```bash
UVICORN_BACKLOG=2048  # Default: 2048
```

**Tuning Guidelines:**
- **High-traffic (4096-8192):** Handle traffic spikes without dropping connections
- **Low-traffic (1024):** Reduce memory footprint
- **Kubernetes (512-1024):** Let service mesh handle queuing

### Proxy Headers
Enable when behind reverse proxy (Nginx, HAProxy, etc.):
```bash
UVICORN_PROXY_HEADERS=true  # Default: enabled
```

**What it does:**
- Parses `X-Forwarded-For` for real client IP
- Parses `X-Forwarded-Proto` for original protocol (http/https)
- Parses `X-Forwarded-Host` for original host header

**Disable only if:**
- Running without reverse proxy (direct public exposure)
- Proxy headers not trusted (security concern)

**Section sources**
- [config.py](file://vertex-ar/app/config.py#L215-L219)
- [start.sh](file://vertex-ar/start.sh#L49-L59)
- [uvicorn-tuning.md](file://docs/deployment/uvicorn-tuning.md#L88-L152)

## Graceful Shutdown and Proxy Headers
Proper configuration of graceful shutdown and proxy headers ensures reliable service restarts and accurate request metadata.

### Graceful Shutdown
Time to wait for active requests during shutdown:
```bash
UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=30  # Default: 30 seconds
```

**Tuning Guidelines:**
- **Long-running uploads (60-120s):** Allow file uploads to complete
- **Video processing (120-300s):** Let AR generation finish
- **Quick APIs (10-15s):** Fast restarts for deployments

The graceful shutdown timeout is synchronized with Supervisor's `stopwaitsecs` parameter to prevent premature termination.

### Proxy Headers
As mentioned in the connection management section, `UVICORN_PROXY_HEADERS=true` enables parsing of reverse proxy headers. This is essential in production deployments where Nginx or similar proxies handle SSL termination and load balancing.

The setting ensures that:
- Client IP addresses are preserved for logging and rate limiting
- Original protocol (HTTP/HTTPS) is maintained for redirect logic
- Host headers are preserved for multi-tenant scenarios

**Section sources**
- [config.py](file://vertex-ar/app/config.py#L219-L220)
- [start.sh](file://vertex-ar/start.sh#L61)
- [uvicorn-tuning.md](file://docs/deployment/uvicorn-tuning.md#L153-L165)

## Health Check Optimization
Health check configuration prevents monitoring systems from amplifying load during incidents and reduces operational overhead.

### Request Timeout
Control how long monitoring waits for health response:
```bash
WEB_HEALTH_CHECK_TIMEOUT=5  # Default: 5 seconds
```

**Tuning:**
- **High-load systems (10-15s):** Prevent false failures under load
- **Fast environments (2-3s):** Quick failure detection
- **Match application P99:** Set to P99 response time + buffer

### HEAD vs GET Requests
Use lightweight HEAD requests for health checks:
```bash
WEB_HEALTH_CHECK_USE_HEAD=false  # Default: disabled (uses GET)
```

**Enable HEAD when:**
- High-frequency health checks (< 10s interval)
- Limited bandwidth
- Health endpoint returns large response body
- Monitoring load is measurable (> 5% of total requests)

**Benefits:**
- ~70% reduction in bandwidth usage
- ~40% faster response time
- Reduced server-side processing

**Trade-offs:**
- Doesn't verify response body
- Some proxies don't cache HEAD responses
- Not all health libraries support HEAD

### Check Cooldown
Minimum time between health check attempts:
```bash
WEB_HEALTH_CHECK_COOLDOWN=30  # Default: 30 seconds
```

**Prevents:**
- Monitoring amplifying load during incidents
- Unnecessary network traffic
- False positive cascades

**Adjust based on:**
- Alert SLA requirements
- System stability
- Available bandwidth

The health check implementation includes process and port verification when HTTP checks fail, providing comprehensive diagnostics.

**Section sources**
- [config.py](file://vertex-ar/app/config.py#L222-L225)
- [monitoring.py](file://vertex-ar/app/monitoring.py#L43-L44)
- [api/monitoring.py](file://vertex-ar/app/api/monitoring.py#L120-L138)
- [uvicorn-tuning.md](file://docs/deployment/uvicorn-tuning.md#L166-L222)

## Deployment Integration
Uvicorn settings are integrated across multiple deployment methods, ensuring consistent behavior regardless of deployment platform.

### Makefile
Production run target with full tuning:
```bash
make run-production
```

Development mode (single worker, reload enabled):
```bash
make run
```

### start.sh Script
The startup script automatically:
1. Loads `.env` file
2. Calculates default workers from CPU count
3. Builds uvicorn command with all flags
4. Uses reload mode in development, multi-worker in production

```bash
./start.sh
```

### Docker
The Docker image uses environment variables for configuration:
```dockerfile
CMD uvicorn app.main:app \
    --host ${APP_HOST:-0.0.0.0} \
    --port ${APP_PORT:-8000} \
    --workers ${UVICORN_WORKERS:-...} \
    ...
```

Set via docker-compose or Kubernetes environment:
```yaml
environment:
  - UVICORN_WORKERS=12
  - UVICORN_BACKLOG=4096
```

### Deployment Script
The improved deployment script:
1. Reads tuning settings from `.env`
2. Generates Supervisor configuration with optimized flags
3. Validates settings before deployment
4. Logs applied configuration

```bash
sudo ./deploy-vertex-ar-cloud-ru-improved.sh
```

### Supervisor Configuration
Generated config respects all tuning settings:
```ini
[program:vertex-ar]
command=/path/to/venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 9 \
    --timeout-keep-alive 5 \
    --backlog 2048 \
    --proxy-headers \
    --timeout-graceful-shutdown 30
stopwaitsecs=30
```

**Section sources**
- [start.sh](file://vertex-ar/start.sh#L43-L69)
- [deploy-vertex-ar-cloud-ru-improved.sh](file://deploy-vertex-ar-cloud-ru-improved.sh#L776-L880)
- [uvicorn-tuning.md](file://docs/deployment/uvicorn-tuning.md#L223-L298)

## Tuning Scenarios
Optimal configurations for common deployment scenarios.

### High-Traffic Production (1000+ req/sec)
Optimize for throughput:
```bash
# .env
UVICORN_WORKERS=17              # 8-core server
UVICORN_LIMIT_CONCURRENCY=1000  # Per worker
UVICORN_BACKLOG=8192            # Large queue
UVICORN_KEEPALIVE_TIMEOUT=15    # Keep connections open
UVICORN_PROXY_HEADERS=true      # Behind Nginx
WEB_HEALTH_CHECK_USE_HEAD=true  # Reduce monitoring load
WEB_HEALTH_CHECK_COOLDOWN=60    # Less frequent checks
```
**Expected capacity:** 17,000 concurrent requests

### Memory-Constrained (< 2 GB RAM)
Optimize for low memory footprint:
```bash
# .env
UVICORN_WORKERS=3               # Minimum viable
UVICORN_LIMIT_CONCURRENCY=100   # Cap per worker
UVICORN_BACKLOG=512             # Small queue
UVICORN_KEEPALIVE_TIMEOUT=2     # Free connections quickly
WEB_HEALTH_CHECK_COOLDOWN=60    # Reduce monitoring overhead
```
**Expected capacity:** 300 concurrent requests, ~600 MB RAM

### Long-Running Requests (uploads, video processing)
Optimize for request completion:
```bash
# .env
UVICORN_WORKERS=5                        # Moderate count
UVICORN_LIMIT_CONCURRENCY=50             # Low concurrency per worker
UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=120    # Wait for completion
UVICORN_KEEPALIVE_TIMEOUT=30             # Keep upload connections
WEB_HEALTH_CHECK_TIMEOUT=15              # Generous timeout
```
**Expected capacity:** 250 concurrent long requests

### Development/Testing
Optimize for debugging:
```bash
# .env
UVICORN_WORKERS=1                   # Single worker for easier debugging
UVICORN_LIMIT_CONCURRENCY=0         # No artificial limits
WEB_HEALTH_CHECK_COOLDOWN=10        # Fast feedback
ENVIRONMENT=development             # Enables auto-reload
```

### Docker/Kubernetes
Optimize for orchestration:
```bash
# .env or ConfigMap
UVICORN_WORKERS=5                   # Fixed count per pod
UVICORN_LIMIT_CONCURRENCY=200       # Per worker
UVICORN_BACKLOG=1024                # Let K8s handle queuing
UVICORN_PROXY_HEADERS=true          # Behind service mesh
UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=30  # Match terminationGracePeriodSeconds
```

**Section sources**
- [uvicorn-tuning.md](file://docs/deployment/uvicorn-tuning.md#L301-L372)
- [UVICORN_TUNING_IMPLEMENTATION.md](file://docs/releases/UVICORN_TUNING_IMPLEMENTATION.md#L212-L268)

## Performance Benchmarks
Empirical performance data from testing on a 4-core server (8 vCPU), 4 GB RAM:

| Workers | Req/sec | P50 (ms) | P95 (ms) | CPU (%) | RAM (MB) |
|---------|---------|----------|----------|---------|----------|
| 1 | 450 | 22 | 85 | 98 | 180 |
| 3 | 1,200 | 18 | 45 | 92 | 540 |
| 5 | 1,800 | 15 | 38 | 88 | 900 |
| 9 | 2,400 | 12 | 32 | 85 | 1,620 |
| 17 | 2,500 | 11 | 30 | 82 | 3,060 |

**Optimal:** 9 workers = (2 × 4 cores) + 1

### Health Check Overhead
GET vs HEAD comparison (1000 checks, 5s interval):

| Method | Total Time | Bandwidth | Server CPU | Response Size |
|--------|------------|-----------|------------|---------------|
| GET | 45.2s | 125 KB | 2.1% | 125 bytes |
| HEAD | 28.7s | 38 KB | 1.3% | 0 bytes |

**Improvement:** 37% faster, 70% less bandwidth, 38% less CPU

**Section sources**
- [uvicorn-tuning.md](file://docs/deployment/uvicorn-tuning.md#L575-L600)

## Monitoring & Validation
Verification methods to confirm Uvicorn configuration effectiveness.

### Health Check Endpoint
Verify configuration via monitoring API:
```bash
curl http://localhost:8000/api/monitoring/metrics
```

Response includes:
```json
{
  "services": {
    "web_server": {
      "healthy": true,
      "check_method": "HEAD",
      "response_time_ms": 12.5,
      "successful_url": "http://localhost:8000/health"
    }
  }
}
```

### Process Metrics
Check worker processes:
```bash
ps aux | grep uvicorn
```

Expected output:
```
uvicorn    1234  ... uvicorn app.main:app --workers 9 ...
uvicorn    1235  ... uvicorn.workers.UvicornWorker
uvicorn    1236  ... uvicorn.workers.UvicornWorker
...
```

Count should match `UVICORN_WORKERS + 1` (master + workers).

### Connection Statistics
Monitor active connections:
```bash
netstat -an | grep :8000 | grep ESTABLISHED | wc -l
```

Should stay below:
```
UVICORN_WORKERS * UVICORN_LIMIT_CONCURRENCY
```

### Supervisor Status
Check application health:
```bash
sudo supervisorctl status vertex-ar
```

Expected: `RUNNING` with PID and uptime

### Logs
Verify configuration on startup:
```bash
sudo tail -f /var/log/vertex-ar/access.log
```

Look for:
```
Started server process [...]
Waiting for application startup.
Application startup complete.
Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

**Section sources**
- [uvicorn-tuning.md](file://docs/deployment/uvicorn-tuning.md#L374-L446)
- [api/monitoring.py](file://vertex-ar/app/api/monitoring.py#L140-L158)

## Troubleshooting
Common issues and their solutions.

### Problem: Workers Not Starting
**Symptoms:**
- Application fails to start
- Supervisor shows `FATAL` status
- Error logs show port binding issues

**Solutions:**
```bash
# Check port availability
sudo netstat -tlnp | grep :8000

# Verify worker calculation
python3 -c "import psutil; print((2 * (psutil.cpu_count() or 1)) + 1)"

# Reduce worker count temporarily
UVICORN_WORKERS=2 supervisorctl restart vertex-ar
```

### Problem: Out of Memory
**Symptoms:**
- Workers being killed (OOM killer)
- Slow performance, swapping
- `memory_percent > 90%` in monitoring

**Solutions:**
```bash
# Reduce workers
UVICORN_WORKERS=3  # Or fewer

# Add concurrency limit
UVICORN_LIMIT_CONCURRENCY=100

# Monitor per-worker memory
ps aux --sort=-rss | head -10
```

### Problem: Connection Refused
**Symptoms:**
- Health checks fail with connection errors
- `connection refused` in logs
- Intermittent 502 errors from Nginx

**Solutions:**
```bash
# Increase backlog
UVICORN_BACKLOG=4096

# Check if port is listening
sudo netstat -tlnp | grep :8000

# Verify process is running
ps aux | grep uvicorn
```

### Problem: Slow Graceful Shutdown
**Symptoms:**
- Deployments take too long
- `stopwaitsecs` timeout in Supervisor
- Active requests being killed

**Solutions:**
```bash
# Increase graceful shutdown timeout
UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=60

# Match Supervisor stopwaitsecs
# Edit /etc/supervisor/conf.d/vertex-ar.conf
stopwaitsecs=60

# Reload Supervisor
sudo supervisorctl reread && sudo supervisorctl update
```

### Problem: Health Check False Positives
**Symptoms:**
- Monitoring shows service down but it's running
- Frequent degraded status alerts
- Process/port checks pass but HTTP fails

**Solutions:**
```bash
# Increase health check timeout
WEB_HEALTH_CHECK_TIMEOUT=10

# Use internal URL for monitoring
INTERNAL_HEALTH_URL=http://localhost:8000

# Reduce health check frequency
WEB_HEALTH_CHECK_COOLDOWN=60

# Enable HEAD requests
WEB_HEALTH_CHECK_USE_HEAD=true
```

### Problem: Worker Saturation
**Symptoms:**
- High CPU on all workers
- Request queue growing
- Response time degrading

**Solutions:**
```bash
# Add more workers (if RAM available)
UVICORN_WORKERS=17

# Add concurrency limit to prevent overload
UVICORN_LIMIT_CONCURRENCY=500

# Scale horizontally (multiple instances)
# Use load balancer to distribute traffic
```

**Section sources**
- [uvicorn-tuning.md](file://docs/deployment/uvicorn-tuning.md#L455-L574)

## Conclusion
The Uvicorn server tuning framework in Vertex AR provides comprehensive control over performance characteristics through environment-driven configuration. By understanding and properly configuring worker sizing, connection management, graceful shutdown, and health check parameters, administrators can optimize the application for various deployment scenarios—from resource-constrained environments to high-traffic production systems. The integration with monitoring systems provides validation capabilities, while the troubleshooting guidance addresses common operational issues. Following the recommended tuning scenarios and performance benchmarks ensures optimal balance between throughput, resource consumption, and reliability.

**Section sources**
- [uvicorn-tuning.md](file://docs/deployment/uvicorn-tuning.md#L1-L623)
- [UVICORN_TUNING_IMPLEMENTATION.md](file://docs/releases/UVICORN_TUNING_IMPLEMENTATION.md#L1-L269)