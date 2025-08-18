"""Tests for pinjected/di/designed.py module."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from pinjected.di.designed import Designed, PureDesigned
from pinjected.di.proxiable import DelegatedVar


class TestDesigned:
    """Tests for Designed abstract class."""

    def test_from_data(self):
        """Test from_data static method."""
        mock_design = Mock()
        mock_injected = Mock()

        result = Designed.from_data(mock_design, mock_injected)

        assert isinstance(result, PureDesigned)
        assert result._design is mock_design
        assert result._internal_injected is mock_injected

    def test_bind_with_injected(self):
        """Test bind with Injected object."""
        from pinjected import Injected
        from pinjected.di.util import EmptyDesign

        mock_injected = MagicMock(spec=Injected)

        result = Designed.bind(mock_injected)

        assert isinstance(result, PureDesigned)
        # EmptyDesign is a singleton instance, not a type
        assert result._design is EmptyDesign
        assert result._internal_injected is mock_injected

    def test_bind_with_delegated_var(self):
        """Test bind with DelegatedVar object."""
        from pinjected.di.util import EmptyDesign

        # Create a mock DelegatedVar
        mock_var = MagicMock(spec=DelegatedVar)

        # Mock Injected at the import location inside the function
        with patch("pinjected.Injected") as mock_injected_class:
            mock_injected = Mock()
            mock_injected_class.ensure_injected.return_value = mock_injected

            result = Designed.bind(mock_var)

            assert isinstance(result, PureDesigned)
            assert result._design is EmptyDesign
            assert result._internal_injected is mock_injected
            mock_injected_class.ensure_injected.assert_called_once_with(mock_var)

    def test_bind_with_callable(self):
        """Test bind with callable object."""
        from pinjected.di.util import EmptyDesign
        from pinjected import Injected

        def test_func():
            return "test"

        # Use the real Injected class but mock its bind method
        with patch.object(Injected, "bind") as mock_bind:
            mock_injected_bound = Mock()
            mock_bind.return_value = mock_injected_bound

            # Also need to patch the recursive Designed.bind call
            original_bind = Designed.bind

            def mock_designed_bind(target):
                if target is mock_injected_bound:
                    return PureDesigned(EmptyDesign, mock_injected_bound)
                return original_bind(target)

            with patch.object(Designed, "bind", side_effect=mock_designed_bind):
                result = Designed.bind(test_func)

            assert isinstance(result, PureDesigned)
            assert result._design is EmptyDesign
            assert result._internal_injected is mock_injected_bound
            mock_bind.assert_called_once_with(test_func)

    def test_bind_with_invalid_type(self):
        """Test bind with invalid type raises TypeError."""
        with pytest.raises(TypeError, match="target must be a subclass of Injected"):
            Designed.bind(123)  # Not a valid type

    def test_override(self):
        """Test override method."""
        # Create a designed instance
        mock_design1 = Mock()
        mock_design2 = Mock()
        mock_combined_design = Mock()
        mock_injected = Mock()

        # Set up the addition operation
        mock_design1.__add__ = Mock(return_value=mock_combined_design)

        designed = PureDesigned(mock_design1, mock_injected)

        result = designed.override(mock_design2)

        assert isinstance(result, PureDesigned)
        assert result._design is mock_combined_design
        assert result._internal_injected is mock_injected
        mock_design1.__add__.assert_called_once_with(mock_design2)

    def test_map(self):
        """Test map method."""
        # Create a designed instance
        mock_design = Mock()
        mock_injected = Mock()
        mock_mapped_injected = Mock()

        # Set up the map operation
        mock_injected.map = Mock(return_value=mock_mapped_injected)

        designed = PureDesigned(mock_design, mock_injected)

        # Mock Designed.bind to return a new PureDesigned
        with patch.object(Designed, "bind") as mock_bind:
            mock_new_designed = Mock(spec=PureDesigned)
            mock_new_designed.override = Mock(return_value="final_result")
            mock_bind.return_value = mock_new_designed

            def test_mapper(x):
                return x * 2

            result = designed.map(test_mapper)

            assert result == "final_result"
            mock_injected.map.assert_called_once_with(test_mapper)
            mock_bind.assert_called_once_with(mock_mapped_injected)
            mock_new_designed.override.assert_called_once_with(mock_design)

    def test_zip(self):
        """Test zip static method."""
        # Create multiple designed instances
        mock_design1 = Mock()
        mock_design2 = Mock()
        mock_injected1 = Mock()
        mock_injected2 = Mock()

        designed1 = PureDesigned(mock_design1, mock_injected1)
        designed2 = PureDesigned(mock_design2, mock_injected2)

        # Mock the required imports and operations
        with (
            patch("pinjected.EmptyDesign") as mock_empty_design,
            patch("pinjected.Injected") as mock_injected_class,
        ):
            # Set up design addition
            mock_empty_design.__add__ = Mock(side_effect=lambda x: x)
            mock_design1.__add__ = Mock(return_value="combined_design")

            # Set up Injected.mzip
            mock_zipped = Mock()
            mock_injected_class.mzip.return_value = mock_zipped

            # Mock Designed.bind
            with patch.object(Designed, "bind") as mock_bind:
                mock_bound = Mock(spec=PureDesigned)
                mock_bound.override = Mock(return_value="final_result")
                mock_bind.return_value = mock_bound

                result = Designed.zip(designed1, designed2)

                assert result == "final_result"
                mock_injected_class.mzip.assert_called_once_with(
                    mock_injected1, mock_injected2
                )
                mock_bind.assert_called_once_with(mock_zipped)
                mock_bound.override.assert_called_once()

    def test_proxy_property(self):
        """Test proxy property."""
        mock_design = Mock()
        mock_injected = Mock()

        designed = PureDesigned(mock_design, mock_injected)

        with patch("pinjected.di.app_designed.designed_proxy") as mock_proxy:
            mock_proxy.return_value = "proxy_result"

            result = designed.proxy

            assert result == "proxy_result"
            mock_proxy.assert_called_once_with(designed)


class TestPureDesigned:
    """Tests for PureDesigned class."""

    def test_pure_designed_creation(self):
        """Test creating PureDesigned instance."""
        mock_design = Mock()
        mock_injected = Mock()

        designed = PureDesigned(mock_design, mock_injected)

        assert designed._design is mock_design
        assert designed._internal_injected is mock_injected

    def test_design_property(self):
        """Test design property."""
        mock_design = Mock()
        mock_injected = Mock()

        designed = PureDesigned(mock_design, mock_injected)

        assert designed.design is mock_design

    def test_internal_injected_property(self):
        """Test internal_injected property."""
        mock_design = Mock()
        mock_injected = Mock()

        designed = PureDesigned(mock_design, mock_injected)

        assert designed.internal_injected is mock_injected


class TestDesignedAbstractMethods:
    """Test that Designed is properly abstract."""

    def test_cannot_instantiate_designed(self):
        """Test that Designed cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Designed()

    def test_concrete_subclass_must_implement_methods(self):
        """Test that concrete subclass must implement abstract methods."""

        class IncompleteDesigned(Designed):
            pass

        with pytest.raises(TypeError):
            IncompleteDesigned()

    def test_concrete_subclass_with_methods(self):
        """Test that concrete subclass with all methods can be instantiated."""

        class CompleteDesigned(Designed):
            @property
            def design(self):
                return Mock()

            @property
            def internal_injected(self):
                return Mock()

        # Should not raise
        instance = CompleteDesigned()
        assert instance.design is not None
        assert instance.internal_injected is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
