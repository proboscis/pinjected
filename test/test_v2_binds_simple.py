"""Simple tests for v2/binds.py module to improve coverage."""

import pytest
from unittest.mock import Mock, AsyncMock
from dataclasses import is_dataclass

from pinjected.v2.binds import (
    IBind,
    JustBind,
    BindInjected,
    StrBind,
    ExprBind,
    MappedBind,
)
from pinjected.v2.keys import StrBindKey
from pinjected.v2.provide_context import ProvideContext
from pinjected.di.injected import Injected, InjectedPure
from pinjected.di.app_injected import EvaledInjected


class TestJustBind:
    """Test the JustBind class."""

    def test_just_bind_is_dataclass(self):
        """Test that JustBind is a dataclass."""
        assert is_dataclass(JustBind)

    def test_just_bind_creation(self):
        """Test creating JustBind instance."""

        async def impl(ctx, deps):
            return "result"

        deps = {StrBindKey("dep1"), StrBindKey("dep2")}
        bind = JustBind(impl=impl, deps=deps)

        assert bind.impl is impl
        assert bind.deps == deps

    @pytest.mark.asyncio
    async def test_just_bind_provide_method(self):
        """Test provide method calls the impl."""

        async def impl(ctx, deps):
            return "result"

        bind = JustBind(impl=impl, deps=set())

        # Test that provide calls the implementation
        ctx = Mock(spec=ProvideContext)
        deps = {}
        result = await bind.provide(ctx, deps)

        assert result == "result"

    def test_just_bind_str_representation(self):
        """Test string representation."""

        async def my_impl(ctx, deps):
            return "result"

        bind = JustBind(impl=my_impl, deps={StrBindKey("dep1")})
        str_repr = str(bind)

        assert "JustBind" in str_repr
        assert "my_impl" in str_repr


class TestBindInjected:
    """Test the BindInjected class."""

    def test_bind_injected_is_dataclass(self):
        """Test that BindInjected is a dataclass."""
        assert is_dataclass(BindInjected)

    def test_bind_injected_creation(self):
        """Test creating BindInjected instance."""
        injected = InjectedPure("value")
        bind = BindInjected(src=injected)

        assert bind.src is injected

    def test_bind_injected_deps_property(self):
        """Test deps property returns empty set."""
        injected = InjectedPure("value")
        bind = BindInjected(src=injected)

        assert bind.dependencies == set()

    @pytest.mark.asyncio
    async def test_bind_injected_provide(self):
        """Test provide method."""
        # Create a mock injected that has dependencies and get_provider methods
        mock_injected = Mock(spec=Injected)
        mock_injected.dependencies.return_value = ["dep1", "dep2"]
        mock_injected.dynamic_dependencies.return_value = []

        async def mock_provider(dep1=None, dep2=None):
            return "result"

        mock_injected.get_provider.return_value = mock_provider

        bind = BindInjected(src=mock_injected)

        # Call the provider
        ctx = Mock(spec=ProvideContext)
        deps = {StrBindKey("dep1"): "value1", StrBindKey("dep2"): "value2"}
        result = await bind.provide(ctx, deps)

        assert result == "result"

    def test_bind_injected_str_representation(self):
        """Test string representation."""
        injected = InjectedPure("test_value")
        bind = BindInjected(src=injected)
        str_repr = str(bind)

        assert "BindInjected" in str_repr


class TestStrBind:
    """Test the StrBind class."""

    def test_str_bind_is_dataclass(self):
        """Test that StrBind is a dataclass."""
        assert is_dataclass(StrBind)

    def test_str_bind_creation(self):
        """Test creating StrBind instance."""

        async def test_impl(**kwargs):
            return "test_result"

        bind = StrBind(impl=test_impl, deps={"dep1"})

        assert bind.impl == test_impl
        assert bind.deps == {"dep1"}

    @pytest.mark.asyncio
    async def test_str_bind_provide_method(self):
        """Test provide method."""

        async def my_impl(**kwargs):
            return "result"

        bind = StrBind(impl=my_impl, deps=set())

        # Create mock context and deps
        ctx = Mock(spec=ProvideContext)
        deps = {}

        result = await bind.provide(ctx, deps)
        assert result == "result"

    def test_str_bind_str_representation(self):
        """Test string representation."""

        async def test_impl(**kwargs):
            return "result"

        bind = StrBind(impl=test_impl, deps={"dep1"})
        str_repr = str(bind)

        assert "StrBind" in str_repr
        assert "test_impl" in str_repr


