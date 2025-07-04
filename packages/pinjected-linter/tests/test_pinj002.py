"""Test PINJ002: Instance function default arguments."""

import ast
from pathlib import Path

from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.rules.pinj002_instance_defaults import PINJ002InstanceDefaults
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj002_detects_default_arguments():
    """Test that PINJ002 detects default arguments in @instance functions."""
    source = '''
from pinjected import instance

@instance
def database(host="localhost", port=5432):
    return Database(host, port)

@instance
def cache(ttl=3600):
    return Cache(ttl)

@instance
def config(debug=False, max_retries=3):
    return Config(debug, max_retries)

@instance
def service():  # This is correct
    return Service()
'''
    
    rule = PINJ002InstanceDefaults()
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
    
    # Check first violation
    assert violations[0].rule_id == "PINJ002"
    assert "database" in violations[0].message
    assert "'localhost'" in violations[0].message  # Check for quoted string
    assert "5432" in violations[0].message
    assert violations[0].severity == Severity.ERROR
    assert "design()" in violations[0].message
    
    # Check second violation
    assert violations[1].rule_id == "PINJ002"
    assert "cache" in violations[1].message
    assert "ttl=3600" in violations[1].message
    
    # Check third violation
    assert violations[2].rule_id == "PINJ002"
    assert "config" in violations[2].message
    assert "debug=False" in violations[2].message
    assert "max_retries=3" in violations[2].message


def test_pinj002_ignores_non_instance_functions():
    """Test that PINJ002 ignores functions without @instance decorator."""
    source = '''
from pinjected import injected

def regular_function(x=10):  # Not @instance, should be ignored
    return x * 2

@injected
def injected_function(dep, /, x=10):  # @injected can have defaults for runtime args
    return dep.process(x)

class MyClass:
    def method(self, x=10):  # Class method, should be ignored
        return x
'''
    
    rule = PINJ002InstanceDefaults()
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


def test_pinj002_handles_async_functions():
    """Test that PINJ002 handles async @instance functions."""
    source = '''
from pinjected import instance

@instance
async def async_database(host="localhost"):
    return await create_database(host)

@instance
async def async_service():  # This is correct
    return await create_service()
'''
    
    rule = PINJ002InstanceDefaults()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )
    
    violations = rule.check(context)
    
    # Should detect 1 violation
    assert len(violations) == 1
    assert violations[0].rule_id == "PINJ002"
    assert "async_database" in violations[0].message
    assert "'localhost'" in violations[0].message


if __name__ == "__main__":
    test_pinj002_detects_default_arguments()
    test_pinj002_ignores_non_instance_functions()
    test_pinj002_handles_async_functions()
    print("All PINJ002 tests passed!")