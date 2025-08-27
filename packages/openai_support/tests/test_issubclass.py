"""Test issubclass check."""

from pinjected.test import injected_pytest
from pydantic import BaseModel


class SimpleModel(BaseModel):
    """Simple model for testing."""

    name: str
    age: int


@injected_pytest
def test_issubclass_check():
    """Test that issubclass works correctly."""

    # Test with BaseModel subclass
    assert issubclass(SimpleModel, BaseModel)

    # Test with None
    assert not issubclass(type(None), BaseModel)

    # Test with string
    assert not issubclass(str, BaseModel)

    # Test what happens with response_format parameter
    response_format = SimpleModel
    if response_format is None or not issubclass(response_format, BaseModel):
        print("Would skip JSON handling")
    else:
        print("Would use JSON handling")
        assert True  # Should reach here

    # Test with None
    response_format = None
    if response_format is None or not issubclass(response_format, BaseModel):
        assert True  # Should reach here
        print("Correctly skips for None")


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v", "-s"])
