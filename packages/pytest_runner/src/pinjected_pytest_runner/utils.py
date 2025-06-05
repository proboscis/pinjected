"""Simple utilities for running IProxy tests with pytest

This provides a minimal approach to make IProxy tests work with pytest
without requiring complex plugins or conversions.
"""

from typing import Any, Optional
from pinjected import IProxy, design
from pinjected.test.injected_pytest import _to_pytest


def to_pytest(iproxy: IProxy, module_design: Optional[Any] = None) -> Any:
    """Convert an IProxy test to a pytest function

    This is a simple wrapper around pinjected's _to_pytest that handles
    the common case of converting IProxy tests.

    Usage:
        from pinjected_pytest_runner.utils import to_pytest

        test_something_iproxy: IProxy = my_test_function(dependencies)

        test_something = to_pytest(test_something_iproxy)

    Args:
        iproxy: The IProxy test object to convert
        module_design: Optional design configuration (uses default if not provided)

    Returns:
        A pytest-compatible test function
    """
    import inspect

    frame = inspect.currentframe().f_back
    file_path = frame.f_globals.get("__file__", "<unknown>")

    if module_design is None:
        module_design = frame.f_globals.get("__meta_design__", design())

    return _to_pytest(iproxy, module_design, file_path)


__doc__ += """

Example usage in a test file:

```python
from pathlib import Path
from pinjected import IProxy, injected, design
from pinjected_pytest_runner.utils import to_pytest

@injected
async def a_test_example(logger):
    '''Test example'''
    logger.info("Running test")
    assert True
    return True

test_example_iproxy: IProxy = a_test_example(logger)

test_example = to_pytest(test_example_iproxy)
```
"""
