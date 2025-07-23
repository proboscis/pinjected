"""
Pytest fixture integration for pinjected Design objects.

This module provides a way to expose pinjected Design bindings as pytest fixtures.

Example Usage:
-------------
```python
# In conftest.py or test file
from pinjected import design
from pinjected.pytest_fixtures import register_fixtures_from_design

# Define your design
test_design = design(
    database=database_connection,
    user_service=user_service,
    auth_service=auth_service,
)

# Register fixtures
register_fixtures_from_design(test_design)

# In test file
@pytest.mark.asyncio
async def test_user_creation(user_service, database):
    # user_service and database are now available as fixtures
    user = await user_service.create_user("test@example.com")
    assert user.id in database
```
"""

import asyncio
import inspect
from collections.abc import Awaitable
from pathlib import Path
from typing import Dict, Optional, Set, Union
from weakref import WeakKeyDictionary

import pytest_asyncio
from loguru import logger

from pinjected import AsyncResolver, Design, design, Injected
from pinjected.compatibility.task_group import TaskGroup
from pinjected.di.partially_injected import PartiallyInjectedFunction
from pinjected.di.proxiable import DelegatedVar
from pinjected.helper_structure import MetaContext
from pinjected.v2.keys import StrBindKey


# Global storage for shared state per test
_test_state: WeakKeyDictionary = WeakKeyDictionary()


class SharedTestState:
    """Holds shared resolver and resolved values for a test."""

    def __init__(self):
        self.resolver: Optional[AsyncResolver] = None
        self.task_group: Optional[TaskGroup] = None
        self.resolved_values: Dict[str, any] = {}
        self._cleanup_scheduled = False

    async def close(self):
        """Close the resolver and task group."""
        if self.resolver:
            await self.resolver.destruct()
            self.resolver = None
        if self.task_group:
            await self.task_group.__aexit__(None, None, None)
            self.task_group = None


