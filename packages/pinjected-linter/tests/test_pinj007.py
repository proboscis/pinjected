"""Test PINJ007: Instance function runtime dependencies."""

import ast
from pathlib import Path
from pinjected_linter.rules.pinj007_instance_runtime_dependencies import (
    PINJ007InstanceRuntimeDependencies,
)
from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj007_detects_parameters():
    """Test that PINJ007 detects @instance functions with parameters."""
    source = """
from pinjected import instance

@instance
def database_connection(host: str, port: int):
    # Bad - @instance should not have parameters
    return Database(host=host, port=port)

@instance
def api_client(base_url: str, timeout: int = 30):
    # Bad - even with defaults
    return APIClient(base_url=base_url, timeout=timeout)

@instance
def service_factory(config: dict):
    # Bad - single parameter
    return Service(**config)

@instance
def complex_provider(
    env: str,
    debug: bool = False,
    options: dict = None
):
    # Bad - multiple parameters
    return ComplexService(env=env, debug=debug, options=options)
"""

    rule = PINJ007InstanceRuntimeDependencies()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect 4 violations
    assert len(violations) == 4

    for violation in violations:
        assert violation.rule_id == "PINJ007"
        assert "should not accept any runtime parameters" in violation.message
        assert violation.severity == Severity.ERROR
        assert "Remove all parameters" in violation.suggestion

    # Check specific functions
    messages = [v.message for v in violations]
    assert any("database_connection" in msg for msg in messages)
    assert any("api_client" in msg for msg in messages)
    assert any("service_factory" in msg for msg in messages)
    assert any("complex_provider" in msg for msg in messages)


def test_pinj007_detects_varargs():
    """Test that PINJ007 detects @instance functions with *args and **kwargs."""
    source = """
from pinjected import instance

@instance
def flexible_factory(*args):
    # Bad - varargs
    return Factory(*args)

@instance
def config_provider(**kwargs):
    # Bad - keyword args
    return Config(**kwargs)

@instance
def ultra_flexible(*args, **kwargs):
    # Bad - both varargs and kwargs
    return Service(*args, **kwargs)

@instance
def mixed_params(base_path: str, *args, debug=False, **kwargs):
    # Bad - mixed parameter types
    return ComplexService(base_path, *args, debug=debug, **kwargs)
"""

    rule = PINJ007InstanceRuntimeDependencies()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect 4 violations
    assert len(violations) == 4

    for violation in violations:
        assert violation.rule_id == "PINJ007"
        assert "@instance function" in violation.message
        assert "accepts parameters" in violation.message


def test_pinj007_allows_parameterless():
    """Test that PINJ007 allows @instance functions without parameters."""
    source = """
from pinjected import instance

@instance
def database_connection():
    # Good - no parameters
    return Database(host="localhost", port=5432)

@instance
def logger():
    # Good - pure provider
    import logging
    return logging.getLogger(__name__)

@instance
def config():
    # Good - returns configuration
    return {
        "api_url": "https://api.example.com",
        "timeout": 30,
        "retries": 3
    }

@instance
async def async_client():
    # Good - async instance without params
    client = AsyncHTTPClient()
    await client.initialize()
    return client

@instance
def complex_service():
    # Good - complex construction but no params
    cache = InMemoryCache()
    validator = DataValidator()
    processor = DataProcessor(cache=cache, validator=validator)
    return Service(processor=processor)
"""

    rule = PINJ007InstanceRuntimeDependencies()
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


def test_pinj007_ignores_non_instance():
    """Test that PINJ007 ignores non-@instance functions."""
    source = """
from pinjected import injected

# Regular function with params - OK
def create_connection(host: str, port: int):
    return Connection(host, port)

# @injected with params - OK  
@injected
def process_data(validator, transformer, /, data: dict):
    if validator.validate(data):
        return transformer.transform(data)
    return None

# Class method - OK
class Factory:
    def create(self, config: dict):
        return Product(**config)

# Other decorator - OK
@some_decorator
def decorated_function(x: int, y: int):
    return x + y
"""

    rule = PINJ007InstanceRuntimeDependencies()
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


def test_pinj007_detects_positional_only():
    """Test that PINJ007 detects positional-only parameters."""
    source = """
from pinjected import instance

@instance
def service_with_posonly(config, /, debug=False):
    # Bad - has positional-only parameter
    return Service(config=config, debug=debug)

@instance
def provider(a, b, /):
    # Bad - multiple positional-only
    return Provider(a=a, b=b)
"""

    rule = PINJ007InstanceRuntimeDependencies()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect violations
    assert len(violations) == 2

    for violation in violations:
        assert violation.rule_id == "PINJ007"
        assert "accepts parameters" in violation.message


def test_pinj007_detects_keyword_only():
    """Test that PINJ007 detects keyword-only parameters."""
    source = """
from pinjected import instance

@instance
def service_with_kwonly(*, host: str, port: int):
    # Bad - has keyword-only parameters
    return Service(host=host, port=port)

@instance
def provider(*, config: dict = None):
    # Bad - keyword-only with default
    return Provider(config=config or {})
"""

    rule = PINJ007InstanceRuntimeDependencies()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect violations
    assert len(violations) == 2

    for violation in violations:
        assert violation.rule_id == "PINJ007"
        assert "accepts parameters" in violation.message


if __name__ == "__main__":
    test_pinj007_detects_parameters()
    test_pinj007_detects_varargs()
    test_pinj007_allows_parameterless()
    test_pinj007_ignores_non_instance()
    test_pinj007_detects_positional_only()
    test_pinj007_detects_keyword_only()
    print("All PINJ007 tests passed!")
