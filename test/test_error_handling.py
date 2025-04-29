import pytest

from pinjected.exceptions import DependencyValidationError
from pinjected.run_helpers.run_injected import PinjectedRunFailure


def test_validation_error_handling():
    """Test that DependencyValidationError is properly handled."""

    with pytest.raises(PinjectedRunFailure) as excinfo:
        try:
            raise DependencyValidationError("Test validation error", None)
        except Exception as e:
            raise PinjectedRunFailure("pinjected run failed") from e

    assert isinstance(excinfo.value.__cause__, DependencyValidationError)
    assert "Test validation error" in str(excinfo.value.__cause__)
