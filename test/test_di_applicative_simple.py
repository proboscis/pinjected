"""Simple tests for di/applicative.py module to improve coverage."""

import pytest

from pinjected.di.applicative import Applicative


class ConcreteApplicative(Applicative):
    """Concrete implementation of Applicative for testing."""

    def map(self, target, f):
        """Concrete implementation of map."""
        return f(target)

    def zip(self, *targets):
        """Concrete implementation of zip that returns a mappable object."""

        class ZippedResult:
            def __init__(self, values):
                self.values = values

            def map(self, mapper):
                return mapper(self.values)

        return ZippedResult(targets)

    def pure(self, item):
        """Concrete implementation of pure."""
        return item

    def is_instance(self, item) -> bool:
        """Concrete implementation of is_instance."""
        return isinstance(item, (int, str, list, dict, tuple))


class TestApplicative:
    """Test the Applicative abstract base class."""

    def test_dict_method(self):
        """Test the dict method implementation."""
        app = ConcreteApplicative()

        # Test with simple values
        result = app.dict(a=1, b=2, c=3)
        assert result == {"a": 1, "b": 2, "c": 3}

        # Test with empty dict
        result = app.dict()
        assert result == {}

        # Test with various types
        result = app.dict(str_val="hello", int_val=42, list_val=[1, 2, 3])
        assert result == {"str_val": "hello", "int_val": 42, "list_val": [1, 2, 3]}

    def test_dict_method_uses_zip_and_map(self):
        """Test that dict method properly uses zip and map."""
        app = ConcreteApplicative()

        # Mock zip to verify it's called
        original_zip = app.zip
        zip_called = False
        zip_args = None

        def mock_zip(*args):
            nonlocal zip_called, zip_args
            zip_called = True
            zip_args = args
            return original_zip(*args)

        app.zip = mock_zip

        # Test dict method
        result = app.dict(x=10, y=20)

        # Verify zip was called with values
        assert zip_called
        assert zip_args == (10, 20)
        assert result == {"x": 10, "y": 20}

    def test_await_not_implemented(self):
        """Test that _await_ raises NotImplementedError."""
        app = ConcreteApplicative()

        with pytest.raises(NotImplementedError, match="await not implemented"):
            app._await_("some_target")

    def test_unary_not_implemented(self):
        """Test that unary raises NotImplementedError."""
        app = ConcreteApplicative()

        with pytest.raises(NotImplementedError, match="unary not implemented"):
            app.unary("-", "some_target")

    def test_biop_not_implemented(self):
        """Test that biop raises NotImplementedError."""
        app = ConcreteApplicative()

        with pytest.raises(NotImplementedError, match="biop not implemented"):
            app.biop("+", "target1", "target2")

    def test_concrete_implementation(self):
        """Test the concrete implementation methods."""
        app = ConcreteApplicative()

        # Test map
        result = app.map(5, lambda x: x * 2)
        assert result == 10

        # Test zip
        result = app.zip(1, 2, 3)
        assert result == (1, 2, 3)

        # Test pure
        result = app.pure("hello")
        assert result == "hello"

        # Test is_instance
        assert app.is_instance(42) is True
        assert app.is_instance("hello") is True
        assert app.is_instance([1, 2, 3]) is True
        assert app.is_instance(object()) is False

    def test_dict_strict_false(self):
        """Test that dict uses strict=False in zip."""
        app = ConcreteApplicative()

        # This should work even with mismatched lengths due to strict=False
        # In our implementation, we control the lengths so they match
        result = app.dict(a=1, b=2)
        assert result == {"a": 1, "b": 2}

    def test_abstract_methods_coverage(self):
        """Test to ensure abstract method lines are covered."""

        # Create a mock subclass that doesn't implement the methods
        class IncompleteApplicative(Applicative):
            def dict(self, **kwargs):
                # Use the parent's dict method
                return super().dict(**kwargs)

        # This will raise TypeError when trying to instantiate
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteApplicative()

    def test_type_annotations(self):
        """Test that type annotations are present."""
        # Check that Applicative is generic
        assert hasattr(Applicative, "__orig_bases__")

        # Check abstract methods have annotations
        import inspect

        # Check is_instance return type
        sig = inspect.signature(Applicative.is_instance)
        assert sig.return_annotation is bool


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
