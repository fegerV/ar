#!/bin/bash
# Quick test script for Vertex AR
# This script helps you quickly set up and test the application locally

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Print functions
print_header() {
    echo -e "\n${CYAN}${BOLD}========================================${NC}"
    echo -e "${CYAN}${BOLD}  $1${NC}"
    echo -e "${CYAN}${BOLD}========================================${NC}\n"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_step() {
    echo -e "\n${BOLD}► $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "pytest.ini" ]; then
    print_error "pytest.ini not found. Please run this script from the project root."
    exit 1
fi

# Parse command line arguments
TEST_TYPE="${1:-all}"

print_header "Vertex AR - Quick Test Tool"

echo -e "Available test modes:"
echo -e "  ${BOLD}all${NC}        - Run all tests (default)"
echo -e "  ${BOLD}quick${NC}      - Run quick tests only (no slow tests)"
echo -e "  ${BOLD}unit${NC}       - Run unit tests only"
echo -e "  ${BOLD}api${NC}        - Run API tests only"
echo -e "  ${BOLD}setup${NC}      - Setup test environment"
echo -e "  ${BOLD}demo${NC}       - Run demo scenarios"
echo -e "  ${BOLD}coverage${NC}   - Run tests with coverage report"
echo -e "  ${BOLD}clean${NC}      - Clean test artifacts"
echo ""
print_info "Current mode: ${BOLD}$TEST_TYPE${NC}"
echo ""

# Function to check prerequisites
check_prerequisites() {
    print_step "Checking prerequisites..."
    
    # Check Python version
    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
        print_error "Python 3.10 or higher is required. Found: $PYTHON_VERSION"
        exit 1
    fi
    print_success "Python version: $PYTHON_VERSION"
    
    # Check if virtual environment is activated
    if [ -z "$VIRTUAL_ENV" ]; then
        print_warning "Virtual environment not activated"
        
        if [ -d ".venv" ]; then
            print_info "Activating virtual environment..."
            source .venv/bin/activate
            print_success "Virtual environment activated"
        else
            print_warning "Virtual environment not found. Creating..."
            python -m venv .venv
            source .venv/bin/activate
            print_success "Virtual environment created and activated"
        fi
    else
        print_success "Virtual environment: $VIRTUAL_ENV"
    fi
    
    # Check if pytest is installed
    if ! python -m pytest --version &> /dev/null; then
        print_warning "pytest not found. Installing dependencies..."
        pip install -q -r vertex-ar/requirements-dev.txt
        print_success "Dependencies installed"
    else
        print_success "pytest is installed"
    fi
}

# Function to setup test environment
setup_test_environment() {
    print_step "Setting up test environment..."
    
    # Create test directories
    mkdir -p test_storage
    mkdir -p test_files
    mkdir -p logs
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        print_info "Creating .env file from template..."
        cp .env.example .env
        
        # Set test-friendly defaults
        sed -i.bak 's/DEBUG=False/DEBUG=True/' .env
        sed -i.bak 's/RATE_LIMIT_ENABLED=true/RATE_LIMIT_ENABLED=false/' .env
        rm .env.bak
        
        print_success ".env file created with test defaults"
    fi
    
    # Clean old test database
    if [ -f "test_app_data.db" ]; then
        print_info "Cleaning old test database..."
        rm test_app_data.db
    fi
    
    print_success "Test environment ready"
}

# Function to run tests
run_tests() {
    local test_type=$1
    
    print_step "Running ${test_type} tests..."
    
    case $test_type in
        "all")
            python -m pytest -v --tb=short --disable-warnings
            ;;
        "quick")
            python -m pytest -v -m "not slow" --tb=short --disable-warnings
            ;;
        "unit")
            python -m pytest -v -m "unit" --tb=short --disable-warnings
            ;;
        "api")
            python -m pytest -v -m "api" --tb=short --disable-warnings vertex-ar/tests/test_api.py
            ;;
        "coverage")
            python -m pytest --cov=vertex-ar --cov-report=term-missing --cov-report=html:htmlcov --disable-warnings
            print_success "Coverage report generated: htmlcov/index.html"
            
            # Try to open the report
            if command -v open &> /dev/null; then
                print_info "Opening coverage report..."
                open htmlcov/index.html
            elif command -v xdg-open &> /dev/null; then
                print_info "Opening coverage report..."
                xdg-open htmlcov/index.html
            fi
            ;;
        *)
            print_error "Unknown test type: $test_type"
            return 1
            ;;
    esac
    
    return $?
}

