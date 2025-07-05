"""Test PINJ009: No await in injected AST building."""

import ast
from pathlib import Path

from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.rules.pinj009_no_await_in_injected import PINJ009NoAwaitInInjected
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj009_detects_await_on_injected_calls():
    """Test that PINJ009 detects await on @injected function calls."""
    source = """
from pinjected import injected

@injected
async def a_fetch_data(api, /, user_id):
    return await api.get_user(user_id)

@injected
async def a_process_user(logger, /, user):
    logger.info(f"Processing {user}")
    return user.process()

@injected
async def a_bad_example(a_fetch_data, a_process_user, /, user_id):
    # These awaits are WRONG - building AST, not executing!
    data = await a_fetch_data(user_id)  # Bad - await on @injected
    result = await a_process_user(data)  # Bad - await on @injected
    return result

@injected
async def a_another_bad(a_fetch_data, logger, /, ids):
    results = []
    for id in ids:
        # This await is wrong!
        data = await a_fetch_data(id)  # Bad - await on @injected
        results.append(data)
    return results

@injected
async def a_single_bad(a_process_user, /, user):
    # Single bad await
    return await a_process_user(user)  # Bad
"""

    rule = PINJ009NoAwaitInInjected()
    tree = ast.parse(source)
    symbol_table = SymbolTable()
    
    # Build symbol table
    class SymbolTableBuilder(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            symbol_table.add_function(node)
            self.generic_visit(node)
        
        def visit_AsyncFunctionDef(self, node):
            symbol_table.add_function(node)
            self.generic_visit(node)
    
    builder = SymbolTableBuilder()
    builder.visit(tree)
    
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=symbol_table,
        config={},
    )

    violations = rule.check(context)

    # Should detect 4 await violations
    assert len(violations) >= 4
    
    # Check violations
    for violation in violations:
        assert violation.rule_id == "PINJ009"
        assert "await" in violation.message
        assert "AST" in violation.message
        assert violation.severity == Severity.ERROR


def test_pinj009_allows_await_on_non_injected():
    """Test that PINJ009 allows await on non-@injected calls."""
    source = """
from pinjected import injected

@injected
async def a_good_example(a_fetch_data, a_process_user, /, user_id):
    # Correct - no await when calling @injected functions
    data = a_fetch_data(user_id)  # Good - no await
    result = a_process_user(data)  # Good - no await
    return result

@injected
async def a_mixed_example(api_client, a_process_data, /, url):
    # This await is OK - api_client is not @injected
    raw_data = await api_client.fetch(url)  # Good - not @injected
    # But this should not have await
    processed = a_process_data(raw_data)  # Good - no await
    return processed

@injected
async def a_database_example(db, a_transform, /, query):
    # OK to await database operations
    results = await db.execute(query)  # Good - db is not @injected
    
    # Transform each result without await
    transformed = [a_transform(r) for r in results]  # Good - no await
    
    # More async db operations
    await db.commit()  # Good - not @injected
    
    return transformed

@injected
async def a_only_external_awaits(logger, cache, /, key):
    # All these awaits are on non-@injected dependencies
    logger.info(f"Fetching {key}")
    
    value = await cache.get(key)  # Good
    if value is None:
        value = await cache.compute(key)  # Good
        await cache.set(key, value)  # Good
    
    return value
"""

    rule = PINJ009NoAwaitInInjected()
    tree = ast.parse(source)
    symbol_table = SymbolTable()
    
    # Build symbol table
    class SymbolTableBuilder(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            symbol_table.add_function(node)
            self.generic_visit(node)
        
        def visit_AsyncFunctionDef(self, node):
            symbol_table.add_function(node)
            self.generic_visit(node)
    
    builder = SymbolTableBuilder()
    builder.visit(tree)
    
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=symbol_table,
        config={},
    )

    violations = rule.check(context)

    # Should have no violations
    assert len(violations) == 0


