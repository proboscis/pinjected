import pytest

from pinjected.di.decorators import injected, instance
from pinjected.di.bindings import bind_instance


class MockService:
    def __init__(self):
        self.calls = []
    
    def record(self, value: str) -> str:
        self.calls.append(value)
        return f"Recorded: {value}"


@instance
def provide_default_service() -> MockService:
    return MockService()


@injected
def use_service(service: MockService) -> str:
    return service.record("test_value")


def test_injected_function_resolves_dependencies():
    # Default resolution
    result = use_service()
    assert result == "Recorded: test_value"
    
    # Override with custom instance
    custom_service = MockService()
    with bind_instance(MockService, custom_service):
        result = use_service()
        assert result == "Recorded: test_value"
        assert len(custom_service.calls) == 1
        assert custom_service.calls[0] == "test_value"


@injected
def nested_function(service: MockService) -> str:
    return inner_function()


@injected
def inner_function(service: MockService) -> str:
    return service.record("inner_call")


def test_nested_injected_functions():
    service = MockService()
    with bind_instance(MockService, service):
        result = nested_function()
        assert result == "Recorded: inner_call"
        assert len(service.calls) == 1