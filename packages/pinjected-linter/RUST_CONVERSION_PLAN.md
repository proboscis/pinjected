# Pinjected Linter Rust Conversion Plan

## Overview
Convert the Python-based pinjected-linter to Rust for improved performance and integration with other Rust-based tools.

## Why Rust?
- **Performance**: 10-100x faster than Python for AST parsing and analysis
- **Memory efficiency**: Lower memory footprint
- **Parallelization**: Built-in safe concurrency with Rayon
- **Integration**: Can be used with other Rust tools like Ruff
- **Distribution**: Single binary, no Python runtime needed

## Architecture

### 1. Core Components

#### AST Parser
- Use `rustpython-parser` for Python AST parsing
- Alternative: Consider `ruff_python_parser` if it becomes available as a library

#### Rule Engine
```rust
trait LintRule {
    fn rule_id(&self) -> &str;
    fn check(&self, context: &RuleContext) -> Vec<Violation>;
    fn is_enabled(&self) -> bool;
}
```

#### Configuration
- Support pyproject.toml via `toml` crate
- Command-line interface via `clap`
- JSON output support via `serde_json`

### 2. Implementation Phases

#### Phase 1: Core Infrastructure (Week 1)
- [x] Basic AST parsing with rustpython-parser
- [x] Rule trait definition
- [x] Simple CLI with clap
- [ ] Configuration loading from pyproject.toml
- [ ] Basic reporting (terminal output)

#### Phase 2: Rule Implementation (Week 2-3)
Convert all 15 rules to Rust:
- [x] PINJ001: Instance naming convention
- [ ] PINJ002: Instance defaults
- [ ] PINJ003: Async instance naming
- [ ] PINJ004: Direct instance call
- [ ] PINJ005: Injected function naming
- [ ] PINJ006: Async injected naming
- [ ] PINJ007: Slash separator position
- [ ] PINJ008: Injected dependency declaration
- [ ] PINJ009: No await in injected
- [ ] PINJ010: Design usage
- [ ] PINJ011: IProxy annotations
- [ ] PINJ012: Dependency cycles
- [ ] PINJ013: Builtin shadowing
- [ ] PINJ014: Missing stub file
- [ ] PINJ015: Missing slash

#### Phase 3: Advanced Features (Week 4)
- [ ] Parallel file processing with Rayon
- [ ] Symbol table builder
- [ ] Cross-file analysis
- [ ] Performance optimization
- [ ] Memory optimization

#### Phase 4: Integration (Week 5)
- [ ] Python bindings via PyO3 (optional)
- [ ] Integration tests
- [ ] Migration guide
- [ ] Performance benchmarks

### 3. Technical Decisions

#### Line/Column Conversion
rustpython-parser provides byte offsets. We need to:
1. Build a line offset table during parsing
2. Convert byte offsets to line:column for output

```rust
struct LineOffsetTable {
    offsets: Vec<usize>,
}

impl LineOffsetTable {
    fn from_source(source: &str) -> Self { ... }
    fn get_location(&self, offset: usize) -> (usize, usize) { ... }
}
```

#### Symbol Table
For rules that need cross-reference information:
```rust
struct SymbolTable {
    functions: HashMap<String, FunctionInfo>,
    classes: HashMap<String, ClassInfo>,
    imports: HashMap<String, ImportInfo>,
}
```

#### Configuration
Match Python configuration structure:
```rust
#[derive(Deserialize)]
struct Config {
    enable: Option<Vec<String>>,
    disable: Option<Vec<String>>,
    rules: HashMap<String, RuleConfig>,
    exclude: Vec<String>,
}
```

### 4. Performance Goals
- Parse and lint 1000 files in < 1 second
- Memory usage < 100MB for large projects
- Support incremental linting (future)

### 5. Compatibility
- Maintain same rule IDs and messages
- Support same configuration format
- Provide migration tool for custom rules

## Migration Strategy

1. **Parallel Development**: Keep Python version while developing Rust version
2. **Feature Parity**: Ensure Rust version has all features
3. **Beta Testing**: Release as `pinjected-lint-rust` for testing
4. **Gradual Migration**: 
   - v0.2.0: Rust version available as opt-in
   - v0.3.0: Rust version as default, Python as fallback
   - v0.4.0: Rust only

## Development Setup

```bash
# Create Rust project structure
cargo new --lib pinjected-linter-rust
cd pinjected-linter-rust

# Add dependencies
cargo add rustpython-parser rustpython-ast
cargo add clap --features derive
cargo add anyhow
cargo add rayon
cargo add serde --features derive
cargo add toml
cargo add walkdir
```

## Testing Strategy
1. Port all Python tests to Rust
2. Property-based testing with `proptest`
3. Fuzzing with `cargo-fuzz`
4. Benchmark against Python version

## Future Enhancements
- LSP server for real-time linting
- Integration with rust-analyzer
- Custom rule API
- Incremental parsing with tree-sitter