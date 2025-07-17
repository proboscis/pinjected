"""
Simplified pytest fixture integration for pinjected Design objects.

This module provides async-only fixtures with proper shared resolver support per test.
"""

import asyncio
import inspect
from collections.abc import Awaitable
from pathlib import Path
from typing import Optional, Set, Union
from weakref import WeakKeyDictionary

import pytest_asyncio
from loguru import logger

from pinjected import AsyncResolver, Design, design
from pinjected.compatibility.task_group import TaskGroup
from pinjected.di.proxiable import DelegatedVar
from pinjected.helper_structure import MetaContext
from pinjected.v2.keys import StrBindKey


# Global storage for resolvers per test
_test_resolvers: WeakKeyDictionary = WeakKeyDictionary()


class DesignFixtures:
    """
    Factory for creating pytest fixtures from a pinjected Design.

    All fixtures are async - tests using them should be marked with @pytest.mark.asyncio.
    This ensures a single shared resolver per test function.
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

    async def _get_or_create_resolver(self, request) -> tuple[AsyncResolver, dict]:
        """Get or create a shared resolver and cache for the current test."""
        # Use the test function as the key
        test_func = request.function

        # Check if we already have a resolver for this test
        if test_func in _test_resolvers:
            return _test_resolvers[test_func]

        # Create a new resolver for this test
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

        # Merge designs
        merged_design = final_design + resolved_design

        # Create resolver with TaskGroup
        # Note: We don't use async with here because we need to manage lifecycle manually
        tg = TaskGroup()
        await tg.__aenter__()

        design_with_tg = merged_design + design(__task_group__=tg)
        resolver = AsyncResolver(design_with_tg, callbacks=[])

        # Create a cache for resolved values
        resolved_cache = {}

        # Store resolver and cache
        _test_resolvers[test_func] = (resolver, resolved_cache)

        # Add finalizer to clean up after test
        async def cleanup():
            if test_func in _test_resolvers:
                resolver, _ = _test_resolvers.pop(test_func)
                try:
                    await resolver.destruct()
                finally:
                    await tg.__aexit__(None, None, None)

        request.addfinalizer(lambda: asyncio.run(cleanup()))

        return resolver, resolved_cache

    def register(
        self,
        binding_name: str,
        scope: str = "function",
        fixture_name: Optional[str] = None,
    ) -> None:
        """
        Register a specific binding as a pytest fixture.

        Creates only async fixtures since pinjected uses async resolvers.
        Tests that need these fixtures should be marked with @pytest.mark.asyncio.
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
            """Async fixture implementation using shared resolver and cache."""
            from pinjected import Injected

            resolver, cache = await self._get_or_create_resolver(request)

            # Check if already resolved in cache
            if binding_name in cache:
                logger.debug(f"Using cached value for {binding_name}")
                return cache[binding_name]

            # Always use Injected.by_name to ensure proper dependency chain resolution
            # The resolver will look up the binding from the merged design
            to_provide = Injected.by_name(binding_name)

            # Provide through resolver
            result = await resolver.provide(to_provide)

            # Debug logging
            logger.debug(f"Initial result for {binding_name}: type={type(result)}")

            # If result is a PartiallyInjectedFunction, call it to get the actual value
            from pinjected.di.partially_injected import PartiallyInjectedFunction

            if isinstance(result, PartiallyInjectedFunction):
                logger.debug(f"Calling PartiallyInjectedFunction for {binding_name}")
                result = result()  # Call with no args since deps are already injected

            # Check if result is awaitable
            if isinstance(result, Awaitable):
                logger.debug(f"Awaiting result for {binding_name}")
                result = await result

            # Cache the resolved value
            cache[binding_name] = result

            # Final debug logging
            logger.debug(
                f"Final resolved {binding_name}: type={type(result)}, value={result}"
            )

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
        from pinjected.pytest_fixtures_simple import register_fixtures_from_design
        from my_app import test_design

        # Register all fixtures (async only)
        register_fixtures_from_design(test_design)

        # In test file
        @pytest.mark.asyncio
        async def test_something(database, user_service):
            # database and user_service are resolved from test_design
            pass
    """
    fixtures = DesignFixtures(design_obj)
    fixtures.register_all(scope=scope, prefix=prefix, include=include, exclude=exclude)
    return fixtures
