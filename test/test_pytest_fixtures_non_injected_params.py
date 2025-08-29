"""
Test for pytest fixtures with runtime parameters.
"""

import pytest
import warnings
from typing import Protocol, TypedDict, Optional

from pinjected import design, injected
from pinjected.pytest_fixtures import register_fixtures_from_design

pytestmark = pytest.mark.skip(reason="pytest_fixtures.py is deprecated")

warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*register_fixtures_from_design.*"
)


class SegSample(TypedDict):
    """Sample data structure similar to user's use case."""

    id: str
    data: str


class ConverterProtocol(Protocol):
    def __call__(self, sample: dict) -> dict: ...


class SimpleConverterProtocol(Protocol):
    def __call__(self, prefix: str = "default") -> str: ...


class MultiParamConverterProtocol(Protocol):
    def __call__(self, sample: dict, extra: str, prefix: str = "test") -> dict: ...


class ConverterWithDepsProtocol(Protocol):
    def __call__(self, sample: dict) -> dict: ...


class ConverterWithPositionalDepsProtocol(Protocol):
    def __call__(self, user_id: str) -> dict: ...


# Type definitions for dependencies
class Logger(Protocol):
    def info(self, msg: str) -> None: ...


class Database(Protocol):
    def get(self, key: str) -> dict: ...


class Cache(Protocol):
    def get(self, key: str) -> Optional[dict]: ...
    def set(self, key: str, value: dict) -> None: ...


# CORRECT: For @injected with no dependencies, don't use /
# All parameters are runtime parameters
@injected(protocol=ConverterProtocol)
def convert_to_colored(sample: dict) -> dict:
    """Function that requires a runtime parameter."""
    return {"colored": True, **sample}


@injected(protocol=ConverterProtocol)
def convert_to_colored_sge(sample: SegSample) -> SegSample:
    """Function similar to user's actual use case."""
    return SegSample(id=sample["id"], data=f"colored_{sample['data']}")


@injected(protocol=SimpleConverterProtocol)
def simple_converter(prefix: str = "default") -> str:
    """Function with only optional parameters."""
    return f"{prefix}_converted"


@injected(protocol=MultiParamConverterProtocol)
def multi_param_converter(sample: dict, extra: str, prefix: str = "test") -> dict:
    """Function with multiple runtime parameters."""
    return {"prefix": prefix, "extra": extra, **sample}


# Example with dependencies before / and runtime params after /
@injected(protocol=ConverterWithDepsProtocol)
def converter_with_deps(logger: Logger, config: str, /, sample: dict) -> dict:
    """Function with both dependencies and runtime parameters."""
    logger.info(f"Processing with config: {config}")
    return {"processed": True, "config": config, **sample}


# Example showing the pattern: dependencies are positional-only (before /)
@injected(protocol=ConverterWithPositionalDepsProtocol)
def converter_with_positional_deps(
    database: Database, cache: Cache, logger: Logger, /, user_id: str
) -> dict:
    """Proper use of / separator - dependencies before, runtime params after."""
    # database, cache, logger are injected
    # user_id is a runtime parameter
    cached = cache.get(f"user:{user_id}")
    if cached:
        logger.info(f"Cache hit for {user_id}")
        return cached

    data = database.get(f"user:{user_id}")
    if data:
        cache.set(f"user:{user_id}", data)
    return data


# Register all converters
test_design = design(
    convert_to_colored=convert_to_colored,
    convert_to_colored_sge=convert_to_colored_sge,
    simple_converter=simple_converter,
    multi_param_converter=multi_param_converter,
    converter_with_deps=converter_with_deps,
    converter_with_positional_deps=converter_with_positional_deps,
    # Add some dependencies for testing
    logger=type("Logger", (), {"info": lambda self, msg: print(msg)})(),
    config="test_config",
    database=type("DB", (), {"get": lambda self, key: {"id": key, "name": "test"}})(),
    cache=type(
        "Cache",
        (),
        {
            "_data": {},
            "get": lambda self, key: self._data.get(key),
            "set": lambda self, key, value: setattr(
                self, "_data", {**self._data, key: value}
            ),
        },
    )(),
)

register_fixtures_from_design(test_design)


class TestNonInjectedParams:
    """Test fixtures that have runtime parameters."""

    @pytest.mark.asyncio
    async def test_converter_with_runtime_params(self, convert_to_colored):
        """Test that fixture returns a callable when runtime params are needed."""
        # The fixture should return a callable since it has runtime params
        assert callable(convert_to_colored)

        # We should be able to call it with the required parameter
        sample = {"name": "test", "value": 42}
        result = convert_to_colored(sample)

        assert result == {"colored": True, "name": "test", "value": 42}

    @pytest.mark.asyncio
    async def test_converter_sge_like_user_case(self, convert_to_colored_sge):
        """Test case similar to user's actual scenario with SegSample."""
        # Should return a callable
        assert callable(convert_to_colored_sge)

        # Call with required SegSample parameter
        sample: SegSample = {"id": "123", "data": "original"}
        result = convert_to_colored_sge(sample)

        assert result == {"id": "123", "data": "colored_original"}

    @pytest.mark.asyncio
    async def test_converter_with_no_required_params(self, simple_converter):
        """Test that fixture returns a callable even with only optional params."""
        # Should return a callable (not the result)
        assert callable(simple_converter)

        # Can call with default
        assert simple_converter() == "default_converted"

        # Can call with argument
        assert simple_converter("custom") == "custom_converted"

    @pytest.mark.asyncio
    async def test_converter_with_multiple_runtime_params(self, multi_param_converter):
        """Test function with multiple runtime parameters."""
        # Should return a callable
        assert callable(multi_param_converter)

        # Call with all required parameters
        sample = {"base": "data"}
        result = multi_param_converter(sample, "extra_value")

        assert result == {"prefix": "test", "extra": "extra_value", "base": "data"}

    @pytest.mark.asyncio
    async def test_converter_with_deps_and_runtime_params(self, converter_with_deps):
        """Test function that has both dependencies and runtime parameters."""
        # Should return a callable (dependencies are already injected)
        assert callable(converter_with_deps)

        # Call with runtime parameter
        sample = {"user": "test"}
        result = converter_with_deps(sample)

        assert result == {"processed": True, "config": "test_config", "user": "test"}

    @pytest.mark.asyncio
    async def test_converter_with_positional_deps(self, converter_with_positional_deps):
        """Test proper use of / separator with positional-only dependencies."""
        # Should return a callable
        assert callable(converter_with_positional_deps)

        # First call - cache miss
        result1 = converter_with_positional_deps("user123")
        assert result1 == {"id": "user:user123", "name": "test"}

        # Second call - cache hit
        result2 = converter_with_positional_deps("user123")
        assert result2 == {"id": "user:user123", "name": "test"}
