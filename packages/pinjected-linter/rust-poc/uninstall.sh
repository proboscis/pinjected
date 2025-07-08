#!/bin/bash

# Uninstall script for pinjected-linter

echo "Uninstalling pinjected-linter..."

# Try cargo uninstall first
if command -v cargo &> /dev/null; then
    if cargo uninstall pinjected-linter 2>/dev/null; then
        echo "✓ Uninstalled via cargo"
        exit 0
    fi
fi

# Remove from common locations
REMOVED=false
for dir in "/usr/local/bin" "$HOME/.local/bin" "$HOME/bin" "$HOME/.cargo/bin"; do
    if [ -f "$dir/pinjected-linter" ]; then
        echo "Removing $dir/pinjected-linter..."
        rm -f "$dir/pinjected-linter"
        REMOVED=true
    fi
done

if [ "$REMOVED" = true ]; then
    echo "✓ pinjected-linter uninstalled"
else
    echo "pinjected-linter not found in standard locations"
fi