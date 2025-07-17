"""
Batch pytest fixture integration for pinjected Design objects.

This version resolves all fixtures in a single batch to ensure shared state.
"""

import inspect
from pathlib import Path
from typing import Optional, Set, Union

import pytest_asyncio
from loguru import logger

from pinjected import AsyncResolver, Design, design, Injected
from pinjected.compatibility.task_group import TaskGroup
from pinjected.di.proxiable import DelegatedVar
from pinjected.helper_structure import MetaContext
from pinjected.v2.keys import StrBindKey
from pinjected.di.partially_injected import PartiallyInjectedFunction
from collections.abc import Awaitable


class BatchDesignFixtures:
    """
    Factory for creating a batch pytest fixture from a pinjected Design.

    This version resolves all bindings at once to ensure proper shared state.
    """

    def __init__(
        self,
        design_obj: Union[Design, DelegatedVar[Design]],
        caller_file: Optional[str] = None,
    ):
        """Initialize BatchDesignFixtures with a Design object."""
        self.design_obj = design_obj
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
                "Consider using register_batch() with explicit binding names."
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

    def register_batch(
        self,
        fixture_name: str = "pinjected_context",
        scope: str = "function",
        include: Optional[Set[str]] = None,
        exclude: Optional[Set[str]] = None,
    ) -> None:
        """
        Register a single batch fixture that resolves all bindings at once.

        The fixture returns a dictionary mapping binding names to resolved values.
        """
        if not self.caller_module:
            raise RuntimeError("Cannot register fixtures: caller module not found")

        # Get all binding names
        all_bindings = self._extract_binding_names()

        if not all_bindings:
            logger.warning("No bindings found in Design to register")
            return

        # Filter bindings
        bindings_to_resolve = all_bindings.copy()
        if include:
            bindings_to_resolve &= include
        if exclude:
            bindings_to_resolve -= exclude

        # Create batch fixture
        @pytest_asyncio.fixture(scope=scope, name=fixture_name)
        async def batch_fixture_impl():
            """Batch fixture that resolves all bindings at once."""
            # Create resolver
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

            resolver = None
            try:
                async with TaskGroup() as tg:
                    design_with_tg = merged_design + design(__task_group__=tg)
                    resolver = AsyncResolver(design_with_tg, callbacks=[])

                    # Resolve all bindings
                    results = {}
                    for binding_name in bindings_to_resolve:
                        logger.debug(f"Resolving {binding_name}")

                        # Use Injected.by_name for resolution
                        to_provide = Injected.by_name(binding_name)
                        result = await resolver.provide(to_provide)

                        # Handle PartiallyInjectedFunction
                        if isinstance(result, PartiallyInjectedFunction):
                            logger.debug(
                                f"Executing PartiallyInjectedFunction for {binding_name}"
                            )
                            result = result()

                        # Handle awaitable results
                        if isinstance(result, Awaitable):
                            result = await result

                        results[binding_name] = result
                        logger.debug(f"Resolved {binding_name}: {type(result)}")

                    return results
            finally:
                if resolver:
                    await resolver.destruct()

        # Register fixture
        setattr(self.caller_module, fixture_name, batch_fixture_impl)

        # Also register individual fixture accessors
        for binding_name in bindings_to_resolve:
            self._register_accessor(binding_name, fixture_name, scope)

        logger.info(
            f"Registered batch fixture '{fixture_name}' with {len(bindings_to_resolve)} bindings"
        )

    def _register_accessor(
        self, binding_name: str, batch_fixture_name: str, scope: str
    ):
        """Register an individual fixture that accesses the batch result."""
        import pytest

        @pytest.fixture(scope=scope, name=binding_name)
        def accessor_fixture(request):
            """Access individual binding from batch fixture."""
            # Get the batch fixture value - this works because the batch fixture is already resolved
            batch_result = request.getfixturevalue(batch_fixture_name)
            return batch_result[binding_name]

        setattr(self.caller_module, binding_name, accessor_fixture)


def register_batch_fixtures_from_design(
    design_obj: Union[Design, DelegatedVar[Design]],
    fixture_name: str = "pinjected_context",
    scope: str = "function",
    include: Optional[Set[str]] = None,
    exclude: Optional[Set[str]] = None,
) -> BatchDesignFixtures:
    """
    Convenience function to create BatchDesignFixtures and register all bindings.

    This ensures all fixtures share the same resolver context.
    """
    fixtures = BatchDesignFixtures(design_obj)
    fixtures.register_batch(
        fixture_name=fixture_name, scope=scope, include=include, exclude=exclude
    )
    return fixtures
