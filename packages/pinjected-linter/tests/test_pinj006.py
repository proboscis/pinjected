"""Test PINJ006: Instance function side effects."""

import ast
from pathlib import Path

from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.rules.pinj006_instance_side_effects import (
    PINJ006InstanceSideEffects,
)
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj006_detects_file_io():
    """Test that PINJ006 detects file I/O operations in @instance functions."""
    source = """
from pinjected import instance

@instance
def config_reader():
    # Bad - file I/O
    with open("config.json", "r") as f:
        data = f.read()
    return data

@instance
def file_writer():
    # Bad - file write
    open("output.txt", "w").write("data")
    return "done"

@instance
def path_reader():
    # Bad - Path.read_text() is also file I/O
    from pathlib import Path
    content = Path("file.txt").read_text()
    return content

# Regular function - file I/O is allowed
def regular_file_operation():
    with open("file.txt") as f:
        return f.read()
"""

    rule = PINJ006InstanceSideEffects()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect at least 3 violations
    assert len(violations) >= 3

    # Check violations
    for violation in violations:
        assert violation.rule_id == "PINJ006"
        assert "side effect" in violation.message
        assert violation.severity == Severity.ERROR


def test_pinj006_detects_print_and_logging():
    """Test that PINJ006 detects print and logging operations."""
    source = """
from pinjected import instance
import logging

logger = logging.getLogger(__name__)

@instance
def verbose_service():
    # Bad - print statement
    print("Creating service...")
    return Service()

@instance
def logging_factory():
    # Bad - logging operations
    logger.info("Creating factory")
    logger.debug("Debug info")
    logging.warning("This is a warning")
    return Factory()

@instance
def debug_component():
    # Bad - various logging patterns
    log.info("Creating component")
    self.logger.error("Error message")
    return Component()
"""

    rule = PINJ006InstanceSideEffects()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect multiple violations
    assert len(violations) >= 6

    # Check that print and logging were detected
    violation_messages = [v.message for v in violations]
    assert any("print" in msg for msg in violation_messages)
    assert any("logging" in msg for msg in violation_messages)


def test_pinj006_detects_network_calls():
    """Test that PINJ006 detects network operations."""
    source = """
from pinjected import instance
import requests
import urllib.request

@instance
def api_client():
    # Bad - network call
    response = requests.get("https://api.example.com")
    return APIClient(response.json())

@instance
def http_service():
    # Bad - various HTTP operations
    requests.post("https://api.example.com", data={})
    urllib.request.urlopen("https://example.com")
    return HTTPService()

@instance
async def async_client():
    # Bad - async network operations
    import aiohttp
    async with aiohttp.ClientSession() as session:
        await session.get("https://api.example.com")
    return AsyncClient()
"""

    rule = PINJ006InstanceSideEffects()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect network operations
    assert len(violations) >= 4

    # Check specific operations were detected
    violation_messages = [v.message for v in violations]
    assert any("requests" in msg for msg in violation_messages)


def test_pinj006_detects_environment_access():
    """Test that PINJ006 detects environment variable access."""
    source = """
from pinjected import instance
import os

@instance
def env_config():
    # Bad - environment variable access
    api_key = os.environ.get("API_KEY")
    db_url = os.environ["DATABASE_URL"]
    return Config(api_key=api_key, db_url=db_url)

@instance
def system_service():
    # Bad - OS operations
    os.system("ls -la")
    os.mkdir("new_directory")
    return SystemService()
"""

    rule = PINJ006InstanceSideEffects()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect environment and OS operations
    assert len(violations) >= 4

    violation_messages = [v.message for v in violations]
    assert any("environment" in msg for msg in violation_messages)
    assert any("os.system" in msg for msg in violation_messages)


def test_pinj006_allows_pure_construction():
    """Test that PINJ006 allows pure object construction."""
    source = """
from pinjected import instance
from typing import Dict

@instance
def database_config():
    # Good - pure construction
    return {
        "host": "localhost",
        "port": 5432,
        "database": "myapp"
    }

@instance
def service_factory():
    # Good - creating objects
    config = {"timeout": 30, "retries": 3}
    return ServiceImpl(config)

@instance
def complex_builder():
    # Good - complex but pure construction
    components = []
    for i in range(10):
        components.append(Component(id=i))
    return Container(components)

@instance
async def async_provider():
    # Good - async but pure
    return AsyncService(pool_size=10)
"""

    rule = PINJ006InstanceSideEffects()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should have no violations
    assert len(violations) == 0


def test_pinj006_ignores_non_instance_functions():
    """Test that PINJ006 ignores side effects in non-@instance functions."""
    source = """
from pinjected import injected

def regular_function():
    # OK - not @instance
    print("This is fine")
    with open("file.txt") as f:
        return f.read()

@injected
def workflow(logger, /):
    # OK - @injected can have side effects
    logger.info("Starting workflow")
    print("Processing...")
    return "result"

class Service:
    def method(self):
        # OK - class method
        print("Method called")
        return self.process()
"""

    rule = PINJ006InstanceSideEffects()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should have no violations
    assert len(violations) == 0


if __name__ == "__main__":
    test_pinj006_detects_file_io()
    test_pinj006_detects_print_and_logging()
    test_pinj006_detects_network_calls()
    test_pinj006_detects_environment_access()
    test_pinj006_allows_pure_construction()
    test_pinj006_ignores_non_instance_functions()
    print("All PINJ006 tests passed!")
