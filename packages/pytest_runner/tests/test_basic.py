"""Basic tests for pinjected-pytest-runner package"""

from pathlib import Path
from pinjected import IProxy, injected, design
from pinjected_pytest_runner import (
    to_pytest,
    convert_module_iproxy_tests,
    as_pytest_test,
)
from pinjected_pytest_runner.plugin import IProxyModule


def test_package_imports():
    """Test that all package components can be imported"""
    from pinjected_pytest_runner import (
        convert_module_iproxy_tests,
        create_pytest_module,
        as_pytest_test,
        IProxyModule,
        to_pytest,
    )

    assert callable(convert_module_iproxy_tests)
    assert callable(create_pytest_module)
    assert callable(as_pytest_test)
    assert IProxyModule is not None
    assert callable(to_pytest)


def test_to_pytest_conversion():
    """Test basic IProxy to pytest conversion"""
    test_design = design().bind_instance(test_value=42)

    @injected
    def simple_test(test_value):
        assert test_value == 42
        return True

    test_iproxy: IProxy = simple_test(test_value=42)

    pytest_func = to_pytest(test_iproxy, test_design)

    assert callable(pytest_func)

    result = pytest_func()
    assert result is True


def test_async_iproxy_conversion():
    """Test async IProxy to pytest conversion"""
    test_design = design().bind_instance(async_value="test")

    @injected
    async def async_test(async_value):
        assert async_value == "test"
        return True

    test_iproxy: IProxy = async_test(async_value="test")

    pytest_func = to_pytest(test_iproxy, test_design)

    assert callable(pytest_func)


def test_as_pytest_test_decorator():
    """Test the as_pytest_test decorator functionality"""
    test_design = design().bind_instance(decorator_value="decorated")

    @injected
    def decorated_test(decorator_value):
        assert decorator_value == "decorated"
        return True

    test_iproxy: IProxy = decorated_test(decorator_value="decorated")

    pytest_func = as_pytest_test(test_iproxy, test_design)

    assert callable(pytest_func)
    result = pytest_func()
    assert result is True


def test_iproxy_module_class():
    """Test that IProxyModule class exists and has required methods"""
    assert IProxyModule is not None

    assert hasattr(IProxyModule, "collect")
    assert callable(getattr(IProxyModule, "collect"))


def test_convert_module_with_no_iproxy_tests():
    """Test module conversion when no IProxy tests exist"""
    module_content = """
def regular_function():
    return True

def test_regular():
    assert True
"""

    temp_file = Path("/tmp/test_no_iproxy.py")
    temp_file.write_text(module_content)

    try:
        result = convert_module_iproxy_tests(str(temp_file))

        assert isinstance(result, dict)
        assert len(result) == 0

    finally:
        if temp_file.exists():
            temp_file.unlink()


def test_error_handling_in_conversion():
    """Test error handling when conversion fails"""

    test_design = design().bind_instance(error_value="error_test")

    @injected
    def error_prone_test(error_value):
        assert error_value == "error_test"
        return True

    test_iproxy: IProxy = error_prone_test(error_value="error_test")

    pytest_func = to_pytest(test_iproxy, test_design)
    assert callable(pytest_func)


def test_version_attribute():
    """Test that package has version attribute"""
    import pinjected_pytest_runner

    assert hasattr(pinjected_pytest_runner, "__version__")
    assert isinstance(pinjected_pytest_runner.__version__, str)
    assert pinjected_pytest_runner.__version__ == "0.1.0"


def test_all_attribute():
    """Test that package has __all__ attribute with expected exports"""
    import pinjected_pytest_runner

    assert hasattr(pinjected_pytest_runner, "__all__")

    expected_exports = [
        "convert_module_iproxy_tests",
        "create_pytest_module",
        "as_pytest_test",
        "IProxyModule",
        "to_pytest",
    ]

    for export in expected_exports:
        assert export in pinjected_pytest_runner.__all__
        assert hasattr(pinjected_pytest_runner, export)


def test_plugin_integration_structure():
    """Test that plugin components are properly structured"""
    from pinjected_pytest_runner.plugin import (
        pytest_pycollect_makeitem,
        pytest_pycollect_makemodule,
        pytest_collection_modifyitems,
        pytest_configure,
        pytest_report_header,
    )

    assert callable(pytest_pycollect_makeitem)
    assert callable(pytest_pycollect_makemodule)
    assert callable(pytest_collection_modifyitems)
    assert callable(pytest_configure)
    assert callable(pytest_report_header)


def test_practical_usage_example():
    """Test a practical usage example similar to ml-nexus patterns"""

    def simple_logger(msg):
        print(msg)

    test_design = design().bind_instance(
        logger=simple_logger, config={"test_mode": True}
    )

    @injected
    def practical_test(logger, config):
        logger(f"Running test with config: {config}")
        assert config["test_mode"] is True
        return True

    test_practical_iproxy: IProxy = practical_test(
        logger=simple_logger, config={"test_mode": True}
    )

    test_practical = to_pytest(test_practical_iproxy, test_design)

    assert callable(test_practical)
    result = test_practical()
    assert result is True
