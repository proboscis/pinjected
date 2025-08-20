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

import pytest
import pytest_asyncio
from loguru import logger

from pinjected import AsyncResolver, Design, design, Injected
from pinjected.compatibility.task_group import TaskGroup
from pinjected.di.partially_injected import PartiallyInjectedFunction
from pinjected.di.proxiable import DelegatedVar
from pinjected.helper_structure import MetaContext
from pinjected.picklable_logger import PicklableLogger
from pinjected.v2.keys import StrBindKey


# Global storage for shared state keyed by scope-aware identifiers
_test_state: Dict[object, "SharedTestState"] = {}


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
        self._resolved_design_cache: Optional[Design] = None

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
            logger.info(
                "Resolving DelegatedVar to extract binding names for fixture registration"
            )
            # Run async resolution in sync context
            resolved_design = asyncio.run(self._resolve_delegated_var())
            if resolved_design:
                # Cache the resolved design for later use
                self._resolved_design_cache = resolved_design
                if hasattr(resolved_design, "bindings"):
                    bindings = resolved_design.bindings
                    for key, binding in bindings.items():
                        if isinstance(key, StrBindKey) or hasattr(key, "name"):
                            binding_names.add(key.name)
                        elif isinstance(key, str):
                            binding_names.add(key)
            logger.debug(
                f"Extracted {len(binding_names)} binding names from resolved DelegatedVar"
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

    async def _resolve_delegated_var(self) -> Optional[Design]:
        """Resolve a DelegatedVar[Design] to extract its bindings."""
        if not isinstance(self.design_obj, DelegatedVar):
            return None

        # Get MetaContext for proper resolution
        caller_path = Path(self.caller_file)
        mc = await MetaContext.a_gather_bindings_with_legacy(caller_path)
        final_design = await mc.a_final_design

        # Create resolver and resolve the DelegatedVar
        resolver = AsyncResolver(final_design, callbacks=[])
        try:
            resolved_design = await resolver.provide(self.design_obj)
            if not isinstance(resolved_design, Design):
                logger.error(
                    f"DelegatedVar resolved to {type(resolved_design)}, expected Design"
                )
                return None

            return resolved_design
        finally:
            await resolver.destruct()

    async def _get_or_create_state(self, request) -> SharedTestState:
        """Get or create shared state for the current scope."""
        scope = getattr(request, "scope", "function")
        if scope == "function":
            key = (
                getattr(request, "node", None).nodeid
                if getattr(request, "node", None)
                else request
            )
        elif scope == "module":
            key = getattr(request, "module", None)
        elif scope == "class":
            key = (
                getattr(request, "cls", None)
                or getattr(request.node, "cls", None)
                or request.node
            )
        elif scope == "session":
            key = ("session",)
        else:
            key = (scope, request.node)

        if key not in _test_state:
            state = SharedTestState()
            _test_state[key] = state

            # Create resolver once for the given scope
            caller_path = Path(self.caller_file)
            mc = await MetaContext.a_gather_bindings_with_legacy(caller_path)
            final_design = await mc.a_final_design

            # Resolve design if DelegatedVar
            if self._resolved_design_cache:
                # Use cached resolved design if available
                resolved_design = self._resolved_design_cache
            elif isinstance(self.design_obj, DelegatedVar):
                # Resolve DelegatedVar if not already cached
                temp_resolver = AsyncResolver(final_design, callbacks=[])
                try:
                    resolved_design = await temp_resolver.provide(self.design_obj)
                    if not isinstance(resolved_design, Design):
                        raise TypeError(
                            f"DelegatedVar must resolve to Design, got {type(resolved_design)}"
                        )
                    self._resolved_design_cache = resolved_design
                finally:
                    await temp_resolver.destruct()
            else:
                resolved_design = self.design_obj

            # Create TaskGroup and resolver
            state.task_group = TaskGroup()
            await state.task_group.__aenter__()

            fallback = None
            if not self._has_binding(final_design, "logger") and not self._has_binding(
                resolved_design, "logger"
            ):
                fallback = design(logger=PicklableLogger())
            if fallback is not None:
                merged_design = (
                    fallback
                    + final_design
                    + resolved_design
                    + design(__task_group__=state.task_group)
                )
            else:
                merged_design = (
                    final_design
                    + resolved_design
                    + design(__task_group__=state.task_group)
                )
            state.resolver = AsyncResolver(merged_design, callbacks=[])

            # Schedule cleanup after test
            if not state._cleanup_scheduled:
                state._cleanup_scheduled = True

                def cleanup():
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            _ = asyncio.create_task(state.close())  # noqa: RUF006
                        else:
                            loop.run_until_complete(state.close())
                    except RuntimeError:
                        asyncio.run(state.close())
                    finally:
                        _test_state.pop(key, None)

                request.addfinalizer(cleanup)

        return _test_state[key]

    def _has_binding(self, d: Design, name: str) -> bool:
        if not hasattr(d, "bindings"):
            return False
        for k in d.bindings:
            if isinstance(k, StrBindKey):
                if k.name == name:
                    return True
            elif (hasattr(k, "name") and getattr(k, "name", None) == name) or (
                isinstance(k, str) and k == name
            ):
                return True
        return False

    async def _resolve_binding_value(self, state: "SharedTestState", name: str):
        if name in state.resolved_values:
            return state.resolved_values[name]
        to_provide = Injected.by_name(name)
        result = await state.resolver.provide(to_provide)
        if isinstance(result, Awaitable):
            result = await result
        if isinstance(result, PartiallyInjectedFunction):
            injected_params = set((result.injected_params or {}).keys())
            param_names = list(result.func_sig.parameters.keys())
            names_to_inject = [
                pname
                for pname in param_names
                if pname not in injected_params
                and self._has_binding(state.resolver.design, pname)
            ]
            injected_values = {}
            for pname in names_to_inject:
                injected_values[pname] = await self._resolve_binding_value(state, pname)
            original_pif = result
            remaining_params = [
                n for n in original_pif.final_sig.parameters if n not in injected_values
            ]
            if len(remaining_params) == 0:
                computed = original_pif(**injected_values)
                if isinstance(computed, Awaitable):
                    computed = await computed

                class _PinjComputed:
                    def __init__(self, value):
                        self._pinj_cached = value

                    def __call__(self, *args, **kwargs):
                        return self._pinj_cached

                    def __getattr__(self, name):
                        return getattr(self._pinj_cached, name)

                    def __getitem__(self, key):
                        return self._pinj_cached[key]

                    def __iter__(self):
                        return iter(self._pinj_cached)

                    def __len__(self):
                        return len(self._pinj_cached)

                    def __repr__(self):
                        return repr(self._pinj_cached)

                    def __str__(self):
                        return str(self._pinj_cached)

                result = _PinjComputed(computed)
            else:

                def _wrapped(*args, **kwargs):
                    merged_kwargs = {**injected_values, **kwargs}
                    res = original_pif(*args, **merged_kwargs)
                    return res

                result = _wrapped
        state.resolved_values[name] = result
        return result

    def _resolve_binding_value_sync(self, state: "SharedTestState", name: str):
        return asyncio.run(self._resolve_binding_value(state, name))

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

        existing = getattr(self.caller_module, fixture_name, None)
        if existing is not None and getattr(existing, "__pinj_fixture__", False):
            logger.warning(f"Fixture '{fixture_name}' already registered, skipping")
            self._registered_fixtures.add(fixture_name)
            return

        if scope == "function":

            @pytest_asyncio.fixture(scope=scope, name=fixture_name)
            async def async_fixture_impl(request):
                state = await self._get_or_create_state(request)
                if binding_name in state.resolved_values:
                    return state.resolved_values[binding_name]
                result = await self._resolve_binding_value(state, binding_name)
                return result

            setattr(async_fixture_impl, "__pinj_fixture__", True)
            setattr(async_fixture_impl, "__pinj_scope__", scope)
            setattr(self.caller_module, fixture_name, async_fixture_impl)
        else:

            @pytest.fixture(scope=scope, name=fixture_name)
            def sync_fixture_impl(request):
                state = asyncio.run(self._get_or_create_state(request))
                if binding_name in state.resolved_values:
                    return state.resolved_values[binding_name]
                result = self._resolve_binding_value_sync(state, binding_name)
                return result

            setattr(sync_fixture_impl, "__pinj_fixture__", True)
            setattr(sync_fixture_impl, "__pinj_scope__", scope)
            setattr(self.caller_module, fixture_name, sync_fixture_impl)

        self._registered_fixtures.add(fixture_name)
        logger.info(f"Registered fixture '{fixture_name}' with scope '{scope}'")

    def register_all(
        self,
        scope: str = "function",
        include: Optional[Set[str]] = None,
        exclude: Optional[Set[str]] = None,
    ) -> None:
        """
        Register all bindings from the Design as fixtures.

        Parameters:
        ----------
        scope : str
            The pytest fixture scope for all fixtures
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
            self.register(binding_name, scope=scope)

        logger.info(f"Registered {len(bindings_to_register)} fixtures from Design")


def register_fixtures_from_design(
    design_obj: Union[Design, DelegatedVar[Design]],
    scope: str = "function",
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
        exclude={'logger', 'config'}  # Don't register these
    )
    ```

    Parameters:
    ----------
    design_obj : Union[Design, DelegatedVar[Design]]
        The pinjected Design object containing bindings
    scope : str
        The pytest fixture scope ('function', 'class', 'module', 'session')
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
    fixtures.register_all(scope=scope, include=include, exclude=exclude)
    return fixtures
