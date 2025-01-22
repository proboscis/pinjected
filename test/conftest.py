import copy
import pytest
from pinjected.di.design_interface import DESIGN_OVERRIDES_STORE, DesignOverridesStore

@pytest.fixture(scope="function")
def override_store_isolation():
    """
    Fixture to isolate DESIGN_OVERRIDES_STORE state between tests.
    
    This fixture preserves the global state of DESIGN_OVERRIDES_STORE before each test,
    provides a clean state during the test, and restores the original state afterward.
    This prevents test interference while maintaining the intentionally non-thread-safe
    behavior of the store.
    """
    # Deep copy to ensure complete isolation of mutable state
    original_store = copy.deepcopy(DESIGN_OVERRIDES_STORE.bindings)
    original_stack = copy.deepcopy(DESIGN_OVERRIDES_STORE.stack)
    
    try:
        # Provide the test with an empty store
        DESIGN_OVERRIDES_STORE.bindings = {}
        DESIGN_OVERRIDES_STORE.stack = []
        yield
    finally:
        # Restore original state after test
        DESIGN_OVERRIDES_STORE.bindings = original_store
        DESIGN_OVERRIDES_STORE.stack = original_stack
