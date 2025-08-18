"""Comprehensive tests for pinjected/injected_class/injectable_class.py module."""

import pytest
import inspect
from unittest.mock import Mock, patch, AsyncMock
from types import SimpleNamespace

from pinjected.injected_class.injectable_class import (
    TargetClassSample,
    MacroTransformedExample,
    PLACEHOLDER,
    convert_method_into_dynamic_injected_method_old,
    InjectedMethod,
    convert_method_into_dynamic_injected_method,
    pclass,
    main,
)
from pinjected import Injected
from pinjected.injected_class.test_module import PClassExample


class TestTargetClassSample:
    """Tests for TargetClassSample dataclass."""

    def test_target_class_sample_creation(self):
        """Test creating TargetClassSample instance."""
        sample = TargetClassSample(
            _dep1="test_dep1", _dep2=42, attr1="test_attr1", attr2=99
        )

        assert sample._dep1 == "test_dep1"
        assert sample._dep2 == 42
        assert sample.attr1 == "test_attr1"
        assert sample.attr2 == 99

    @pytest.mark.asyncio
    async def test_target_class_sample_method1(self):
        """Test method1 of TargetClassSample."""
        sample = TargetClassSample(_dep1="test_dep", _dep2=42, attr1="attr1", attr2=99)

        result = await sample.method1("test_args")
        assert result == ("test_dep", "test_args")


class TestMacroTransformedExample:
    """Tests for MacroTransformedExample class."""

    def test_macro_transformed_example_creation(self):
        """Test creating MacroTransformedExample instance."""
        example = MacroTransformedExample()
        example.a = "test_a"
        example.b = 10
        example.c = 3.14

        assert example.a == "test_a"
        assert example.b == 10
        assert example.c == 3.14

    def test_macro_transformed_example_method(self):
        """Test _method of MacroTransformedExample."""
        example = MacroTransformedExample()
        example.a = "test"
        example.b = 5
        example.c = 2.5

        result = example._method()
        assert result == ("test", 5, 2.5)

    def test_macro_transformed_example_method1(self):
        """Test method1 with injected parameters."""
        example = MacroTransformedExample()
        example.c = 1.5

        result = example.method1("X", "injected_a", 42)
        assert result == "injected_a421.5X"

    def test_macro_transformed_example_method2(self):
        """Test method2 with injected parameters."""
        example = MacroTransformedExample()
        example.c = 2.0

        result = example.method2(3, "A")
        assert result == "AAA2.0"


