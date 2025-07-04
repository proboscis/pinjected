"""Test PINJ003: Async instance naming."""

import ast
from pathlib import Path

from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.rules.pinj003_async_instance_naming import PINJ003AsyncInstanceNaming
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj003_detects_a_prefix():
    """Test that PINJ003 detects 'a_' prefix in async @instance functions."""
    source = '''
from pinjected import instance

@instance
async def a_database_connection():
    return await create_connection()

@instance
async def a_rabbitmq_channel():
    return await create_channel()

@instance
async def database_connection():  # This is correct
    return await create_connection()

@instance
async def cache_client():  # This is correct
    return await create_cache()
'''
    
    rule = PINJ003AsyncInstanceNaming()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )
    
    violations = rule.check(context)
    
    # Should detect 2 violations
    assert len(violations) == 2
    
    # Check first violation
    assert violations[0].rule_id == "PINJ003"
    assert "a_database_connection" in violations[0].message
    assert "'a_' prefix" in violations[0].message
    assert violations[0].severity == Severity.ERROR
    assert violations[0].fix is not None
    assert violations[0].fix.replacement == "database_connection"
    
    # Check second violation
    assert violations[1].rule_id == "PINJ003"
    assert "a_rabbitmq_channel" in violations[1].message
    assert violations[1].fix is not None
    assert violations[1].fix.replacement == "rabbitmq_channel"


def test_pinj003_ignores_injected_functions():
    """Test that PINJ003 ignores @injected functions (which should have 'a_' prefix)."""
    source = '''
from pinjected import injected, instance

@injected
async def a_process_data(processor, /, data):  # @injected should have a_ prefix
    return await processor.process(data)

@injected
async def a_fetch_results(client, /, query):  # @injected should have a_ prefix
    return await client.fetch(query)

async def a_regular_function():  # Not decorated, should be ignored
    return await something()
'''
    
    rule = PINJ003AsyncInstanceNaming()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )
    
    violations = rule.check(context)
    
    # Should detect no violations
    assert len(violations) == 0


def test_pinj003_ignores_sync_functions():
    """Test that PINJ003 ignores synchronous functions."""
    source = '''
from pinjected import instance

@instance
def a_database():  # Sync function, not checked by PINJ003
    return Database()

@instance
def database():  # Sync function, not checked by PINJ003
    return Database()
'''
    
    rule = PINJ003AsyncInstanceNaming()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )
    
    violations = rule.check(context)
    
    # Should detect no violations (PINJ003 only checks async functions)
    assert len(violations) == 0


if __name__ == "__main__":
    test_pinj003_detects_a_prefix()
    test_pinj003_ignores_injected_functions()
    test_pinj003_ignores_sync_functions()
    print("All PINJ003 tests passed!")