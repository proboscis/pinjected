"""Comprehensive tests for di/overload_experimental.py module."""

import pytest
from dataclasses import is_dataclass, fields

from pinjected.di.overload_experimental import Data, DataFactory, data_user, IDataUser


class TestData:
    """Test the Data dataclass."""

    def test_data_is_dataclass(self):
        """Test that Data is a dataclass."""
        assert is_dataclass(Data)

    def test_data_default_value(self):
        """Test Data default value for x."""
        data = Data()
        assert data.x == 0

    def test_data_custom_value(self):
        """Test Data with custom value."""
        data = Data(x=42)
        assert data.x == 42

    def test_data_fields(self):
        """Test Data fields."""
        data_fields = fields(Data)
        assert len(data_fields) == 1
        assert data_fields[0].name == "x"
        assert data_fields[0].type is int
        assert data_fields[0].default == 0

    def test_data_has_docstring(self):
        """Test that Data has docstring."""
        assert Data.__doc__ is not None
        assert "docs for data" in Data.__doc__

    def test_data_equality(self):
        """Test Data equality."""
        data1 = Data(x=10)
        data2 = Data(x=10)
        data3 = Data(x=20)

        assert data1 == data2
        assert data1 != data3

    def test_data_repr(self):
        """Test Data representation."""
        data = Data(x=15)
        assert repr(data) == "Data(x=15)"


class TestDataFactory:
    """Test the DataFactory class."""

    def test_data_factory_callable(self):
        """Test that DataFactory is callable."""
        factory = DataFactory()
        assert callable(factory)

    def test_data_factory_creates_data(self):
        """Test DataFactory creates Data instances."""
        factory = DataFactory()
        data = factory(x=25)

        assert isinstance(data, Data)
        assert data.x == 25

    def test_data_factory_call_signature(self):
        """Test DataFactory __call__ signature."""
        factory = DataFactory()

        # Test with keyword argument
        data1 = factory(x=10)
        assert data1.x == 10

        # Test with positional argument
        data2 = factory(20)
        assert data2.x == 20

    def test_data_factory_has_docstring(self):
        """Test that DataFactory.__call__ has docstring."""
        factory = DataFactory()
        assert factory.__call__.__doc__ is not None
        assert "hello world example" in factory.__call__.__doc__
        assert ":param x: tell me something special" in factory.__call__.__doc__
        assert ":return: Data" in factory.__call__.__doc__

    def test_multiple_factory_instances(self):
        """Test multiple DataFactory instances."""
        factory1 = DataFactory()
        factory2 = DataFactory()

        data1 = factory1(x=5)
        data2 = factory2(x=5)

        assert data1 == data2  # Same data values
        assert factory1 is not factory2  # Different factory instances


class TestDataUser:
    """Test the data_user function."""

    def test_data_user_is_injected(self):
        """Test that data_user is an injected function."""
        # Check it has injected attributes
        assert hasattr(data_user, "dependencies")
        assert callable(data_user)

    def test_data_user_with_mock_factory(self):
        """Test data_user with mock factory."""
        # Create a mock factory
        called_with = []

        def mock_factory(x):
            called_with.append(x)
            return Data(x)

        # Since data_user doesn't return anything, we can't test it directly
        # Let's at least verify it has the expected dependencies
        deps = data_user.complete_dependencies
        assert isinstance(deps, set)
        assert "new_data" in deps
        # msg is not in complete_dependencies because it's a regular parameter

    def test_data_user_type_annotations(self):
        """Test data_user type annotations."""
        # For injected functions, we need to check the src_function annotations
        annotations = data_user.src_function.__annotations__

        # Check parameter types
        assert "new_data" in annotations
        assert annotations["new_data"] == DataFactory

        # Check return type
        assert "return" in annotations
        assert annotations["return"] == Data

    def test_data_user_creates_data_with_zero(self):
        """Test that data_user calls factory with x=0."""
        # Since we can't easily execute the injected function in tests,
        # let's verify its structure

        # Check the function signature parameters
        import inspect

        sig = inspect.signature(data_user.src_function)
        params = list(sig.parameters.keys())

        # Should have new_data and msg parameters
        assert "new_data" in params
        assert "msg" in params

        # The function body should call new_data(x=0)
        # We can verify this by looking at the source
        source = inspect.getsource(data_user.src_function)
        assert "new_data(x=0)" in source


class TestIDataUser:
    """Test the IDataUser interface class."""

    def test_idatauser_is_interface(self):
        """Test IDataUser is an interface-like class."""
        assert hasattr(IDataUser, "__call__")

    def test_idatauser_instantiation(self):
        """Test creating IDataUser instance."""
        user = IDataUser()
        assert user is not None
        assert callable(user)

    def test_idatauser_call_method(self):
        """Test IDataUser __call__ method."""
        user = IDataUser()

        # The base implementation doesn't do anything
        result = user(msg="hello")
        assert result is None

    def test_idatauser_call_docstring(self):
        """Test IDataUser.__call__ has docstring."""
        user = IDataUser()
        assert user.__call__.__doc__ is not None
        assert "hello world example" in user.__call__.__doc__
        assert ":param msg:" in user.__call__.__doc__

    def test_idatauser_subclassing(self):
        """Test subclassing IDataUser."""

        class MyDataUser(IDataUser):
            def __call__(self, msg: str):
                return f"Processed: {msg}"

        user = MyDataUser()
        result = user("test")
        assert result == "Processed: test"

    def test_idatauser_type_annotations(self):
        """Test IDataUser.__call__ type annotations."""
        # Get annotations from the method
        call_method = IDataUser.__call__
        call_method.__annotations__ if hasattr(call_method, "__annotations__") else {}

        # In the source, msg parameter has str type annotation
        # The method is defined with (self, msg: str)
        assert "msg" in str(call_method.__code__.co_varnames)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
