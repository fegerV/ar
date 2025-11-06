# Performance Testing with psutil

This document describes the comprehensive performance testing suite implemented for the Vertex AR application using psutil and other performance monitoring tools.

## Overview

The performance testing suite includes:

1. **Comprehensive Performance Testing** (`test_comprehensive_performance.py`)
2. **Load Testing for Portraits API** (`test_portraits_load.py`)
3. **Storage Integration Testing** (`test_storage_integration.py`)
4. **Automated Portraits Testing** (`test_portraits_automated.py`)

## Installation

Install the required dependencies:

```bash
pip install psutil requests pillow minio memory-profiler py-spy
```

Or use the development requirements:

```bash
pip install -r vertex-ar/requirements-dev.txt
```

## 1. Comprehensive Performance Testing

### Features

- **Real-time system monitoring**: CPU, memory, disk I/O, network
- **Memory leak detection**: Tracks memory usage over time
- **Concurrent request testing**: Tests performance under load
- **Database performance**: Measures query and insert speeds
- **Large file handling**: Tests upload of large files (10MB+)

### Metrics Tracked

- CPU usage percentage
- Memory usage (RSS, percentage)
- Disk read/write operations
- Network send/receive
- Open files count
- Thread count
- Response times

### Usage

```bash
python test_comprehensive_performance.py
```

### Output

- Real-time performance graphs
- Summary statistics
- JSON report with all metrics
- Memory leak detection results

## 2. Load Testing for Portraits API

### Features

- **Concurrent order creation**: Tests multiple simultaneous requests
- **API endpoint testing**: Tests all portrait-related endpoints
- **Stress testing**: Continuous load for specified duration
- **Performance comparison**: Different load levels

### Test Scenarios

1. **Concurrent Orders**: 20 simultaneous order creations
2. **API Endpoints**: 100 requests to various endpoints
3. **Stress Test**: 30-60 seconds of continuous load

### Usage

```bash
python test_portraits_load.py
```

### Metrics

- Requests per second
- Average/Min/Max response times
- Success rate
- Error analysis
- Endpoint-specific performance

## 3. Storage Integration Testing

### Features

- **Local storage testing**: Tests file upload/download performance
- **MinIO integration**: Direct MinIO API testing
- **Performance comparison**: Local vs MinIO storage
- **Scalability testing**: Different file sizes
- **Concurrent operations**: Multiple simultaneous uploads

### Storage Types Tested

1. **Local Storage**: Default file system storage
2. **MinIO Direct**: Direct MinIO API calls
3. **MinIO via Application**: Through the application API

### Usage

```bash
python test_storage_integration.py
```

### File Sizes Tested

- 1 MB files
- 5 MB files
- 10 MB files
- 20 MB files

### Metrics

- Upload speed (MB/s)
- Download speed (MB/s)
- Storage type comparison
- Resource usage
- Data integrity verification

## 4. Automated Portraits Testing

### Features

- **Full workflow testing**: Complete portrait creation to viewing
- **API validation**: All portrait-related endpoints
- **Data integrity**: Verifies data consistency
- **Public access testing**: Tests public portrait viewing
- **System endpoints**: Tests admin and monitoring endpoints

### Test Coverage

1. Authentication
2. Order creation
3. Client search and listing
4. Portrait management
5. Video management
6. Public access
7. System monitoring
8. Data integrity

### Usage

```bash
python test_portraits_automated.py
```

## Running All Tests

Use the provided script to run all performance tests:

```bash
./run_performance_tests.sh
```

This script will:

1. Check dependencies
2. Verify the application is running
3. Run all test suites
4. Generate comprehensive reports
5. Save results to `performance_reports/` directory

## Report Analysis

### Generated Reports

Each test generates a JSON report with:

- Test metadata
- Performance metrics
- System information
- Error details
- Timing information

### Key Performance Indicators

1. **CPU Usage**: Should not exceed 80% under normal load
2. **Memory Usage**: Monitor for leaks (<100MB increase)
3. **Response Times**: <2 seconds for most operations
4. **Throughput**: >5 requests/second for API endpoints
5. **Storage Speed**: >10 MB/s for file operations

### Performance Benchmarks

| Operation | Target | Acceptable |
|-----------|--------|------------|
| API Response Time | <500ms | <2s |
| File Upload Speed | >20 MB/s | >5 MB/s |
| Database Queries | <100ms | <500ms |
| Concurrent Requests | >90% success | >80% success |
| Memory Growth | <50MB | <100MB |

## Troubleshooting

### Common Issues

1. **psutil Import Error**
   ```bash
   pip install psutil
   ```

2. **Application Not Running**
   ```bash
   cd vertex-ar && python main.py
   ```

3. **MinIO Connection Issues**
   - Check MinIO is running: `docker-compose up -d minio`
   - Verify environment variables
   - Check network connectivity

4. **Memory Issues**
   - Monitor system memory usage
   - Check for memory leaks in reports
   - Reduce concurrent request count

### Performance Optimization

Based on test results:

1. **High CPU Usage**: Optimize image processing
2. **Slow Uploads**: Check disk I/O, network bandwidth
3. **Memory Leaks**: Review code for unclosed resources
4. **Database Slowness**: Add indexes, optimize queries

## Continuous Integration

Add to CI/CD pipeline:

```yaml
performance_test:
  stage: test
  script:
    - pip install -r vertex-ar/requirements-dev.txt
    - python test_comprehensive_performance.py
    - python test_portraits_load.py
    - python test_storage_integration.py
  artifacts:
    reports:
      junit: performance_reports/*.json
```

## Monitoring in Production

Use the same metrics in production:

1. **Application Monitoring**: Integrate psutil monitoring
2. **APM Tools**: Use with Sentry, New Relic, etc.
3. **Resource Monitoring**: System-level monitoring
4. **Performance Alerts**: Set up alerts for thresholds

## Best Practices

1. **Regular Testing**: Run performance tests weekly
2. **Baseline Comparison**: Compare with previous results
3. **Load Testing**: Before major releases
4. **Monitor Trends**: Track performance over time
5. **Profile Optimization**: Use py-spy for detailed profiling

## Future Enhancements

1. **Distributed Load Testing**: Use Locust for larger scale
2. **Real User Monitoring**: RUM integration
3. **Automated Benchmarking**: CI integration
4. **Performance Regression Detection**: Automated alerts
5. **Cloud Performance Testing**: Multi-region testing