# Function to run demo scenarios
run_demo() {
    print_step "Running demo scenarios..."
    
    # Start the application in background
    print_info "Starting application..."
    cd vertex-ar
    uvicorn app.main:app --host 127.0.0.1 --port 8000 > /tmp/vertexar_demo.log 2>&1 &
    APP_PID=$!
    cd ..
    
    # Wait for application to start
    print_info "Waiting for application to start..."
    sleep 3
    
    # Check if app is running
    if ! curl -s http://localhost:8000/health > /dev/null; then
        print_error "Application failed to start. Check logs at /tmp/vertexar_demo.log"
        kill $APP_PID 2>/dev/null || true
        exit 1
    fi
    print_success "Application started (PID: $APP_PID)"
    
    echo ""
    print_header "Demo Scenario: User Registration and Login"
    
    # Demo 1: Register user
    print_step "1. Registering test user..."
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/auth/register \
      -H "Content-Type: application/json" \
      -d '{
        "username": "demouser",
        "password": "DemoPass123!",
        "email": "demo@example.com",
        "full_name": "Demo User"
      }')
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
        print_success "User registered successfully"
        echo "$BODY" | python -m json.tool
    else
        print_warning "Registration returned code: $HTTP_CODE (user might already exist)"
    fi
    
    # Demo 2: Login
    print_step "2. Logging in..."
    RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login \
      -H "Content-Type: application/json" \
      -d '{
        "username": "demouser",
        "password": "DemoPass123!"
      }')
    
    TOKEN=$(echo "$RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null || echo "")
    
    if [ -n "$TOKEN" ]; then
        print_success "Login successful"
        print_info "Token: ${TOKEN:0:30}..."
    else
        print_error "Login failed"
        echo "$RESPONSE" | python -m json.tool 2>/dev/null || echo "$RESPONSE"
        kill $APP_PID
        exit 1
    fi
    
    # Demo 3: Get profile
    print_step "3. Fetching user profile..."
    RESPONSE=$(curl -s -X GET http://localhost:8000/api/users/me \
      -H "Authorization: Bearer $TOKEN")
    
    print_success "Profile retrieved:"
    echo "$RESPONSE" | python -m json.tool
    
    # Demo 4: Create client
    print_step "4. Creating a client..."
    RESPONSE=$(curl -s -X POST http://localhost:8000/api/clients/ \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "name": "Demo Client",
        "phone": "+1234567890",
        "email": "client@example.com"
      }')
    
    print_success "Client created:"
    echo "$RESPONSE" | python -m json.tool
    
    # Demo 5: List clients
    print_step "5. Listing all clients..."
    RESPONSE=$(curl -s -X GET http://localhost:8000/api/clients/ \
      -H "Authorization: Bearer $TOKEN")
    
    print_success "Clients list:"
    echo "$RESPONSE" | python -m json.tool
    
    echo ""
    print_header "Demo completed successfully!"
    
    print_info "Application is still running. Access it at:"
    echo -e "  ${BOLD}API:${NC}         http://localhost:8000"
    echo -e "  ${BOLD}Swagger UI:${NC}  http://localhost:8000/docs"
    echo -e "  ${BOLD}ReDoc:${NC}       http://localhost:8000/redoc"
    echo ""
    print_info "Press Ctrl+C to stop the application and exit"
    echo ""
    
    # Wait for user to stop
    trap "kill $APP_PID 2>/dev/null; print_info 'Application stopped'; exit 0" INT
    wait $APP_PID
}

# Function to clean test artifacts
clean_artifacts() {
    print_step "Cleaning test artifacts..."
    
    # Remove test database
    [ -f "test_app_data.db" ] && rm test_app_data.db && print_info "Removed test database"
    [ -f "app_data.db" ] && rm app_data.db && print_info "Removed main database"
    
    # Remove test storage
    [ -d "test_storage" ] && rm -rf test_storage && print_info "Removed test storage"
    
    # Remove pytest cache
    [ -d ".pytest_cache" ] && rm -rf .pytest_cache && print_info "Removed pytest cache"
    [ -d "__pycache__" ] && rm -rf __pycache__ && print_info "Removed __pycache__"
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
    
    # Remove coverage reports
    [ -d "htmlcov" ] && rm -rf htmlcov && print_info "Removed coverage reports"
    [ -f ".coverage" ] && rm .coverage && print_info "Removed coverage data"
    
    # Remove log files
    [ -d "logs" ] && rm -rf logs/*.log 2>/dev/null && print_info "Removed log files"
    [ -f "/tmp/vertexar_demo.log" ] && rm /tmp/vertexar_demo.log && print_info "Removed demo logs"
    
    print_success "Cleanup completed"
}

# Main execution
case $TEST_TYPE in
    "setup")
        check_prerequisites
        setup_test_environment
        print_success "Setup completed!"
        ;;
    
    "demo")
        check_prerequisites
        setup_test_environment
        run_demo
        ;;
    
    "clean")
        clean_artifacts
        ;;
    
    *)
        check_prerequisites
        setup_test_environment
        
        if run_tests "$TEST_TYPE"; then
            echo ""
            print_header "All tests passed! ✓"
            echo ""
            print_info "Next steps:"
            echo "  • Run 'open htmlcov/index.html' to see coverage report"
            echo "  • Run './quick_test.sh demo' to test the API interactively"
            echo "  • Run './quick_test.sh clean' to clean up test artifacts"
            echo ""
            exit 0
        else
            echo ""
            print_header "Some tests failed ✗"
            echo ""
            print_info "Troubleshooting:"
            echo "  • Check logs in logs/ directory"
            echo "  • Run with -vv for verbose output: pytest -vv"
            echo "  • See LOCAL_TESTING_GUIDE.md for more help"
            echo ""
            exit 1
        fi
        ;;
esac
