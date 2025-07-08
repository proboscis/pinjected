"""Simple tests for di/design_spec/impl.py module to improve coverage."""

import pytest
from dataclasses import is_dataclass

from pinjected.di.design_spec.impl import BindSpecImpl, MergedDesignSpec, DesignSpecImpl
from pinjected.v2.keys import StrBindKey
from returns.maybe import Nothing, Some
from returns.future import FutureSuccess


class TestBindSpecImpl:
    """Test the BindSpecImpl class."""

    def test_bind_spec_impl_is_dataclass(self):
        """Test that BindSpecImpl is a dataclass."""
        assert is_dataclass(BindSpecImpl)

    def test_bind_spec_impl_creation_default(self):
        """Test creating BindSpecImpl with defaults."""
        spec = BindSpecImpl()

        assert spec.validator == Nothing
        assert spec.spec_doc_provider == Nothing

    def test_bind_spec_impl_creation_with_validator(self):
        """Test creating BindSpecImpl with a validator."""

        async def validator_func(key, value):
            return FutureSuccess("Valid")

        spec = BindSpecImpl(validator=Some(validator_func))

        assert spec.validator != Nothing
        assert spec.spec_doc_provider == Nothing

    def test_bind_spec_impl_creation_with_doc_provider(self):
        """Test creating BindSpecImpl with doc provider."""

        async def doc_func(key):
            return FutureSuccess("Documentation")

        spec = BindSpecImpl(spec_doc_provider=Some(doc_func))

        assert spec.validator == Nothing
        assert spec.spec_doc_provider != Nothing

    def test_bind_spec_impl_str_representation(self):
        """Test string representation of BindSpecImpl."""
        # Test with no validator or doc
        spec = BindSpecImpl()
        str_repr = str(spec)

        assert "BindSpecImpl" in str_repr
        assert "has_validator" in str_repr
        assert "False" in str_repr
        assert "has_documentation" in str_repr

        # Test with validator and doc
        spec_with_both = BindSpecImpl(
            validator=Some(lambda k, v: FutureSuccess("ok")),
            spec_doc_provider=Some(lambda k: FutureSuccess("doc")),
        )
        str_repr2 = str(spec_with_both)

        assert "True" in str_repr2


class TestDesignSpecImpl:
    """Test the DesignSpecImpl class."""

    def test_design_spec_impl_is_dataclass(self):
        """Test that DesignSpecImpl is a dataclass."""
        assert is_dataclass(DesignSpecImpl)

    def test_design_spec_impl_creation(self):
        """Test creating DesignSpecImpl."""
        key1 = StrBindKey("test1")
        key2 = StrBindKey("test2")

        bind_spec1 = BindSpecImpl()
        bind_spec2 = BindSpecImpl(validator=Some(lambda k, v: FutureSuccess("ok")))

        specs = {key1: bind_spec1, key2: bind_spec2}
        design_spec = DesignSpecImpl(specs=specs)

        assert design_spec.specs == specs

    def test_get_spec_found(self):
        """Test get_spec when key is found."""
        key = StrBindKey("test")
        bind_spec = BindSpecImpl()

        design_spec = DesignSpecImpl(specs={key: bind_spec})
        result = design_spec.get_spec(key)

        assert result == Some(bind_spec)

    def test_get_spec_not_found(self):
        """Test get_spec when key is not found."""
        design_spec = DesignSpecImpl(specs={})
        result = design_spec.get_spec(StrBindKey("missing"))

        assert result == Nothing

    def test_add_operator(self):
        """Test the + operator for DesignSpecImpl."""
        spec1 = DesignSpecImpl(specs={StrBindKey("a"): BindSpecImpl()})
        spec2 = DesignSpecImpl(specs={StrBindKey("b"): BindSpecImpl()})

        merged = spec1 + spec2

        assert isinstance(merged, MergedDesignSpec)
        assert len(merged.srcs) == 2
        assert merged.srcs[0] is spec1
        assert merged.srcs[1] is spec2


