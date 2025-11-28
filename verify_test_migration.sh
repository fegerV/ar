#!/bin/bash
# Verification script for test layout migration

set -e

echo "============================================"
echo "Test Layout Migration Verification"
echo "============================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}✗${NC} $1"
        FAIL=$((FAIL + 1))
    fi
}

# Check old locations are empty
echo "Checking old test locations removed..."
! find vertex-ar -maxdepth 1 -name "test*.py" 2>/dev/null | grep -q .
check "No test files in vertex-ar/"

! find scripts -maxdepth 1 -name "test*.py" 2>/dev/null | grep -q .
check "No test files in scripts/"

[ ! -d "vertex-ar/tests" ]
check "vertex-ar/tests directory removed"

echo ""
echo "Checking new test structure..."

# Check new structure exists
[ -d "test_files/unit" ]
check "test_files/unit/ exists"

[ -d "test_files/integration" ]
check "test_files/integration/ exists"

[ -d "test_files/performance" ]
check "test_files/performance/ exists"

[ -d "test_files/assets" ]
check "test_files/assets/ exists"

# Check for required files
[ -f "test_files/conftest.py" ]
check "test_files/conftest.py exists"

[ -f "test_files/__init__.py" ]
check "test_files/__init__.py exists"

[ -f "test_files/README.md" ]
check "test_files/README.md exists"

echo ""
echo "Checking test counts..."

UNIT_COUNT=$(find test_files/unit -name "test*.py" | wc -l)
[ "$UNIT_COUNT" -ge 14 ]
check "Unit tests: $UNIT_COUNT files"

INTEGRATION_COUNT=$(find test_files/integration -name "test*.py" | wc -l)
[ "$INTEGRATION_COUNT" -ge 44 ]
check "Integration tests: $INTEGRATION_COUNT files"

PERFORMANCE_COUNT=$(find test_files/performance -name "test*.py" | wc -l)
[ "$PERFORMANCE_COUNT" -ge 4 ]
check "Performance tests: $PERFORMANCE_COUNT files"

ASSETS_COUNT=$(ls test_files/assets/ 2>/dev/null | wc -l)
[ "$ASSETS_COUNT" -ge 9 ]
check "Test assets: $ASSETS_COUNT files"

echo ""
echo "Checking configuration files..."

grep -q "test_files" pytest.ini
check "pytest.ini updated"

grep -q "test_files" vertex-ar/pyproject.toml
check "pyproject.toml updated"

grep -q "test_files/unit" .github/workflows/ci-cd.yml
check "ci-cd.yml updated"

grep -q "test_files/unit" scripts/quick_test.sh
check "quick_test.sh updated"

grep -q "test_files" test_files/run_tests.sh
check "run_tests.sh updated"

echo ""
echo "Checking documentation..."

[ -f "TEST_LAYOUT_MIGRATION.md" ]
check "Migration documentation exists"

grep -q "Unit tests" test_files/README.md
check "README.md updated"

echo ""
echo "============================================"
echo "Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
echo "============================================"

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}All checks passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed ✗${NC}"
    exit 1
fi
