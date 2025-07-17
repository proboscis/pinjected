"""
Pytest fixture integration for pinjected Design objects (Version 2).

This module provides a class-based approach to register pinjected Design bindings
as pytest fixtures, with proper shared resolver support per test function.
"""

import asyncio
import inspect
from collections.abc import Awaitable
from pathlib import Path
from typing import Optional, Set, Union
from weakref import WeakKeyDictionary

import pytest
import pytest_asyncio
from loguru import logger

from pinjected import AsyncResolver, Design, design
from pinjected.compatibility.task_group import TaskGroup
from pinjected.di.proxiable import DelegatedVar
from pinjected.helper_structure import MetaContext
from pinjected.v2.keys import StrBindKey


# Global storage for resolvers per test
_test_resolvers: WeakKeyDictionary = WeakKeyDictionary()


class DesignFixturesV2:
    """
    Factory for creating pytest fixtures from a pinjected Design.

    This version ensures a single shared resolver per test function.
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

    async def _get_or_create_resolver(self, request) -> AsyncResolver:
        """Get or create a shared resolver for the current test."""
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

        # Store resolver and cleanup info
        _test_resolvers[test_func] = resolver

        # Add finalizer to clean up after test
        async def cleanup():
            if test_func in _test_resolvers:
                resolver = _test_resolvers.pop(test_func)
                try:
                    await resolver.destruct()
                finally:
                    await tg.__aexit__(None, None, None)

        request.addfinalizer(lambda: asyncio.run(cleanup()))

        return resolver

    def register(
        self,
        binding_name: str,
        scope: str = "function",
        fixture_name: Optional[str] = None,
        sync: bool = True,
        async_: bool = True,
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
        @pytest_asyncio.fixture(scope=scope, name=f"{fixture_name}_async")
        async def async_fixture_impl(request):
            """Async fixture implementation using shared resolver."""
            resolver = await self._get_or_create_resolver(request)
            result = await resolver.provide(binding_name)
            if isinstance(result, Awaitable):
                result = await result
            return result

        # Create sync fixture
        @pytest.fixture(scope=scope, name=fixture_name)
        def sync_fixture_impl(request):
            """Sync fixture implementation using shared resolver."""

            # We need to run the async code in a way that works with pytest
            # The simplest approach is to use the async fixture
            async def get_value():
                resolver = await self._get_or_create_resolver(request)
                result = await resolver.provide(binding_name)
                if isinstance(result, Awaitable):
                    result = await result
                return result

            # Check if we're already in an event loop
            try:
                asyncio.get_running_loop()
                # We're in an event loop, can't use asyncio.run
                # This is a limitation - sync fixtures won't work in async context
                raise RuntimeError(
                    f"Cannot use sync fixture '{fixture_name}' in async context. "
                    f"Use '{fixture_name}_async' instead."
                )
            except RuntimeError:
                # No event loop, we can create one
                return asyncio.run(get_value())

        # Register fixtures
        if async_:
            setattr(self.caller_module, f"{fixture_name}_async", async_fixture_impl)

        if sync:
            setattr(self.caller_module, fixture_name, sync_fixture_impl)

        self._registered_fixtures.add(fixture_name)
        logger.info(f"Registered fixture '{fixture_name}' with scope '{scope}'")

    def register_all(
        self,
        scope: str = "function",
        prefix: str = "",
        include: Optional[Set[str]] = None,
        exclude: Optional[Set[str]] = None,
        sync: bool = True,
        async_: bool = True,
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
            self.register(
                binding_name,
                scope=scope,
                fixture_name=fixture_name,
                sync=sync,
                async_=async_,
            )

        logger.info(f"Registered {len(bindings_to_register)} fixtures from Design")


def register_fixtures_from_design_v2(
    design_obj: Union[Design, DelegatedVar[Design]],
    scope: str = "function",
    prefix: str = "",
    include: Optional[Set[str]] = None,
    exclude: Optional[Set[str]] = None,
) -> DesignFixturesV2:
    """
    Convenience function to create DesignFixtures and register all bindings.

    Example:
        # In conftest.py
        from pinjected.pytest_fixtures_v2 import register_fixtures_from_design_v2
        from my_app import test_design

        # Register all fixtures
        register_fixtures_from_design_v2(test_design)
    """
    fixtures = DesignFixturesV2(design_obj)
    fixtures.register_all(scope=scope, prefix=prefix, include=include, exclude=exclude)
    return fixtures
