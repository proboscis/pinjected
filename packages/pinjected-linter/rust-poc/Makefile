.PHONY: all build release install uninstall test test-compat clean

# Default target
all: release

# Development build
build: lint
	cargo build

# Release build (optimized)
release: lint
	cargo build --release

# Install globally via cargo
install: release
	./install.sh

# Uninstall
uninstall:
	./uninstall.sh

# Run tests
test:
	cargo test

# Test CLI compatibility
test-compat: release
	./test_compatibility.sh

# Run on test files
test-files: release
	./target/release/pinjected-linter test_*.py --verbose

# Benchmark performance
benchmark: release
	./benchmark.sh

# Clean build artifacts
clean:
	cargo clean
	rm -f /tmp/rust_output.txt /tmp/python_output.txt

# Format code
fmt:
	cargo fmt

# Check code
check:
	cargo check
	cargo clippy -- -D warnings -W clippy::cognitive_complexity

# Run strict linting (including complexity checks)
lint:
	@echo "Running strict linting with complexity checks..."
	cargo clippy -- -D warnings -D clippy::cognitive_complexity -D clippy::too_many_lines -D clippy::too_many_arguments

# Run on proboscis-ema source
run-ema: release
	./target/release/pinjected-linter ~/repos/proboscis-ema/src --timing --cache

# Help
help:
	@echo "Available targets:"
	@echo "  make build      - Build debug version"
	@echo "  make release    - Build optimized release version"
	@echo "  make install    - Install globally (via cargo or to /usr/local/bin)"
	@echo "  make uninstall  - Remove global installation"
	@echo "  make test       - Run unit tests"
	@echo "  make test-compat - Test CLI compatibility"
	@echo "  make benchmark  - Run performance benchmarks"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make run-ema    - Run on proboscis-ema source"