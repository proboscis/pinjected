"""Pytest plugin for discovering and running IProxy test objects

This plugin properly integrates with pytest's collection system to
automatically discover and run IProxy objects as test items.
"""

import pytest
from _pytest.python import Module
from pinjected import IProxy, design
from pinjected.test.injected_pytest import _to_pytest
from pinjected.di.partially_injected import Partial


class IProxyModule(Module):
    """Custom Module collector that handles IProxy objects"""

    def collect(self):
        """Collect test items from the module, converting IProxy objects"""
        yield from self._collect_standard_items()

        yield from self._collect_iproxy_items()

    def _collect_standard_items(self):
        """Collect standard pytest items, skipping Partial objects"""
        for item in super().collect():
            if hasattr(item, "obj") and isinstance(item.obj, Partial):
                continue
            yield item

    def _collect_iproxy_items(self):
        """Collect IProxy objects and convert them to pytest functions"""
        module = self.obj
        module_design = getattr(module, "__meta_design__", design())
        module_file = str(self.path)

        for name in dir(module):
            if not name.startswith("test"):
                continue

            obj = getattr(module, name)
            if isinstance(obj, Partial) or not isinstance(obj, IProxy):
                continue

            yield from self._convert_iproxy_to_test(
                name, obj, module_design, module_file
            )

    def _convert_iproxy_to_test(self, name, obj, module_design, module_file):
        """Convert a single IProxy object to a pytest function"""
        try:
            test_func = _to_pytest(obj, module_design, module_file)
            test_func._iproxy_original = obj
            test_func.__name__ = name
            yield pytest.Function.from_parent(self, name=name, callobj=test_func)
        except Exception as e:
            yield self._create_error_test(name, str(e))

    def _create_error_test(self, name, error_msg):
        """Create an error test for failed IProxy conversion"""

        def error_test():
            pytest.fail(f"Failed to convert IProxy '{name}': {error_msg}")

        error_test.__name__ = name
        return pytest.Function.from_parent(self, name=name, callobj=error_test)


def pytest_pycollect_makeitem(collector, name, obj):
    """Hook to prevent collection of @injected functions"""
    from pinjected.di.partially_injected import Partial

    if isinstance(obj, Partial):
        return []  # Return empty list to skip this item

    return None


def pytest_pycollect_makemodule(module_path, parent):
    """Replace the default module collector with our IProxy-aware version"""
    if module_path.suffix == ".py":
        return IProxyModule.from_parent(parent, path=module_path)
    return None


def pytest_collection_modifyitems(session, config, items):
    """Add markers to IProxy tests"""
    for item in items:
        if hasattr(item.obj, "_iproxy_original"):
            item.add_marker(pytest.mark.iproxy)


def pytest_configure(config):
    """Register plugin configuration"""
    config.addinivalue_line(
        "markers", "iproxy: marks tests as converted from IProxy objects"
    )


def pytest_report_header(config):
    """Add IProxy plugin info to pytest header"""
    return "IProxy plugin: enabled (automatic IProxy test discovery)"