class TestExprBind:
    """Test the ExprBind class."""

    def test_expr_bind_is_dataclass(self):
        """Test that ExprBind is a dataclass."""
        assert is_dataclass(ExprBind)

    def test_expr_bind_creation(self):
        """Test creating ExprBind instance."""
        # Create a mock EvaledInjected
        mock_evaled = Mock(spec=EvaledInjected)
        bind = ExprBind(src=mock_evaled)

        assert bind.src is mock_evaled

    def test_expr_bind_deps_property(self):
        """Test deps property extracts dependencies from AST."""
        mock_evaled = Mock(spec=EvaledInjected)
        # Mock the dependencies method to return expected dependencies
        mock_evaled.dependencies.return_value = ["dep1", "dep2"]
        mock_evaled.dynamic_dependencies.return_value = []

        bind = ExprBind(src=mock_evaled)
        deps = bind.dependencies

        # Should extract "dep1" and "dep2" from the AST
        assert StrBindKey("dep1") in deps
        assert StrBindKey("dep2") in deps

    def test_expr_bind_deps_empty(self):
        """Test deps when AST has no Object nodes."""
        # Use a simple mock since Const doesn't exist
        from unittest.mock import Mock

        mock_evaled = Mock(spec=EvaledInjected)
        mock_evaled.dependencies.return_value = []
        mock_evaled.dynamic_dependencies.return_value = []

        bind = ExprBind(src=mock_evaled)
        assert bind.dependencies == set()

    def test_expr_bind_str_representation(self):
        """Test string representation."""
        mock_evaled = Mock(spec=EvaledInjected)
        mock_evaled.ast = Mock()
        mock_evaled.ast.__str__ = Mock(return_value="test_ast")

        bind = ExprBind(src=mock_evaled)
        str_repr = str(bind)

        assert "ExprBind" in str_repr


class TestMappedBind:
    """Test the MappedBind class."""

    def test_mapped_bind_is_dataclass(self):
        """Test that MappedBind is a dataclass."""
        assert is_dataclass(MappedBind)

    def test_mapped_bind_creation(self):
        """Test creating MappedBind instance."""
        mock_bind = Mock(spec=IBind)

        def mapper(x):
            return x.upper()

        async def async_mapper(x):
            return mapper(x)

        bind = MappedBind(src=mock_bind, async_f=async_mapper)

        assert bind.src is mock_bind
        assert bind.async_f is async_mapper

    def test_mapped_bind_deps_property(self):
        """Test deps property delegates to src."""
        mock_bind = Mock(spec=IBind)
        mock_bind.dependencies = {StrBindKey("dep1")}
        mock_bind.dynamic_dependencies = set()

        async def async_identity(x):
            return x

        bind = MappedBind(src=mock_bind, async_f=async_identity)

        assert bind.dependencies == {StrBindKey("dep1")}

    @pytest.mark.asyncio
    async def test_mapped_bind_provide(self):
        """Test provide method applies mapper."""
        # Create a mock bind with provider
        mock_bind = Mock(spec=IBind)

        async def mock_provider(ctx, deps):
            return "result"

        mock_bind.provide.return_value = mock_provider

        # Create mapper that transforms the result
        def mapper(value):
            return value.upper()

        async def async_mapper(value):
            return mapper(value)

        bind = MappedBind(src=mock_bind, async_f=async_mapper)

        # Call the provider
        ctx = Mock(spec=ProvideContext)
        deps = {}

        # Set up mock_bind.provide to return "result"
        mock_bind.provide = AsyncMock(return_value="result")

        result = await bind.provide(ctx, deps)

        # Should apply mapper to the result
        assert result == "RESULT"

    def test_mapped_bind_str_representation(self):
        """Test string representation."""
        mock_bind = Mock(spec=IBind)
        mock_bind.__str__ = Mock(return_value="MockBind")

        async def async_identity(x):
            return x

        bind = MappedBind(src=mock_bind, async_f=async_identity)
        str_repr = str(bind)

        assert "MappedBind" in str_repr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
