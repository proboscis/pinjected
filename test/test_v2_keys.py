"""Tests for v2/keys.py module."""

import pytest
from pinjected.v2.keys import IBindKey, StrBindKey, DestructorKey


def test_ibindkey_abstract():
    """Test that IBindKey is abstract and can't be instantiated."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IBindKey()


def test_ibindkey_default_ide_hint_string():
    """Test IBindKey default ide_hint_string implementation."""

    class CustomKey(IBindKey):
        def __init__(self, value):
            self.value = value

        def ide_hint_string(self):
            # Call parent implementation
            return super().ide_hint_string()

    key = CustomKey("test")
    # The default implementation returns repr(self)
    assert "CustomKey" in key.ide_hint_string()


def test_strbindkey_creation():
    """Test StrBindKey dataclass creation."""
    key = StrBindKey(name="test_key")
    assert key.name == "test_key"

    # Test frozen
    with pytest.raises(AttributeError):
        key.name = "new_name"


def test_strbindkey_post_init_validation():
    """Test StrBindKey __post_init__ validation."""
    # Valid string
    key = StrBindKey(name="valid")
    assert key.name == "valid"

    # Invalid non-string
    with pytest.raises(AssertionError):
        StrBindKey(name=123)


def test_strbindkey_ide_hint_string_short():
    """Test StrBindKey ide_hint_string for short names."""
    key = StrBindKey(name="short_name")
    assert key.ide_hint_string() == "short_name"

    # Test exactly 19 chars (should still be full name)
    key19 = StrBindKey(name="a" * 19)
    assert key19.ide_hint_string() == "a" * 19


def test_strbindkey_ide_hint_string_long():
    """Test StrBindKey ide_hint_string for long names."""
    # Test with 21 chars (should be truncated)
    long_name = "a" * 10 + "b" * 11
    key = StrBindKey(name=long_name)
    # First 10 chars: "aaaaaaaaaa", last 10 chars: "bbbbbbbbbb"
    assert key.ide_hint_string() == "aaaaaaaaaa...bbbbbbbbbb"

    # Test with very long name
    very_long = "start" + "x" * 50 + "end"
    key2 = StrBindKey(name=very_long)
    # First 10 chars: "startxxxxx", last 10 chars: "xxxxxxxend"
    assert key2.ide_hint_string() == "startxxxxx...xxxxxxxend"


def test_strbindkey_repr():
    """Test StrBindKey string representation."""
    key = StrBindKey(name="test")
    assert repr(key) == "StrBindKey(name='test')"


def test_destructorkey_creation():
    """Test DestructorKey dataclass creation."""
    target = StrBindKey(name="target_key")
    destructor = DestructorKey(tgt=target)

    assert destructor.tgt is target

    # Test frozen
    with pytest.raises(AttributeError):
        destructor.tgt = StrBindKey(name="new")


def test_destructorkey_ide_hint_string():
    """Test DestructorKey ide_hint_string method."""
    # Test with short target name
    target = StrBindKey(name="short")
    destructor = DestructorKey(tgt=target)
    assert destructor.ide_hint_string() == "destructor(short)"

    # Test with long target name (20 chars triggers truncation)
    long_target = StrBindKey(name="a" * 20)
    destructor2 = DestructorKey(tgt=long_target)
    assert destructor2.ide_hint_string() == "destructor(aaaaaaaaaa...aaaaaaaaaa)"


def test_destructorkey_nested():
    """Test nested DestructorKey."""
    base = StrBindKey(name="base")
    destructor1 = DestructorKey(tgt=base)
    destructor2 = DestructorKey(tgt=destructor1)

    assert destructor2.ide_hint_string() == "destructor(destructor(base))"


def test_keys_equality():
    """Test key equality based on frozen dataclass."""
    key1 = StrBindKey(name="test")
    key2 = StrBindKey(name="test")
    key3 = StrBindKey(name="other")

    assert key1 == key2
    assert key1 != key3

    # Test DestructorKey equality
    d1 = DestructorKey(tgt=key1)
    d2 = DestructorKey(tgt=key2)
    d3 = DestructorKey(tgt=key3)

    assert d1 == d2
    assert d1 != d3


def test_keys_hashable():
    """Test that keys are hashable (frozen dataclass)."""
    key1 = StrBindKey(name="test")
    key2 = StrBindKey(name="test")

    # Should be able to use as dict keys
    d = {key1: "value"}
    assert d[key2] == "value"

    # Should be able to add to set
    s = {key1, key2}
    assert len(s) == 1  # Same key


def test_custom_bindkey_implementation():
    """Test custom IBindKey implementation."""

    class CustomBindKey(IBindKey):
        def __init__(self, id, description):
            self.id = id
            self.description = description

        def ide_hint_string(self):
            return f"Custom[{self.id}]: {self.description}"

    custom = CustomBindKey(42, "test key")
    assert custom.ide_hint_string() == "Custom[42]: test key"

    # Test with DestructorKey
    destructor = DestructorKey(tgt=custom)
    assert destructor.ide_hint_string() == "destructor(Custom[42]: test key)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
