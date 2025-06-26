"""
Test for injected_pytest with DelegatedVar[Design]/IProxy[Design] support
"""

import pytest
from pinjected import Injected, design, instance
from pinjected.di.iproxy import IProxy
from pinjected.test import injected_pytest


class MockLogger:
    """Mock logger for testing"""

    def __init__(self):
        self.logs = []

    def info(self, message):
        self.logs.append(message)
        return message


class MockService:
    """Mock service for testing"""

    def __init__(self, logger):
        self.logger = logger

    def do_something(self):
        self.logger.info("Service did something")
        return "Service result"


# Define service provider using @instance
@instance
def service(logger):
    return MockService(logger)


def test_injected_pytest_with_iproxy():
    """Test @injected_pytest with IProxy[Design]"""
    # Create a design with dependencies
    base_design = design(
        logger=Injected.pure(MockLogger()),
        service=service,  # Use the @instance decorated function
    )

    # Create an IProxy[Design]
    design_proxy = IProxy(base_design)

    @injected_pytest(design_proxy)
    def test_func(service):
        return service.do_something()

    # Run the test
    result = test_func()

    assert result == "Service result"
    # Verify the logger was called
    logger_instance = base_design.provide("logger")
    assert logger_instance.logs == ["Service did something"]


def test_injected_pytest_with_delegated_var():
    """Test @injected_pytest with DelegatedVar[Design] from Injected.proxy"""
    # Create a design
    base_design = design(
        logger=Injected.pure(MockLogger()),
        service=service,  # Use the @instance decorated function
    )

    # Create a DelegatedVar[Design] using Injected.proxy
    design_proxy = Injected.pure(base_design).proxy

    @injected_pytest(design_proxy)
    def test_func(service):
        result = service.do_something()
        return result

    # Run the test
    result = test_func()

    assert result == "Service result"
    logger_instance = base_design.provide("logger")
    assert logger_instance.logs == ["Service did something"]


def test_injected_pytest_proxy_with_empty_design():
    """Test that proxy works with EmptyDesign"""
    from pinjected import EmptyDesign

    # Create proxy of EmptyDesign
    empty_proxy = IProxy(EmptyDesign)

    @injected_pytest(empty_proxy)
    def test_func():
        return "Success with empty design proxy"

    result = test_func()
    assert result == "Success with empty design proxy"


def test_injected_pytest_with_complex_proxy_expression():
    """Test with a more complex proxy expression"""
    # Create two designs
    design1 = design(value1=Injected.pure("value1"))
    design2 = design(value2=Injected.pure("value2"))

    # Create a proxy that will resolve to combined design
    # This tests that any expression that resolves to Design works
    combined_proxy = Injected.pure(design1 + design2).proxy

    @injected_pytest(combined_proxy)
    def test_func(value1, value2):
        return f"{value1},{value2}"

    result = test_func()
    assert result == "value1,value2"


def test_backward_compatibility_with_design():
    """Ensure regular Design instances still work"""
    test_design = design(
        logger=Injected.pure(MockLogger()),
        service=service,  # Use the @instance decorated function
    )

    @injected_pytest(test_design)
    def test_func(service):
        return service.do_something()

    result = test_func()
    assert result == "Service result"


def test_backward_compatibility_no_parentheses():
    """Ensure no-parentheses usage still works"""

    @injected_pytest
    def test_func():
        return "No parentheses success"

    result = test_func()
    assert result == "No parentheses success"


def test_backward_compatibility_empty_parentheses():
    """Ensure empty parentheses usage still works"""

    @injected_pytest()
    def test_func():
        return "Empty parentheses success"

    result = test_func()
    assert result == "Empty parentheses success"


def test_invalid_proxy_type_error():
    """Test that invalid proxy types raise appropriate errors"""
    # Create a proxy that doesn't resolve to Design
    invalid_proxy = Injected.pure("not a design").proxy

    @injected_pytest(invalid_proxy)
    def test_func():
        return "Should not reach here"

    # Should raise TypeError when executing
    with pytest.raises(
        TypeError, match="DelegatedVar must resolve to a Design instance"
    ):
        test_func()


def test_async_test_function_with_proxy():
    """Test that async test functions work with proxy"""
    test_design = design(value=Injected.pure("async value"))
    design_proxy = IProxy(test_design)

    @injected_pytest(design_proxy)
    async def test_func(value):
        # Simulate async operation
        import asyncio

        await asyncio.sleep(0.001)
        return f"Async: {value}"

    result = test_func()
    assert result == "Async: async value"


def test_proxy_resolution_with_module_design():
    """Test that proxy resolution works with module-level designs"""
    # This test verifies that the proxy is resolved in the context
    # of the final_design from module hierarchy
    base_design = design(test_value=Injected.pure("from proxy"))
    proxy = IProxy(base_design)

    @injected_pytest(proxy)
    def test_func(test_value):
        # If module designs are present, they should be combined
        # with the proxy-resolved design
        return test_value

    result = test_func()
    assert result == "from proxy"


def test_complex_service_dependencies_with_proxy():
    """Test complex service dependencies resolved through proxy"""

    # Alternative approach using class with underscore prefix
    class ServiceWithAutoInject:
        def __init__(self, _logger, name: str):
            # _logger is auto-injected
            self.logger = _logger
            self.name = name

        def process(self):
            self.logger.info(f"Processing in {self.name}")
            return f"Processed by {self.name}"

    # Create factory using injected()
    from pinjected import injected

    new_service = injected(ServiceWithAutoInject)

    # Create design with proxy
    test_design = design(
        logger=Injected.pure(MockLogger()), my_service=new_service(name="TestService")
    )
    proxy = IProxy(test_design)

    @injected_pytest(proxy)
    def test_func(my_service):
        return my_service.process()

    result = test_func()
    assert result == "Processed by TestService"

    # Verify logger was called
    logger_instance = test_design.provide("logger")
    assert "Processing in TestService" in logger_instance.logs[0]
