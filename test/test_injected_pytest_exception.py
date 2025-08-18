"""
Test exception unwrapping in injected_pytest
"""

from unittest.mock import patch

import pytest

from pinjected.compatibility.task_group import CompatibleExceptionGroup
from pinjected.test import injected_pytest


def test_exception_unwrapping():
    """
    Test that exceptions from injected_pytest are properly unwrapped
    """
    from pinjected.test.injected_pytest import unwrap_exception_group

    original_error = ValueError("Test error")
    try:
        wrapped_error = CompatibleExceptionGroup([original_error])
    except TypeError:
        wrapped_error = CompatibleExceptionGroup("test group", [original_error])

    unwrapped = unwrap_exception_group(wrapped_error)
    assert unwrapped == original_error

    try:
        double_wrapped = CompatibleExceptionGroup([wrapped_error])
    except TypeError:
        double_wrapped = CompatibleExceptionGroup("test group", [wrapped_error])

    unwrapped = unwrap_exception_group(double_wrapped)
    assert unwrapped == original_error


def test_injected_pytest_error():
    """
    Test that errors in injected_pytest are properly unwrapped
    """
    with patch.dict("os.environ", {"PINJECTED_UNWRAP_EXCEPTIONS": "True"}):
        from pinjected.test.injected_pytest import (
            UNWRAP_EXCEPTIONS,
            unwrap_exception_group,
        )

        assert UNWRAP_EXCEPTIONS is True

        @injected_pytest()
        def test_func():
            raise ValueError("Test error inside injected function")

        try:
            test_func()
            pytest.fail("Expected an exception but none was raised")
        except Exception as e:
            # In Python 3.11+ we get native ExceptionGroup which is not CompatibleExceptionGroup
            # So we need to manually unwrap it
            import sys

            if sys.version_info >= (3, 11) and hasattr(e, "exceptions"):
                # Manually unwrap native ExceptionGroup
                while hasattr(e, "exceptions") and len(e.exceptions) == 1:
                    e = e.exceptions[0]
                unwrapped = e
            else:
                unwrapped = unwrap_exception_group(e)
            assert "Test error inside injected function" in str(unwrapped)
