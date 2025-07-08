#!/bin/bash

# Benchmark script for pinjected-linter-rust

echo "Building release version..."
cargo build --release

echo ""
echo "Testing on small test files..."
time ./target/release/pinjected-linter-rust test_pinj001.py

echo ""
echo "Testing on directory with timing and caching..."
echo "Command: ./target/release/pinjected-linter-rust ~/repos/proboscis-ema --timing --cache"
time ./target/release/pinjected-linter-rust ~/repos/proboscis-ema --timing --cache

echo ""
echo "Testing with parallel threads..."
echo "Command: ./target/release/pinjected-linter-rust ~/repos/proboscis-ema --timing --cache -j 8"
time ./target/release/pinjected-linter-rust ~/repos/proboscis-ema --timing --cache -j 8

echo ""
echo "Testing specific rule..."
echo "Command: ./target/release/pinjected-linter-rust ~/repos/proboscis-ema --timing --rule PINJ001"
time ./target/release/pinjected-linter-rust ~/repos/proboscis-ema --timing --rule PINJ001

echo ""
echo "Testing with skip patterns..."
echo "Command: ./target/release/pinjected-linter-rust ~/repos/proboscis-ema --timing --skip test_ --skip __pycache__"
time ./target/release/pinjected-linter-rust ~/repos/proboscis-ema --timing --skip test_ --skip __pycache__