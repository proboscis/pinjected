"""Additional tests for PINJ002 to improve coverage."""

import ast
from pathlib import Path

from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.rules.pinj002_instance_defaults import PINJ002InstanceDefaults
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj002_various_default_types():
    """Test PINJ002 with various default value types."""
    source = '''
from pinjected import instance

@instance
def service1(name="default"):
    return name

@instance
def service2(count=42):
    return count

@instance
def service3(flag=True):
    return flag

@instance  
def service4(items=None):
    return items

@instance
def service5(config={"key": "value"}):
    return config
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
    
    # Should detect all 5 violations
    assert len(violations) == 5
    
    # Check various default representations
    messages = [v.message for v in violations]
    assert any("name='default'" in msg for msg in messages)
    assert any("count=42" in msg for msg in messages)
    assert any("flag=True" in msg for msg in messages)
    assert any("items=None" in msg for msg in messages)
    assert any("config=..." in msg for msg in messages)  # Complex expression


def test_pinj002_complex_defaults():
    """Test PINJ002 with complex default value types."""
    source = '''
from pinjected import instance

@instance
def service_with_list(items=[]):
    return items

@instance  
def service_with_dict(config={}):
    return config

@instance
def service_with_tuple(data=(1, 2, 3)):
    return data
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
    
    # Should detect all 3 violations with complex defaults
    assert len(violations) == 3
    
    # Check that complex expressions are represented as "..."
    messages = [v.message for v in violations]
    assert any("items=..." in msg for msg in messages)
    assert any("config=..." in msg for msg in messages) 
    assert any("data=..." in msg for msg in messages)