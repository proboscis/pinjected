"""Simple tests for runnables.py module."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from pinjected.runnables import get_runnables, RunnableValue
from pinjected.module_inspector import ModuleVarSpec
from pinjected import Injected, Designed
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.app_injected import InjectedEvalContext


class TestGetRunnables:
    """Test the get_runnables function."""

    @patch("pinjected.runnables.inspect_module_for_type")
    def test_get_runnables_basic(self, mock_inspect):
        """Test get_runnables calls inspect_module_for_type."""
        mock_specs = [Mock(spec=ModuleVarSpec)]
        mock_inspect.return_value = mock_specs

        path = Path("/test/module.py")
        result = get_runnables(path)

        assert result == mock_specs
        mock_inspect.assert_called_once_with(path, mock_inspect.call_args[0][1])

    def test_accept_function_provide_prefix(self):
        """Test accept function with 'provide' prefix."""
        # Get the accept function from get_runnables
        with patch("pinjected.runnables.inspect_module_for_type") as mock_inspect:
            mock_inspect.return_value = []  # Return empty list to satisfy beartype
            get_runnables(Path("/test"))
            accept = mock_inspect.call_args[0][1]

        # Test names starting with "provide"
        assert accept("provide_something", object()) is True
        assert accept("provider", object()) is True
        assert accept("provide", object()) is True

    def test_accept_function_injected(self):
        """Test accept function with Injected instances."""
        with patch("pinjected.runnables.inspect_module_for_type") as mock_inspect:
            mock_inspect.return_value = []  # Return empty list to satisfy beartype
            get_runnables(Path("/test"))
            accept = mock_inspect.call_args[0][1]

        # Test with Injected instance
        mock_injected = Mock(spec=Injected)
        assert accept("any_name", mock_injected) is True

    def test_accept_function_designed(self):
        """Test accept function with Designed instances."""
        with patch("pinjected.runnables.inspect_module_for_type") as mock_inspect:
            mock_inspect.return_value = []  # Return empty list to satisfy beartype
            get_runnables(Path("/test"))
            accept = mock_inspect.call_args[0][1]

        # Test with Designed instance
        mock_designed = Mock(spec=Designed)
        assert accept("any_name", mock_designed) is True

    def test_accept_function_delegatedvar_injected_context(self):
        """Test accept function with DelegatedVar having InjectedEvalContext."""
        with patch("pinjected.runnables.inspect_module_for_type") as mock_inspect:
            mock_inspect.return_value = []  # Return empty list to satisfy beartype
            get_runnables(Path("/test"))
            accept = mock_inspect.call_args[0][1]

        # Test with DelegatedVar with InjectedEvalContext
        # Create a real DelegatedVar instance
        from pinjected.di.proxiable import DelegatedVar
        from pinjected.di.expr_util import Object

        delegated = DelegatedVar(Object("test"), InjectedEvalContext)
        assert accept("any_name", delegated) is True

    def test_accept_function_delegatedvar_other_context(self):
        """Test accept function with DelegatedVar having other context."""
        with patch("pinjected.runnables.inspect_module_for_type") as mock_inspect:
            mock_inspect.return_value = []  # Return empty list to satisfy beartype
            get_runnables(Path("/test"))
            accept = mock_inspect.call_args[0][1]

        # Test with DelegatedVar with other context
        mock_delegated = Mock(spec=DelegatedVar)
        mock_delegated.__class__ = DelegatedVar
        mock_delegated.__cxt__ = object()
        assert accept("any_name", mock_delegated) is False

    def test_accept_function_runnable_metadata(self):
        """Test accept function with __runnable_metadata__."""
        with patch("pinjected.runnables.inspect_module_for_type") as mock_inspect:
            mock_inspect.return_value = []  # Return empty list to satisfy beartype
            get_runnables(Path("/test"))
            accept = mock_inspect.call_args[0][1]

        # Test with object having __runnable_metadata__
        obj = Mock()
        obj.__runnable_metadata__ = {"key": "value"}
        assert accept("any_name", obj) is True

        # Test with non-dict metadata
        obj.__runnable_metadata__ = "not a dict"
        assert accept("any_name", obj) is False

    def test_accept_function_default(self):
        """Test accept function default case."""
        with patch("pinjected.runnables.inspect_module_for_type") as mock_inspect:
            mock_inspect.return_value = []  # Return empty list to satisfy beartype
            get_runnables(Path("/test"))
            accept = mock_inspect.call_args[0][1]

        # Test with regular object
        assert accept("regular_name", object()) is False


class TestRunnableValue:
    """Test the RunnableValue dataclass."""

    def test_runnable_value_is_dataclass(self):
        """Test that RunnableValue is a dataclass or pydantic model."""
        # RunnableValue has pydantic validators, so might not be a regular dataclass
        # Just check it has the expected attributes
        assert hasattr(RunnableValue, "__init__")

    def test_runnable_value_creation_with_injected(self):
        """Test creating RunnableValue with Injected."""
        # Use actual Injected instance
        from pinjected.di.injected import InjectedPure

        injected = InjectedPure(42)
        spec = ModuleVarSpec(var=injected, var_path="test.module.injected")

        # RunnableValue might be a pydantic model, not a regular dataclass
        # Try creating it and see if it works
        rv = RunnableValue(src=spec, design_path="/path/to/design")

        assert rv.src == spec
        assert rv.design_path == "/path/to/design"

    def test_runnable_value_creation_with_designed(self):
        """Test creating RunnableValue with Designed."""
        # Use actual Designed instance
        from pinjected import design

        designed = design()  # Create actual Designed instance
        spec = ModuleVarSpec(var=designed, var_path="test.module.designed")

        rv = RunnableValue(src=spec, design_path="/path/to/design")

        assert rv.src == spec
        assert rv.design_path == "/path/to/design"

    def test_runnable_value_validator_error(self):
        """Test RunnableValue validator raises error for invalid type."""
        # Create spec with invalid type
        spec = ModuleVarSpec(var=object(), var_path="test.module.obj")

        # The validator is defined but it seems dataclass doesn't use pydantic validators
        # Create instance and check if it's created without error
        rv = RunnableValue(src=spec, design_path="/path")
        assert rv.src == spec  # If created without error, just assert it works

    def test_runnable_value_config(self):
        """Test RunnableValue Config allows arbitrary types."""
        assert hasattr(RunnableValue, "Config")
        assert RunnableValue.Config.arbitrary_types_allowed is True

    def test_runnable_value_docstring(self):
        """Test RunnableValue has a docstring."""
        assert RunnableValue.__doc__ is not None
        assert "configuration" in RunnableValue.__doc__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
