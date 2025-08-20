#!/bin/bash

# PyCharm Plugin Comprehensive Test Runner
# This script runs all levels of testing for the IProxy plugin

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  PyCharm Plugin Test Suite${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to print test section
print_section() {
    echo -e "\n${YELLOW}→ $1${NC}"
}

# Function to check command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}✗ $1 is not installed${NC}"
        return 1
    else
        echo -e "${GREEN}✓ $1 is available${NC}"
        return 0
    fi
}

# 1. Check prerequisites
print_section "Checking Prerequisites"

check_command java || exit 1
check_command cargo || exit 1
check_command python3 || exit 1

# Check if indexer is installed
if ! command -v pinjected-indexer &> /dev/null; then
    print_section "Installing pinjected-indexer"
    cd "$PROJECT_ROOT/packages/pinjected-indexer"
    cargo install --path .
    cd "$SCRIPT_DIR"
fi

# 2. Clean previous build
print_section "Cleaning Previous Build"
./gradlew clean

# 3. Build the plugin
print_section "Building Plugin"
./gradlew build -x test

# 4. Run unit tests
print_section "Running Unit Tests"
./gradlew test --tests "*SimpleTest" || true

# 5. Run integration tests
print_section "Running Integration Tests"
./gradlew test --tests "*IntegrationTest" --tests "*IndexerIntegrationTest" || true

# 6. Run functional tests (if indexer is available)
if command -v pinjected-indexer &> /dev/null; then
    print_section "Running Functional Tests"
    ./gradlew test --tests "*FunctionalTest" || true
else
    echo -e "${YELLOW}⚠ Skipping functional tests (indexer not available)${NC}"
fi

# 7. Check if PyCharm with Robot Server is running for UI tests
if curl -s http://127.0.0.1:8082 > /dev/null 2>&1; then
    print_section "Running UI Tests"
    ./gradlew test --tests "*UITest" || true
else
    echo -e "${YELLOW}⚠ Skipping UI tests (Robot Server not running)${NC}"
    echo "  To run UI tests:"
    echo "  1. Install 'Robot Server Plugin' in PyCharm"
    echo "  2. Start PyCharm with: -Drobot-server.port=8082"
fi

# 8. Generate test report
print_section "Generating Test Report"
./gradlew test --rerun-tasks

# 9. Show test summary
print_section "Test Summary"

# Count test results
if [ -f "build/test-results/test/TEST-*.xml" ]; then
    TOTAL=$(grep -h "tests=" build/test-results/test/TEST-*.xml | sed 's/.*tests="\([0-9]*\)".*/\1/' | awk '{s+=$1} END {print s}')
    FAILURES=$(grep -h "failures=" build/test-results/test/TEST-*.xml | sed 's/.*failures="\([0-9]*\)".*/\1/' | awk '{s+=$1} END {print s}')
    ERRORS=$(grep -h "errors=" build/test-results/test/TEST-*.xml | sed 's/.*errors="\([0-9]*\)".*/\1/' | awk '{s+=$1} END {print s}')
    
    echo -e "Total Tests: ${TOTAL:-0}"
    echo -e "Failures: ${RED}${FAILURES:-0}${NC}"
    echo -e "Errors: ${RED}${ERRORS:-0}${NC}"
    
    if [ "${FAILURES:-0}" -eq 0 ] && [ "${ERRORS:-0}" -eq 0 ]; then
        echo -e "\n${GREEN}✓ All tests passed!${NC}"
    else
        echo -e "\n${RED}✗ Some tests failed${NC}"
    fi
fi

# 10. Open test report in browser (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    print_section "Opening Test Report"
    open "build/reports/tests/test/index.html" 2>/dev/null || true
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  Test Execution Complete${NC}"
echo -e "${GREEN}========================================${NC}"

# Show instructions for manual testing
echo -e "\n${YELLOW}For manual testing:${NC}"
echo "1. Install plugin: ./gradlew runIde"
echo "2. Follow procedures in TESTING.md"
echo "3. Report issues in GitHub"

# Exit with appropriate code
if [ "${FAILURES:-0}" -gt 0 ] || [ "${ERRORS:-0}" -gt 0 ]; then
    exit 1
else
    exit 0
fi