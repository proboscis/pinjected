# Pinjected IProxy[T] Entrypoint Indexer

Fast Rust-based indexer for discovering @injected functions that can work with IProxy[T] objects in the pinjected dependency injection framework.

## Overview

This indexer helps IDE plugins and tools find which @injected functions can be called with a given IProxy[T] type. It only indexes functions that follow the pinjected pattern: exactly one non-default parameter after any positional-only parameters.

## Installation

```bash
# Build from source
cargo build --release

# Install globally
cp target/release/pinjected-indexer ~/.local/bin/
```

## CLI Usage

### Finding IProxy Functions

```bash
# Find all @injected functions that accept User type
pinjected-indexer --root /path/to/project query-iproxy-functions User

# Find functions for generic types
pinjected-indexer --root /path/to/project query-iproxy-functions "List[User]"
pinjected-indexer --root /path/to/project query-iproxy-functions "Dict[str, User]"
```

### Daemon Mode (for IDE Integration)

```bash
# Start daemon in background
pinjected-indexer start

# Check daemon status
pinjected-indexer status

# Stop daemon
pinjected-indexer stop

# Test query to running daemon
pinjected-indexer test-iproxy-query User
```

### Other Commands

```bash
# Build index and show statistics
pinjected-indexer --root /path/to/project build

# Show index statistics
pinjected-indexer --root /path/to/project stats
```

## Function Validation Rules

The indexer only finds @injected functions that have **exactly one parameter without a default value**:

### Valid Functions
```python
@injected
def process_user(user: User, timeout=30):  # ✅ Valid: user is the only non-default param

@injected
def handle_data(data: List[User]):  # ✅ Valid: data is the only param

@injected
def transform(x: Product, limit=10, offset=0):  # ✅ Valid: x is the only non-default param
```

### Invalid Functions (Not Indexed)
```python
@injected
def process(x: User, y: Product):  # ❌ Invalid: 2 non-default params

@injected
def handle():  # ❌ Invalid: no parameters

@injected
def transform(x: User = None):  # ❌ Invalid: all params have defaults
```

## Performance

- **Warm queries**: <10ms
- **Cold start**: ~130ms
- **Binary size**: ~5.2MB (optimized release build)

## Architecture

- **In-memory index** with DashMap for concurrent access
- **Binary cache** for instant warm starts
- **Unix socket RPC** for daemon communication
- **AST parsing** with rustpython-parser
- **Auto-shutdown** after 5 minutes idle

## Integration

The indexer is designed for transparent integration with IDE plugins:

1. Plugin detects IProxy[T] variable in code
2. Plugin queries indexer for matching @injected functions
3. Plugin shows dropdown with available entrypoints
4. User selects function to run with the IProxy object

## Development

```bash
# Run tests
cargo test

# Run specific test
cargo test test_parameter_validation

# Build with debug info
cargo build

# Run with debug logging
./target/debug/pinjected-indexer --log-level debug query-iproxy-functions User
```