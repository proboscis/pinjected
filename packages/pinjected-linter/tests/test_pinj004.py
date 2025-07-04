"""Test PINJ004: Direct instance call detection."""

import ast
from pathlib import Path

from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.rules.pinj004_direct_instance_call import PINJ004DirectInstanceCall
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj004_detects_direct_calls():
    """Test that PINJ004 detects direct calls to @instance functions."""
    source = '''
from pinjected import instance, design

@instance
def database():
    return Database()

@instance
def cache():
    return Cache()

def bad_usage():
    # Direct calls - should trigger PINJ004
    db = database()  # ❌ Direct call
    c = cache()  # ❌ Direct call
    
    # More complex direct call
    result = database().query("SELECT * FROM users")  # ❌
    
    return db, c

# This should also trigger
global_db = database()  # ❌ Direct call at module level
'''
    
    rule = PINJ004DirectInstanceCall()
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
    
    # Check violations
    for violation in violations:
        assert violation.rule_id == "PINJ004"
        assert "Direct call" in violation.message
        assert violation.severity == Severity.ERROR
        assert ("database" in violation.message or "cache" in violation.message)


def test_pinj004_allows_design_usage():
    """Test that PINJ004 allows @instance functions in design() calls."""
    source = '''
from pinjected import instance, design

@instance
def database():
    return Database()

@instance
def cache():
    return Cache()

@instance
def logger():
    return Logger()

# Good usage - should NOT trigger
config = design(
    db=database,  # ✅ Used in design
    cache=cache,  # ✅ Used in design
    logger=logger,  # ✅ Used in design
)

# Nested design
base_design = design(
    database=database,
    config=design(
        cache=cache,  # ✅ Nested design is OK
        logger=logger,
    )
)

# Design with call
my_design = design(db=database)  # ✅ OK
'''
    
    rule = PINJ004DirectInstanceCall()
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


def test_pinj004_allows_dependency_injection():
    """Test that PINJ004 allows passing @instance functions as dependencies."""
    source = '''
from pinjected import instance, injected

@instance
def database():
    return Database()

@instance
def cache():
    return Cache()

@injected
def process_data(database, cache, /, data):
    # Using injected dependencies is fine
    result = database.query(data)
    cache.set("result", result)
    return result

# Good - passing as reference, not calling
processors = [database, cache]  # ✅ Just references

# Good - used in function signature
def create_service(db=database):  # ✅ Default parameter
    return Service(db)
'''
    
    rule = PINJ004DirectInstanceCall()
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


def test_pinj004_ignores_non_instance_functions():
    """Test that PINJ004 ignores functions without @instance decorator."""
    source = '''
from pinjected import injected

def regular_function():
    return "regular"

@injected
def injected_function(dep, /):
    return dep.process()

# These are all fine - not @instance functions
result1 = regular_function()  # ✅ Not @instance
result2 = injected_function()  # ✅ @injected can be called

class MyClass:
    def method(self):
        return "method"

obj = MyClass()
result3 = obj.method()  # ✅ Method call
'''
    
    rule = PINJ004DirectInstanceCall()
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


if __name__ == "__main__":
    test_pinj004_detects_direct_calls()
    test_pinj004_allows_design_usage()
    test_pinj004_allows_dependency_injection()
    test_pinj004_ignores_non_instance_functions()
    print("All PINJ004 tests passed!")