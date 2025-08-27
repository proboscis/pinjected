#!/bin/bash

# Install script for pinjected-linter (Rust version)

set -e

echo "Installing pinjected-linter (Rust version)..."

# Detect OS
OS="unknown"
case "$(uname -s)" in
    Linux*)     OS="linux";;
    Darwin*)    OS="macos";;
    MINGW*|MSYS*|CYGWIN*)     OS="windows";;
esac

echo "Detected OS: $OS"

# Method 1: Install via cargo (recommended)
if command -v cargo &> /dev/null; then
    echo "Installing via cargo..."
    cargo install --path . --force
    echo "✓ Installed via cargo to $(which pinjected-linter)"
    exit 0
fi

# Method 2: Direct binary installation
echo "Cargo not found. Installing binary directly..."

# Build if not already built
if [ ! -f "./target/release/pinjected-linter" ]; then
    echo "Error: Binary not found. Please build first with: cargo build --release"
    exit 1
fi

# Determine install location
INSTALL_DIR=""
if [ -w "/usr/local/bin" ]; then
    INSTALL_DIR="/usr/local/bin"
elif [ -w "$HOME/.local/bin" ]; then
    INSTALL_DIR="$HOME/.local/bin"
    mkdir -p "$INSTALL_DIR"
elif [ -w "$HOME/bin" ]; then
    INSTALL_DIR="$HOME/bin"
    mkdir -p "$INSTALL_DIR"
else
    echo "Error: No writable installation directory found"
    echo "Please run with sudo or add ~/.local/bin to your PATH"
    exit 1
fi

# Copy binary
echo "Installing to $INSTALL_DIR..."
cp ./target/release/pinjected-linter "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/pinjected-linter"

# Check if directory is in PATH
if ! echo "$PATH" | grep -q "$INSTALL_DIR"; then
    echo ""
    echo "⚠️  Warning: $INSTALL_DIR is not in your PATH"
    echo "Add this line to your shell configuration file:"
    echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
fi

echo "✓ Installed pinjected-linter to $INSTALL_DIR/pinjected-linter"

# Test installation
if command -v pinjected-linter &> /dev/null; then
    echo "✓ Installation successful!"
    pinjected-linter --version
else
    echo "⚠️  pinjected-linter installed but not in PATH"
fi