class TestMergedDesignSpec:
    """Test the MergedDesignSpec class."""

    def test_merged_design_spec_is_dataclass(self):
        """Test that MergedDesignSpec is a dataclass."""
        assert is_dataclass(MergedDesignSpec)

    def test_merged_design_spec_creation(self):
        """Test creating MergedDesignSpec."""
        spec1 = DesignSpecImpl(specs={})
        spec2 = DesignSpecImpl(specs={})

        merged = MergedDesignSpec(srcs=[spec1, spec2])

        assert merged.srcs == [spec1, spec2]

    def test_get_spec_precedence(self):
        """Test get_spec respects precedence (last spec wins)."""
        key = StrBindKey("duplicate")

        bind_spec1 = BindSpecImpl()
        bind_spec2 = BindSpecImpl(validator=Some(lambda k, v: FutureSuccess("ok")))

        spec1 = DesignSpecImpl(specs={key: bind_spec1})
        spec2 = DesignSpecImpl(specs={key: bind_spec2})

        # Create merged spec where spec2 comes after spec1
        merged = MergedDesignSpec(srcs=[spec1, spec2])

        # Should return bind_spec2 since spec2 comes after spec1
        result = merged.get_spec(key)
        assert result == Some(bind_spec2)

    def test_get_spec_searches_all_sources(self):
        """Test get_spec searches all source specs."""
        key1 = StrBindKey("key1")
        key2 = StrBindKey("key2")

        bind_spec1 = BindSpecImpl()
        bind_spec2 = BindSpecImpl()

        spec1 = DesignSpecImpl(specs={key1: bind_spec1})
        spec2 = DesignSpecImpl(specs={key2: bind_spec2})

        merged = MergedDesignSpec(srcs=[spec1, spec2])

        # Should find both keys
        assert merged.get_spec(key1) == Some(bind_spec1)
        assert merged.get_spec(key2) == Some(bind_spec2)
        assert merged.get_spec(StrBindKey("missing")) == Nothing

    def test_add_operator(self):
        """Test the + operator for MergedDesignSpec."""
        spec1 = DesignSpecImpl(specs={})
        spec2 = DesignSpecImpl(specs={})

        merged1 = MergedDesignSpec(srcs=[spec1])
        merged2 = merged1 + spec2

        assert isinstance(merged2, MergedDesignSpec)
        assert len(merged2.srcs) == 2
        assert merged2.srcs[0] is merged1
        assert merged2.srcs[1] is spec2

    def test_empty_merged_spec(self):
        """Test MergedDesignSpec with no sources."""
        merged = MergedDesignSpec(srcs=[])

        result = merged.get_spec(StrBindKey("any"))
        assert result == Nothing


class TestIntegration:
    """Integration tests for design spec implementations."""

    def test_complex_merging(self):
        """Test complex merging scenarios."""
        # Create several specs with overlapping keys
        key_a = StrBindKey("a")
        key_b = StrBindKey("b")
        key_c = StrBindKey("c")

        spec1 = DesignSpecImpl(specs={key_a: BindSpecImpl(), key_b: BindSpecImpl()})

        spec2 = DesignSpecImpl(
            specs={
                key_b: BindSpecImpl(
                    validator=Some(lambda k, v: FutureSuccess("spec2"))
                ),
                key_c: BindSpecImpl(),
            }
        )

        spec3 = DesignSpecImpl(
            specs={
                key_a: BindSpecImpl(validator=Some(lambda k, v: FutureSuccess("spec3")))
            }
        )

        # Create complex merged spec: (spec1 + spec2) + spec3
        merged = (spec1 + spec2) + spec3

        # Verify the structure
        assert isinstance(merged, MergedDesignSpec)
        assert len(merged.srcs) == 2
        assert isinstance(merged.srcs[0], MergedDesignSpec)
        assert merged.srcs[1] is spec3

        # Test precedence - last spec wins for duplicates
        result_a = merged.get_spec(key_a)
        assert result_a != Nothing
        # spec3 should win for key_a

        result_b = merged.get_spec(key_b)
        assert result_b != Nothing
        # spec2 should win for key_b

        result_c = merged.get_spec(key_c)
        assert result_c != Nothing
        # Only spec2 has key_c


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
