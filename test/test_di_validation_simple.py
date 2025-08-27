"""Simple tests for di/validation.py module."""

import pytest
from dataclasses import is_dataclass

from pinjected.di.validation import ValResult, ValSuccess, ValFailure


class TestValResult:
    """Test the ValResult base class."""

    def test_val_result_exists(self):
        """Test that ValResult class exists."""
        assert ValResult is not None
        assert isinstance(ValResult, type)

    def test_val_result_instantiation(self):
        """Test creating ValResult instance."""
        result = ValResult()
        assert result is not None
        assert isinstance(result, ValResult)

    def test_val_result_is_base_class(self):
        """Test that ValResult is a base class."""
        assert issubclass(ValSuccess, ValResult)
        assert issubclass(ValFailure, ValResult)


class TestValSuccess:
    """Test the ValSuccess dataclass."""

    def test_val_success_is_dataclass(self):
        """Test that ValSuccess is a dataclass."""
        assert is_dataclass(ValSuccess)

    def test_val_success_creation(self):
        """Test creating ValSuccess instance."""
        success = ValSuccess()

        assert success is not None
        assert isinstance(success, ValSuccess)
        assert isinstance(success, ValResult)

    def test_val_success_no_attributes(self):
        """Test that ValSuccess has no special attributes."""
        success = ValSuccess()
        # Should not have exc attribute like ValFailure
        assert not hasattr(success, "exc")

    def test_val_success_equality(self):
        """Test ValSuccess equality."""
        success1 = ValSuccess()
        success2 = ValSuccess()

        # Dataclasses with no fields should be equal
        assert success1 == success2

    def test_val_success_repr(self):
        """Test ValSuccess string representation."""
        success = ValSuccess()
        assert repr(success) == "ValSuccess()"


class TestValFailure:
    """Test the ValFailure dataclass."""

    def test_val_failure_is_dataclass(self):
        """Test that ValFailure is a dataclass."""
        assert is_dataclass(ValFailure)

    def test_val_failure_creation(self):
        """Test creating ValFailure instance."""
        exc = ValueError("Test error")
        failure = ValFailure(exc=exc)

        assert failure is not None
        assert isinstance(failure, ValFailure)
        assert isinstance(failure, ValResult)
        assert failure.exc is exc

    def test_val_failure_with_different_exceptions(self):
        """Test ValFailure with different exception types."""
        value_error = ValueError("Value error")
        type_error = TypeError("Type error")
        custom_exc = Exception("Custom error")

        failure1 = ValFailure(exc=value_error)
        failure2 = ValFailure(exc=type_error)
        failure3 = ValFailure(exc=custom_exc)

        assert failure1.exc is value_error
        assert failure2.exc is type_error
        assert failure3.exc is custom_exc

    def test_val_failure_equality(self):
        """Test ValFailure equality."""
        exc1 = ValueError("Error")
        exc2 = ValueError("Error")
        exc3 = ValueError("Different")

        failure1 = ValFailure(exc=exc1)
        failure2 = ValFailure(exc=exc1)  # Same exception object
        failure3 = ValFailure(exc=exc2)  # Different object, same value
        failure4 = ValFailure(exc=exc3)  # Different value

        assert failure1 == failure2  # Same exception object
        assert failure1 != failure3  # Different objects
        assert failure1 != failure4  # Different values

    def test_val_failure_repr(self):
        """Test ValFailure string representation."""
        exc = ValueError("Test error")
        failure = ValFailure(exc=exc)

        repr_str = repr(failure)
        assert "ValFailure" in repr_str
        assert "exc=" in repr_str


class TestValidationResults:
    """Test usage patterns for validation results."""

    def test_result_type_checking(self):
        """Test checking result types."""
        success = ValSuccess()
        failure = ValFailure(exc=Exception("Error"))

        # Both are ValResult
        assert isinstance(success, ValResult)
        assert isinstance(failure, ValResult)

        # Can distinguish between success and failure
        assert isinstance(success, ValSuccess)
        assert not isinstance(success, ValFailure)

        assert isinstance(failure, ValFailure)
        assert not isinstance(failure, ValSuccess)

    def test_result_pattern_matching(self):
        """Test pattern matching with results."""

        def process_result(result: ValResult) -> str:
            match result:
                case ValSuccess():
                    return "success"
                case ValFailure(exc=exc):
                    return f"failure: {exc}"
                case _:
                    return "unknown"

        success = ValSuccess()
        failure = ValFailure(exc=ValueError("Test"))

        assert process_result(success) == "success"
        assert process_result(failure) == "failure: Test"

    def test_collecting_failures(self):
        """Test collecting multiple failures."""
        failures = []

        for i in range(3):
            if i == 1:
                failures.append(ValFailure(exc=ValueError(f"Error {i}")))
            else:
                # Success cases don't get added
                pass

        assert len(failures) == 1
        assert isinstance(failures[0], ValFailure)
        assert str(failures[0].exc) == "Error 1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
