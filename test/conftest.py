import copy

import pytest

from pinjected.di.design_interface import DESIGN_OVERRIDES_STORE
from pinjected.di.implicit_globals import IMPLICIT_BINDINGS


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


@pytest.fixture(scope="function")
def implicit_bindings_isolation():
    """
    Fixture to isolate IMPLICIT_BINDINGS state between tests.

    This prevents test interference from global implicit bindings modifications.
    """
    # Deep copy the original bindings
    original_bindings = copy.deepcopy(IMPLICIT_BINDINGS)

    try:
        yield
    finally:
        # Clear current bindings and restore original
        IMPLICIT_BINDINGS.clear()
        IMPLICIT_BINDINGS.update(original_bindings)


@pytest.fixture(scope="function")
def full_isolation(override_store_isolation, implicit_bindings_isolation):
    """
    Combined fixture that provides both override store and implicit bindings isolation.

    Use this when tests might modify global injection state.
    """
    yield
