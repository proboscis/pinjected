"""Tests for @injected decorator functionality with Protocol support."""

import pytest
from typing import Protocol
from pinjected import injected, instance, design


# Define test protocols
class GreeterProtocol(Protocol):
    def __call__(self, name: str) -> str: ...


class CalculatorProtocol(Protocol):
    def __call__(self, a: int, b: int) -> int: ...


class FormatterProtocol(Protocol):
    def __call__(self, text: str, uppercase: bool = False) -> str: ...


def test_injected_basic_with_protocol():
    """Test basic @injected functionality with Protocol."""

    @instance
    def greeting_template():
        return "Hello, {name}!"

    @injected(protocol=GreeterProtocol)
    def greet(greeting_template, /, name: str) -> str:
        return greeting_template.format(name=name)

    d = design()
    g = d.to_graph()

    # @injected returns a value that can be provided by the graph
    # No need to assert specific type

    # Resolve the function
    greet_func = g.provide(greet)
    assert callable(greet_func)

    # Call with runtime argument
    result = greet_func("Alice")
    assert result == "Hello, Alice!"


def test_injected_slash_separator():
    """Test the / separator for dependency vs runtime args."""

    @instance
    def multiplier():
        return 10

    @injected(protocol=CalculatorProtocol)
    def multiply(multiplier, /, a: int, b: int) -> int:
        # multiplier is injected, a and b are runtime args
        return multiplier * a * b

    d = design()
    g = d.to_graph()

    multiply_func = g.provide(multiply)
    result = multiply_func(2, 3)
    assert result == 60  # 10 * 2 * 3


def test_injected_with_multiple_dependencies():
    """Test @injected with multiple injected dependencies."""

    @instance
    def prefix():
        return "LOG:"

    @instance
    def suffix():
        return "[END]"

    @injected(protocol=FormatterProtocol)
    def format_message(prefix, suffix, /, text: str, uppercase: bool = False) -> str:
        message = f"{prefix} {text} {suffix}"
        return message.upper() if uppercase else message

    d = design()
    g = d.to_graph()

    formatter = g.provide(format_message)
    assert formatter("Hello") == "LOG: Hello [END]"
    assert formatter("Hello", uppercase=True) == "LOG: HELLO [END]"


def test_injected_calling_other_injected():
    """Test @injected functions calling other @injected functions."""

    class DataFetcherProtocol(Protocol):
        def __call__(self, id: str) -> dict: ...

    class DataProcessorProtocol(Protocol):
        def __call__(self, data: dict) -> str: ...

    class CompleteHandlerProtocol(Protocol):
        def __call__(self, id: str) -> str: ...

    @injected(protocol=DataFetcherProtocol)
    def fetch_data(database, /, id: str) -> dict:
        # Simulate fetching from database
        return {"id": id, "value": f"data_{id}"}

    @injected(protocol=DataProcessorProtocol)
    def process_data(logger, /, data: dict) -> str:
        # Process the data
        return f"Processed: {data['value']}"

    @injected(protocol=CompleteHandlerProtocol)
    def handle_request(
        fetch_data: DataFetcherProtocol,  # Must declare as dependency with Protocol type
        process_data: DataProcessorProtocol,  # Must declare as dependency with Protocol type
        /,
        id: str,
    ) -> str:
        # Call other @injected functions (building AST, not executing)
        data = fetch_data(id)  # No await needed - building AST
        result = process_data(data)
        return result

    @instance
    def database():
        return "mock_database"

    @instance
    def logger():
        return "mock_logger"

    d = design()
    g = d.to_graph()

    handler = g.provide(handle_request)
    result = handler("123")
    assert result == "Processed: data_123"


def test_injected_without_protocol_warning():
    """Test that @injected works without protocol but it's not recommended."""

    @injected  # No protocol - not recommended but should work
    def simple_func(config, /, name: str) -> str:
        return f"{config}: {name}"

    d = design(config="CONFIG")
    g = d.to_graph()

    func = g.provide(simple_func)
    assert func("test") == "CONFIG: test"


