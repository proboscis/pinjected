#!/bin/bash


set -e

echo "🚀 Installing pinjected-linter (Rust version) from remote repository..."

if ! command -v cargo &> /dev/null; then
    echo "❌ Error: cargo is required but not installed"
    echo "Please install Rust and cargo from https://rustup.rs/"
    exit 1
fi

if ! command -v git &> /dev/null; then
    echo "❌ Error: git is required but not installed"
    echo "Please install git first"
    exit 1
fi

TEMP_DIR=$(mktemp -d)
echo "📁 Using temporary directory: $TEMP_DIR"

cleanup() {
    echo "🧹 Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

echo "📥 Cloning pinjected repository..."
git clone --depth 1 https://github.com/proboscis/pinjected.git "$TEMP_DIR/pinjected" || {
    echo "❌ Error: Failed to clone repository"
    exit 1
}

cd "$TEMP_DIR/pinjected/packages/pinjected-linter/rust-poc" || {
    echo "❌ Error: rust-poc directory not found"
    exit 1
}

echo "⚙️  Installing pinjected-linter via cargo..."
cargo install --path . --force || {
    echo "❌ Error: Failed to install via cargo"
    exit 1
}

if command -v pinjected-linter &> /dev/null; then
    echo "✅ Installation successful!"
    echo "📍 Installed to: $(which pinjected-linter)"
    echo "🔧 Version: $(pinjected-linter --version 2>/dev/null || echo 'version check failed')"
else
    echo "⚠️  pinjected-linter installed but not found in PATH"
    echo "You may need to add ~/.cargo/bin to your PATH:"
    echo "  export PATH=\"\$HOME/.cargo/bin:\$PATH\""
fi

echo "🎉 Done! You can now use 'pinjected-linter' command."
