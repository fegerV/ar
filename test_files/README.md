# Test Files Organization

This document describes the unified test organization for the Vertex AR project.

> 📌 **Unified Structure**: All tests are now consolidated in `test_files/` with clear categorization by type.

## Directory Structure

```
test_files/
├── README.md                          # This file
├── conftest.py                        # Shared pytest configuration and path setup
├── __init__.py                        # Package initialization
├── run_tests.sh                       # Test runner script
├── run_performance_tests.sh           # Performance test runner
├── create_test_video.py               # Test video generator utility
│
├── unit/                              # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_ar_features.py
│   ├── test_auth.py
│   ├── test_backup_can_delete.py
│   ├── test_database.py
│   ├── test_lifecycle_scheduler.py
│   ├── test_models.py
│   ├── test_monitoring.py
│   ├── test_nft_generation.py
│   ├── test_orders_endpoints.py
│   ├── test_storage.py
│   ├── test_storage_adapter.py
│   ├── test_videos_list_endpoint.py
│   └── test_videos_schedule_endpoint.py
│
├── integration/                       # Integration tests (multi-component)
│   ├── __init__.py
│   ├── test_admin_login_flow.py
│   ├── test_admin_panel.py
│   ├── test_api_endpoints.py
│   ├── test_api_upload.py
│   ├── test_ar_functionality.py
│   ├── test_ar_upload_functionality.py
│   ├── test_backup_fix.py
│   ├── test_backup_path_fix.py
│   ├── test_backup_security_fix.py
│   ├── test_backup_system.py
│   ├── test_basic.py
│   ├── test_changes.py
│   ├── test_companies.py
│   ├── test_comprehensive_backup_fix.py
│   ├── test_cross_platform_backup.py
│   ├── test_deployment.py
│   ├── test_docker_fix.py
│   ├── test_documentation.py
│   ├── test_fixes.py
│   ├── test_implementation.py
│   ├── test_monitoring.py
│   ├── test_monitoring_alert_dedup.py
│   ├── test_nft_improvements.py
│   ├── test_nft_marker_integration.py
│   ├── test_nft_size.py
│   ├── test_notifications_comprehensive.py
│   ├── test_order_creation_complete.py
│   ├── test_orders_api.py
│   ├── test_portraits_api.py
│   ├── test_portraits_automated.py
│   ├── test_preview_generation.py
│   ├── test_projects_folders_api.py
│   ├── test_psutil_basic.py
│   ├── test_real_video_preview.py
│   ├── test_refactored_app.py
│   ├── test_security.py
│   ├── test_simple_nft_size.py
│   ├── test_storage_config.py
│   ├── test_storage_integration.py
│   ├── test_ui_improvements.py
│   ├── test_web_health_check.py
│   └── test_yandex_integration.py
│
├── performance/                       # Performance and load tests
│   ├── __init__.py
│   ├── test_comprehensive_performance.py
│   ├── test_memory_profiler.py
│   ├── test_performance.py
│   └── test_portraits_load.py
│
└── assets/                            # Test data and fixtures
    ├── test_image.jpg
    ├── test_image.png
    ├── test_video.mp4
    ├── test_document_preview.jpg
    ├── test_image_preview.jpg
    ├── test_real_video_preview.jpg
    ├── test_video_preview.jpg
    ├── test_video_stub.jpg
    └── test_results.json
```

## Test Categories

### Unit Tests (`unit/`)
- **Purpose:** Fast, isolated tests for individual components and business logic
- **Characteristics:**
  - No external dependencies
  - No network calls
  - Mock external services
  - Run in milliseconds
- **Run with:** `pytest test_files/unit/`

### Integration Tests (`integration/`)
- **Purpose:** Test interaction between multiple components, full API flows, admin panel, AR features
- **Characteristics:**
  - Test component integration
  - May use test database
  - May make HTTP requests
  - Test complete workflows
- **Run with:** `pytest test_files/integration/`

### Performance Tests (`performance/`)
- **Purpose:** Test system performance under various conditions, load testing, memory profiling
- **Characteristics:**
  - Stress testing
  - Load simulation
  - Memory profiling
  - Response time measurement
- **Run with:** `pytest test_files/performance/` or `./test_files/run_performance_tests.sh`

### Test Assets (`assets/`)
- **Purpose:** Shared test fixtures, images, videos, and expected results
- **Files:**
  - Images for portrait upload tests
  - Videos for AR tests
  - Preview images
  - Expected test results (JSON)

## Running Tests

### From Project Root (Recommended)

