# Pinjected Pytest Runner

A pytest plugin and utilities for automatic IProxy test discovery and conversion in the pinjected ecosystem.

## Overview

The `pinjected-pytest-runner` package extends pinjected's testing capabilities by providing automatic discovery and conversion of IProxy test objects into pytest-compatible functions. This eliminates the need for manual conversion using the `@injected_pytest` decorator.

## Features

### 1. Automatic Discovery
- **Pytest Plugin**: Automatically finds IProxy objects with `test_` prefix
- **Seamless Integration**: Works with pytest's standard test discovery
- **No Manual Conversion**: Tests work without explicit `@injected_pytest` decorator

### 2. Manual Conversion Utilities
- **Adapter Functions**: Utilities for explicit conversion of IProxy objects
- **Batch Conversion**: Convert entire modules of IProxy tests
- **CLI Tools**: Command-line utilities for test conversion

### 3. Plugin Integration
- **Custom Collectors**: Uses pytest's collection hooks for seamless integration
- **Marker Support**: Adds `@pytest.mark.iproxy` to converted tests
- **Error Handling**: Graceful handling of conversion failures

## Installation

```bash
pip install pinjected-pytest-runner
```

## Usage

### Automatic Plugin Mode

Enable the plugin in your `conftest.py`:

```python
"""Pytest configuration for automatic IProxy test discovery"""

# Enable the IProxy pytest plugin
pytest_plugins = ['pinjected_pytest_runner.plugin']
```

Then define your tests as IProxy objects:

```python
from pinjected import IProxy, injected, design
from loguru import logger

# Create __pinjected__.py file with design configuration
# __pinjected__.py
__design__ = design().bind(
    logger=logger
)

# Define your IProxy test - will be automatically discovered
@injected
async def a_test_example(logger):
    """Test example with dependency injection"""
    logger.info("Running test")
    assert True
    return True

# Create IProxy object - pytest will automatically convert this
test_example: IProxy = a_test_example(logger)
```

### Manual Conversion Mode

For more control, use the manual conversion utilities:

```python
from pinjected import IProxy, injected, design
from pinjected_pytest_runner.utils import to_pytest

# Define your IProxy test
@injected
async def a_test_something(logger):
    """Test with manual conversion"""
    logger.info("Running manual test")
    assert True
    return True

# Create IProxy object
test_something_iproxy: IProxy = a_test_something(logger)

# Manually convert to pytest - this is what pytest will discover and run
test_something = to_pytest(test_something_iproxy)
```

### Batch Conversion

Convert entire modules of IProxy tests:

```python
from pinjected_pytest_runner.adapter import convert_module_iproxy_tests, create_pytest_module

# Convert all IProxy tests in a module
pytest_tests = convert_module_iproxy_tests("path/to/test_module.py")

# Create a new pytest module file
create_pytest_module("path/to/test_module.py", "path/to/converted_tests.py")
```

### CLI Usage

List IProxy tests in a module:

```bash
python -m pinjected_pytest_runner.adapter path/to/test_module.py --list
```

Convert a module to pytest format:

```bash
python -m pinjected_pytest_runner.adapter path/to/test_module.py -o converted_tests.py
```

## API Reference

### Core Functions

#### `to_pytest(iproxy, module_design=None)`
Convert an IProxy test to a pytest function.

**Parameters:**
- `iproxy`: The IProxy test object to convert
- `module_design`: Optional design configuration (uses default if not provided)

**Returns:** A pytest-compatible test function

#### `convert_module_iproxy_tests(module_path)`
Convert all IProxy test objects in a module to pytest functions.

**Parameters:**
- `module_path`: Path to the module file or dotted module name

**Returns:** Dictionary of test name to pytest function mappings

#### `create_pytest_module(source_module, output_file)`
Create a new pytest module file with converted IProxy tests.

**Parameters:**
- `source_module`: Path to module containing IProxy tests
- `output_file`: Path where to write the pytest module

#### `as_pytest_test(iproxy, module_design=None)`
Decorator to convert an IProxy object to a pytest function.

**Usage:**
```python
@as_pytest_test
test_something: IProxy = my_iproxy_function()
```

### Plugin Classes

#### `IProxyModule`
Custom Module collector that handles IProxy objects and integrates with pytest's collection system.

## Configuration

### Plugin Configuration

Add to your `conftest.py`:

```python
# Enable the IProxy pytest plugin
pytest_plugins = ['pinjected_pytest_runner.plugin']

# Optional: Configure pytest settings  
def pytest_configure(config):
    """Additional pytest configuration"""
    # Add custom markers or settings if needed
    pass
```

### Design Configuration

Configure dependency injection using the new `__pinjected__.py` file approach:

```python
# __pinjected__.py
from pinjected import design
from loguru import logger

# Configure module design
__design__ = design().bind(
    logger=logger,
    # Add other dependencies here
)
```

## Examples

### Basic Test Example

```python
# __pinjected__.py
from pinjected import design
from loguru import logger

__design__ = design().bind(logger=logger)

# test_basic.py
from pinjected import IProxy, injected

@injected
async def a_test_basic(logger):
    """Basic test example"""
    logger.info("Running basic test")
    assert 1 + 1 == 2
    return True

# This will be automatically discovered by pytest
test_basic: IProxy = a_test_basic(logger)
```

### Test with Multiple Dependencies

```python
# __pinjected__.py
from pinjected import design
from loguru import logger

__design__ = design().bind(
    logger=logger,
    config={"test_mode": True}
)

# test_with_config.py
from pinjected import IProxy, injected

@injected
async def a_test_with_config(logger, config):
    """Test with multiple dependencies"""
    logger.info(f"Running test with config: {config}")
    assert config["test_mode"] is True
    return True

test_with_config: IProxy = a_test_with_config(logger, config)
```

## Integration with Existing Tests

The plugin is designed to work alongside existing pinjected test functionality:

- **Existing `@injected_pytest` tests**: Continue to work as before
- **Regular pytest tests**: Unaffected by the plugin
- **Mixed test files**: Can contain both IProxy and regular pytest tests

## Troubleshooting

### Common Issues

1. **IProxy tests not discovered**: Ensure the plugin is enabled in `conftest.py`
2. **Import errors**: Check that all dependencies are properly configured in `__meta_design__`
3. **Conversion failures**: Check the pytest output for specific error messages

### Debug Mode

Enable verbose pytest output to see IProxy conversion details:

```bash
pytest -v --tb=short
```

## Requirements

- Python >= 3.10
- pinjected
- pytest >= 8.1.1

## License

MIT License - see the LICENSE file for details.
