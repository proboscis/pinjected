#!/bin/bash

# Pinjected Linter Script
# This script runs pinjected-linter (Rust version) on the main source and all package sources

set -e  # Exit on error

echo "Running pinjected-linter on pinjected sources..."
echo "============================================"

# Store exit codes
EXIT_CODE=0

# Parse command line arguments
EXTRA_ARGS=""
PATHS_TO_LINT=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --timing|--cache|--error-on-warning|-j)
            if [[ "$1" == "-j" ]]; then
                EXTRA_ARGS="$EXTRA_ARGS $1 $2"
                shift 2
            else
                EXTRA_ARGS="$EXTRA_ARGS $1"
                shift
            fi
            ;;
        *)
            PATHS_TO_LINT+=("$1")
            shift
            ;;
    esac
done

# If no paths specified, use default paths
if [ ${#PATHS_TO_LINT[@]} -eq 0 ]; then
    # Default: lint main source and all package sources
    PATHS_TO_LINT=("pinjected/")
    
    # Add all package sources
    for package_dir in packages/*/; do
        if [ -d "${package_dir}src" ]; then
            PATHS_TO_LINT+=("${package_dir}src")
        fi
    done
fi

# Run linter on each path separately
echo -e "\n📍 Linting ${#PATHS_TO_LINT[@]} directories..."
echo "----------------------------------------"

# Function to run linter and capture exit code
run_lint() {
    local path=$1
    echo -e "\n🔍 Checking: $path"
    
    if [ -d "$path" ]; then
        pinjected-linter "$path" $EXTRA_ARGS || {
            local exit_code=$?
            if [ $exit_code -ne 0 ]; then
                EXIT_CODE=$exit_code
            fi
        }
    else
        echo "⚠️  Directory not found: $path"
    fi
}

# Run linter on each path
for path in "${PATHS_TO_LINT[@]}"; do
    run_lint "$path"
done

echo -e "\n============================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All pinjected linting checks passed!"
else
    echo "❌ Pinjected linting found issues (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
