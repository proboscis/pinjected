"""Test PINJ005: Instance function imports."""

import ast
from pathlib import Path

from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.rules.pinj005_instance_imports import PINJ005InstanceImports
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj005_detects_imports_in_instance():
    """Test that PINJ005 detects import statements inside @instance functions."""
    source = """
from pinjected import instance
import os  # Module-level import is fine

@instance
def database_connection():
    import sqlite3  # Bad - import inside @instance
    return sqlite3.connect(":memory:")

@instance
def redis_client():
    from redis import Redis  # Bad - from-import inside @instance
    return Redis()

@instance
async def async_service():
    import asyncio  # Bad - import inside async @instance
    from aiohttp import ClientSession  # Bad - from-import inside async @instance
    return ClientSession()

# Regular function - imports are allowed
def regular_function():
    import json  # OK - not @instance
    return json.dumps({})
"""

    rule = PINJ005InstanceImports()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect 4 violations (2 in database_connection, 1 in redis_client, 2 in async_service)
    assert len(violations) == 4

    # Check violations
    for violation in violations:
        assert violation.rule_id == "PINJ005"
        assert "import" in violation.message
        assert "@instance function" in violation.message
        assert violation.severity == Severity.ERROR

    # Check specific functions mentioned
    violation_messages = [v.message for v in violations]
    assert any("database_connection" in msg for msg in violation_messages)
    assert any("redis_client" in msg for msg in violation_messages)
    assert any("async_service" in msg for msg in violation_messages)


def test_pinj005_allows_module_level_imports():
    """Test that PINJ005 allows imports at module level."""
    source = """
from pinjected import instance
import os
from pathlib import Path
import json
from typing import Dict, List

@instance
def file_handler():
    # Using imported modules is fine
    return Path(os.getcwd())

@instance
def json_parser():
    # Using imported functions is fine
    return lambda data: json.loads(data)

@instance
def type_annotated_function() -> Dict[str, List[str]]:
    # Using imported types is fine
    return {"keys": ["value1", "value2"]}
"""

    rule = PINJ005InstanceImports()
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


def test_pinj005_handles_nested_functions():
    """Test that PINJ005 handles nested functions correctly."""
    source = """
from pinjected import instance

@instance
def service_factory():
    def helper_function():
        import subprocess  # Still bad - inside @instance function scope
        return subprocess
    
    # Even worse - direct import in @instance
    import threading
    
    return helper_function

def outer_function():
    @instance
    def inner_instance():
        from collections import defaultdict  # Bad - import in nested @instance
        return defaultdict(list)
    
    return inner_instance
"""

    rule = PINJ005InstanceImports()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect 3 violations
    assert len(violations) == 3

    # Check that we caught imports in both regular and nested @instance functions
    violation_messages = [v.message for v in violations]
    assert any("service_factory" in msg for msg in violation_messages)
    assert any("inner_instance" in msg for msg in violation_messages)


def test_pinj005_ignores_non_instance_functions():
    """Test that PINJ005 ignores functions without @instance decorator."""
    source = """
from pinjected import injected

def regular_function():
    import time  # OK - not @instance
    return time.time()

@injected
def injected_function(logger, /):
    import datetime  # OK - @injected, not @instance
    return datetime.datetime.now()

class MyClass:
    def method(self):
        import random  # OK - class method
        return random.random()
"""

    rule = PINJ005InstanceImports()
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
    test_pinj005_detects_imports_in_instance()
    test_pinj005_allows_module_level_imports()
    test_pinj005_handles_nested_functions()
    test_pinj005_ignores_non_instance_functions()
    print("All PINJ005 tests passed!")
