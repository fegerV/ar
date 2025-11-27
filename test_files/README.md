# Test Files Organization

This document describes the organization and execution of tests in the Vertex AR project.

> 📌 **New Structure**: Tests have been consolidated in `test_files/` for integration and performance tests, with unit tests remaining in `vertex-ar/tests/`

## Directory Structure

```
test_files/
├── README.md                          # This file
├── run_tests.sh                       # Test runner script
├── run_performance_tests.sh           # Performance test runner
├── create_test_video.py               # Test video generator
│
├── Integration Tests
│   ├── test_api_endpoints.py          # REST API tests
│   ├── test_admin_panel.py            # Admin panel tests
│   ├── test_admin_login_flow.py       # Login flow tests
│   ├── test_ar_functionality.py       # AR features tests
│   ├── test_ar_upload_functionality.py # AR upload tests
│   ├── test_orders_api.py             # Orders API tests
│   ├── test_security.py               # Security tests
│   └── test_storage_integration.py    # Storage integration tests
│
├── Performance Tests
│   ├── test_comprehensive_performance.py  # Comprehensive performance tests
│   ├── test_performance.py                # General performance tests
│   ├── test_portraits_load.py             # Portrait load tests
│   └── test_memory_profiler.py            # Memory profiling tests
│
├── Deployment & Documentation Tests
│   ├── test_deployment.py             # Deployment checks
│   ├── test_documentation.py          # Documentation validation
│   └── test_changes.py                # Change validation
│
└── Test Data
    ├── test_image.jpg                 # Test portrait image
    ├── test_image.png                 # Test portrait image (PNG)
    ├── test_video.mp4                 # Test video file
    ├── test_*_preview.jpg             # Preview images
    └── test_results.json              # Expected test results
```

## Test Categories

### Unit Tests
- **Location:** `vertex-ar/tests/`
- **Purpose:** Fast, isolated tests for individual components and business logic
- **Run with:** `pytest vertex-ar/tests/`

### Integration Tests
- **Location:** `test_files/test_*.py` (excluding performance tests)
- **Purpose:** Test the interaction between multiple components, full API flows, admin panel, AR features
- **Run with:** `./test_files/run_tests.sh integration` or `pytest test_files/ -m integration`

### Performance Tests
- **Location:** `test_files/test_*performance*.py` and `test_files/test_*load*.py`
- **Purpose:** Test system performance under various conditions, load testing, memory profiling
- **Run with:** `./test_files/run_performance_tests.sh`

### API Tests
- **Files:** `test_api_endpoints.py`, `test_orders_api.py`, `test_ar_upload_functionality.py`
- **Purpose:** Test REST API endpoints, request/response validation
- **Run with:** `pytest test_files/test_api*.py`

## Running Tests

### From Root Directory (Recommended)

```bash
# Run all tests with pytest
pytest

# Run only unit tests
pytest vertex-ar/tests/

# Run only integration tests
pytest test_files/ -k "not performance"

# Run only performance tests
pytest test_files/ -k "performance or load"

# Run with coverage
pytest --cov=vertex-ar --cov-report=term-missing
pytest --cov=vertex-ar --cov-report=html
```

### Using Test Scripts

```bash
# Quick test script (from root)
./scripts/quick_test.sh                # All tests
./scripts/quick_test.sh quick          # Fast tests only
./scripts/quick_test.sh demo           # Interactive demo

# Test runner in test_files/
cd test_files
./run_tests.sh                         # All tests
./run_tests.sh integration             # Integration tests
./run_tests.sh unit                    # Unit tests (from vertex-ar/tests/)

# Performance tests
cd test_files
./run_performance_tests.sh             # All performance tests
```

### Running Individual Test Files

```bash
# Run a specific test file
pytest test_files/test_api_endpoints.py -v

# Run a specific test function
pytest test_files/test_api_endpoints.py::test_auth_registration -v

# Run with detailed output
pytest test_files/test_admin_panel.py -vv -s
```

### Advanced Options

```bash
# Run tests in parallel (faster)
pytest -n auto

# Run only failed tests from last run
pytest --lf

# Run with timeout (prevent hanging tests)
pytest --timeout=300

# Generate HTML coverage report
pytest --cov=vertex-ar --cov-report=html
open htmlcov/index.html  # View report
```

## Test Organization Best Practices

1. **Unit Tests** (`vertex-ar/tests/`) - Fast, isolated, no external dependencies
2. **Integration Tests** (`test_files/`) - Test full workflows, API endpoints, database interactions
3. **Performance Tests** (`test_files/`) - Load testing, stress testing, profiling
4. **Test Data** (`test_files/`) - Shared test fixtures (images, videos, JSON)

## CI/CD Integration

The GitHub Actions workflow uses the new test structure:

- **Unit tests:** `pytest vertex-ar/tests/`
- **Integration tests:** `pytest test_files/ -k "not performance"`
- **Performance tests:** `./test_files/run_performance_tests.sh` (scheduled)
- **Coverage report:** Automatically generated and published

## Test Data Files

Test fixtures are stored in `test_files/`:
- **Images:** `test_image.jpg`, `test_image.png` - Portrait images for upload tests
- **Videos:** `test_video.mp4` - Video file for AR tests
- **Previews:** `test_*_preview.jpg` - Expected preview images
- **Results:** `test_results.json` - Expected test outcomes

## Notes

- All integration/performance tests consolidated in `test_files/`
- Unit tests remain in `vertex-ar/tests/` for logical separation
- Test scripts updated to reference new paths
- No changes to test logic - only organization improved
- Use `pytest` from project root for best experience