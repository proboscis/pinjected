#!/bin/bash
# Verify all PINJ rules have documentation

echo "Checking PINJ rule documentation..."
echo ""

# Get all implemented rules
RULES=$(grep -E "^pub mod pinj[0-9]+" rust-poc/src/rules/mod.rs | sed 's/pub mod //' | sed 's/;$//' | sort)

# Special case: pinj014 is documented as pinj014_missing_stub_file
RULES=$(echo "$RULES" | sed 's/^pinj014$/pinj014_missing_stub_file/')

MISSING=0
FOUND=0

for rule in $RULES; do
    DOC_FILE="docs/rules/${rule}.md"
    if [ -f "$DOC_FILE" ]; then
        echo "✅ $rule - Documentation found"
        FOUND=$((FOUND + 1))
    else
        echo "❌ $rule - MISSING DOCUMENTATION"
        MISSING=$((MISSING + 1))
    fi
done

echo ""
echo "Summary:"
echo "  Found: $FOUND"
echo "  Missing: $MISSING"
echo ""

# Check for extra documentation files
echo "Checking for orphaned documentation files..."
for doc in docs/rules/pinj*.md; do
    basename=$(basename "$doc" .md)
    # Handle special case
    check_name=$basename
    if [ "$basename" = "pinj014_missing_stub_file" ]; then
        check_name="pinj014"
    fi
    
    if ! echo "$RULES" | grep -q "^$basename$"; then
        echo "⚠️  $basename - Documentation exists but no rule implementation found"
    fi
done

if [ $MISSING -eq 0 ]; then
    echo ""
    echo "✅ All rules have documentation!"
    exit 0
else
    echo ""
    echo "❌ Some rules are missing documentation"
    exit 1
fi