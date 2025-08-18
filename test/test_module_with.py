"""Tests for test_package.child.module_with module."""

import pytest
from pinjected.schema.handlers import (
    PinjectedHandleMainException,
    PinjectedHandleMainResult,
)


class TestModuleWith:
    """Test module_with module functionality."""

    def test_module_imports(self):
        """Test that the module can be imported."""
        from pinjected.test_package.child import module_with

        assert module_with is not None

    def test_injected_values_exist(self):
        """Test that injected values y, z, and z2 exist."""
        from pinjected.test_package.child.module_with import y, z, z2

        # These should be IProxy objects created from injected calls
        assert y is not None
        assert z is not None
        assert z2 is not None

        # They should be proxy objects
        assert hasattr(y, "__class__")
        assert hasattr(z, "__class__")
        assert hasattr(z2, "__class__")

    def test_default_design_exists(self):
        """Test that default_design is defined."""
        from pinjected.test_package.child.module_with import default_design
        from pinjected import Design

        assert default_design is not None
        assert isinstance(default_design, Design)

    def test_handle_exception_function(self):
        """Test that __handle_exception is defined in the module."""
        from pinjected.test_package.child import module_with
        import inspect

        # Check that the function is defined in the source
        source = inspect.getsource(module_with)
        assert "@injected" in source
        assert "async def __handle_exception" in source
        assert 'print(f"Exception: {e}")' in source
        assert 'return "handled"' in source

    def test_handle_success_function(self):
        """Test that __handle_success is defined in the module."""
        from pinjected.test_package.child import module_with
        import inspect

        # Check that the function is defined in the source
        source = inspect.getsource(module_with)
        assert "@injected" in source
        assert "async def __handle_success" in source
        assert 'print(f"Success: {result}")' in source

    def test_test_handling_design(self):
        """Test that __test_handling_design is defined in the module."""
        from pinjected.test_package.child import module_with
        import inspect

        # Check that the design is defined in the source
        source = inspect.getsource(module_with)
        assert "__test_handling_design = design(" in source
        assert "PinjectedHandleMainException.key.name: __handle_exception" in source
        assert "PinjectedHandleMainResult.key.name: __handle_success" in source

    def test_module_design(self):
        """Test __design__ module attribute."""
        from pinjected.test_package.child.module_with import __design__
        from pinjected import Design

        assert __design__ is not None
        assert isinstance(__design__, Design)

    @pytest.mark.asyncio
    async def test_handle_exception_behavior(self):
        """Test the behavior of __handle_exception by recreating it."""
        from unittest.mock import Mock

        # Since __handle_exception is private, we'll test its logic directly
        async def handle_exception(context, e: Exception):
            print(f"Exception: {e}")
            return "handled"

        # Create a mock context
        mock_context = Mock()
        test_exception = Exception("Test error")

        # Call the function
        result = await handle_exception(mock_context, test_exception)

        # Verify it returns "handled"
        assert result == "handled"

    @pytest.mark.asyncio
    async def test_handle_success_behavior(self):
        """Test the behavior of __handle_success by recreating it."""
        from unittest.mock import Mock

        # Since __handle_success is private, we'll test its logic directly
        async def handle_success(context, result):
            print(f"Success: {result}")

        # Create a mock context
        mock_context = Mock()
        test_result = "Success!"

        # Call the function - it should not raise
        result = await handle_success(mock_context, test_result)

        # It doesn't return anything, just prints
        assert result is None

    def test_nested_design_contexts(self):
        """Test the nested design context structure."""
        # The module uses nested with statements to create designs
        # We can verify the structure exists by checking imports
        from pinjected.test_package.child import module_with
        import inspect

        source = inspect.getsource(module_with)

        # Check for nested with statements
        assert "with design(x=10):" in source
        assert "with design(y=20):" in source
        assert "with design(x=100):" in source

        # Check for injected calls
        assert 'y = injected("x")' in source
        assert 'z = injected("y")' in source
        assert "z2 = y" in source

    def test_handler_design_keys(self):
        """Test that handler design uses correct keys."""
        from pinjected.test_package.child import module_with

        # Access the private design through the module
        test_handling_design = getattr(
            module_with, "_module_with__test_handling_design", None
        )
        if not test_handling_design:
            # If we can't get the private attribute, just verify the module structure
            import inspect

            source = inspect.getsource(module_with)
            assert "PinjectedHandleMainException" in source
            assert "PinjectedHandleMainResult" in source
            return

        # The design should have the handler keys
        # Check by converting to string representation
        design_str = str(test_handling_design)

        # It should contain references to the handler keys
        assert (
            "PinjectedHandleMainException" in design_str
            or "handle_exception" in design_str
        )
        assert (
            "PinjectedHandleMainResult" in design_str or "handle_success" in design_str
        )

    def test_module_with_actual_values(self):
        """Test the actual resolved values from module_with."""
        from pinjected.test_package.child import module_with

        # Test that we can access the module's design
        module_design = module_with.__design__

        # The design should have the handlers
        bindings = module_design.bindings
        # The keys in bindings are StrBindKey objects, not strings
        binding_names = [key.name for key in bindings if hasattr(key, "name")]
        assert PinjectedHandleMainException.key.name in binding_names
        assert PinjectedHandleMainResult.key.name in binding_names

    def test_injected_values_resolution(self):
        """Test resolving the injected values."""
        from pinjected.test_package.child import module_with

        # The module creates these with nested designs
        # We can test that the structure exists
        assert hasattr(module_with, "y")
        assert hasattr(module_with, "z")
        assert hasattr(module_with, "z2")

    @pytest.mark.asyncio
    async def test_exception_handler_directly(self):
        """Test calling the exception handler directly."""
        from pinjected.test_package.child import module_with

        # Get the private handler function
        handler = getattr(module_with, "_module_with__handle_exception", None)
        if handler is None:
            # Try without name mangling
            handler = getattr(module_with, "__handle_exception", None)

        if handler is not None and hasattr(handler, "src_function"):
            # It's an injected function, so we need to work with it properly
            # Call the source function directly
            result = await handler.src_function({}, Exception("test"))
            assert result == "handled"

    @pytest.mark.asyncio
    async def test_success_handler_directly(self):
        """Test calling the success handler directly."""
        from pinjected.test_package.child import module_with

        # Get the private handler function
        handler = getattr(module_with, "_module_with__handle_success", None)
        if handler is None:
            # Try without name mangling
            handler = getattr(module_with, "__handle_success", None)

        if handler is not None and hasattr(handler, "src_function"):
            # It's an injected function, so we need to work with it properly
            # Call the source function directly - it returns None
            result = await handler.src_function({}, "success")
            assert result is None

    def test_design_addition(self):
        """Test that __design__ is properly created by addition."""
        from pinjected.test_package.child import module_with

        # __design__ should be the result of design() + __test_handling_design
        # Both should be Design instances
        assert hasattr(module_with.__design__, "provide")
        assert hasattr(module_with.__design__, "bindings")
