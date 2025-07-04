"""Runtime tests for decorator protocol feature (ARC-320)."""

import pytest
from typing import Protocol
from pinjected import injected, design
from pinjected.di.partially_injected import Partial


class DataFetcherProtocol(Protocol):
    """Protocol for data fetching."""

    def __call__(self, item_id: str) -> dict: ...


class ComputeProtocol(Protocol):
    """Protocol for computation."""

    def __call__(self, x: int, y: int) -> int: ...


def test_injected_returns_correct_runtime_type():
    """Test that @injected returns the correct runtime types."""

    # Test with protocol - should return a Partial object
    @injected(protocol=DataFetcherProtocol)
    def fetch_data(db, /, item_id: str) -> dict:
        return {"id": item_id, "data": f"from {db}"}

    # Runtime check: it should be a Partial
    assert isinstance(fetch_data, Partial)

    # Test without protocol - should also return Partial
    @injected
    def simple_func(dep, /, arg: str) -> str:
        return f"{dep}: {arg}"

    assert isinstance(simple_func, Partial)


def test_protocol_attribute_is_stored():
    """Test that the protocol information is stored on the function."""

    @injected(protocol=DataFetcherProtocol)
    def fetch_with_protocol(db, /, item_id: str) -> dict:
        return {"id": item_id}

    # Check if protocol is stored (this was added in the implementation)
    assert hasattr(fetch_with_protocol, "__protocol__")
    assert fetch_with_protocol.__protocol__ == DataFetcherProtocol


def test_protocol_with_multiple_dependencies():
    """Test protocol with multiple injected dependencies."""

    @injected(protocol=ComputeProtocol)
    def compute(multiplier, offset, /, x: int, y: int) -> int:
        return (x + y) * multiplier + offset

    di = design(multiplier=2, offset=10, compute=compute)

    graph = di.to_graph()
    compute_func = graph["compute"]

    # Test the computation
    result = compute_func(3, 4)
    assert result == (3 + 4) * 2 + 10  # = 24


def test_nested_protocol_dependencies():
    """Test using protocol-typed functions as dependencies of other functions."""

    @injected(protocol=DataFetcherProtocol)
    def fetcher(db, /, item_id: str) -> dict:
        return {"id": item_id, "value": len(item_id) * 10}

    @injected(protocol=ComputeProtocol)
    def calculator(base, /, x: int, y: int) -> int:
        return base + x * y

    @injected
    def process(
        fetcher: DataFetcherProtocol,
        calculator: ComputeProtocol,
        /,
        item_id: str,
        x: int,
        y: int,
    ) -> dict:
        data = fetcher(item_id)
        computed = calculator(x, y)
        return {"item": data, "result": computed + data["value"]}

    di = design(
        db="test_db", base=100, fetcher=fetcher, calculator=calculator, process=process
    )

    graph = di.to_graph()
    process_func = graph["process"]

    result = process_func("test", 5, 3)
    # fetcher("test") returns {"id": "test", "value": 40}
    # calculator(5, 3) returns 100 + 5*3 = 115
    # Final result: {"item": {"id": "test", "value": 40}, "result": 115 + 40 = 155}
    assert result == {"item": {"id": "test", "value": 40}, "result": 155}


def test_protocol_error_handling():
    """Test error cases with protocol parameter."""

    # Test that string dependencies don't support protocol
    with pytest.raises(
        TypeError, match="Protocol parameter is not supported for string dependencies"
    ):
        injected("some_dep", protocol=DataFetcherProtocol)

    # Test invalid target type
    with pytest.raises(TypeError, match="Invalid target type"):
        injected(123)  # Numbers are not valid targets


def test_protocol_with_class():
    """Test @injected with protocol on a class."""

    class ServiceProtocol(Protocol):
        def process(self, data: str) -> str: ...

    @injected
    class MyService:
        def __init__(self, config, /):
            self.config = config

        def process(self, data: str) -> str:
            return f"{self.config}: {data}"

    di = design(config="prod", MyService=MyService)

    graph = di.to_graph()
    service = graph["MyService"]()
    assert service.process("test") == "prod: test"


def test_async_protocol_runtime():
    """Test async functions with protocol at runtime."""
    import asyncio
    from pinjected.v2.async_resolver import AsyncResolver

    class AsyncServiceProtocol(Protocol):
        async def __call__(self, data: str) -> dict: ...

    @injected(protocol=AsyncServiceProtocol)
    async def async_service(prefix, /, data: str) -> dict:
        # Simulate async operation
        await asyncio.sleep(0.001)
        return {"prefix": prefix, "data": data, "processed": True}

    di = design(prefix="async", async_service=async_service)

    async def run_test():
        resolver = AsyncResolver(di)
        service = await resolver.provide("async_service")
        result = await service("test_data")
        assert result == {"prefix": "async", "data": "test_data", "processed": True}

    asyncio.run(run_test())


if __name__ == "__main__":
    test_injected_returns_correct_runtime_type()
    test_protocol_attribute_is_stored()
    test_protocol_with_multiple_dependencies()
    test_nested_protocol_dependencies()
    test_protocol_error_handling()
    test_protocol_with_class()
    test_async_protocol_runtime()
    print("All runtime tests passed!")

