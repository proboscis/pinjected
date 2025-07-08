# Pinjected Linter (Rust)

A blazing fast linter for the Pinjected dependency injection framework, written in Rust.

## Performance

- **26x faster** than the Python version
- Processes **2,600+ files/second**
- Supports parallel processing with configurable threads
- Includes AST caching for repeated runs

## Features

- All 15 pinjected lint rules implemented
- Directory walking with pattern exclusion
- Parallel file processing
- AST caching
- Early exit optimizations
- Detailed timing information
- Rule filtering
- Support for `# noqa` comment directives to suppress violations
- Automatic configuration loading from `pyproject.toml`

## Usage

```bash
# Lint a single file
pinjected-linter-rust myfile.py

# Lint a directory
pinjected-linter-rust /path/to/project

# With caching and timing
pinjected-linter-rust /path/to/project --cache --timing

# Run specific rule only
pinjected-linter-rust /path/to/project --rule PINJ001

# Skip patterns
pinjected-linter-rust /path/to/project --skip test_ --skip __pycache__

# Use specific number of threads
pinjected-linter-rust /path/to/project -j 8

# Count files only (no analysis)
pinjected-linter-rust /path/to/project --count

# Exit with error code 1 if warnings are found
pinjected-linter-rust /path/to/project --error-on-warning

# Show only specific severity levels
pinjected-linter-rust /path/to/project --show-only error
pinjected-linter-rust /path/to/project --show-only warning
pinjected-linter-rust /path/to/project --show-only error,warning

# Show minimum severity level and above (threshold)
pinjected-linter-rust /path/to/project --severity error     # errors only
pinjected-linter-rust /path/to/project --severity warning   # warnings and errors
```

### Severity Filtering

The linter provides two ways to filter violations by severity:

- `--severity <level>`: Shows violations at or above the specified severity level (threshold)
  - `--severity error`: Shows only errors
  - `--severity warning`: Shows warnings AND errors
  - `--severity info`: Shows all violations

- `--show-only <levels>`: Shows only the specific severity levels listed (exact match)
  - `--show-only error`: Shows only errors
  - `--show-only warning`: Shows only warnings
  - `--show-only error,warning`: Shows errors and warnings, but not info

Note: `--severity` and `--show-only` cannot be used together.

### Output Statistics

The linter always displays comprehensive statistics at the end:

```
============================================================
Linting Summary:
------------------------------------------------------------
Total violations: 55
  Errors: 29
  Warnings: 26
  Info: 0

Violations by rule:
  PINJ005: 26
  PINJ015: 14
  PINJ006: 7
  PINJ004: 6
  PINJ003: 1
  PINJ001: 1

Performance:
  Files analyzed: 128
  Time: 0.03s
  Files/second: 3887.19
============================================================
```

## Suppressing Violations with `# noqa`

You can suppress linter violations on specific lines using `# noqa` comments:

```python
# Suppress all violations on this line
@instance
def get_data():  # noqa
    pass

# Suppress specific rule
@instance
def fetch_info():  # noqa: PINJ001
    pass

# Suppress multiple rules
@injected
def process(logger,/, data):  # noqa: PINJ005, PINJ015
    pass

# Case-insensitive
def list():  # NOQA: PINJ013
    pass
```

### Supported formats:
- `# noqa` - Suppress all violations on this line
- `# noqa: RULE_ID` - Suppress specific rule (e.g., PINJ001)
- `# noqa: RULE1, RULE2` - Suppress multiple rules

Note: The noqa comment must be on the same line as the violation. Comments are case-insensitive (`noqa`, `NOQA`, `NoQa` all work).

## Configuration

The linter automatically loads configuration from `pyproject.toml` in the `[tool.pinjected-linter]` section:

```toml
[tool.pinjected-linter]
# Enable specific rules (if not specified, all rules are enabled)
enable = ["PINJ001", "PINJ002", "PINJ003"]

# Or disable specific rules
disable = ["PINJ001", "PINJ005"]

# Exclude paths from linting
exclude = [
    ".venv",
    "venv", 
    ".git",
    "__pycache__",
    "build",
    "dist",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
]

# Configure specific rules
[tool.pinjected-linter.rules.PINJ014]
min_injected_functions = 3
stub_search_paths = ["stubs", "typings", "types"]
ignore_patterns = ["**/tests/**", "**/test_*.py"]
```

Command line options override configuration file settings.

## Building

```bash
# Development build
cargo build

# Release build (optimized)
cargo build --release
```

## Rules

| Rule ID | Description | Severity |
|---------|-------------|----------|
| PINJ001 | Instance naming convention | Warning |
| PINJ002 | Instance default arguments | Error |
| PINJ003 | Async instance naming (a_ prefix) | Warning |
| PINJ004 | Direct instance function calls | Warning |
| PINJ005 | Injected function naming (verb form) | Warning |
| PINJ006 | Async injected naming (a_ prefix) | Error |
| PINJ007 | Slash separator position | Warning |
| PINJ009 | No direct calls to @injected functions | Error |
| PINJ010 | Design usage patterns | Warning |
| PINJ011 | IProxy annotations for service types | Warning |
| PINJ012 | Dependency cycle detection | Error |
| PINJ013 | Builtin shadowing prevention | Warning |
| PINJ014 | Missing stub file detection | Warning |
| PINJ015 | Missing slash separator | Warning |
| PINJ016 | Missing protocol parameter in @injected | Warning |
| PINJ017 | Missing type annotations for dependencies | Warning |

## Exit Codes

The linter uses different exit codes to indicate various failure conditions:

| Code | Description |
|------|-------------|
| 0 | Success - no violations found, or only warnings (without `--error-on-warning`) |
| 1 | Violations found (errors, or warnings with `--error-on-warning`) |
| 2 | Usage error - invalid command-line arguments |
| 3 | File error - file not found or I/O error |
| 4 | Parse error - syntax error in Python files |
| 5 | Configuration error - invalid config file |

Use `--error-on-warning` to treat warnings as errors for CI/CD pipelines.

## Architecture

The linter is structured as:
- `src/rules/`: One file per rule implementation
- `src/utils/`: Shared utilities and patterns
- `src/models.rs`: Core data structures
- `src/lib.rs`: Library interface
- `src/main.rs`: CLI application

## Optimizations

1. **Parallel Processing**: Uses rayon for multi-threaded file analysis
2. **AST Caching**: Caches parsed ASTs to avoid re-parsing
3. **Early Exit**: Skips files without pinjected imports
4. **Rule Filtering**: Only runs relevant rules based on file content
5. **Single Pass**: Groups rules by statement type for cache efficiency

## Development

To add a new rule:
1. Create `src/rules/pinjXXX_rule_name.rs`
2. Implement the `LintRule` trait
3. Add to `src/rules/mod.rs`
4. Create tests in the test file

## Integration

This can be integrated into:
- Pre-commit hooks
- CI/CD pipelines
- IDE extensions
- Build systems

## Future Work

- Python bindings via PyO3
- LSP server for real-time linting
- Auto-fix capabilities
- Configuration file support