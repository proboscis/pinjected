"""Tests for di.validation module."""

from pinjected.di.validation import ValResult, ValSuccess, ValFailure


class TestValResult:
    """Test ValResult base class."""

    def test_is_base_class(self):
        """Test that ValResult is a base class."""
        result = ValResult()
        assert isinstance(result, ValResult)

    def test_subclasses(self):
        """Test that ValSuccess and ValFailure are subclasses of ValResult."""
        assert issubclass(ValSuccess, ValResult)
        assert issubclass(ValFailure, ValResult)


class TestValSuccess:
    """Test ValSuccess class."""

    def test_instantiation(self):
        """Test that ValSuccess can be instantiated."""
        success = ValSuccess()
        assert isinstance(success, ValSuccess)
        assert isinstance(success, ValResult)

    def test_is_dataclass(self):
        """Test that ValSuccess is a dataclass."""
        from dataclasses import is_dataclass

        assert is_dataclass(ValSuccess)

    def test_equality(self):
        """Test equality of ValSuccess instances."""
        success1 = ValSuccess()
        success2 = ValSuccess()
        assert success1 == success2

    def test_repr(self):
        """Test string representation of ValSuccess."""
        success = ValSuccess()
        assert repr(success) == "ValSuccess()"


class TestValFailure:
    """Test ValFailure class."""

    def test_instantiation(self):
        """Test that ValFailure can be instantiated with exception."""
        exc = ValueError("test error")
        failure = ValFailure(exc=exc)
        assert isinstance(failure, ValFailure)
        assert isinstance(failure, ValResult)
        assert failure.exc is exc

    def test_is_dataclass(self):
        """Test that ValFailure is a dataclass."""
        from dataclasses import is_dataclass

        assert is_dataclass(ValFailure)

    def test_equality(self):
        """Test equality of ValFailure instances."""
        exc = ValueError("test error")
        failure1 = ValFailure(exc=exc)
        failure2 = ValFailure(exc=exc)
        assert failure1 == failure2

        # Different exceptions should not be equal
        failure3 = ValFailure(exc=TypeError("different error"))
        assert failure1 != failure3

    def test_repr(self):
        """Test string representation of ValFailure."""
        exc = ValueError("test error")
        failure = ValFailure(exc=exc)
        assert "ValFailure" in repr(failure)
        assert "exc=" in repr(failure)

    def test_different_exception_types(self):
        """Test ValFailure with different exception types."""
        failures = [
            ValFailure(exc=ValueError("value error")),
            ValFailure(exc=TypeError("type error")),
            ValFailure(exc=RuntimeError("runtime error")),
            ValFailure(exc=Exception("general error")),
        ]

        for failure in failures:
            assert isinstance(failure, ValFailure)
            assert isinstance(failure.exc, Exception)

    def test_access_exception_attributes(self):
        """Test accessing exception attributes through ValFailure."""
        exc = ValueError("test error message")
        failure = ValFailure(exc=exc)

        assert str(failure.exc) == "test error message"
        assert type(failure.exc) is ValueError
