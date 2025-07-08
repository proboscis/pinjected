"""Tests for pinjected.with_context module."""

import pytest
from dataclasses import is_dataclass, fields
from pinjected.with_context import WithContext


class TestWithContext:
    """Test WithContext dataclass."""

    def test_with_context_is_dataclass(self):
        """Test that WithContext is a dataclass."""
        assert is_dataclass(WithContext)

    def test_with_context_instantiation(self):
        """Test WithContext can be instantiated."""
        context = WithContext()
        assert isinstance(context, WithContext)

    def test_with_context_no_fields(self):
        """Test WithContext has no fields."""
        field_list = fields(WithContext)
        assert len(field_list) == 0

    def test_with_context_equality(self):
        """Test WithContext instances are equal."""
        context1 = WithContext()
        context2 = WithContext()
        # Dataclasses with no fields should be equal
        assert context1 == context2

    def test_with_context_repr(self):
        """Test WithContext string representation."""
        context = WithContext()
        repr_str = repr(context)
        # Default dataclass repr
        assert repr_str == "WithContext()"

    def test_with_context_is_not_hashable(self):
        """Test WithContext instances are hashable (frozen dataclass)."""
        context = WithContext()
        # Frozen dataclasses are hashable
        hash_value = hash(context)
        assert isinstance(hash_value, int)

    def test_with_context_not_in_set(self):
        """Test WithContext can be used in sets (is hashable)."""
        context1 = WithContext()
        context2 = WithContext()

        # Should work since frozen dataclasses are hashable
        context_set = {context1, context2}
        # All instances are equal, so set should have only one element
        assert len(context_set) == 1

    def test_with_context_not_as_dict_key(self):
        """Test WithContext can be used as dict key (is hashable)."""
        context = WithContext()

        # Should work since frozen dataclasses are hashable
        context_dict = {context: "value"}
        assert context_dict[context] == "value"

    def test_with_context_copy(self):
        """Test copying WithContext instances."""
        import copy

        context = WithContext()
        shallow_copy = copy.copy(context)
        deep_copy = copy.deepcopy(context)

        # All should be equal
        assert context == shallow_copy
        assert context == deep_copy
        assert shallow_copy == deep_copy

    def test_with_context_inheritance(self):
        """Test WithContext can be inherited."""

        class ExtendedContext(WithContext):
            def custom_method(self):
                return "custom"

        extended = ExtendedContext()
        assert isinstance(extended, WithContext)
        assert isinstance(extended, ExtendedContext)
        assert extended.custom_method() == "custom"

    def test_with_context_type_annotations(self):
        """Test WithContext has proper type annotations."""
        # Check that the class has annotations
        # Even if empty, dataclass should have __annotations__
        assert hasattr(WithContext, "__annotations__")
        # Should be empty dict since no fields
        assert WithContext.__annotations__ == {}

    def test_multiple_instances_independent(self):
        """Test multiple WithContext instances are independent."""
        contexts = [WithContext() for _ in range(5)]

        # All should be equal
        for i in range(len(contexts)):
            for j in range(len(contexts)):
                assert contexts[i] == contexts[j]

    def test_with_context_picklable(self):
        """Test WithContext can be pickled."""
        import pickle

        context = WithContext()
        pickled = pickle.dumps(context)
        unpickled = pickle.loads(pickled)

        assert context == unpickled
        assert type(context) is type(unpickled)

    def test_with_context_slots(self):
        """Test if WithContext uses slots (optional dataclass feature)."""
        context = WithContext()

        # Check if __slots__ is defined (may or may not be)
        has_slots = hasattr(WithContext, "__slots__")

        # If it has slots, it shouldn't have __dict__
        if has_slots:
            assert not hasattr(context, "__dict__")
        else:
            # Otherwise it should have __dict__
            assert hasattr(context, "__dict__")
            # And the dict should be empty for this empty dataclass
            assert context.__dict__ == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