def test_injected_with_default_runtime_args():
    """Test @injected with default values for runtime arguments."""

    @injected(protocol=FormatterProtocol)
    def format_with_defaults(template, /, text: str, uppercase: bool = False) -> str:
        result = template.format(text=text)
        return result.upper() if uppercase else result

    d = design(template="[{text}]")
    g = d.to_graph()

    formatter = g.provide(format_with_defaults)

    # Use default uppercase=False
    assert formatter("hello") == "[hello]"

    # Override default
    assert formatter("hello", uppercase=True) == "[HELLO]"


def test_injected_error_handling():
    """Test error propagation in @injected functions."""

    class ErrorHandlerProtocol(Protocol):
        def __call__(self, value: int) -> int: ...

    @injected(protocol=ErrorHandlerProtocol)
    def may_fail(threshold, /, value: int) -> int:
        if value > threshold:
            raise ValueError(f"Value {value} exceeds threshold {threshold}")
        return value * 2

    d = design(threshold=10)
    g = d.to_graph()

    func = g.provide(may_fail)

    # Should work for valid values
    assert func(5) == 10

    # Should raise for invalid values
    with pytest.raises(ValueError, match="Value 15 exceeds threshold 10"):
        func(15)


def test_injected_vs_instance_difference():
    """Test the key difference between @instance and @injected."""

    @instance
    def instance_value():
        return "I am a value"

    @injected(protocol=GreeterProtocol)
    def injected_function(prefix, /, name: str) -> str:
        return f"{prefix} {name}"

    d = design(prefix="Hello")
    g = d.to_graph()

    # @instance provides a value directly
    assert g.provide(instance_value) == "I am a value"

    # @injected provides a function
    func = g.provide(injected_function)
    assert callable(func)
    assert func("World") == "Hello World"


def test_injected_with_kwargs():
    """Test @injected with keyword arguments."""

    class KwargsHandlerProtocol(Protocol):
        def __call__(self, **kwargs) -> dict: ...

    @injected(protocol=KwargsHandlerProtocol)
    def handle_kwargs(prefix, /, **kwargs) -> dict:
        return {f"{prefix}_{k}": v for k, v in kwargs.items()}

    d = design(prefix="processed")
    g = d.to_graph()

    handler = g.provide(handle_kwargs)
    result = handler(foo="bar", baz=42)
    assert result == {"processed_foo": "bar", "processed_baz": 42}


def test_injected_class_constructor():
    """Test using injected() function with class constructors."""

    # For classes, we need to define a factory function with slash separator
    @injected
    def create_user_service(database, cache, /, user_id: str, active: bool = True):
        class UserService:
            def __init__(self):
                self.database = database
                self.cache = cache
                self.user_id = user_id
                self.active = active

            def get_info(self):
                return f"User {self.user_id} (active={self.active})"

        return UserService()

    @instance
    def database():
        return "mock_db"

    @instance
    def cache():
        return "mock_cache"

    d = design()
    g = d.to_graph()

    # Get the injectable factory
    user_factory = g.provide(create_user_service)

    # Create instances with runtime args
    user1 = user_factory("user123")
    assert user1.get_info() == "User user123 (active=True)"

    user2 = user_factory("user456", active=False)
    assert user2.get_info() == "User user456 (active=False)"


def test_injected_naming_convention():
    """Test naming conventions for @injected functions."""

    # Good examples - verb forms
    @injected(protocol=GreeterProtocol)
    def send_message(channel, /, message: str) -> str:
        return f"Sent to {channel}: {message}"

    @injected(protocol=CalculatorProtocol)
    def calculate_total(tax_rate, /, amount: int, quantity: int) -> int:
        return int((amount * quantity) * (1 + tax_rate))

    d = design(channel="general", tax_rate=0.1)
    g = d.to_graph()

    sender = g.provide(send_message)
    assert sender("Hello") == "Sent to general: Hello"

    calculator = g.provide(calculate_total)
    assert calculator(100, 2) == 220  # 100 * 2 * 1.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
