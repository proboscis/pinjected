# UV Monorepo Conversion Log

This document logs the process of converting the pinjected repository to a uv-based monorepo structure, integrating the pinjected-openai package as a subpackage.

## Initial State

The repository started with the following structure:
- Core pinjected package in the root directory
- No monorepo structure for additional packages
- Using Poetry for dependency management

## Target State

The target structure was:
- Core pinjected package remains in the root directory
- Additional packages under `packages/` directory
- pinjected-openai integrated as `packages/openai_support`
- Using uv for dependency management with workspace features
- No PYTHONPATH usage for imports

## Conversion Steps

### 1. Repository Structure Setup

1. Created the packages directory structure:
   ```bash
   mkdir -p packages/openai_support/src/pinjected_openai
   mkdir -p packages/openai_support/tests
   ```

2. Cloned and integrated the pinjected-openai repository:
   ```bash
   git clone https://github.com/proboscis/pinjected-openai.git
   cp -r pinjected-openai/* packages/openai_support/
   rm -rf packages/openai_support/.git
   ```

### 2. Package Configuration

1. Created pyproject.toml for the openai_support package:
   ```toml
   [build-system]
   requires = ["hatchling==1.26.3"]
   build-backend = "hatchling.build"

   [project]
   name = "pinjected-openai"
   version = "1.0.2"
   description = "openai bindings for pinjected library"
   readme = "README.md"
   requires-python = ">=3.10"
   license = "MIT"
   authors = [
       { name = "proboscis", email = "nameissoap@gmail.com" }
   ]
   classifiers = [
       "Programming Language :: Python :: 3",
       "License :: OSI Approved :: MIT License",
       "Operating System :: OS Independent",
   ]

   dependencies = [
       "pinjected",
       "openai>=1.61.0",
       "tiktoken",
       "injected-utils>=0.1.32",
       "pydub",
       "pillow",
       "loguru",
       "pandas",
       "filelock",
       "reactivex>=4.0.4",
       "moviepy>=1.0.3",
       "pinjected-rate-limit>=0.1.0",
       "tenacity>=9.0.0",
       "json-repair>=0.35.0",
   ]

   [tool.hatch.metadata]
   allow-direct-references = true

   [tool.hatch.build.targets.wheel]
   packages = ["src"]

   [tool.pytest.ini_options]
   pythonpath = ["src"]

   [tool.uv.sources]
   pinjected = { workspace = true }

   [dependency-groups]
   dev = [
       "pytest>=8.1.1,<9"
   ]
   ```

2. Updated the root pyproject.toml with workspace configuration:
   ```toml
   [tool.uv.workspace]
   members = ["packages/*"]
   ```

3. Created a basic test file for the openai_support package:
   ```python
   # packages/openai_support/tests/test_basic.py
   import pytest
   from pinjected_openai import __version__

   def test_version():
       """Test that the version is a string."""
       assert isinstance(__version__, str)
   ```

### 3. Build and Test Configuration

1. Updated the Makefile with targets for the openai_support package:
   ```makefile
   setup-all:
       cd packages/openai_support && uv sync --group dev

   test:
       cd test && uv run pytest
       cd packages/openai_support && uv sync --group dev && uv run -m pytest tests

   test-cov:
       cd test && uv run pytest -v --cov=pinjected --cov-report=xml
       cd packages/openai_support && uv sync --group dev && uv run -m pytest tests

   publish-openai:
       cd packages/openai_support && uv build
       cd packages/openai_support && uv pip publish dist/*.whl dist/*.tar.gz

   tag-version-openai:
       git tag pinjected-openai-v$(shell grep -m 1 version packages/openai_support/pyproject.toml | cut -d'"' -f2)
       git push --tags

   release-openai: tag-version-openai publish-openai
   ```

2. Updated CI workflows to include setup for all packages:
   ```yaml
   # In .github/workflows/ci.yml and .github/workflows/pytest.yml
   - name: Install dependencies
     run: |
       make sync
       make setup-all
   ```

### 4. Dependency Management

1. Initially tried using `--dependency-group` flag but discovered it was incorrect
2. Updated to use the correct `--group` flag for uv sync:
   ```makefile
   setup-all:
       cd packages/openai_support && uv sync --group dev
   ```

3. Removed unnecessary pythonpath configuration from root pyproject.toml

### 5. Testing and Verification

1. Ran local tests to verify the setup:
   ```bash
   make sync
   make setup-all
   make test
   ```

2. Verified that all tests pass across Python versions 3.10-3.13 in CI

### 6. Documentation

1. Created how-to-add-package.md guide for future package additions
2. Updated README.md with monorepo structure information

## Challenges and Solutions

### Challenge: Incorrect uv Sync Flag
- **Problem**: Initially used `--dependency-group dev` which is not supported
- **Solution**: Updated to use the correct `--group dev` flag

### Challenge: Unnecessary pythonpath Configuration
- **Problem**: Added pythonpath to root pyproject.toml which was unnecessary with workspace configuration
- **Solution**: Removed pythonpath configuration and relied on proper workspace setup

### Challenge: CI Configuration
- **Problem**: CI workflows needed to be updated to install dependencies for all packages
- **Solution**: Added `make setup-all` to CI workflows

## Results

The conversion was successful with:
- All tests passing locally and in CI
- Proper dependency resolution between packages
- No PYTHONPATH usage
- Clean monorepo structure
- Documentation for future package additions

## Lessons Learned

1. **Workspace Configuration**: uv workspace features provide proper dependency resolution without needing pythonpath
2. **Dependency Groups**: Use `--group` flag for managing development dependencies
3. **CI Integration**: Ensure CI workflows install dependencies for all packages
4. **Testing**: Verify changes across all supported Python versions

## Future Improvements

1. Consider adding more comprehensive tests for the openai_support package
2. Explore additional uv workspace features for improved dependency management
3. Add more documentation for package development workflows
