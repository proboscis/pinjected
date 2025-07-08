"""Simple tests for di/overload_experimental.py module."""

import pytest
from dataclasses import is_dataclass

from pinjected.di.overload_experimental import Data, DataFactory, data_user, IDataUser
from pinjected.di.partially_injected import Partial


class TestOverloadExperimental:
    """Test the overload_experimental module functionality."""

    def test_data_class(self):
        """Test the Data dataclass."""
        assert is_dataclass(Data)

        # Test default value
        data = Data()
        assert data.x == 0

        # Test with custom value
        data = Data(x=42)
        assert data.x == 42

    def test_data_factory(self):
        """Test the DataFactory class."""
        factory = DataFactory()

        # Test calling the factory
        data = factory(x=10)
        assert isinstance(data, Data)
        assert data.x == 10

        # Test with different value
        data2 = factory(x=99)
        assert data2.x == 99

    def test_data_factory_docstring(self):
        """Test DataFactory.__call__ has proper docstring."""
        assert DataFactory.__call__.__doc__ is not None
        assert "hello world example" in DataFactory.__call__.__doc__
        assert "param x:" in DataFactory.__call__.__doc__

    def test_data_user_is_injected(self):
        """Test that data_user is decorated with @injected."""
        # Should be a Partial since it's decorated
        assert isinstance(data_user, Partial)

    def test_data_user_function(self):
        """Test the data_user function logic."""
        # Get the underlying function
        func = data_user.src_function

        # Create a mock factory
        factory = DataFactory()
        msg = "test message"

        # Call the function
        result = func(factory, msg)

        # The function creates Data(x=0) but doesn't return it
        # So result should be None
        assert result is None

    def test_idata_user_interface(self):
        """Test the IDataUser interface class."""
        interface = IDataUser()

        # Check it has __call__ method
        assert hasattr(interface, "__call__")
        assert callable(interface)

        # Check docstring
        assert IDataUser.__call__.__doc__ is not None
        assert "hello world example" in IDataUser.__call__.__doc__

    def test_module_docstring(self):
        """Test the module has proper documentation."""
        from pinjected.di import overload_experimental

        assert overload_experimental.__doc__ is not None
        assert "@injected" in overload_experimental.__doc__
        assert "dataclass_transform" in overload_experimental.__doc__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
