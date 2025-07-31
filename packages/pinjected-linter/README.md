# Pinjected Linter

A comprehensive linter for the Pinjected dependency injection library that enforces best practices and catches common mistakes.

## Features

- **25+ specialized rules** for Pinjected-specific patterns
- **Auto-fix support** for common issues
- **pyproject.toml configuration** for project-specific settings
- **Pre-commit hook integration** for automated checking
- **VSCode extension** for real-time feedback (coming soon)

## Installation

### Option 1: Rust Binary (Recommended - 26x faster)

Install the Rust binary directly with a one-liner:

```bash
curl -sSL https://raw.githubusercontent.com/proboscis/pinjected/main/packages/pinjected-linter/rust-poc/remote-install.sh | bash
```

**Prerequisites:** Requires [Rust and Cargo](https://rustup.rs/) to be installed.

**Alternative Rust installation methods:**
```bash
# Clone and install locally
git clone https://github.com/proboscis/pinjected.git
cd pinjected/packages/pinjected-linter/rust-poc
cargo install --path . --force

# Or use the local install script
./install.sh
```

### Option 2: Python Wrapper

Install the Python wrapper (delegates to Rust binary if available):

```bash
pip install pinjected-linter
```

## Quick Start

```bash
# Lint all Python files in the current directory
pinjected-linter

# Lint specific files
pinjected-linter src/mymodule.py

# Auto-fix issues
pinjected-linter --fix

# Show detailed explanations
pinjected-linter --show-source
```

## Configuration

Configure the linter in your `pyproject.toml`:

```toml
[tool.pinjected-linter]
# Enable/disable specific rules
enable = ["PINJ001", "PINJ002", "PINJ008"]
disable = ["PINJ016"]

# Rule-specific configuration
[tool.pinjected-linter.rules.PINJ017]
categories = ["model", "dataset", "service", "custom_category"]

[tool.pinjected-linter.rules.PINJ020]
allow_in_tests = false
```

## Pre-commit Integration

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pinjected/pinjected-linter
    rev: v0.1.0
    hooks:
      - id: pinjected-linter
```

## Available Rules

### @instance Decorator Rules
- **PINJ001**: Instance function naming convention (use nouns, not verbs)
- **PINJ002**: Instance function default arguments (don't use defaults)
- **PINJ003**: Async instance naming (no `a_` prefix)
- **PINJ004**: Direct instance call detection

### @injected Decorator Rules
- **PINJ005**: Injected function naming convention (use verbs)
- **PINJ006**: Async injected naming (must have `a_` prefix)
- **PINJ007**: Slash separator position
- **PINJ008**: Injected function dependency declaration (CRITICAL)
- **PINJ009**: No await in injected AST building
- **PINJ010**: Incomplete injected usage
- **PINJ015**: Missing slash in injected
- **PINJ025**: Protocol class for injected functions

### design() Function Rules
- **PINJ011**: Design key naming convention (snake_case)
- **PINJ012**: Deprecated `__meta_design__`
- **PINJ013**: Global variable injection

### IProxy Type Rules
- **PINJ014**: Entry point type annotation
- **PINJ023**: IProxy method chaining validation
- **PINJ024**: Entry point naming convention

### Code Style Rules
- **PINJ016**: Underscore parameter convention
- **PINJ017**: Category prefix convention
- **PINJ020**: No print statements
- **PINJ021**: Logger context for long procedures
- **PINJ022**: Double injected wrapping

### Testing Rules
- **PINJ018**: Test function decorator
- **PINJ019**: Test design patterns

## Development

```bash
# Clone the repository
git clone https://github.com/pinjected/pinjected.git
cd pinjected/packages/pinjected-linter

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run linter on itself
pinjected-linter src/
```

## License

MIT License - see LICENSE file for details.
