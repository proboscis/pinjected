"""Pytest runner with automatic IProxy test discovery for pinjected."""

from .adapter import convert_module_iproxy_tests, create_pytest_module, as_pytest_test
from .plugin import IProxyModule
from .utils import to_pytest

__version__ = "0.1.0"
__all__ = [
    "IProxyModule",
    "as_pytest_test",
    "convert_module_iproxy_tests",
    "create_pytest_module",
    "to_pytest",
]
