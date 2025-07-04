"""Test PINJ009: Injected async function prefix."""

import ast
from pathlib import Path

from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.rules.pinj009_injected_async_prefix import (
    PINJ009InjectedAsyncPrefix,
)
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj009_detects_missing_prefix():
    """Test that PINJ009 detects async @injected functions without a_ prefix."""
    source = """
from pinjected import injected

@injected
async def fetch_data(client, /, url: str):
    # Bad - missing a_ prefix
    return await client.get(url)

@injected
async def process_items(processor, /, items: list):
    # Bad - missing a_ prefix
    results = []
    for item in items:
        result = await processor.process(item)
        results.append(result)
    return results

@injected
async def upload_file(storage, /, file_path: str):
    # Bad - missing a_ prefix
    async with storage.session() as session:
        return await session.upload(file_path)
"""

    rule = PINJ009InjectedAsyncPrefix()
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

    # Check violations
    for violation in violations:
        assert violation.rule_id == "PINJ009"
        assert "should have 'a_' prefix" in violation.message
        assert violation.severity == Severity.ERROR
        assert violation.fix is not None  # Should have auto-fix

    # Check specific functions
    violation_messages = [v.message for v in violations]
    assert any("fetch_data" in msg for msg in violation_messages)
    assert any("process_items" in msg for msg in violation_messages)
    assert any("upload_file" in msg for msg in violation_messages)


def test_pinj009_allows_proper_prefix():
    """Test that PINJ009 allows async @injected functions with a_ prefix."""
    source = """
from pinjected import injected

@injected
async def a_fetch_data(client, /, url: str):
    # Good - has a_ prefix
    return await client.get(url)

@injected
async def a_process_batch(
    logger,
    a_validate_item,
    a_transform_item,
    /,
    items: list
):
    # Good - has a_ prefix and uses other async functions
    # Note: No await when calling @injected functions - building AST!
    results = []
    for item in items:
        valid = a_validate_item(item)  # No await - building AST
        if valid:
            transformed = a_transform_item(item)  # No await - building AST
            results.append(transformed)
    return results

@injected
async def a_complex_workflow(database, cache, a_fetch_external_data, /, request_id: str):
    # Good - has a_ prefix
    # Note: await is OK for injected params (not @injected functions)
    cached = await cache.get(request_id)
    if cached:
        return cached
    
    # No await for @injected function calls - building AST!
    data = a_fetch_external_data(request_id)
    await database.save(request_id, data)
    await cache.set(request_id, data)
    return data
"""

    rule = PINJ009InjectedAsyncPrefix()
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


def test_pinj009_ignores_sync_injected():
    """Test that PINJ009 ignores synchronous @injected functions."""
    source = """
from pinjected import injected

@injected
def process_data(transformer, /, data):
    # OK - synchronous function doesn't need a_ prefix
    return transformer.transform(data)

@injected
def calculate_result(calculator, logger, /, x: float, y: float):
    # OK - synchronous function
    logger.info(f"Calculating {x} + {y}")
    return calculator.add(x, y)

@injected
def workflow(database, validator, transformer, /, input_data):
    # OK - synchronous workflow
    if validator.validate(input_data):
        result = transformer.transform(input_data)
        database.save(result)
        return result
    return None
"""

    rule = PINJ009InjectedAsyncPrefix()
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


def test_pinj009_ignores_non_injected_async():
    """Test that PINJ009 ignores async functions without @injected decorator."""
    source = """
from pinjected import instance

# Regular async function - no decorator
async def fetch_data(url):
    # OK - not @injected
    return await some_client.get(url)

# Async @instance function
@instance
async def database_connection():
    # OK - @instance, not @injected
    conn = await create_connection()
    return conn

# Async method in a class
class Service:
    async def process(self, data):
        # OK - class method
        return await self.do_processing(data)

# Async function with other decorator
@some_other_decorator
async def decorated_function():
    # OK - not @injected
    return "result"
"""

    rule = PINJ009InjectedAsyncPrefix()
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


def test_pinj009_provides_correct_fix():
    """Test that PINJ009 provides correct auto-fix suggestions."""
    source = """
from pinjected import injected

@injected
async def fetch_user(database, /, user_id: int):
    return await database.get_user(user_id)
"""

    rule = PINJ009InjectedAsyncPrefix()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should have 1 violation with fix
    assert len(violations) == 1
    violation = violations[0]

    assert violation.fix is not None
    assert violation.fix.replacement == "a_fetch_user"
    assert "Consider renaming to 'a_fetch_user'" in violation.suggestion


if __name__ == "__main__":
    test_pinj009_detects_missing_prefix()
    test_pinj009_allows_proper_prefix()
    test_pinj009_ignores_sync_injected()
    test_pinj009_ignores_non_injected_async()
    test_pinj009_provides_correct_fix()
    print("All PINJ009 tests passed!")
