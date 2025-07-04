"""Test PINJ008: Injected function dependency declaration."""

import ast
from pathlib import Path
from pinjected_linter.rules.pinj008_injected_dependency_declaration import PINJ008InjectedDependencyDeclaration
from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj008_detects_undeclared_dependencies():
    """Test that PINJ008 detects calls to @injected functions without declaring them."""
    source = '''
from pinjected import injected

@injected
def process_data(transformer, /):
    return transformer.process()

@injected
def validate_data(validator, /):
    return validator.validate()

@injected
def workflow(database, /):
    # Bad - calling other @injected functions without declaring them
    data = process_data("test")  # ❌ process_data not declared
    valid = validate_data(data)  # ❌ validate_data not declared
    return database.save(valid)

@injected
def another_workflow(logger, /):
    # Also bad
    result = process_data("input")  # ❌ process_data not declared
    return result
'''
    
    rule = PINJ008InjectedDependencyDeclaration()
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
        assert violation.rule_id == "PINJ008"
        assert "without declaring it as a dependency" in violation.message
        assert violation.severity == Severity.ERROR


def test_pinj008_allows_declared_dependencies():
    """Test that PINJ008 allows calling @injected functions that are declared."""
    source = '''
from pinjected import injected

@injected
def process_data(transformer, /):
    return transformer.process()

@injected
def validate_data(validator, /):
    return validator.validate()

@injected
def workflow(database, process_data, validate_data, /):
    # Good - these are declared as dependencies
    data = process_data("test")  # ✅ Declared
    valid = validate_data(data)  # ✅ Declared
    return database.save(valid)

@injected
def complex_workflow(logger, process_data, /):
    # Good - process_data is declared
    result = process_data("input")  # ✅ Declared
    logger.info(f"Result: {result}")
    return result
'''
    
    rule = PINJ008InjectedDependencyDeclaration()
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


def test_pinj008_ignores_non_injected_calls():
    """Test that PINJ008 ignores calls to non-@injected functions."""
    source = '''
from pinjected import injected

def regular_function():
    return "regular"

def helper_function(x):
    return x * 2

@injected
def workflow(database, /):
    # These are fine - not @injected functions
    result1 = regular_function()  # ✅ Not @injected
    result2 = helper_function(10)  # ✅ Not @injected
    
    # Also fine - built-in functions
    items = list(range(10))  # ✅ Built-in
    text = str(result1)  # ✅ Built-in
    
    return database.save(result2)
'''
    
    rule = PINJ008InjectedDependencyDeclaration()
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


def test_pinj008_handles_async_functions():
    """Test that PINJ008 handles async @injected functions."""
    source = '''
from pinjected import injected

@injected
async def a_fetch_data(client, /):
    return await client.fetch()

@injected
async def a_process_data(processor, /):
    return await processor.process()

@injected
async def a_workflow(database, /):
    # Bad - not declaring async dependencies
    # Note: No await when calling @injected functions (building AST)
    data = a_fetch_data()  # ❌ a_fetch_data not declared
    result = a_process_data()  # ❌ a_process_data not declared
    return database.save(result)  # Note: database is injected param, not @injected func

@injected
async def a_good_workflow(database, a_fetch_data, a_process_data, /):
    # Good - declaring async dependencies
    # Note: No await when calling @injected functions (building AST)
    data = a_fetch_data()  # ✅ Declared
    result = a_process_data()  # ✅ Declared
    return database.save(result)  # Note: database is injected param, not @injected func
'''
    
    rule = PINJ008InjectedDependencyDeclaration()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )
    
    violations = rule.check(context)
    
    # Should detect 2 violations (in a_workflow)
    assert len(violations) == 2
    assert all(v.rule_id == "PINJ008" for v in violations)


if __name__ == "__main__":
    test_pinj008_detects_undeclared_dependencies()
    test_pinj008_allows_declared_dependencies()
    test_pinj008_ignores_non_injected_calls()
    test_pinj008_handles_async_functions()
    print("All PINJ008 tests passed!")