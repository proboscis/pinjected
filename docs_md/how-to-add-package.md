# How to Add a Package to the Pinjected Monorepo

This guide explains the process of adding a new package to the pinjected monorepo structure. The monorepo is configured to use `uv` for dependency management and workspace features.

## Prerequisites

- [uv](https://github.com/astral-sh/uv) installed on your system
- Basic understanding of Python packaging
- Git access to the pinjected repository

## Directory Structure

The pinjected monorepo follows this structure:

```
pinjected/
├── pinjected/           # Core package code
├── packages/            # Additional packages
│   └── openai_support/  # Example: pinjected-openai package
│       ├── pyproject.toml
│       ├── README.md
│       ├── src/
│       │   └── pinjected_openai/
│       └── tests/
├── test/                # Core package tests
├── pyproject.toml       # Root workspace configuration
├── Makefile             # Build and test commands
└── uv.lock              # Shared lockfile
```

## Step-by-Step Guide

### 1. Create the Package Directory

Create a new directory under `packages/` with a descriptive name for your package:

```bash
mkdir -p packages/your_package_name/src/your_package_name
mkdir -p packages/your_package_name/tests
```

### 2. Configure Package Metadata

Create a `pyproject.toml` file in your package directory:

```toml
[build-system]
requires = ["hatchling==1.26.3"]
build-backend = "hatchling.build"

[project]
name = "pinjected-your-package-name"
version = "0.1.0"
description = "Your package description"
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
authors = [
    { name = "Your Name", email = "your.email@example.com" }
]
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]

dependencies = [
    "pinjected",
    # Add other dependencies here
]

[tool.hatch.metadata]
allow-direct-references = true

[tool.hatch.build.targets.wheel]
packages = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]

# If your package depends on other workspace packages
[tool.uv.sources]
pinjected = { workspace = true }
# Add other workspace dependencies if needed

# Development dependencies
[dependency-groups]
dev = [
    "pytest>=8.1.1,<9"
    # Add other development dependencies here
]
```

### 3. Create Basic Package Files

Create the following files to set up your package:

#### `packages/your_package_name/README.md`

```markdown
# Pinjected Your Package Name

Description of your package and its purpose.

## Installation

```bash
pip install pinjected-your-package-name
```

## Usage

Basic usage examples.
```

#### `packages/your_package_name/src/your_package_name/__init__.py`

```python
"""Your package description."""

__version__ = "0.1.0"
```

#### `packages/your_package_name/tests/test_basic.py`

```python
import pytest
from your_package_name import __version__

def test_version():
    """Test that the version is a string."""
    assert isinstance(__version__, str)
```

### 4. Update Root Configuration

Ensure the root `pyproject.toml` has the workspace configuration:

```toml
[tool.uv.workspace]
members = ["packages/*"]
```

### 5. Update the Makefile

Add targets for your package in the Makefile:

```makefile
# Add your package to setup-all
setup-all:
	cd packages/openai_support && uv sync --group dev
	cd packages/your_package_name && uv sync --group dev

# Add your package to test
test:
	cd test && uv run pytest
	cd packages/openai_support && uv sync --group dev && uv run -m pytest tests
	cd packages/your_package_name && uv sync --group dev && uv run -m pytest tests

# Add your package to test-cov (if needed)
test-cov:
	cd test && uv run pytest -v --cov=pinjected --cov-report=xml
	cd packages/openai_support && uv sync --group dev && uv run -m pytest tests
	cd packages/your_package_name && uv sync --group dev && uv run -m pytest tests

# Add publish target for your package
publish-your-package:
	cd packages/your_package_name && uv build
	cd packages/your_package_name && uv pip publish dist/*.whl dist/*.tar.gz

# Add tag-version target for your package
tag-version-your-package:
	git tag pinjected-your-package-name-v$(shell grep -m 1 version packages/your_package_name/pyproject.toml | cut -d'"' -f2)
	git push --tags

# Add release target for your package
release-your-package: tag-version-your-package publish-your-package
```

### 6. Update CI Configuration

Ensure CI workflows include your package:

```yaml
# In .github/workflows/ci.yml and .github/workflows/pytest.yml
- name: Install dependencies
  run: |
    make sync
    make setup-all  # This will set up all packages including yours
```

### 7. Test Your Package

Run the following commands to verify your package setup:

```bash
make sync
make setup-all
make test
```

### 8. Commit Your Changes

```bash
git add packages/your_package_name
git add pyproject.toml
git add Makefile
git commit -m "Add your-package-name package to monorepo"
git push
```

## Best Practices

1. **Dependency Management**:
   - Use `[dependency-groups]` for development dependencies
   - Use `[tool.uv.sources]` for workspace dependencies
   - Keep runtime dependencies under `[project].dependencies`

2. **Testing**:
   - Add basic tests for your package
   - Ensure tests run in CI

3. **Documentation**:
   - Add a README.md for your package
   - Document public APIs

4. **Version Management**:
   - Follow semantic versioning
   - Update the version in pyproject.toml when making changes

## Troubleshooting

### Common Issues

1. **Package Not Found in Workspace**:
   - Ensure your package is listed in the root `[tool.uv.workspace]` configuration
   - Check that your package directory is directly under `packages/`

2. **Dependencies Not Resolving**:
   - Verify workspace dependencies are correctly configured in `[tool.uv.sources]`
   - Run `make setup-all` to install all dependencies

3. **Tests Failing**:
   - Check that `pythonpath` is correctly set in your package's `pyproject.toml`
   - Ensure your package is properly installed with `uv sync`

For more complex issues, refer to the [uv documentation](https://github.com/astral-sh/uv) or open an issue in the pinjected repository.
