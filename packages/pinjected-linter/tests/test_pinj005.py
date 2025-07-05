"""Test PINJ005: Injected function naming convention."""

import ast
from pathlib import Path

from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.rules.pinj005_injected_function_naming import PINJ005InjectedFunctionNaming
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj005_detects_noun_forms():
    """Test that PINJ005 detects noun forms in @injected functions."""
    source = """
from pinjected import injected

@injected
def user_data(db, /, user_id):  # Bad - noun form
    return db.query(user_id)

@injected
def result(calculator, /, input):  # Bad - noun form
    return calculator.compute(input)

@injected
def configuration(loader, /):  # Bad - noun form
    return loader.load_config()

@injected
def user_manager(db, /):  # Bad - noun suffix
    return UserManager(db)

@injected
def response(api_client, /, endpoint):  # Bad - noun form
    return api_client.call(endpoint)
"""

    rule = PINJ005InjectedFunctionNaming()
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
        assert violation.rule_id == "PINJ005"
        assert "noun form" in violation.message
        assert "@injected function" in violation.message
        assert violation.severity == Severity.WARNING

    # Check specific functions mentioned
    violation_messages = [v.message for v in violations]
    assert any("user_data" in msg for msg in violation_messages)
    assert any("result" in msg for msg in violation_messages)
    assert any("configuration" in msg for msg in violation_messages)
    assert any("user_manager" in msg for msg in violation_messages)
    assert any("response" in msg for msg in violation_messages)


def test_pinj005_accepts_verb_forms():
    """Test that PINJ005 accepts verb forms in @injected functions."""
    source = """
from pinjected import injected

@injected
def fetch_user_data(db, /, user_id):  # Good - verb form
    return db.query(user_id)

@injected
def calculate_result(calculator, /, input):  # Good - verb form
    return calculator.compute(input)

@injected
def load_configuration(loader, /):  # Good - verb form
    return loader.load_config()

@injected
def create_user_manager(db, /):  # Good - verb form
    return UserManager(db)

@injected
def get_response(api_client, /, endpoint):  # Good - verb form
    return api_client.call(endpoint)

@injected
def process(data, /):  # Good - standalone verb
    return data.transform()

@injected
def initialize(config, /):  # Good - standalone verb
    return System(config)
"""

    rule = PINJ005InjectedFunctionNaming()
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


def test_pinj005_handles_async_prefix():
    """Test that PINJ005 handles async functions with a_ prefix correctly."""
    source = """
from pinjected import injected

@injected
async def a_user_data(db, /, user_id):  # Bad - noun form after prefix
    return await db.query_async(user_id)

@injected
async def a_fetch_user_data(db, /, user_id):  # Good - verb form after prefix
    return await db.query_async(user_id)

@injected
async def a_process_data(processor, /, data):  # Good - verb form after prefix
    return await processor.process(data)

@injected
async def a_result(calculator, /):  # Bad - noun form after prefix
    return await calculator.compute_async()
"""

    rule = PINJ005InjectedFunctionNaming()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect 2 violations (a_user_data and a_result)
    assert len(violations) == 2

    violation_messages = [v.message for v in violations]
    assert any("a_user_data" in msg for msg in violation_messages)
    assert any("a_result" in msg for msg in violation_messages)


def test_pinj005_ignores_non_injected_functions():
    """Test that PINJ005 ignores functions without @injected decorator."""
    source = """
from pinjected import instance

def user_data():  # OK - no decorator
    return get_data()

@instance
def database():  # OK - @instance, not @injected
    return Database()

class MyClass:
    def result(self):  # OK - class method
        return self.compute()

# Regular function with noun name - should be ignored
def configuration():
    return load_config()
"""

    rule = PINJ005InjectedFunctionNaming()
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


def test_pinj005_auto_fix():
    """Test that PINJ005 provides correct auto-fix suggestions."""
    source = """
from pinjected import injected

@injected
def user_data(db, /, user_id):
    return db.query(user_id)

@injected
def configuration(loader, /):
    return loader.load_config()

@injected
async def a_result(calc, /):
    return await calc.compute()
"""

    rule = PINJ005InjectedFunctionNaming()
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
    
    # user_data should suggest get_user_data
    assert fixes["user_data"].replacement == "get_user_data"
    
    # configuration should suggest load_configuration
    assert fixes["configuration"].replacement == "load_configuration"
    
    # a_result should suggest a_get_result (maintaining the async prefix)
    assert fixes["a_result"].replacement == "a_get_result"


def test_pinj005_edge_cases():
    """Test edge cases for PINJ005."""
    source = """
from pinjected import injected

@injected
def data(db, /):  # Bad - single noun
    return db.all()

@injected
def info(api, /):  # Bad - single noun
    return api.get_info()

@injected
def get(api, /, resource):  # Good - single verb
    return api.get(resource)

@injected
def fetch(db, /, id):  # Good - single verb
    return db.fetch(id)

@injected
def _private_data(db, /):  # Bad - noun form even with underscore prefix
    return db.private_data()

@injected
def get_user_data_and_process_it(db, /, id):  # Good - starts with verb
    return process(db.get_user(id))
"""

    rule = PINJ005InjectedFunctionNaming()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect 3 violations (data, info, _private_data)
    assert len(violations) == 3

    violation_functions = [v.message.split("'")[1] for v in violations]
    assert "data" in violation_functions
    assert "info" in violation_functions
    assert "_private_data" in violation_functions


if __name__ == "__main__":
    test_pinj005_detects_noun_forms()
    test_pinj005_accepts_verb_forms()
    test_pinj005_handles_async_prefix()
    test_pinj005_ignores_non_injected_functions()
    test_pinj005_auto_fix()
    test_pinj005_edge_cases()
    print("All PINJ005 tests passed!")