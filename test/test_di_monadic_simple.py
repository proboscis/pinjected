"""Simple tests for di/monadic.py module."""

import pytest
from returns.result import Success, Failure

from pinjected.di.monadic import getitem_opt


class TestGetitemOpt:
    """Test the getitem_opt function."""

    def test_getitem_opt_with_dict_success(self):
        """Test getitem_opt with dict and existing key."""
        data = {"key": "value", "number": 42}

        result = getitem_opt(data, "key")

        assert isinstance(result, Success)
        assert result.unwrap() == "value"

        result2 = getitem_opt(data, "number")
        assert isinstance(result2, Success)
        assert result2.unwrap() == 42

    def test_getitem_opt_with_dict_failure(self):
        """Test getitem_opt with dict and missing key."""
        data = {"key": "value"}

        result = getitem_opt(data, "missing")

        assert isinstance(result, Failure)
        # Should contain KeyError
        assert isinstance(result.failure(), KeyError)

    def test_getitem_opt_with_list_success(self):
        """Test getitem_opt with list and valid index."""
        data = [10, 20, 30, 40]

        result = getitem_opt(data, 0)
        assert isinstance(result, Success)
        assert result.unwrap() == 10

        result2 = getitem_opt(data, 3)
        assert isinstance(result2, Success)
        assert result2.unwrap() == 40

    def test_getitem_opt_with_list_failure(self):
        """Test getitem_opt with list and invalid index."""
        data = [10, 20, 30]

        result = getitem_opt(data, 5)

        assert isinstance(result, Failure)
        # Should contain IndexError
        assert isinstance(result.failure(), IndexError)

        # Negative index out of bounds
        result2 = getitem_opt(data, -10)
        assert isinstance(result2, Failure)

    def test_getitem_opt_with_string(self):
        """Test getitem_opt with string indexing."""
        data = "hello"

        result = getitem_opt(data, 0)
        assert isinstance(result, Success)
        assert result.unwrap() == "h"

        result2 = getitem_opt(data, 4)
        assert isinstance(result2, Success)
        assert result2.unwrap() == "o"

        # Out of bounds
        result3 = getitem_opt(data, 10)
        assert isinstance(result3, Failure)

    def test_getitem_opt_with_custom_object(self):
        """Test getitem_opt with custom object implementing __getitem__."""

        class CustomContainer:
            def __getitem__(self, key):
                if key == "valid":
                    return "success"
                raise ValueError(f"Invalid key: {key}")

        obj = CustomContainer()

        result = getitem_opt(obj, "valid")
        assert isinstance(result, Success)
        assert result.unwrap() == "success"

        result2 = getitem_opt(obj, "invalid")
        assert isinstance(result2, Failure)
        assert isinstance(result2.failure(), ValueError)

    def test_getitem_opt_with_no_getitem(self):
        """Test getitem_opt with object that doesn't have __getitem__."""

        class NoGetItem:
            pass

        obj = NoGetItem()

        result = getitem_opt(obj, "key")

        assert isinstance(result, Failure)
        # Should contain AttributeError
        assert isinstance(result.failure(), AttributeError)

    def test_getitem_opt_with_none(self):
        """Test getitem_opt with None object."""
        result = getitem_opt(None, "key")

        assert isinstance(result, Failure)
        # Should contain AttributeError
        assert isinstance(result.failure(), AttributeError)

    def test_getitem_opt_preserves_exception_type(self):
        """Test that getitem_opt preserves the original exception type."""
        data = {"key": "value"}

        result = getitem_opt(data, "missing")

        # Check the failure contains the original exception
        assert isinstance(result.failure(), KeyError)
        assert "missing" in str(result.failure())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
