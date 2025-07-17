"""
Final pytest fixture integration for pinjected Design objects.

This version properly handles shared resolver state per test.
"""

import asyncio
import inspect
from collections.abc import Awaitable
from pathlib import Path
from typing import Dict, Optional, Set, Union
from weakref import WeakKeyDictionary

import pytest_asyncio
from loguru import logger

from pinjected import AsyncResolver, Design, design
from pinjected.compatibility.task_group import TaskGroup
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

    async def cleanup(self):
        """Clean up resolver and task group."""
        if self.resolver:
            await self.resolver.destruct()
        if self.task_group:
            await self.task_group.__aexit__(None, None, None)


class DesignFixtures:
    """
    Factory for creating pytest fixtures from a pinjected Design.

    This version ensures proper shared state across fixtures in a test.
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

        # For DelegatedVar, we need to resolve it first
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

            # Add cleanup
            request.addfinalizer(lambda: asyncio.run(state.cleanup()))

        return _test_state[test_func]

    async def _resolve_value(self, state: SharedTestState, binding_name: str):
        """Resolve a value, using cache if available."""
        if binding_name in state.resolved_values:
            return state.resolved_values[binding_name]

        # Resolve the value
        result = await state.resolver.provide(binding_name)

        # Execute if it's a callable
        while callable(result):
            result = result()
            if isinstance(result, Awaitable):
                result = await result

        # Cache the result
        state.resolved_values[binding_name] = result
        return result

    def register(
        self,
        binding_name: str,
        scope: str = "function",
        fixture_name: Optional[str] = None,
    ) -> None:
        """Register a specific binding as a pytest fixture."""
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
            return await self._resolve_value(state, binding_name)

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
        """Register all bindings from the Design as fixtures."""
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

    This provides the simple interface requested:
        register_fixtures_from_design(test_design)

    Example:
        # In conftest.py
        from pinjected.pytest_fixtures_final import register_fixtures_from_design
        from my_app import test_design

        # Register all fixtures
        register_fixtures_from_design(test_design)

        # In test file
        @pytest.mark.asyncio
        async def test_something(database, user_service):
            # database and user_service are resolved from test_design
            # All fixtures in the same test share the same resolver
            pass
    """
    fixtures = DesignFixtures(design_obj)
    fixtures.register_all(scope=scope, prefix=prefix, include=include, exclude=exclude)
    return fixtures
