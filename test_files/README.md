# Test Files Organization

This document describes the organization of test files in the Vertex AR project.

## Directory Structure

```
test_files/
├── test_admin_login_flow.py
├── test_admin_panel.py
├── test_api_endpoints.py
├── test_api_upload.py
├── test_ar_functionality.py
├── test_ar_upload_functionality.py
├── test_ar_upload_simple.py
├── test_comprehensive_performance.py
├── test_deployment.py
├── test_docker_fix.py
├── test_document_preview.jpg
├── test_documentation.py
├── test_image.jpg
├── test_image.png
├── test_image_preview.jpg
├── test_memory_profiler.py
├── test_nft_improvements.py
├── test_order_creation_complete.py
├── test_orders_api.py
├── test_performance.py
├── test_portraits_automated.py
├── test_portraits_load.py
├── test_preview_generation.py
├── test_psutil_basic.py
├── test_real_video_preview.jpg
├── test_real_video_preview.py
├── test_refactored_app.py
├── test_results.json
├── test_security.py
├── test_storage_integration.py
├── test_ui_improvements.py
├── test_video.mp4
├── test_video_preview.jpg
└── test_video_stub.jpg
```

## Test Categories

### Unit Tests
- Located in `vertex-ar/tests/`
- Fast, isolated tests for individual components
- Run with: `./run_tests.sh unit` or `./quick_test.sh unit`

### Integration Tests
- Located in `test_files/`
- Test the interaction between multiple components
- Include API tests, performance tests, and end-to-end scenarios
- Run with: `./run_tests.sh integration` or `./quick_test.sh integration`

### Performance Tests
- Files with `performance` or `load` in the name
- Test system performance under various conditions
- Run with: `./run_performance_tests.sh`

### API Tests
- Files with `api` in the name
- Test REST API endpoints
- Run with: `./quick_test.sh api`

## Running Tests

### Quick Test Script
```bash
# Run all tests
./quick_test.sh

# Run specific test types
./quick_test.sh unit          # Unit tests only
./quick_test.sh integration   # Integration tests only
./quick_test.sh api          # API tests only
./quick_test.sh coverage     # With coverage report
./quick_test.sh quick        # Fast tests only
```

### Comprehensive Test Script
```bash
# Run all tests
./run_tests.sh

# Run specific test types
./run_tests.sh unit          # Unit tests only
./run_tests.sh integration   # Integration tests only
./run_tests.sh fast          # Fast tests only
./run_tests.sh coverage      # With coverage report
```

### Performance Tests
```bash
# Run all performance tests
./run_performance_tests.sh

# Run individual performance tests
python3 test_files/test_comprehensive_performance.py
python3 test_files/test_portraits_load.py
python3 test_files/test_storage_integration.py
```

## CI/CD Integration

The GitHub Actions workflow has been updated to use the new test structure:

- Unit tests run from `vertex-ar/tests/`
- Integration tests run from `test_files/`
- Performance tests use files from `test_files/`
- Test artifacts are collected from both directories

## Test Data

Test images, videos, and other data files are stored in `test_files/`:
- `test_*.jpg` and `test_*.png` - Test images
- `test_video.mp4` - Test video file
- `test_results.json` - Expected test results

## Notes

- All test files have been moved from the project root to `test_files/`
- Test scripts have been updated to use the new paths
- CI/CD workflow automatically detects and runs tests from both locations
- No changes to test content were made - only file locations were updated