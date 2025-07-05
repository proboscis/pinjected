"""Test PINJ006: Async injected naming."""

import ast
from pathlib import Path

from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.rules.pinj006_async_injected_naming import PINJ006AsyncInjectedNaming
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj006_detects_missing_prefix():
    """Test that PINJ006 detects async @injected functions without a_ prefix."""
    source = """
from pinjected import injected

@injected
async def fetch_data(api_client, /, id):  # Bad - missing a_ prefix
    return await api_client.get(id)

@injected
async def process_queue(mq, /, message):  # Bad - missing a_ prefix
    return await mq.process(message)

@injected
async def upload_file(storage, /, file):  # Bad - missing a_ prefix
    return await storage.upload(file)

@injected
async def getData(api, /):  # Bad - camelCase without a_
    return await api.get_all()

@injected
async def FETCH_USER(db, /, id):  # Bad - uppercase without a_
    return await db.get_user(id)
"""

    rule = PINJ006AsyncInjectedNaming()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect 5 violations
    assert len(violations) == 5

    # Check violations
    for violation in violations:
        assert violation.rule_id == "PINJ006"
        assert "must have 'a_' prefix" in violation.message
        assert violation.severity == Severity.ERROR

    # Check specific functions mentioned
    violation_messages = [v.message for v in violations]
    assert any("fetch_data" in msg for msg in violation_messages)
    assert any("process_queue" in msg for msg in violation_messages)
    assert any("upload_file" in msg for msg in violation_messages)
    assert any("getData" in msg for msg in violation_messages)
    assert any("FETCH_USER" in msg for msg in violation_messages)


def test_pinj006_accepts_proper_prefix():
    """Test that PINJ006 accepts async @injected functions with a_ prefix."""
    source = """
from pinjected import injected

@injected
async def a_fetch_data(api_client, /, id):  # Good - has a_ prefix
    return await api_client.get(id)

@injected
async def a_process_queue(mq, /, message):  # Good - has a_ prefix
    return await mq.process(message)

@injected
async def a_upload_file(storage, /, file):  # Good - has a_ prefix
    return await storage.upload(file)

@injected
async def a__special_case(api, /):  # Good - multiple underscores OK
    return await api.special()

@injected
async def a_getUserData(db, /, id):  # Good - camelCase after a_ is OK
    return await db.get_user(id)

# Sync functions don't need a_ prefix
@injected
def fetch_data_sync(api_client, /, id):  # Good - sync function
    return api_client.get_sync(id)
"""

    rule = PINJ006AsyncInjectedNaming()
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


def test_pinj006_edge_cases():
    """Test edge cases for PINJ006."""
    source = """
from pinjected import injected

@injected
async def A_fetch_data(api, /):  # Bad - capital A
    return await api.get()

@injected
async def fetch_a_data(api, /):  # Bad - a_ in middle
    return await api.get()

@injected
async def _a_private(api, /):  # Bad - underscore before a_
    return await api.get()

# Functions without @injected decorator
async def fetch_data(api):  # OK - not @injected
    return await api.get()

# Non-async @injected
@injected
def sync_function(api, /):  # OK - not async
    return api.get()

# Different decorator
@instance
async def instance_function():  # OK - not @injected
    return await create_instance()
"""

    rule = PINJ006AsyncInjectedNaming()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect 3 violations (A_fetch_data, fetch_a_data, _a_private)
    assert len(violations) == 3

    violation_functions = [v.message.split("'")[1] for v in violations]
    assert "A_fetch_data" in violation_functions
    assert "fetch_a_data" in violation_functions
    assert "_a_private" in violation_functions


def test_pinj006_auto_fix():
    """Test that PINJ006 provides correct auto-fix suggestions."""
    source = """
from pinjected import injected

@injected
async def fetch_data(api, /, id):
    return await api.get(id)

@injected
async def processQueue(mq, /, msg):
    return await mq.process(msg)

@injected
async def UPLOAD_FILE(storage, /, file):
    return await storage.upload(file)
"""

    rule = PINJ006AsyncInjectedNaming()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Check that fixes are provided
    assert all(v.fix is not None for v in violations)

    # Check specific fix suggestions
    fixes = {v.message.split("'")[1]: v.fix for v in violations}
    
    # fetch_data should become a_fetch_data
    assert fixes["fetch_data"].replacement == "a_fetch_data"
    
    # processQueue should become a_processQueue (preserving case)
    assert fixes["processQueue"].replacement == "a_processQueue"
    
    # UPLOAD_FILE should become a_UPLOAD_FILE (preserving case)
    assert fixes["UPLOAD_FILE"].replacement == "a_UPLOAD_FILE"


def test_pinj006_complex_scenarios():
    """Test complex scenarios for PINJ006."""
    source = """
from pinjected import injected

# Nested functions
def outer():
    @injected
    async def fetch_nested(api, /):  # Bad - missing a_
        return await api.get()
    
    @injected
    async def a_process_nested(proc, /):  # Good
        return await proc.run()
    
    return fetch_nested, a_process_nested

# Class methods
class Service:
    @injected
    async def fetch_method(self, api, /):  # Bad - missing a_
        return await api.get()
    
    @injected
    async def a_process_method(self, proc, /):  # Good
        return await proc.run()

# Multiple decorators
@custom_decorator
@injected
async def multi_decorated(api, /):  # Bad - missing a_
    return await api.get()

@injected
@another_decorator
async def a_multi_decorated2(api, /):  # Good
    return await api.get()
"""

    rule = PINJ006AsyncInjectedNaming()
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

    violation_functions = [v.message.split("'")[1] for v in violations]
    assert "fetch_nested" in violation_functions
    assert "fetch_method" in violation_functions
    assert "multi_decorated" in violation_functions


if __name__ == "__main__":
    test_pinj006_detects_missing_prefix()
    test_pinj006_accepts_proper_prefix()
    test_pinj006_edge_cases()
    test_pinj006_auto_fix()
    test_pinj006_complex_scenarios()
    print("All PINJ006 tests passed!")