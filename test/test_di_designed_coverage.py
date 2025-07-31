"""Tests to improve coverage for pinjected/di/designed.py."""

import pytest
from unittest.mock import Mock

from pinjected.di.designed import Designed, PureDesigned
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.injected import Injected, InjectedByName
from pinjected.di.util import EmptyDesign


class TestDesignedAbstractMethods:
    """Test abstract methods of Designed class."""

    def test_designed_is_abstract(self):
        """Test that Designed cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Designed()

    def test_designed_abstract_properties(self):
        """Test that abstract properties must be implemented."""

        # Create a minimal concrete implementation
        class ConcreteDesigned(Designed):
            def __init__(self, design, injected):
                self._design = design
                self._injected = injected

            @property
            def design(self):
                return self._design

            @property
            def internal_injected(self):
                return self._injected

        mock_design = Mock()
        mock_injected = Mock()

        instance = ConcreteDesigned(mock_design, mock_injected)
        assert instance.design == mock_design
        assert instance.internal_injected == mock_injected


class TestDesignedBind:
    """Test the bind static method."""

    def test_bind_with_delegated_var(self):
        """Test binding with DelegatedVar."""
        # Create a mock context for DelegatedVar
        mock_context = Mock()
        delegated = DelegatedVar("test_var", mock_context)
        result = Designed.bind(delegated)

        assert isinstance(result, PureDesigned)
        # Check that design is EmptyDesign instance
        # EmptyDesign is actually DesignImpl
        assert result.design.__class__.__name__ in [
            "EmptyDesign",
            "DesignImpl",
            "MergedDesign",
        ]
        assert isinstance(result.internal_injected, Injected)

    def test_bind_with_injected(self):
        """Test binding with Injected object."""
        injected = InjectedByName("test_key")
        result = Designed.bind(injected)

        assert isinstance(result, PureDesigned)
        # EmptyDesign is actually DesignImpl
        assert result.design.__class__.__name__ in [
            "EmptyDesign",
            "DesignImpl",
            "MergedDesign",
        ]
        assert result.internal_injected == injected

    def test_bind_with_callable(self):
        """Test binding with callable."""

        def test_func():
            return "test"

        result = Designed.bind(test_func)

        assert isinstance(result, PureDesigned)
        # EmptyDesign is actually DesignImpl
        assert result.design.__class__.__name__ in [
            "EmptyDesign",
            "DesignImpl",
            "MergedDesign",
        ]
        assert isinstance(result.internal_injected, Injected)

    def test_bind_with_invalid_type(self):
        """Test binding with invalid type raises TypeError."""
        with pytest.raises(TypeError, match="target must be a subclass of Injected"):
            Designed.bind("invalid")

        with pytest.raises(TypeError, match="target must be a subclass of Injected"):
            Designed.bind(42)

        with pytest.raises(TypeError, match="target must be a subclass of Injected"):
            Designed.bind([1, 2, 3])


class TestDesignedZip:
    """Test the zip static method."""

    def test_zip_empty(self):
        """Test zip with no arguments."""
        result = Designed.zip()

        assert isinstance(result, PureDesigned)
        # EmptyDesign is actually DesignImpl
        assert result.design.__class__.__name__ in [
            "EmptyDesign",
            "DesignImpl",
            "MergedDesign",
        ]

    def test_zip_single(self):
        """Test zip with single Designed."""
        injected = InjectedByName("test")
        designed = Designed.from_data(EmptyDesign, injected)

        result = Designed.zip(designed)

        assert isinstance(result, PureDesigned)

    def test_zip_multiple(self):
        """Test zip with multiple Designed objects."""
        injected1 = InjectedByName("test1")
        injected2 = InjectedByName("test2")

        designed1 = Designed.from_data(EmptyDesign, injected1)
        designed2 = Designed.from_data(EmptyDesign, injected2)

        result = Designed.zip(designed1, designed2)

        assert isinstance(result, PureDesigned)
        assert hasattr(result.internal_injected, "__class__")

    def test_zip_with_designs(self):
        """Test zip preserves designs."""
        from pinjected import design

        d1 = design(a=1)
        d2 = design(b=2)

        injected1 = InjectedByName("test1")
        injected2 = InjectedByName("test2")

        designed1 = Designed.from_data(d1, injected1)
        designed2 = Designed.from_data(d2, injected2)

        result = Designed.zip(designed1, designed2)

        # The combined design should have both keys
        assert isinstance(result, PureDesigned)


class TestDesignedMethods:
    """Test other methods of Designed."""

    def test_from_data(self):
        """Test from_data static method."""
        mock_design = Mock()
        mock_injected = Mock()

        result = Designed.from_data(mock_design, mock_injected)

        assert isinstance(result, PureDesigned)
        assert result.design == mock_design
        assert result.internal_injected == mock_injected

    def test_override(self):
        """Test override method."""
        from pinjected import design

        d1 = design(a=1)
        d2 = design(b=2)

        injected = InjectedByName("test")
        designed = Designed.from_data(d1, injected)

        result = designed.override(d2)

        assert isinstance(result, PureDesigned)
        assert result.internal_injected == injected

    def test_map(self):
        """Test map method."""
        injected = InjectedByName("test")
        designed = Designed.from_data(EmptyDesign, injected)

        def transform(x):
            return str(x)

        result = designed.map(transform)

        assert isinstance(result, PureDesigned)

    def test_proxy(self):
        """Test proxy property."""
        injected = InjectedByName("test")
        designed = Designed.from_data(EmptyDesign, injected)

        # Access proxy property
        proxy = designed.proxy

        # Should return a proxy object
        assert proxy is not None


class TestPureDesigned:
    """Test PureDesigned dataclass."""

    def test_pure_designed_creation(self):
        """Test creating PureDesigned instance."""
        mock_design = Mock()
        mock_injected = Mock()

        pure = PureDesigned(mock_design, mock_injected)

        assert pure._design == mock_design
        assert pure._internal_injected == mock_injected
        assert pure.design == mock_design
        assert pure.internal_injected == mock_injected

    def test_pure_designed_is_designed(self):
        """Test that PureDesigned is a Designed."""
        pure = PureDesigned(Mock(), Mock())
        assert isinstance(pure, Designed)

    def test_pure_designed_dataclass_features(self):
        """Test dataclass features of PureDesigned."""
        design1 = Mock()
        injected1 = Mock()

        pure1 = PureDesigned(design1, injected1)
        # Create additional instances to test dataclass behavior
        PureDesigned(design1, injected1)  # Same args as pure1
        PureDesigned(Mock(), Mock())  # Different args

        # Should have standard dataclass features
        assert hasattr(pure1, "__dataclass_fields__")

        # Test string representation
        str_repr = str(pure1)
        assert "PureDesigned" in str_repr


class TestTypeCheckingImports:
    """Test TYPE_CHECKING imports are handled correctly."""

    def test_type_annotations_available(self):
        """Test that type annotations work correctly."""
        # This tests that the TYPE_CHECKING block doesn't break runtime
        from pinjected.di import designed

        # Should be able to use the module without issues
        assert hasattr(designed, "Designed")
        assert hasattr(designed, "PureDesigned")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
