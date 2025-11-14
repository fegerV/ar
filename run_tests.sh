#!/bin/bash
# Test runner script for Vertex AR project

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the project root
if [ ! -f "pytest.ini" ]; then
    print_error "pytest.ini not found. Please run this script from the project root."
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    print_warning "Virtual environment not activated. Activating..."
    source .venv/bin/activate
fi

# Check if pytest is installed
if ! command -v python -m pytest &> /dev/null; then
    print_error "pytest not found. Installing..."
    pip3 install pytest pytest-asyncio pytest-cov pytest-mock httpx
fi

print_status "Running Vertex AR test suite..."
echo

# Set test file paths
TEST_PATHS="vertex-ar/tests test_files"

# Run tests with different options based on arguments
case "${1:-all}" in
    "fast")
        print_status "Running fast tests only..."
        python -m pytest $TEST_PATHS --tb=no -q --disable-warnings -m "not slow"
        ;;
    "coverage")
        print_status "Running tests with coverage report..."
        python -m pytest $TEST_PATHS --cov=vertex-ar --cov-report=term-missing --cov-report=html:htmlcov --disable-warnings
        print_success "Coverage report generated in htmlcov/index.html"
        ;;
    "verbose")
        print_status "Running tests with verbose output..."
        python -m pytest $TEST_PATHS -v --disable-warnings
        ;;
    "watch")
        print_status "Running tests in watch mode (requires pytest-xdist)..."
        python -m pytest $TEST_PATHS -f --disable-warnings
        ;;
    "failed")
        print_status "Running only failed tests..."
        python -m pytest $TEST_PATHS --lf --disable-warnings
        ;;
    "unit")
        print_status "Running unit tests only..."
        python -m pytest vertex-ar/tests -v --disable-warnings
        ;;
    "integration")
        print_status "Running integration tests only..."
        python -m pytest test_files -v --disable-warnings
        ;;
    "all"|*)
        print_status "Running all tests..."
        python -m pytest $TEST_PATHS --tb=short --disable-warnings
        ;;
esac

# Exit with the same code as pytest
exit_code=$?

echo
if [ $exit_code -eq 0 ]; then
    print_success "All tests passed!"
else
    print_error "Some tests failed. Exit code: $exit_code"
fi

exit $exit_code