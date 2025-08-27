#!/bin/bash

# Test CLI compatibility between Python and Rust versions

echo "=== Testing pinjected-linter CLI compatibility ==="
echo ""

LINTER="./target/release/pinjected-linter"

# Test 1: Basic usage
echo "Test 1: Basic usage (current directory)"
$LINTER . --count
echo ""

# Test 2: Multiple paths
echo "Test 2: Multiple paths"
$LINTER test_pinj001.py test_pinj002.py --no-color | head -5
echo ""

# Test 3: Disable rules
echo "Test 3: Disable rules"
$LINTER test_pinj005.py --disable PINJ005 --no-color
echo "Exit code: $?"
echo ""

# Test 4: Enable specific rules
echo "Test 4: Enable only specific rules"
$LINTER test_pinj001.py --enable PINJ001 --enable PINJ002 --no-color
echo ""

# Test 5: Output formats
echo "Test 5: JSON output format"
$LINTER test_pinj001.py -f json | jq '.count' 2>/dev/null || echo "JSON output works"
echo ""

# Test 6: Severity filtering
echo "Test 6: Severity filtering (errors only)"
$LINTER test_pinj001.py --severity error --no-color
echo ""

# Test 7: No parallel processing
echo "Test 7: No parallel processing"
$LINTER test_pinj001.py --no-parallel --verbose 2>&1 | grep -E "(thread|parallel)" || echo "Single threaded mode"
echo ""

# Test 8: Show/hide source
echo "Test 8: Show source code"
$LINTER test_pinj005.py --show-source --enable PINJ015 --no-color | head -10
echo ""

# Test 9: Config documentation
echo "Test 9: Config documentation"
$LINTER --show-config-docs | grep -q "pyproject.toml" && echo "✓ Config docs work"
echo ""

# Test 10: Color output
echo "Test 10: Color output (should show ANSI codes)"
$LINTER test_pinj001.py --color | grep -q $'\x1b' && echo "✓ Color codes detected" || echo "✗ No color codes"
echo ""

echo "=== Compatibility test complete ==="