```bash
# Run all tests
pytest test_files/

# Run only unit tests
pytest test_files/unit/

# Run only integration tests
pytest test_files/integration/

# Run only performance tests
pytest test_files/performance/

# Run with coverage
pytest test_files/ --cov=vertex-ar/app --cov-report=term-missing
pytest test_files/ --cov=vertex-ar/app --cov-report=html

# Run specific test categories using markers
pytest test_files/ -m unit
pytest test_files/ -m integration
pytest test_files/ -m "not slow"
```

### Using Test Scripts

```bash
# Quick test script (from project root)
./scripts/quick_test.sh                # All tests
./scripts/quick_test.sh quick          # Fast tests only (no slow tests)
./scripts/quick_test.sh unit           # Unit tests
./scripts/quick_test.sh integration    # Integration tests
./scripts/quick_test.sh coverage       # Tests with coverage report
./scripts/quick_test.sh demo           # Interactive API demo
./scripts/quick_test.sh clean          # Clean test artifacts

# Test runner in test_files/
cd test_files
./run_tests.sh                         # All tests
./run_tests.sh unit                    # Unit tests
./run_tests.sh integration             # Integration tests
./run_tests.sh performance             # Performance tests
./run_tests.sh coverage                # Tests with coverage
./run_tests.sh fast                    # Fast tests only
./run_tests.sh verbose                 # Verbose output

# Performance tests
cd test_files
./run_performance_tests.sh             # All performance tests
```

### Running Individual Test Files

```bash
# Run a specific test file
pytest test_files/integration/test_api_endpoints.py -v

# Run a specific test function
pytest test_files/unit/test_auth.py::test_password_hashing -v

# Run with detailed output
pytest test_files/integration/test_admin_panel.py -vv -s
```

### Advanced Options

```bash
# Run tests in parallel (faster)
pytest test_files/ -n auto

# Run only failed tests from last run
pytest test_files/ --lf

# Run with timeout (prevent hanging tests)
pytest test_files/ --timeout=300

# Run specific markers
pytest test_files/ -m "api and not slow"

# Generate HTML coverage report
pytest test_files/ --cov=vertex-ar/app --cov-report=html
open htmlcov/index.html  # View report
```

## Test Organization Best Practices

1. **Unit Tests** (`test_files/unit/`) - Fast, isolated, no external dependencies
   - Test individual functions and classes
   - Mock external dependencies
   - Should run in < 1 second

2. **Integration Tests** (`test_files/integration/`) - Test full workflows, API endpoints, database interactions
   - Test component integration
   - Use test database/fixtures
   - May take several seconds

3. **Performance Tests** (`test_files/performance/`) - Load testing, stress testing, profiling
   - Test system under load
   - Memory profiling
   - May take minutes

4. **Test Data** (`test_files/assets/`) - Shared test fixtures
   - Images, videos, JSON files
   - Referenced by tests across all categories

## Path Resolution

The shared `test_files/conftest.py` handles all path resolution automatically:
- Adds `vertex-ar/` to Python path
- Allows imports like `from app.main import create_app`
- No need for `sys.path.insert()` in individual test files

## CI/CD Integration

The GitHub Actions workflow uses the unified test structure:

- **Unit tests:** `pytest test_files/unit/`
- **Integration tests:** `pytest test_files/integration/`
- **Performance tests:** `pytest test_files/performance/` (scheduled/optional)
- **Coverage report:** Automatically generated and published

## Markers

Tests can be marked for selective execution:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow tests (exclude with `-m "not slow"`)
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.storage` - Storage-related tests
- `@pytest.mark.auth` - Authentication tests
- `@pytest.mark.nft` - NFT-related tests
- `@pytest.mark.ar` - AR functionality tests
- `@pytest.mark.admin` - Admin panel tests
- `@pytest.mark.security` - Security tests
- `@pytest.mark.performance` - Performance tests

## Migration Notes

### Previous Structure
```
vertex-ar/tests/          # Unit tests
vertex-ar/test_*.py       # Standalone integration tests
scripts/test_*.py         # Script-based tests
test_files/test_*.py      # Mixed tests
```

### New Structure
```
test_files/
  ├── unit/               # All unit tests
  ├── integration/        # All integration tests
  ├── performance/        # All performance tests
  └── assets/             # All test data
```

### Key Changes
- All tests now in `test_files/` subdirectories
- Shared `conftest.py` for path resolution
- Clear separation by test type
- No tests remain in `vertex-ar/` or `scripts/`
- All tooling updated to use new paths

## Notes

- All tests consolidated in `test_files/` with clear categorization
- Shared configuration in `test_files/conftest.py`
- Test scripts updated to reference new paths
- No changes to test logic - only organization improved
- Use `pytest test_files/` from project root for best experience
- Coverage reports exclude test files by default
