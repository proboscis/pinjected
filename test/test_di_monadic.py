"""Tests for di.monadic module."""

from returns.result import Success, Failure
from pinjected.di.monadic import getitem_opt


class TestGetitemOpt:
    """Test getitem_opt function."""

    def test_successful_dict_access(self):
        """Test successful dictionary access."""
        data = {"key": "value", "number": 42}

        result = getitem_opt(data, "key")
        assert isinstance(result, Success)
        assert result.unwrap() == "value"

        result = getitem_opt(data, "number")
        assert isinstance(result, Success)
        assert result.unwrap() == 42

    def test_failed_dict_access(self):
        """Test failed dictionary access with missing key."""
        data = {"key": "value"}

        result = getitem_opt(data, "missing_key")
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), KeyError)

    def test_successful_list_access(self):
        """Test successful list access."""
        data = ["a", "b", "c"]

        result = getitem_opt(data, 0)
        assert isinstance(result, Success)
        assert result.unwrap() == "a"

        result = getitem_opt(data, 2)
        assert isinstance(result, Success)
        assert result.unwrap() == "c"

    def test_failed_list_access(self):
        """Test failed list access with out of range index."""
        data = ["a", "b", "c"]

        result = getitem_opt(data, 5)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), IndexError)

        result = getitem_opt(data, -10)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), IndexError)

    def test_successful_tuple_access(self):
        """Test successful tuple access."""
        data = ("x", "y", "z")

        result = getitem_opt(data, 1)
        assert isinstance(result, Success)
        assert result.unwrap() == "y"

    def test_object_without_getitem(self):
        """Test object without __getitem__ method returns Failure."""

        class NoGetItem:
            pass

        obj = NoGetItem()
        # getitem_opt returns a Failure, not raises an exception
        result = getitem_opt(obj, "key")
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), AttributeError)
        assert "'NoGetItem' object has no attribute '__getitem__'" in str(
            result.failure()
        )

    def test_custom_getitem(self):
        """Test custom object with __getitem__ method."""

        class CustomContainer:
            def __getitem__(self, key):
                if key == "valid":
                    return "success"
                raise ValueError(f"Invalid key: {key}")

        obj = CustomContainer()

        # Successful access
        result = getitem_opt(obj, "valid")
        assert isinstance(result, Success)
        assert result.unwrap() == "success"

        # Failed access
        result = getitem_opt(obj, "invalid")
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ValueError)

    def test_negative_indices_on_list(self):
        """Test negative indices on list (should work)."""
        data = ["a", "b", "c"]

        result = getitem_opt(data, -1)
        assert isinstance(result, Success)
        assert result.unwrap() == "c"

        result = getitem_opt(data, -2)
        assert isinstance(result, Success)
        assert result.unwrap() == "b"

    def test_string_access(self):
        """Test string character access."""
        data = "hello"

        result = getitem_opt(data, 0)
        assert isinstance(result, Success)
        assert result.unwrap() == "h"

        result = getitem_opt(data, 10)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), IndexError)