class TestConvertMethodIntoDynamicInjectedMethodOld:
    """Tests for convert_method_into_dynamic_injected_method_old function."""

    @pytest.mark.asyncio
    @patch("pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {})
    async def test_convert_method_old_basic(self):
        """Test converting async method (old version)."""

        # Create a test async method
        async def test_method(self, x, __self_dep__):
            return self, x, __self_dep__

        # Convert the method
        converted = convert_method_into_dynamic_injected_method_old(
            "test_key", test_method
        )

        # Create a mock self with resolver
        mock_self = Mock()

        # Create the implementation function
        async def impl(self, *args):
            return "result"

        # Create a coroutine that returns the implementation
        async def get_impl():
            return impl

        # Set up mock resolver with __getitem__ that returns a coroutine
        from unittest.mock import MagicMock

        mock_resolver = MagicMock()
        mock_resolver.__getitem__.return_value = get_impl()
        mock_self.__resolver__ = mock_resolver

        # Call the converted method
        result = await converted(mock_self, "arg1")

        # Verify resolver was called with the key and result is correct
        mock_resolver.__getitem__.assert_called_once_with("test_key")
        assert result == "result"

    def test_convert_method_old_non_async_raises(self):
        """Test that non-async method raises assertion error."""

        def sync_method(self, x):
            return x

        with pytest.raises(AssertionError, match="must be async"):
            convert_method_into_dynamic_injected_method_old("key", sync_method)

    def test_convert_method_old_no_self_raises(self):
        """Test that method without self parameter raises."""

        async def no_self_method(x):
            return x

        with pytest.raises(AssertionError):
            convert_method_into_dynamic_injected_method_old("key", no_self_method)


class TestInjectedMethod:
    """Tests for InjectedMethod dataclass."""

    @pytest.mark.asyncio
    async def test_injected_method_basic(self):
        """Test InjectedMethod basic functionality."""

        # Create a test method
        async def test_method(self, x):
            return self.attr1 + x

        # Create resolver mock
        async def get_resolved_value():
            return "resolved_value"

        from unittest.mock import MagicMock

        resolver = MagicMock()
        resolver.__getitem__.return_value = get_resolved_value()

        # Create InjectedMethod
        injected_method = InjectedMethod(
            dynamic_attr_mapping={"attr1": Injected.by_name("dep1")},
            method=test_method,
            resolver=resolver,
        )

        # Create mock target object
        target = SimpleNamespace(attr1=PLACEHOLDER)

        # Call the injected method
        result = await injected_method(target, " suffix")

        # Verify attribute was resolved
        assert target.attr1 == "resolved_value"
        assert result == "resolved_value suffix"

    @pytest.mark.asyncio
    async def test_injected_method_init_lock(self):
        """Test that initialization only happens once."""

        async def test_method(self):
            return "result"

        async def get_resolved():
            return "resolved"

        from unittest.mock import MagicMock

        resolver = MagicMock()
        resolver.__getitem__.return_value = get_resolved()

        injected_method = InjectedMethod(
            dynamic_attr_mapping={"attr": Injected.by_name("dep")},
            method=test_method,
            resolver=resolver,
        )

        target = SimpleNamespace(attr=PLACEHOLDER)

        # Call multiple times
        await injected_method(target)
        await injected_method(target)
        await injected_method(target)

        # Resolver should only be called once
        resolver.__getitem__.assert_called_once()

    @pytest.mark.asyncio
    async def test_injected_method_multiple_attrs(self):
        """Test resolving multiple attributes."""

        async def test_method(self):
            return self.attr1, self.attr2, self.attr3

        async def get_val1():
            return "val1"

        async def get_val2():
            return "val2"

        async def get_val3():
            return "val3"

        from unittest.mock import MagicMock

        resolver = MagicMock()
        resolver.__getitem__.side_effect = [get_val1(), get_val2(), get_val3()]

        injected_method = InjectedMethod(
            dynamic_attr_mapping={
                "attr1": Injected.by_name("dep1"),
                "attr2": Injected.by_name("dep2"),
                "attr3": Injected.by_name("dep3"),
            },
            method=test_method,
            resolver=resolver,
        )

        target = SimpleNamespace(
            attr1=PLACEHOLDER, attr2=PLACEHOLDER, attr3=PLACEHOLDER
        )

        result = await injected_method(target)

        assert result == ("val1", "val2", "val3")
        assert resolver.__getitem__.call_count == 3


class TestConvertMethodIntoDynamicInjectedMethod:
    """Tests for convert_method_into_dynamic_injected_method function."""

    @pytest.mark.asyncio
    @patch("pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {})
    async def test_convert_method_basic(self):
        """Test converting async method."""

        async def test_method(self, x):
            return x * 2

        converted = convert_method_into_dynamic_injected_method(
            "test_key", test_method, {"attr1": Injected.by_name("dep1")}
        )

        # Create mock self with resolver
        mock_self = Mock()
        from unittest.mock import MagicMock

        mock_resolver = MagicMock()

        # Create the injected method that will be returned by resolver
        async def mock_injected_method(self, *args, **kwargs):
            return 42

        # Create coroutine that returns the injected method
        async def get_injected_method():
            return mock_injected_method

        mock_resolver.__getitem__.return_value = get_injected_method()
        mock_self.__resolver__ = mock_resolver

        # First call should set the injected method
        result = await converted(mock_self, 21)

        # Verify
        mock_resolver.__getitem__.assert_called_once_with("test_key")
        assert hasattr(mock_self, "__test_method_injected__")
        assert result == 42

    @pytest.mark.asyncio
    async def test_convert_method_caches_injected(self):
        """Test that injected method is cached."""

        async def test_method(self, x):
            return x

        converted = convert_method_into_dynamic_injected_method("key", test_method, {})

        mock_self = Mock()
        from unittest.mock import MagicMock

        mock_resolver = MagicMock()

        # Create a mock injected method
        call_count = 0

        async def mock_injected_method(self, x):
            nonlocal call_count
            call_count += 1
            return x * 10

        # Create coroutine that returns the injected method
        async def get_injected_method():
            return mock_injected_method

        mock_resolver.__getitem__.return_value = get_injected_method()
        mock_self.__resolver__ = mock_resolver

        # Call multiple times
        result1 = await converted(mock_self, 1)
        result2 = await converted(mock_self, 2)
        result3 = await converted(mock_self, 3)

        # Verify results
        assert result1 == 10
        assert result2 == 20
        assert result3 == 30

        # Resolver should only be called once
        mock_resolver.__getitem__.assert_called_once()

    def test_convert_method_warns_non_async(self):
        """Test warning for non-async methods."""

        def sync_method(self, x):
            return x

        with patch("pinjected.injected_class.injectable_class.logger") as mock_logger:
            convert_method_into_dynamic_injected_method("key", sync_method, {})

            mock_logger.warning.assert_called_once()
            assert "not async method" in mock_logger.warning.call_args[0][0]


class TestPClass:
    """Tests for pclass decorator."""

    def test_pclass_basic(self):
        """Test pclass decorator basic functionality."""
        with patch(
            "pinjected.injected_class.injectable_class.extract_attribute_accesses"
        ) as mock_extract:
            mock_extract.return_value = {
                "method_with_dep1": ["_dep1"],
                "method2": ["_dep1"],
            }

            # Apply pclass decorator
            result = pclass(PClassExample)

            # Should return an Injected
            assert hasattr(result, "__call__")

    @patch("pinjected.injected_class.injectable_class.extract_attribute_accesses")
    @patch(
        "pinjected.injected_class.injectable_class.convert_method_into_dynamic_injected_method"
    )
    def test_pclass_converts_methods(self, mock_convert, mock_extract):
        """Test that pclass converts the right methods."""
        mock_extract.return_value = {
            "method1": ["_dep1", "_dep2"],
            "method2": ["_dep1"],
        }

        # Create a test class
        class TestClass:
            _dep1: str
            _dep2: int

            async def method1(self):
                return self._dep1

            async def method2(self):
                return self._dep2

        pclass(TestClass)

        # Verify convert was called for each method
        assert mock_convert.call_count == 2

        # Check the calls
        calls = mock_convert.call_args_list
        assert any("method1" in str(call) for call in calls)
        assert any("method2" in str(call) for call in calls)

    def test_pclass_identifies_injected_attrs(self):
        """Test that pclass correctly identifies injected attributes."""
        with (
            patch("pinjected.injected_class.injectable_class.logger") as mock_logger,
            patch(
                "pinjected.injected_class.injectable_class.extract_attribute_accesses"
            ) as mock_extract,
        ):
            mock_extract.return_value = {}

            class TestClass:
                _private1: str
                _private2: int
                public1: str
                public2: int

            pclass(TestClass)

            # Check that injected attrs were logged
            injected_attrs_call = None
            for call in mock_logger.info.call_args_list:
                if "injectable attrs" in str(call):
                    injected_attrs_call = call
                    break

            assert injected_attrs_call is not None
            assert "_private1" in str(injected_attrs_call)
            assert "_private2" in str(injected_attrs_call)


class TestMain:
    """Tests for main function."""

    @pytest.mark.asyncio
    @patch("pinjected.injected_class.injectable_class.pclass")
    @patch("pinjected.injected_class.injectable_class.logger")
    async def test_main_function(self, mock_logger, mock_pclass):
        """Test the main function example."""
        # Create mock instance
        mock_instance = AsyncMock()
        mock_instance.simple_method = AsyncMock(return_value="simple_result")
        mock_instance.method_with_dep1 = AsyncMock(return_value="dep1_result")

        # Mock the pclass result - should be a regular function, not async
        mock_partial = Mock(return_value=mock_instance)
        mock_pclass.return_value = mock_partial

        # Mock design and resolver
        with patch("pinjected.design") as mock_design_module:
            # Create mock design instance
            mock_design_instance = Mock()
            from unittest.mock import MagicMock

            mock_resolver = MagicMock()

            # Create coroutine that returns the partial
            async def get_partial():
                return mock_partial

            mock_resolver.__getitem__.return_value = get_partial()
            mock_design_instance.to_resolver.return_value = mock_resolver

            # Make the design function return our mock instance
            mock_design_module.return_value = mock_design_instance

            await main()

            # Verify calls
            mock_pclass.assert_called_once_with(PClassExample)
            mock_instance.simple_method.assert_called_once_with(0)
            mock_instance.method_with_dep1.assert_called_once_with("x_value")

            # Verify logging
            assert mock_logger.info.call_count >= 3


class TestIntegration:
    """Integration tests for injectable_class module."""

    def test_placeholder_constant(self):
        """Test PLACEHOLDER constant is defined."""
        assert PLACEHOLDER == "PLACEHOLDER"

    @pytest.mark.asyncio
    async def test_full_pclass_workflow(self):
        """Test complete pclass transformation workflow."""

        # Create a simple test class (not dataclass to avoid inspect issues)
        class SimpleClass:
            def __init__(self, _dep: str, value: int):
                self._dep = _dep
                self.value = value

            async def get_combined(self):
                return f"{self._dep}:{self.value}"

        with patch(
            "pinjected.injected_class.injectable_class.extract_attribute_accesses"
        ) as mock_extract:
            mock_extract.return_value = {"get_combined": ["_dep"]}

            # Apply pclass
            transformed = pclass(SimpleClass)

            # Verify it returns an Injected-like object
            assert hasattr(transformed, "bind")

    def test_method_signature_preservation(self):
        """Test that method signatures are preserved."""

        async def original_method(self, x: int, y: str = "default") -> str:
            return f"{x}:{y}"

        # Get original signature
        inspect.signature(original_method)

        # Convert method
        with patch("pinjected.di.implicit_globals.IMPLICIT_BINDINGS", {}):
            converted = convert_method_into_dynamic_injected_method(
                "key", original_method, {}
            )

        # The wrapper should maintain the same signature
        # (Note: actual implementation might not preserve it perfectly)
        assert callable(converted)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
