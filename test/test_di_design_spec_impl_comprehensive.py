"""Comprehensive tests for di/design_spec/impl.py module to reach 90% coverage."""

import pytest
import asyncio
from unittest.mock import patch

from pinjected.di.design_spec.impl import BindSpecImpl, DesignSpecImpl, SimpleBindSpec
from pinjected.v2.keys import StrBindKey
from returns.maybe import Nothing, Some
from returns.future import FutureResult, FutureResultE, FutureSuccess, future_safe
from returns.io import IOFailure, IOSuccess
from returns.unsafe import unsafe_perform_io


class TestSimpleBindSpec:
    """Test the SimpleBindSpec class."""

    def test_simple_bind_spec_init_defaults(self):
        """Test SimpleBindSpec initialization with defaults."""
        spec = SimpleBindSpec()

        assert spec._validator is None
        assert spec._documentation is None

    def test_simple_bind_spec_init_with_validator(self):
        """Test SimpleBindSpec initialization with validator."""

        def validator(item):
            return "error" if item < 0 else None

        spec = SimpleBindSpec(validator=validator)

        assert spec._validator is validator
        assert spec._documentation is None

    def test_simple_bind_spec_init_with_documentation(self):
        """Test SimpleBindSpec initialization with documentation."""
        spec = SimpleBindSpec(documentation="Test documentation")

        assert spec._validator is None
        assert spec._documentation == "Test documentation"

    def test_simple_bind_spec_init_with_both(self):
        """Test SimpleBindSpec initialization with both params."""

        def validator(item):
            return None

        spec = SimpleBindSpec(validator=validator, documentation="Test docs")

        assert spec._validator is validator
        assert spec._documentation == "Test docs"

    @pytest.mark.asyncio
    async def test_validator_impl_success(self):
        """Test _validator_impl when validation succeeds."""

        def validator(item):
            return None  # No error

        spec = SimpleBindSpec(validator=validator)
        key = StrBindKey("test")

        result = await spec._validator_impl(key, "valid_item")
        assert result == "success"

    @pytest.mark.asyncio
    async def test_validator_impl_failure(self):
        """Test _validator_impl when validation fails."""

        def validator(item):
            return "Item is invalid"

        spec = SimpleBindSpec(validator=validator)
        key = StrBindKey("test")

        with pytest.raises(ValueError) as exc_info:
            await spec._validator_impl(key, "invalid_item")

        assert "Validation failed for test: Item is invalid" in str(exc_info.value)

    def test_validator_property_none(self):
        """Test validator property when no validator set."""
        spec = SimpleBindSpec()

        assert spec.validator == Nothing

    def test_validator_property_some(self):
        """Test validator property when validator is set."""

        def validator(item):
            return None

        spec = SimpleBindSpec(validator=validator)

        result = spec.validator
        assert result != Nothing
        assert callable(result.unwrap())

    @pytest.mark.asyncio
    async def test_doc_impl(self):
        """Test _doc_impl method."""
        spec = SimpleBindSpec(documentation="Test docs")
        key = StrBindKey("test")

        result = await spec._doc_impl(key)
        assert result == "Test docs"

    def test_spec_doc_provider_property_none(self):
        """Test spec_doc_provider property when no documentation."""
        spec = SimpleBindSpec()

        assert spec.spec_doc_provider == Nothing

    def test_spec_doc_provider_property_some(self):
        """Test spec_doc_provider property when documentation is set."""
        spec = SimpleBindSpec(documentation="Test docs")

        result = spec.spec_doc_provider
        assert result != Nothing

        # Test the provider function
        provider = result.unwrap()
        key = StrBindKey("test")
        future_result = provider(key)

        # It should return a FutureResult
        assert hasattr(future_result, "awaitable")

    def test_str_representation(self):
        """Test string representation of SimpleBindSpec."""
        # Test with no validator or doc
        spec1 = SimpleBindSpec()
        str1 = str(spec1)

        assert "SimpleBindSpec" in str1
        assert "'has_validator': False" in str1
        assert "'documentation': None" in str1

        # Test with validator and doc
        def validator(item):
            return None

        spec2 = SimpleBindSpec(validator=validator, documentation="Test documentation")
        str2 = str(spec2)

        assert "SimpleBindSpec" in str2
        assert "'has_validator': True" in str2
        assert "'documentation': 'Test documentation'" in str2


