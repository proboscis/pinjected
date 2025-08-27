"""Simple tests for v2/ainjected.py module."""

import pytest
from unittest.mock import Mock
from abc import ABC

from pinjected.v2.ainjected import AInjected, MappedAInjected


class TestAInjected:
    """Test the AInjected abstract base class."""

    def test_ainjected_is_abstract(self):
        """Test that AInjected is an abstract base class."""
        assert issubclass(AInjected, ABC)

        # Cannot instantiate directly
        with pytest.raises(TypeError):
            AInjected()

    def test_ainjected_is_generic(self):
        """Test that AInjected is generic."""
        assert hasattr(AInjected, "__parameters__")

    def test_complete_dependencies_property(self):
        """Test complete_dependencies combines dependencies."""

        class ConcreteAInjected(AInjected):
            @property
            def dependencies(self):
                return {"dep1", "dep2"}

            @property
            def dynamic_dependencies(self):
                return {"dyn1", "dyn2"}

            def get_provider(self):
                return lambda: None

        instance = ConcreteAInjected()
        complete = instance.complete_dependencies

        assert complete == {"dep1", "dep2", "dyn1", "dyn2"}

    def test_zip_static_method(self):
        """Test AInjected.zip static method."""
        mock1 = Mock(spec=AInjected)
        mock2 = Mock(spec=AInjected)

        result = AInjected.zip(mock1, mock2)

        # Should return ZippedAInjected instance
        assert result.__class__.__name__ == "ZippedAInjected"

    @pytest.mark.asyncio
    async def test_map_method(self):
        """Test AInjected.map method."""

        class ConcreteAInjected(AInjected):
            @property
            def dependencies(self):
                return set()

            @property
            def dynamic_dependencies(self):
                return set()

            def get_provider(self):
                async def provider():
                    return 42

                return provider

        instance = ConcreteAInjected()

        async def mapper(x):
            return x * 2

        mapped = instance.map(mapper)

        assert isinstance(mapped, MappedAInjected)

    def test_map_requires_coroutine_function(self):
        """Test that map requires a coroutine function."""

        class ConcreteAInjected(AInjected):
            @property
            def dependencies(self):
                return set()

            @property
            def dynamic_dependencies(self):
                return set()

            def get_provider(self):
                return lambda: None

        instance = ConcreteAInjected()

        # Non-async function should raise assertion error
        def sync_mapper(x):
            return x * 2

        with pytest.raises(AssertionError) as exc_info:
            instance.map(sync_mapper)

        assert "must be a coroutine function" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_dict_static_method(self):
        """Test AInjected.dict static method."""
        mock1 = Mock(spec=AInjected)
        mock2 = Mock(spec=AInjected)

        result = AInjected.dict(key1=mock1, key2=mock2)

        # Should return a mapped ZippedAInjected
        assert hasattr(result, "__class__")
        # The result should have map applied
        assert hasattr(result, "src") or hasattr(result, "targets")


class TestMappedAInjected:
    """Test the MappedAInjected class."""

    def test_mapped_ainjected_init(self):
        """Test MappedAInjected initialization."""
        mock_src = Mock(spec=AInjected)

        async def async_func(x):
            return x

        mapped = MappedAInjected(src=mock_src, f=async_func)

        assert hasattr(mapped, "src")
        assert hasattr(mapped, "f")

    def test_mapped_ainjected_is_ainjected(self):
        """Test that MappedAInjected is an AInjected."""
        assert issubclass(MappedAInjected, AInjected)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
