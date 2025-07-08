"""Tests for pinjected/runnables.py module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from pinjected.runnables import get_runnables, RunnableValue
from pinjected.module_inspector import ModuleVarSpec
from pinjected import Injected, Designed
from pinjected.di.app_injected import InjectedEvalContext
from pinjected.di.proxiable import DelegatedVar


class TestGetRunnables:
    """Tests for get_runnables function."""

    def test_get_runnables_with_provide_prefix(self):
        """Test that variables starting with 'provide' are accepted."""
        mock_module_path = Path("/test/module.py")

        # Create mock for inspect_module_for_type
        def mock_inspect(path, accept_func):
            # Test the accept function with various cases
            assert accept_func("provide_something", "any_value") is True
            assert accept_func("provideFoo", "any_value") is True
            return [ModuleVarSpec("provide_test", "module")]

        with patch("pinjected.runnables.inspect_module_for_type", mock_inspect):
            result = get_runnables(mock_module_path)
            assert len(result) == 1
            assert result[0].var == "provide_test"
            assert result[0].var_path == "module"

    def test_get_runnables_with_injected(self):
        """Test that Injected instances are accepted."""
        mock_module_path = Path("/test/module.py")
        mock_injected = Mock(spec=Injected)

        def mock_inspect(path, accept_func):
            assert accept_func("any_name", mock_injected) is True
            return [ModuleVarSpec("injected_test", "module")]

        with patch("pinjected.runnables.inspect_module_for_type", mock_inspect):
            result = get_runnables(mock_module_path)
            assert len(result) == 1

    def test_get_runnables_with_designed(self):
        """Test that Designed instances are accepted."""
        mock_module_path = Path("/test/module.py")
        mock_designed = Mock(spec=Designed)

        def mock_inspect(path, accept_func):
            assert accept_func("any_name", mock_designed) is True
            return [ModuleVarSpec("designed_test", "module")]

        with patch("pinjected.runnables.inspect_module_for_type", mock_inspect):
            result = get_runnables(mock_module_path)
            assert len(result) == 1

    def test_get_runnables_with_delegated_var_injected_context(self):
        """Test that DelegatedVar with InjectedEvalContext is accepted."""
        mock_module_path = Path("/test/module.py")
        mock_delegated = DelegatedVar("test", InjectedEvalContext)

        def mock_inspect(path, accept_func):
            assert accept_func("any_name", mock_delegated) is True
            return [ModuleVarSpec("delegated_test", "module")]

        with patch("pinjected.runnables.inspect_module_for_type", mock_inspect):
            result = get_runnables(mock_module_path)
            assert len(result) == 1

    def test_get_runnables_with_delegated_var_other_context(self):
        """Test that DelegatedVar with non-InjectedEvalContext is rejected."""
        mock_module_path = Path("/test/module.py")
        mock_delegated = DelegatedVar("test", "OtherContext")

        def mock_inspect(path, accept_func):
            assert accept_func("any_name", mock_delegated) is False
            return []

        with patch("pinjected.runnables.inspect_module_for_type", mock_inspect):
            result = get_runnables(mock_module_path)
            assert len(result) == 0

    def test_get_runnables_with_runnable_metadata(self):
        """Test that objects with __runnable_metadata__ dict are accepted."""
        mock_module_path = Path("/test/module.py")

        # Create object with __runnable_metadata__
        class RunnableObject:
            def __init__(self):
                self.__runnable_metadata__ = {"key": "value"}

        runnable_obj = RunnableObject()

        def mock_inspect(path, accept_func):
            assert accept_func("any_name", runnable_obj) is True
            return [ModuleVarSpec("runnable_test", "module")]

        with patch("pinjected.runnables.inspect_module_for_type", mock_inspect):
            result = get_runnables(mock_module_path)
            assert len(result) == 1

    def test_get_runnables_with_non_runnable(self):
        """Test that regular objects are rejected."""
        mock_module_path = Path("/test/module.py")

        def mock_inspect(path, accept_func):
            assert accept_func("regular_var", "string_value") is False
            assert accept_func("regular_func", lambda x: x) is False
            return []

        with patch("pinjected.runnables.inspect_module_for_type", mock_inspect):
            result = get_runnables(mock_module_path)
            assert len(result) == 0


class TestRunnableValue:
    """Tests for RunnableValue class."""

    def test_runnable_value_with_injected(self):
        """Test RunnableValue creation with Injected ModuleVarSpec."""
        mock_injected = Mock(spec=Injected)
        spec = ModuleVarSpec(mock_injected, "test_module")

        runnable = RunnableValue(src=spec, design_path="path/to/design")

        assert runnable.src == spec
        assert runnable.design_path == "path/to/design"

    def test_runnable_value_with_designed(self):
        """Test RunnableValue creation with Designed ModuleVarSpec."""
        mock_designed = Mock(spec=Designed)
        spec = ModuleVarSpec(mock_designed, "test_module")

        runnable = RunnableValue(src=spec, design_path="path/to/design")

        assert runnable.src == spec
        assert runnable.design_path == "path/to/design"

    def test_runnable_value_validation_error(self):
        """Test RunnableValue validation with invalid src type."""
        # Create invalid ModuleVarSpec (not Injected or Designed)
        spec = ModuleVarSpec("regular_value", "test_module")

        # The validator uses pattern matching, so it won't raise for non-Injected/Designed
        # unless we call validate_src_type directly
        with pytest.raises(ValueError) as exc_info:
            RunnableValue.validate_src_type(spec)

        assert "src must be an instance of Injected of ModuleVarSpec" in str(
            exc_info.value
        )

    def test_runnable_value_field_validator(self):
        """Test the field validator directly."""
        # Test with valid Injected
        mock_injected = Mock(spec=Injected)
        spec_injected = ModuleVarSpec(mock_injected, "test_module")
        result = RunnableValue.validate_src_type(spec_injected)
        assert result == spec_injected

        # Test with valid Designed
        mock_designed = Mock(spec=Designed)
        spec_designed = ModuleVarSpec(mock_designed, "test_module")
        result = RunnableValue.validate_src_type(spec_designed)
        assert result == spec_designed

        # Test with invalid type
        spec_invalid = ModuleVarSpec("not_injected_or_designed", "test_module")
        with pytest.raises(ValueError):
            RunnableValue.validate_src_type(spec_invalid)

    def test_runnable_value_config(self):
        """Test RunnableValue Config allows arbitrary types."""
        assert RunnableValue.Config.arbitrary_types_allowed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
