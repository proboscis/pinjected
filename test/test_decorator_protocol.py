"""Test cases for decorator protocol feature (ARC-320)."""

import pytest
from typing import Protocol, Awaitable, overload, Literal
from pinjected import injected, design


# Define test protocols
class FetchUserDataProtocol(Protocol):
    """Protocol for fetching user data."""

    def __call__(self, user_id: str) -> dict: ...


class AsyncServiceProtocol(Protocol):
    """Protocol for async service."""

    async def __call__(self, request: dict) -> dict: ...


class ComplexServiceProtocol(Protocol):
    """Protocol with multiple signatures."""

    @overload
    def __call__(self, request: dict) -> dict: ...

    @overload
    def __call__(
        self, request: dict, *, async_mode: Literal[True]
    ) -> Awaitable[dict]: ...

    @overload
    def __call__(self, request: dict, *, async_mode: Literal[False]) -> dict: ...


class TestDecoratorProtocol:
    """Test suite for decorator protocol feature."""

    def test_basic_protocol_usage(self):
        """Test basic protocol parameter usage with @injected."""

        # Define a function with protocol
        @injected(protocol=FetchUserDataProtocol)
        def fetch_user_data(db, /, user_id: str) -> dict:
            return {"id": user_id, "name": f"User {user_id}", "db": db}

        # Create design with mock db
        di = design(db="mock_database", fetch_user_data=fetch_user_data)

        # Get the function from the graph
        graph = di.to_graph()
        fetch_func = graph["fetch_user_data"]

        # Verify it works
        result = fetch_func("123")
        assert result == {"id": "123", "name": "User 123", "db": "mock_database"}

        # Verify the type hint is available (this is the key part)
        # The actual implementation will need to expose this somehow
        # assert hasattr(fetch_func, '__protocol__')
        # assert fetch_func.__protocol__ == FetchUserDataProtocol

    def test_protocol_with_dependency_usage(self):
        """Test using a protocol-annotated function as a dependency."""

        @injected(protocol=FetchUserDataProtocol)
        def fetch_user_data(db, /, user_id: str) -> dict:
            return {"id": user_id, "name": f"User {user_id}"}

        @injected
        def process_user(
            fetch_user_data: FetchUserDataProtocol,  # Type hint should work
            /,
            user_id: str,
        ) -> str:
            user = fetch_user_data(user_id)
            return f"Processing {user['name']}"

        di = design(
            db="mock_db", fetch_user_data=fetch_user_data, process_user=process_user
        )

        graph = di.to_graph()
        process_func = graph["process_user"]
        result = process_func("456")
        assert result == "Processing User 456"

    @pytest.mark.asyncio
    async def test_async_protocol(self):
        """Test protocol with async function."""
        from pinjected.v2.async_resolver import AsyncResolver

        @injected(protocol=AsyncServiceProtocol)
        async def async_service(client, /, request: dict) -> dict:
            # Simulate async operation
            return {"response": f"Processed {request['data']}", "client": client}

        di = design(client="async_client", async_service=async_service)

        # Use AsyncResolver for async functions
        resolver = AsyncResolver(di)
        service = await resolver.provide("async_service")
        result = await service({"data": "test"})
        assert result == {"response": "Processed test", "client": "async_client"}

    def test_protocol_validation(self):
        """Test that protocol validation works correctly."""

        # This should work - function matches protocol
        @injected(protocol=FetchUserDataProtocol)
        def correct_fetch(db, /, user_id: str) -> dict:
            return {"id": user_id}

        # In a full implementation, we might want to validate at decoration time
        # that the function signature matches the protocol

        # For now, just verify the decorator doesn't break
        assert correct_fetch is not None

    def test_no_protocol_still_works(self):
        """Test that @injected without protocol parameter still works."""

        @injected
        def simple_function(dep, /, arg: str) -> str:
            return f"{dep}: {arg}"

        di = design(dep="dependency", simple_function=simple_function)

        graph = di.to_graph()
        func = graph["simple_function"]
        assert func("test") == "dependency: test"

    def test_protocol_with_instance_decorator(self):
        """Test protocol parameter with @instance decorator."""
        from pinjected import instance

        # Protocol for a logger
        class LoggerProtocol(Protocol):
            def info(self, message: str) -> None: ...

        # This test is for future consideration - @instance might also benefit
        # from protocol support, but it's not part of the current requirement
        @instance
        def logger(config, /):
            class Logger:
                def info(self, message: str) -> None:
                    print(f"[{config}] {message}")

            return Logger()

        di = design(config="INFO", logger=logger)

        graph = di.to_graph()
        log = graph["logger"]
        # Just verify it works - protocol support for @instance is not required yet
        assert hasattr(log, "info")
