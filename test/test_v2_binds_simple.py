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

    def test_just_bind_provide_method(self):
        """Test provide method returns the impl."""

        async def impl(ctx, deps):
            return "result"

        bind = JustBind(impl=impl, deps=set())

        assert bind.provide() is impl

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

        assert bind.deps == set()

    @pytest.mark.asyncio
    async def test_bind_injected_provide(self):
        """Test provide method."""
        # Create a mock injected that has a_provide method
        mock_injected = Mock(spec=Injected)
        mock_injected.a_provide = AsyncMock(return_value="result")

        bind = BindInjected(src=mock_injected)
        provider = bind.provide()

        # Call the provider
        ctx = Mock(spec=ProvideContext)
        deps = {}
        result = await provider(ctx, deps)

        mock_injected.a_provide.assert_called_once_with(ctx, deps)
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
        bind = StrBind(impl="test_impl", deps={StrBindKey("dep1")})

        assert bind.impl == "test_impl"
        assert bind.deps == {StrBindKey("dep1")}

    def test_str_bind_provide_method(self):
        """Test provide method."""
        bind = StrBind(impl="my_impl", deps=set())

        assert bind.provide() == "my_impl"

    def test_str_bind_str_representation(self):
        """Test string representation."""
        bind = StrBind(impl="test_impl", deps={StrBindKey("dep1")})
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
        from pinjected.di.expr_util import Object, BinOp

        mock_evaled = Mock(spec=EvaledInjected)
        # Create AST with dependencies
        ast = BinOp(left=Object("dep1"), op="+", right=Object("dep2"))
        mock_evaled.ast = ast

        bind = ExprBind(src=mock_evaled)
        deps = bind.deps

        # Should extract "dep1" and "dep2" from the AST
        assert StrBindKey("dep1") in deps
        assert StrBindKey("dep2") in deps

    def test_expr_bind_deps_empty(self):
        """Test deps when AST has no Object nodes."""
        from pinjected.di.expr_util import Const

        mock_evaled = Mock(spec=EvaledInjected)
        mock_evaled.ast = Const(42)

        bind = ExprBind(src=mock_evaled)
        assert bind.deps == set()

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

        bind = MappedBind(src=mock_bind, mapper=mapper)

        assert bind.src is mock_bind
        assert bind.mapper is mapper

    def test_mapped_bind_deps_property(self):
        """Test deps property delegates to src."""
        mock_bind = Mock(spec=IBind)
        mock_bind.deps = {StrBindKey("dep1")}

        bind = MappedBind(src=mock_bind, mapper=lambda x: x)

        assert bind.deps == {StrBindKey("dep1")}

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

        bind = MappedBind(src=mock_bind, mapper=mapper)
        provider = bind.provide()

        # Call the provider
        ctx = Mock(spec=ProvideContext)
        deps = {}

        result = await provider(ctx, deps)

        # Should apply mapper to the result
        assert result == "RESULT"

    def test_mapped_bind_str_representation(self):
        """Test string representation."""
        mock_bind = Mock(spec=IBind)
        mock_bind.__str__ = Mock(return_value="MockBind")

        bind = MappedBind(src=mock_bind, mapper=lambda x: x)
        str_repr = str(bind)

        assert "MappedBind" in str_repr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