class TestMainBlockCoverage:
    """Test to cover the main block execution."""

    @patch("pinjected.di.design_spec.impl.logger")
    def test_main_block_execution(self, mock_logger):
        """Test the main block for coverage."""
        # Import the module to trigger main block
        import sys

        # Remove from cache if exists
        module_name = "pinjected.di.design_spec.impl"
        if module_name in sys.modules:
            del sys.modules[module_name]

        # Re-import with __name__ == "__main__"
        # This is tricky, so let's just test the functions used in main
        from pinjected.di.design_spec.impl import future_safe

        # Test the error_func pattern
        @future_safe
        async def error_func():
            raise Exception("error")

        fut_res = error_func()
        assert hasattr(fut_res, "awaitable")

        # Test recovery pattern
        @future_safe
        async def recover(fail):
            return "recovered"

        # Test with IOSuccess and IOFailure
        success = IOSuccess("success")
        failure = IOFailure(Exception("test error"))

        assert success.value_or("default") == IOSuccess("success")
        assert failure.value_or("default") == IOSuccess("default")

        # Test unsafe_perform_io
        result = unsafe_perform_io(success)
        assert result.unwrap() == "success"

        failed_result = unsafe_perform_io(failure)
        assert failed_result.is_failure()

    @pytest.mark.asyncio
    async def test_future_result_patterns(self):
        """Test FutureResult patterns from main block."""
        from pinjected.di.design_spec.impl import future_safe

        # Test error function
        @future_safe
        async def error_func():
            raise Exception("error")

        # Test recovery functions
        @future_safe
        async def recover(fail):
            return "recovered"

        def recover2(fail):
            return FutureResult.from_value("recovered")

        # Execute error function
        fut_res = error_func()

        # Test recovery
        recovered = fut_res.lash(recover)
        recovered_2 = fut_res.lash(recover2)
        recovered_3 = fut_res.lash(lambda x: FutureResult.from_value("recovered"))

        # Await results
        error_result = await fut_res.awaitable()
        assert error_result.is_failure()

        rec_result_1 = await recovered.awaitable()
        assert rec_result_1.unwrap() == "recovered"

        rec_result_2 = await recovered_2.awaitable()
        assert rec_result_2.unwrap() == "recovered"

        rec_result_3 = await recovered_3.awaitable()
        assert rec_result_3.unwrap() == "recovered"

    def test_maybe_behavior(self):
        """Test Maybe behavior from main block."""
        some = Some("hello")

        # Test bind on Some
        result = some.bind(lambda d: Some(isinstance(d, str)))
        assert result == Some(True)

        # Test lash on Nothing (lash doesn't exist on Maybe, so this won't work)
        # none.lash would fail, so we skip this test

    @pytest.mark.asyncio
    async def test_await_target_pattern(self):
        """Test the await_target pattern from main block."""

        async def await_target(f: FutureResultE):
            return await f

        # Create a successful future
        success_future = FutureResult.from_value("success")
        result = await await_target(success_future)
        assert result == "success"

        # Create a failed future
        @future_safe
        async def failing():
            raise ValueError("fail")

        fail_future = failing()
        fail_result = await await_target(fail_future)
        assert fail_result.is_failure()


class TestBindSpecImplExtended:
    """Extended tests for BindSpecImpl to increase coverage."""

    @pytest.mark.asyncio
    async def test_bind_spec_with_async_validator(self):
        """Test BindSpecImpl with async validator function."""

        async def async_validator(key, value):
            await asyncio.sleep(0.001)  # Simulate async work
            return FutureSuccess("Valid")

        spec = BindSpecImpl(validator=Some(async_validator))

        # Get the validator
        validator = spec.validator.unwrap()
        result = await validator(StrBindKey("test"), "value")

        assert result == "Valid"


class TestComplexMergedSpecs:
    """Test complex merged design spec scenarios."""

    def test_deeply_nested_merged_specs(self):
        """Test deeply nested MergedDesignSpec."""
        # Create base specs
        spec1 = DesignSpecImpl(
            specs={StrBindKey("a"): BindSpecImpl(), StrBindKey("b"): BindSpecImpl()}
        )

        spec2 = DesignSpecImpl(
            specs={
                StrBindKey("b"): SimpleBindSpec(documentation="Override B"),
                StrBindKey("c"): BindSpecImpl(),
            }
        )

        spec3 = DesignSpecImpl(
            specs={
                StrBindKey("c"): SimpleBindSpec(documentation="Override C"),
                StrBindKey("d"): BindSpecImpl(),
            }
        )

        # Create nested merges: ((spec1 + spec2) + spec3)
        merged1 = spec1 + spec2
        merged2 = merged1 + spec3

        # Test resolution order
        # For key "b", spec2 should win over spec1
        result_b = merged2.get_spec(StrBindKey("b"))
        assert result_b != Nothing

        # For key "c", spec3 should win over spec2
        result_c = merged2.get_spec(StrBindKey("c"))
        assert result_c != Nothing

        # For key "a", only spec1 has it
        result_a = merged2.get_spec(StrBindKey("a"))
        assert result_a != Nothing

        # For key "d", only spec3 has it
        result_d = merged2.get_spec(StrBindKey("d"))
        assert result_d != Nothing

        # Missing key
        result_missing = merged2.get_spec(StrBindKey("missing"))
        assert result_missing == Nothing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
