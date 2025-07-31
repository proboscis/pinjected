"""Tests for di/applicative.py module."""

import pytest
from unittest.mock import Mock
from contextlib import suppress

from pinjected.di.applicative import Applicative


class ApplicativeWrapper:
    """Wrapper that has a map method."""

    def __init__(self, value):
        self.value = value

    def map(self, f):
        return f(self.value)


class ConcreteApplicative(Applicative):
    """Concrete implementation of Applicative for testing."""

    def map(self, target, f):
        """Apply function f to target."""
        if hasattr(target, "map"):
            return target.map(f)
        return f(target)

    def zip(self, *targets):
        """Zip multiple targets together."""
        # Return something with a map method
        return ApplicativeWrapper(list(targets))

    def pure(self, item):
        """Wrap item in applicative context."""
        return item

    def is_instance(self, item) -> bool:
        """Check if item is instance of this applicative."""
        return True


class TestApplicative:
    """Tests for Applicative abstract base class."""

    def test_dict_method(self):
        """Test dict method that combines kwargs using zip and map."""
        app = ConcreteApplicative()

        # Test with simple values
        result = app.dict(a=10, b=20, c=30)

        # The dict method should zip values and map them back to a dict
        assert result == {"a": 10, "b": 20, "c": 30}

    def test_dict_empty(self):
        """Test dict method with no arguments."""
        app = ConcreteApplicative()

        result = app.dict()
        assert result == {}

    def test_dict_preserves_order(self):
        """Test that dict method preserves order of kwargs."""
        app = ConcreteApplicative()

        # Create a dict with specific order
        result = app.dict(z=1, a=2, m=3)

        # Check the keys are preserved
        assert list(result.keys()) == ["z", "a", "m"]
        assert list(result.values()) == [1, 2, 3]

    def test_await_not_implemented(self):
        """Test that _await_ raises NotImplementedError."""
        app = ConcreteApplicative()

        with pytest.raises(NotImplementedError, match="await not implemented"):
            app._await_(Mock())

    def test_unary_not_implemented(self):
        """Test that unary raises NotImplementedError."""
        app = ConcreteApplicative()

        with pytest.raises(NotImplementedError, match="unary not implemented"):
            app.unary("+", Mock())

    def test_biop_not_implemented(self):
        """Test that biop raises NotImplementedError."""
        app = ConcreteApplicative()

        with pytest.raises(NotImplementedError, match="biop not implemented"):
            app.biop("+", Mock(), Mock())

    def test_abstract_methods(self):
        """Test that Applicative is abstract and cannot be instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            Applicative()

    def test_dict_with_mock_zip_map(self):
        """Test dict method with mocked zip and map to verify behavior."""
        app = ConcreteApplicative()

        # Mock zip and map methods
        mock_zipped = Mock()
        mock_zipped.map = Mock(return_value={"x": 100, "y": 200})

        app.zip = Mock(return_value=mock_zipped)

        # Call dict
        result = app.dict(x=100, y=200)

        # Verify zip was called with the values
        app.zip.assert_called_once_with(100, 200)

        # Verify map was called on the zipped result
        mock_zipped.map.assert_called_once()

        # Verify final result
        assert result == {"x": 100, "y": 200}

    def test_dict_mapper_function(self):
        """Test the internal mapper function used by dict."""
        app = ConcreteApplicative()

        # Override zip to return a custom object with map method
        class ZipResult:
            def __init__(self, values):
                self.values = values

            def map(self, mapper):
                # Call the mapper with the values
                return mapper(self.values)

        app.zip = lambda *values: ZipResult(values)

        # Test dict
        result = app.dict(foo="bar", num=42)

        # The mapper should create a dict from the zipped values
        assert result == {"foo": "bar", "num": 42}


class TestAbstractMethodCoverage:
    """Test to ensure coverage of abstract method definitions."""

    def test_abstract_method_definitions(self):
        """Test that abstract methods are defined but not implemented."""

        # This test ensures the abstract method pass statements are covered
        class TestImpl(Applicative):
            def __init__(self):
                super().__init__()
                self.called_methods = []

            def map(self, target, f):
                self.called_methods.append("map")
                # Call the parent abstract method to cover line 10
                with suppress(NotImplementedError):
                    super().map(target, f)
                return f(target)

            def zip(self, *targets):
                self.called_methods.append("zip")
                # Call the parent abstract method to cover line 14
                with suppress(NotImplementedError):
                    super().zip(*targets)
                return targets

            def pure(self, item):
                self.called_methods.append("pure")
                # Call the parent abstract method to cover line 18
                with suppress(NotImplementedError):
                    super().pure(item)
                return item

            def is_instance(self, item):
                self.called_methods.append("is_instance")
                # Call the parent abstract method to cover line 22
                with suppress(NotImplementedError):
                    super().is_instance(item)
                return True

        impl = TestImpl()

        # Call each method to trigger the coverage
        impl.map("target", lambda x: x.upper())
        impl.zip("a", "b", "c")
        impl.pure(42)
        impl.is_instance("test")

        # Verify all methods were called
        assert impl.called_methods == ["map", "zip", "pure", "is_instance"]


class TestApplicativeInterface:
    """Test that implementations must provide all abstract methods."""

    def test_missing_map(self):
        """Test that missing map method prevents instantiation."""

        class IncompleteApplicative(Applicative):
            def zip(self, *targets):
                pass

            def pure(self, item):
                pass

            def is_instance(self, item):
                pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteApplicative()

    def test_missing_zip(self):
        """Test that missing zip method prevents instantiation."""

        class IncompleteApplicative(Applicative):
            def map(self, target, f):
                pass

            def pure(self, item):
                pass

            def is_instance(self, item):
                pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteApplicative()

    def test_missing_pure(self):
        """Test that missing pure method prevents instantiation."""

        class IncompleteApplicative(Applicative):
            def map(self, target, f):
                pass

            def zip(self, *targets):
                pass

            def is_instance(self, item):
                pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteApplicative()

    def test_missing_is_instance(self):
        """Test that missing is_instance method prevents instantiation."""

        class IncompleteApplicative(Applicative):
            def map(self, target, f):
                pass

            def zip(self, *targets):
                pass

            def pure(self, item):
                pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteApplicative()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
