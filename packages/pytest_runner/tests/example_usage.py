"""Example usage of pinjected-pytest-runner

This file demonstrates how to use the pytest runner with IProxy objects,
showing both automatic discovery and manual conversion patterns.
"""

from pinjected import IProxy, injected, design
from pinjected_pytest_runner.utils import to_pytest
from loguru import logger

__meta_design__ = design().bind_instance(
    logger=logger, config={"test_mode": True, "debug": False}
)


@injected
async def a_test_basic_functionality(logger, config):
    """Test basic functionality with dependency injection"""
    logger.info("Running basic functionality test")
    assert config["test_mode"] is True
    logger.info("Basic test passed")
    return True


test_basic_functionality: IProxy = a_test_basic_functionality()


@injected
async def a_test_complex_scenario(logger, config):
    """Test a more complex scenario with multiple assertions"""
    logger.info("Running complex scenario test")

    assert "test_mode" in config
    assert config["test_mode"] is True
    assert "debug" in config

    result = {"status": "success", "data": [1, 2, 3]}
    assert result["status"] == "success"
    assert len(result["data"]) == 3

    logger.info(f"Complex test completed with result: {result}")
    return result


test_complex_scenario: IProxy = a_test_complex_scenario()


@injected
async def a_test_error_handling(logger, config):
    """Test error handling capabilities"""
    logger.info("Running error handling test")

    try:
        assert config["test_mode"] is True
        logger.info("Error handling test passed")
        return True
    except Exception as e:
        logger.error(f"Unexpected error in test: {e}")
        raise


test_error_handling: IProxy = a_test_error_handling()


@injected
async def a_test_manual_conversion(logger):
    """Test that demonstrates manual conversion"""
    logger("Running manually converted test")
    assert True
    return True


manual_test_iproxy: IProxy = a_test_manual_conversion()
test_manual_conversion = to_pytest(manual_test_iproxy, __meta_design__)


@injected
async def a_test_custom_assertions(logger, config):
    """Test with custom business logic assertions"""
    logger.info("Running custom assertions test")

    user_data = {
        "id": 123,
        "name": "Test User",
        "active": True,
        "permissions": ["read", "write"],
    }

    assert user_data["id"] > 0
    assert len(user_data["name"]) > 0
    assert user_data["active"] is True
    assert "read" in user_data["permissions"]
    assert "write" in user_data["permissions"]

    logger.info(f"Custom assertions test passed for user: {user_data['name']}")
    return user_data


test_custom_assertions: IProxy = a_test_custom_assertions()