class DesignFixtures:
    """
    Factory for creating pytest fixtures from a pinjected Design.

    This class takes a Design object and registers its bindings as pytest fixtures.
    Fixtures within the same scope share the same resolver instance, ensuring that
    shared dependencies are properly shared.

    Parameters:
    ----------
    design_obj : Union[Design, DelegatedVar[Design]]
        The pinjected Design object containing bindings to expose as fixtures
    caller_file : Optional[str]
        The file path of the caller (auto-detected if not provided)
    """

    def __init__(
        self,
        design_obj: Union[Design, DelegatedVar[Design]],
        caller_file: Optional[str] = None,
    ):
        """Initialize DesignFixtures with a Design object."""
        self.design_obj = design_obj
        self._registered_fixtures: Set[str] = set()
        self._binding_names_cache: Optional[Set[str]] = None

        # Detect caller file if not provided
        if caller_file is None:
            frame = inspect.currentframe()
            if frame and frame.f_back and frame.f_back.f_back:
                caller_module = inspect.getmodule(frame.f_back.f_back)
                if caller_module and hasattr(caller_module, "__file__"):
                    caller_file = caller_module.__file__

        if not caller_file:
            raise ValueError("Could not determine caller file path")

        self.caller_file = caller_file
        self.caller_module = None

        # Get caller module for fixture injection
        frame = inspect.currentframe()
        if frame and frame.f_back and frame.f_back.f_back:
            self.caller_module = inspect.getmodule(frame.f_back.f_back)

    def _extract_binding_names(self) -> Set[str]:
        """Extract all binding names from the Design."""
        if self._binding_names_cache is not None:
            return self._binding_names_cache

        binding_names = set()

        # For DelegatedVar, we need to resolve it first to inspect bindings
        if isinstance(self.design_obj, DelegatedVar):
            logger.warning(
                "Cannot extract binding names from DelegatedVar until resolved. "
                "Consider using register() with explicit binding names."
            )
            self._binding_names_cache = binding_names
            return binding_names

        # Extract from Design object
        if hasattr(self.design_obj, "bindings"):
            bindings = self.design_obj.bindings
            for key, binding in bindings.items():
                if isinstance(key, StrBindKey) or hasattr(key, "name"):
                    binding_names.add(key.name)
                elif isinstance(key, str):
                    binding_names.add(key)

        logger.debug(f"Extracted {len(binding_names)} binding names from Design")
        self._binding_names_cache = binding_names
        return binding_names

    async def _get_or_create_state(self, request) -> SharedTestState:
        """Get or create shared state for the current test."""
        test_func = request.function

        if test_func not in _test_state:
            state = SharedTestState()
            _test_state[test_func] = state

            # Create resolver once for the test
            caller_path = Path(self.caller_file)
            mc = await MetaContext.a_gather_bindings_with_legacy(caller_path)
            final_design = await mc.a_final_design

            # Resolve design if DelegatedVar
            resolved_design = self.design_obj
            if isinstance(self.design_obj, DelegatedVar):
                temp_resolver = AsyncResolver(final_design, callbacks=[])
                try:
                    resolved_design = await temp_resolver.provide(self.design_obj)
                    if not isinstance(resolved_design, Design):
                        raise TypeError(
                            f"DelegatedVar must resolve to Design, got {type(resolved_design)}"
                        )
                finally:
                    await temp_resolver.destruct()

            # Create TaskGroup and resolver
            state.task_group = TaskGroup()
            await state.task_group.__aenter__()

            merged_design = (
                final_design + resolved_design + design(__task_group__=state.task_group)
            )
            state.resolver = AsyncResolver(merged_design, callbacks=[])

            # Schedule cleanup after test
            if not state._cleanup_scheduled:
                state._cleanup_scheduled = True

                def cleanup():
                    # Use existing event loop if available
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Schedule cleanup as a task in the running loop
                            _ = asyncio.create_task(state.close())  # noqa: RUF006
                        else:
                            # Run in the existing loop
                            loop.run_until_complete(state.close())
                    except RuntimeError:
                        # No event loop, create one just for cleanup
                        asyncio.run(state.close())
                    finally:
                        # Remove from global state
                        if test_func in _test_state:
                            del _test_state[test_func]

                request.addfinalizer(cleanup)

        return _test_state[test_func]

    def register(
        self,
        binding_name: str,
        scope: str = "function",
        fixture_name: Optional[str] = None,
    ) -> None:
        """
        Register a specific binding as a pytest fixture.

        Parameters:
        ----------
        binding_name : str
            The name of the binding in the Design to expose as a fixture
        scope : str
            The pytest fixture scope ('function', 'class', 'module', 'session')
        fixture_name : Optional[str]
            The name to use for the fixture (defaults to binding_name)
        """
        if not self.caller_module:
            raise RuntimeError("Cannot register fixtures: caller module not found")

        fixture_name = fixture_name or binding_name

        # Avoid duplicate registration
        if fixture_name in self._registered_fixtures:
            logger.warning(f"Fixture '{fixture_name}' already registered, skipping")
            return

        # Create async fixture
        @pytest_asyncio.fixture(scope=scope, name=fixture_name)
        async def async_fixture_impl(request):
            """Async fixture implementation using shared state."""
            state = await self._get_or_create_state(request)

            # Check if already resolved
            if binding_name in state.resolved_values:
                return state.resolved_values[binding_name]

            # Use Injected.by_name to resolve the binding
            to_provide = Injected.by_name(binding_name)
            result = await state.resolver.provide(to_provide)

            # Handle PartiallyInjectedFunction
            if isinstance(result, PartiallyInjectedFunction):
                result = result()

            # Handle awaitable results
            if isinstance(result, Awaitable):
                result = await result

            # Cache the result
            state.resolved_values[binding_name] = result
            return result

        # Register fixture
        setattr(self.caller_module, fixture_name, async_fixture_impl)

        self._registered_fixtures.add(fixture_name)
        logger.info(f"Registered fixture '{fixture_name}' with scope '{scope}'")

    def register_all(
        self,
        scope: str = "function",
        prefix: str = "",
        include: Optional[Set[str]] = None,
        exclude: Optional[Set[str]] = None,
    ) -> None:
        """
        Register all bindings from the Design as fixtures.

        Parameters:
        ----------
        scope : str
            The pytest fixture scope for all fixtures
        prefix : str
            A prefix to add to all fixture names
        include : Optional[Set[str]]
            If provided, only register these bindings
        exclude : Optional[Set[str]]
            If provided, exclude these bindings from registration
        """
        # Get all binding names
        all_bindings = self._extract_binding_names()

        if not all_bindings:
            logger.warning("No bindings found in Design to register")
            return

        # Filter bindings
        bindings_to_register = all_bindings.copy()
        if include:
            bindings_to_register &= include
        if exclude:
            bindings_to_register -= exclude

        # Register each binding
        for binding_name in bindings_to_register:
            fixture_name = f"{prefix}{binding_name}"
            self.register(binding_name, scope=scope, fixture_name=fixture_name)

        logger.info(f"Registered {len(bindings_to_register)} fixtures from Design")


def register_fixtures_from_design(
    design_obj: Union[Design, DelegatedVar[Design]],
    scope: str = "function",
    prefix: str = "",
    include: Optional[Set[str]] = None,
    exclude: Optional[Set[str]] = None,
) -> DesignFixtures:
    """
    Convenience function to create DesignFixtures and register all bindings.

    This is the main entry point for most users.

    Example:
    -------
    ```python
    # In conftest.py
    from pinjected.pytest_fixtures import register_fixtures_from_design
    from my_app import test_design

    # Register all fixtures from the design
    register_fixtures_from_design(test_design)

    # Or with options
    register_fixtures_from_design(
        test_design,
        scope='module',  # Module-level fixtures
        prefix='app_',   # Prefix all fixtures with 'app_'
        exclude={'logger', 'config'}  # Don't register these
    )
    ```

    Parameters:
    ----------
    design_obj : Union[Design, DelegatedVar[Design]]
        The pinjected Design object containing bindings
    scope : str
        The pytest fixture scope ('function', 'class', 'module', 'session')
    prefix : str
        A prefix to add to all fixture names
    include : Optional[Set[str]]
        If provided, only register these bindings
    exclude : Optional[Set[str]]
        If provided, exclude these bindings from registration

    Returns:
    -------
    DesignFixtures
        The DesignFixtures instance (for advanced use cases)
    """
    fixtures = DesignFixtures(design_obj)
    fixtures.register_all(scope=scope, prefix=prefix, include=include, exclude=exclude)
    return fixtures