def test_pinj009_detects_await_with_prefix_variations():
    """Test that PINJ009 detects await on @injected calls with a_ prefix."""
    source = """
from pinjected import injected

@injected
async def fetch_data(api, /, id):
    return await api.get(id)

@injected
async def a_fetch_data(api, /, id):
    return await api.get(id)

@injected
async def a_workflow(fetch_data, a_fetch_data, /, id):
    # Both of these are wrong - await on @injected functions
    data1 = await fetch_data(id)  # Bad - @injected without prefix
    data2 = await a_fetch_data(id)  # Bad - @injected with prefix
    return data1, data2

@injected
def sync_processor(data, /):
    return data.process()

@injected
async def a_mixed_sync_async(sync_processor, a_fetch_data, /, id):
    # Can't await sync @injected function
    result = await sync_processor(id)  # Bad - await on sync @injected
    
    # Also can't await async @injected function
    data = await a_fetch_data(id)  # Bad
    
    return result, data
"""

    rule = PINJ009NoAwaitInInjected()
    tree = ast.parse(source)
    symbol_table = SymbolTable()
    
    # Build symbol table
    class SymbolTableBuilder(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            symbol_table.add_function(node)
            self.generic_visit(node)
        
        def visit_AsyncFunctionDef(self, node):
            symbol_table.add_function(node)
            self.generic_visit(node)
    
    builder = SymbolTableBuilder()
    builder.visit(tree)
    
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=symbol_table,
        config={},
    )

    violations = rule.check(context)

    # Should detect at least 4 violations
    assert len(violations) >= 4
    
    # Check that violations mention the function names
    violation_messages = [v.message for v in violations]
    assert any("a_workflow" in msg for msg in violation_messages)
    assert any("a_mixed_sync_async" in msg for msg in violation_messages)


def test_pinj009_nested_functions():
    """Test that PINJ009 handles nested @injected functions."""
    source = """
from pinjected import injected

@injected
async def a_helper(service, /, data):
    return await service.process(data)

def outer_function():
    @injected
    async def a_inner(a_helper, /, value):
        # Bad - await on outer @injected function
        result = await a_helper(value)  # Bad
        return result
    
    @injected
    async def a_another_inner(service, /, data):
        # OK - service is not @injected
        return await service.handle(data)  # Good
    
    return a_inner, a_another_inner

@injected
async def a_complex(a_helper, /, items):
    # Nested function that's not @injected
    async def process_item(item):
        # This is inside a non-@injected function, but a_helper is still @injected
        return await a_helper(item)  # Bad - still wrong!
    
    results = []
    for item in items:
        result = await process_item(item)
        results.append(result)
    return results
"""

    rule = PINJ009NoAwaitInInjected()
    tree = ast.parse(source)
    symbol_table = SymbolTable()
    
    # Build symbol table
    class SymbolTableBuilder(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            symbol_table.add_function(node)
            self.generic_visit(node)
        
        def visit_AsyncFunctionDef(self, node):
            symbol_table.add_function(node)
            self.generic_visit(node)
    
    builder = SymbolTableBuilder()
    builder.visit(tree)
    
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=symbol_table,
        config={},
    )

    violations = rule.check(context)

    # Should detect violations in nested contexts
    assert len(violations) >= 2


def test_pinj009_non_injected_functions():
    """Test that PINJ009 ignores non-@injected functions."""
    source = """
from pinjected import instance

# Regular async function - not @injected
async def regular_async(service):
    # Can await anything here
    data = await service.fetch()
    return data

# @instance function - not @injected
@instance
async def async_instance():
    return AsyncService()

# Another regular function calling @injected
async def calls_injected(a_fetch_data, id):
    # This is NOT an @injected function, so it can await
    result = await a_fetch_data(id)  # OK - caller is not @injected
    return result

class MyClass:
    async def method(self, a_process):
        # Class methods can await
        return await a_process()  # OK - not @injected
"""

    rule = PINJ009NoAwaitInInjected()
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
    test_pinj009_detects_await_on_injected_calls()
    test_pinj009_allows_await_on_non_injected()
    test_pinj009_detects_await_with_prefix_variations()
    test_pinj009_nested_functions()
    test_pinj009_non_injected_functions()
    print("All PINJ009 tests passed!")