"""Tests for di/overload_experimental.py module."""

import pytest
from dataclasses import is_dataclass, fields

from pinjected.di.overload_experimental import Data, DataFactory, data_user, IDataUser
from pinjected import Injected


class TestData:
    """Tests for Data dataclass."""

    def test_data_is_dataclass(self):
        """Test that Data is a dataclass."""
        assert is_dataclass(Data)

    def test_data_fields(self):
        """Test Data has expected fields."""
        field_list = fields(Data)
        assert len(field_list) == 1
        assert field_list[0].name == "x"
        assert field_list[0].type is int
        assert field_list[0].default == 0

    def test_data_initialization_with_default(self):
        """Test Data initialization with default value."""
        data = Data()
        assert data.x == 0

    def test_data_initialization_with_value(self):
        """Test Data initialization with provided value."""
        data = Data(x=42)
        assert data.x == 42

    def test_data_has_docstring(self):
        """Test that Data has documentation."""
        assert Data.__doc__ is not None
        assert "docs for data" in Data.__doc__


class TestDataFactory:
    """Tests for DataFactory class."""

    def test_data_factory_callable(self):
        """Test that DataFactory instances are callable."""
        factory = DataFactory()
        assert callable(factory)

    def test_data_factory_creates_data(self):
        """Test that DataFactory creates Data instances."""
        factory = DataFactory()
        data = factory(x=10)

        assert isinstance(data, Data)
        assert data.x == 10

    def test_data_factory_call_signature(self):
        """Test DataFactory __call__ method signature."""
        factory = DataFactory()
        # Should accept x parameter
        data = factory(x=5)
        assert data.x == 5

        # Test with different values
        data2 = factory(x=100)
        assert data2.x == 100

    def test_data_factory_has_docstring(self):
        """Test that DataFactory.__call__ has documentation."""
        assert DataFactory.__call__.__doc__ is not None
        assert "hello world example" in DataFactory.__call__.__doc__
        assert ":param x:" in DataFactory.__call__.__doc__
        assert ":return: Data" in DataFactory.__call__.__doc__


class TestDataUser:
    """Tests for data_user function."""

    def test_data_user_is_injected(self):
        """Test that data_user is decorated with @injected."""
        # Check if it's wrapped by injected decorator
        # When decorated with @injected, it becomes a Partial object
        assert hasattr(data_user, "src_function") or isinstance(data_user, Injected)

    def test_data_user_function_exists(self):
        """Test that data_user function is defined."""
        assert data_user is not None
        assert callable(data_user) or hasattr(data_user, "src_function")

    def test_data_user_annotations(self):
        """Test data_user function annotations."""
        # Get the actual function (might be wrapped)
        if hasattr(data_user, "src_function"):
            func = data_user.src_function
        else:
            func = data_user

        if hasattr(func, "__annotations__"):
            annotations = func.__annotations__
            # Check that new_data parameter is annotated as DataFactory
            assert "new_data" in annotations
            assert annotations["new_data"] == DataFactory
            # Check return type
            assert "return" in annotations
            assert annotations["return"] == Data

    def test_data_user_execution(self):
        """Test that data_user function executes correctly."""
        # Get the actual function (might be wrapped)
        if hasattr(data_user, "src_function"):
            func = data_user.src_function
        else:
            func = data_user

        # Create a mock DataFactory
        from unittest.mock import Mock

        mock_factory = Mock(spec=DataFactory)
        mock_data_instance = Data(x=0)
        mock_factory.return_value = mock_data_instance

        # Call the function
        result = func(mock_factory, "test message")

        # Verify the factory was called with x=0
        mock_factory.assert_called_once_with(x=0)

        # The function doesn't return anything (returns None)
        assert result is None


class TestIDataUser:
    """Tests for IDataUser interface class."""

    def test_idatauser_is_class(self):
        """Test that IDataUser is a class."""
        assert isinstance(IDataUser, type)

    def test_idatauser_callable_method(self):
        """Test that IDataUser has __call__ method."""
        assert hasattr(IDataUser, "__call__")

    def test_idatauser_call_signature(self):
        """Test IDataUser __call__ method signature."""
        # Check method exists and has expected parameters
        call_method = IDataUser.__call__

        # Check it has documentation
        assert call_method.__doc__ is not None
        assert "hello world example" in call_method.__doc__
        assert ":param msg:" in call_method.__doc__

    def test_idatauser_instantiation(self):
        """Test that IDataUser can be instantiated."""
        user = IDataUser()
        assert isinstance(user, IDataUser)
        assert hasattr(user, "__call__")


def test_module_docstring():
    """Test that the module has proper documentation."""
    import pinjected.di.overload_experimental as module

    assert module.__doc__ is not None
    assert "@injected" in module.__doc__
    assert "dataclass" in module.__doc__
    assert "dependency injection" in module.__doc__


def test_example_usage_concept():
    """Test the concept shown in module docstring works."""
    # This tests the example usage pattern from the docstring
    factory = DataFactory()

    # Simulate what data_user should do based on the docstring
    d = factory(x=10)
    assert isinstance(d, Data)
    assert d.x == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
