"""Test PINJ001: Instance function naming convention."""

import ast
from pathlib import Path
from pinjected_linter.rules.pinj001_instance_naming import PINJ001InstanceNaming
from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj001_detects_verb_prefixes():
    """Test that PINJ001 detects verb prefixes in @instance functions."""
    source = '''
from pinjected import instance

@instance
def get_database():
    return Database()

@instance
def create_user():
    return User()

@instance
def database():  # This is correct
    return Database()
'''
    
    rule = PINJ001InstanceNaming()
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
    assert violations[0].rule_id == "PINJ001"
    assert "get_database" in violations[0].message
    assert violations[0].severity == Severity.ERROR
    assert violations[0].fix is not None
    assert violations[0].fix.replacement == "database"
    
    assert violations[1].rule_id == "PINJ001"
    assert "create_user" in violations[1].message
    assert violations[1].fix is not None
    assert violations[1].fix.replacement == "user"


def test_pinj001_detects_standalone_verbs():
    """Test that PINJ001 detects standalone verbs."""
    source = '''
from pinjected import instance

@instance
def setup():
    return Config()

@instance
def processor():  # This is correct
    return Processor()
'''
    
    rule = PINJ001InstanceNaming()
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
    assert violations[0].rule_id == "PINJ001"
    assert "setup" in violations[0].message
    assert violations[0].fix is not None
    assert violations[0].fix.replacement == "configuration"


def test_pinj001_ignores_non_instance_functions():
    """Test that PINJ001 ignores functions without @instance decorator."""
    source = '''
from pinjected import injected

def get_database():  # Not @instance, should be ignored
    return Database()

@injected
def get_user(database,/):  # @injected is fine with verbs
    return database.get_user()
'''
    
    rule = PINJ001InstanceNaming()
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
    test_pinj001_detects_verb_prefixes()
    test_pinj001_detects_standalone_verbs()
    test_pinj001_ignores_non_instance_functions()
    print("All PINJ001 tests passed!")