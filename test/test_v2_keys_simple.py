"""Simple tests for v2/keys.py module."""

import pytest
from abc import ABC
from dataclasses import is_dataclass

from pinjected.v2.keys import IBindKey, StrBindKey, DestructorKey


class TestIBindKey:
    """Test the IBindKey abstract base class."""

    def test_ibindkey_is_abstract(self):
        """Test that IBindKey is an abstract base class."""
        assert issubclass(IBindKey, ABC)

        # Cannot instantiate directly
        with pytest.raises(TypeError):
            IBindKey()

    def test_ibindkey_has_ide_hint_string(self):
        """Test that IBindKey defines ide_hint_string method."""
        assert hasattr(IBindKey, "ide_hint_string")

        # Create a concrete implementation
        class ConcreteKey(IBindKey):
            def ide_hint_string(self):
                return "concrete"

        key = ConcreteKey()
        assert key.ide_hint_string() == "concrete"

    def test_ibindkey_docstring(self):
        """Test IBindKey has proper docstring."""
        assert IBindKey.__doc__ is not None
        assert "key" in IBindKey.__doc__


class TestStrBindKey:
    """Test the StrBindKey dataclass."""

    def test_strbindkey_is_dataclass(self):
        """Test that StrBindKey is a dataclass."""
        assert is_dataclass(StrBindKey)

    def test_strbindkey_is_frozen(self):
        """Test that StrBindKey is frozen."""
        key = StrBindKey(name="test")

        # Should not be able to modify
        with pytest.raises(AttributeError):
            key.name = "modified"

    def test_strbindkey_creation(self):
        """Test creating StrBindKey instance."""
        key = StrBindKey(name="test_key")

        assert key.name == "test_key"
        assert isinstance(key, IBindKey)

    def test_strbindkey_post_init_validation(self):
        """Test that StrBindKey validates name is string."""
        # Should raise assertion error for non-string
        with pytest.raises(AssertionError):
            StrBindKey(name=123)

    def test_strbindkey_ide_hint_string_short(self):
        """Test ide_hint_string for short names."""
        key = StrBindKey(name="short_name")

        assert key.ide_hint_string() == "short_name"

    def test_strbindkey_ide_hint_string_long(self):
        """Test ide_hint_string for long names."""
        long_name = "this_is_a_very_long_key_name_that_exceeds_twenty_chars"
        key = StrBindKey(name=long_name)

        hint = key.ide_hint_string()
        assert len(hint) < len(long_name)
        assert hint.startswith("this_is_a_")
        assert hint.endswith("enty_chars")  # Last 10 characters of the name
        assert "..." in hint

    def test_strbindkey_ide_hint_string_exactly_20(self):
        """Test ide_hint_string for name exactly 20 chars."""
        name_20 = "a" * 20
        key = StrBindKey(name=name_20)

        # Should truncate since >= 20
        hint = key.ide_hint_string()
        assert "..." in hint

    def test_strbindkey_hashable(self):
        """Test that StrBindKey is hashable (frozen dataclass)."""
        key1 = StrBindKey(name="test")
        key2 = StrBindKey(name="test")
        key3 = StrBindKey(name="other")

        # Can be used in sets
        key_set = {key1, key2, key3}
        assert len(key_set) == 2  # key1 and key2 are equal


class TestDestructorKey:
    """Test the DestructorKey dataclass."""

    def test_destructorkey_is_dataclass(self):
        """Test that DestructorKey is a dataclass."""
        assert is_dataclass(DestructorKey)

    def test_destructorkey_is_frozen(self):
        """Test that DestructorKey is frozen."""
        target = StrBindKey(name="target")
        key = DestructorKey(tgt=target)

        # Should not be able to modify
        with pytest.raises(AttributeError):
            key.tgt = StrBindKey(name="other")

    def test_destructorkey_creation(self):
        """Test creating DestructorKey instance."""
        target = StrBindKey(name="target_key")
        key = DestructorKey(tgt=target)

        assert key.tgt is target
        assert isinstance(key, IBindKey)

    def test_destructorkey_ide_hint_string(self):
        """Test ide_hint_string for DestructorKey."""
        target = StrBindKey(name="my_resource")
        key = DestructorKey(tgt=target)

        hint = key.ide_hint_string()
        assert hint == "destructor(my_resource)"

    def test_destructorkey_ide_hint_string_nested(self):
        """Test ide_hint_string with nested DestructorKey."""
        inner_target = StrBindKey(name="inner")
        inner_destructor = DestructorKey(tgt=inner_target)
        outer_destructor = DestructorKey(tgt=inner_destructor)

        hint = outer_destructor.ide_hint_string()
        assert hint == "destructor(destructor(inner))"

    def test_destructorkey_hashable(self):
        """Test that DestructorKey is hashable."""
        target1 = StrBindKey(name="test")
        target2 = StrBindKey(name="test")

        key1 = DestructorKey(tgt=target1)
        key2 = DestructorKey(tgt=target2)

        # Should be equal since targets are equal
        assert hash(key1) == hash(key2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
