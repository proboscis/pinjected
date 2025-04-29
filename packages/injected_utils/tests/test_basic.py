import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import injected_utils


def test_module_imports():
    assert hasattr(injected_utils, "async_batch_cached")
    assert hasattr(injected_utils, "async_cached")
    assert hasattr(injected_utils, "sqlite_dict")
    assert hasattr(injected_utils, "lzma_sqlite")
    assert hasattr(injected_utils, "async_cached_v2")
