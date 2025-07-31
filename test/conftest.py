import copy

import pytest

from pinjected.di.design_interface import DESIGN_OVERRIDES_STORE
from pinjected.di.implicit_globals import IMPLICIT_BINDINGS
from pinjected import Injected


@pytest.fixture(scope="function", autouse=True)
def override_store_isolation():
    """
    Fixture to isolate DESIGN_OVERRIDES_STORE state between tests.

    This fixture preserves the global state of DESIGN_OVERRIDES_STORE before each test,
    provides a clean state during the test, and restores the original state afterward.
    This prevents test interference while maintaining the intentionally non-thread-safe
    behavior of the store.

    This is now autouse to ensure all tests get proper isolation from module-level
    design() contexts.
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


@pytest.fixture(scope="function", autouse=True)
def implicit_bindings_isolation():
    """
    Fixture to isolate IMPLICIT_BINDINGS state between tests.

    This prevents test interference from global implicit bindings modifications.
    This is now autouse to ensure all tests get proper isolation.
    """
    # Save the state at the beginning of the test
    # We track the initial keys and their binding types to detect modifications
    initial_state = {
        key: type(binding).__name__ for key, binding in IMPLICIT_BINDINGS.items()
    }
    initial_keys = set(initial_state.keys())

    # Also save the count for debugging
    initial_count = len(IMPLICIT_BINDINGS)  # noqa: F841

    try:
        yield
    finally:
        # Strategy: Only remove bindings that were added during the test
        # We don't try to restore modified bindings to avoid deepcopy issues
        current_keys = set(IMPLICIT_BINDINGS.keys())
        new_keys = current_keys - initial_keys

        # Remove bindings added during the test
        for key in new_keys:
            del IMPLICIT_BINDINGS[key]

        # Verify we didn't lose any original bindings
        final_keys = set(IMPLICIT_BINDINGS.keys())
        if not initial_keys.issubset(final_keys):
            missing = initial_keys - final_keys
            # Re-add any missing keys with a warning
            # This shouldn't happen in normal test execution
            import warnings

            warnings.warn(
                f"IMPLICIT_BINDINGS lost keys during test: {missing}. "
                "Test may have cleared global state improperly."
            )


@pytest.fixture(scope="function")
def full_isolation(override_store_isolation, implicit_bindings_isolation):
    """
    Combined fixture that provides both override store and implicit bindings isolation.

    Use this when tests might modify global injection state.
    """
    yield


@pytest.fixture(scope="function", autouse=True)
def preserve_injected_methods():
    """
    Preserve the original methods of the Injected class to prevent test pollution.

    Some tests might mock or patch Injected class methods globally without proper cleanup.
    This fixture ensures that the original methods are restored after each test.
    """
    from pinjected import Designed
    from pinjected.di.injected import InjectedPure

    # Store references to original methods
    original_pure = Injected.pure
    original_by_name = getattr(Injected, "by_name", None)
    original_from_function = getattr(Injected, "from_function", None)
    original_bind = getattr(Injected, "bind", None)

    # Store Designed methods too
    original_designed_bind = getattr(Designed, "bind", None)
    original_designed_zip = getattr(Designed, "zip", None)

    # Store all methods that might be patched
    original_injected_methods = {}
    for attr_name in dir(Injected):
        if not attr_name.startswith("_"):
            attr = getattr(Injected, attr_name, None)
            if callable(attr):
                original_injected_methods[attr_name] = attr

    original_designed_methods = {}
    for attr_name in dir(Designed):
        if not attr_name.startswith("_"):
            attr = getattr(Designed, attr_name, None)
            if callable(attr):
                original_designed_methods[attr_name] = attr

    # Also preserve class methods and static methods
    original_injectedpure_call = InjectedPure.__call__

    try:
        yield
    finally:
        # Restore original methods
        Injected.pure = original_pure
        if original_by_name is not None:
            Injected.by_name = original_by_name
        if original_from_function is not None:
            Injected.from_function = original_from_function
        if original_bind is not None:
            Injected.bind = original_bind

        # Restore Designed methods
        if original_designed_bind is not None:
            Designed.bind = original_designed_bind
        if original_designed_zip is not None:
            Designed.zip = original_designed_zip

        # Restore all other methods
        for attr_name, method in original_injected_methods.items():
            setattr(Injected, attr_name, method)

        for attr_name, method in original_designed_methods.items():
            setattr(Designed, attr_name, method)

        # Restore class methods
        InjectedPure.__call__ = original_injectedpure_call
