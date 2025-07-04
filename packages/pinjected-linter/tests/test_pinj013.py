"""Test PINJ013: Builtin shadowing detection."""

import ast
from pathlib import Path
from pinjected_linter.rules.pinj013_builtin_shadowing import PINJ013BuiltinShadowing
from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj013_detects_common_type_shadows():
    """Test that PINJ013 detects shadowing of common type built-ins."""
    source = """
from pinjected import instance

@instance
def dict():  # Bad - shadows built-in dict
    return {}

@instance
def list():  # Bad - shadows built-in list
    return []

@instance
def set():  # Bad - shadows built-in set
    return set()

@instance
def tuple():  # Bad - shadows built-in tuple
    return ()

@instance
def str():  # Bad - shadows built-in str
    return "hello"

@instance
def int():  # Bad - shadows built-in int
    return 42

@instance
def float():  # Bad - shadows built-in float
    return 3.14

@instance
def bool():  # Bad - shadows built-in bool
    return True
"""

    rule = PINJ013BuiltinShadowing()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect all 8 type shadows
    assert len(violations) == 8
    
    shadow_names = {v.message.split("'")[1] for v in violations}
    expected_shadows = {"dict", "list", "set", "tuple", "str", "int", "float", "bool"}
    assert shadow_names == expected_shadows
    
    for violation in violations:
        assert violation.rule_id == "PINJ013"
        assert "shadows Python built-in" in violation.message
        assert violation.severity == Severity.WARNING


def test_pinj013_detects_common_function_shadows():
    """Test that PINJ013 detects shadowing of common function built-ins."""
    source = """
from pinjected import instance, injected

@instance
def len():  # Bad - shadows built-in len
    return 10

@instance
def range():  # Bad - shadows built-in range
    return [1, 2, 3]

@injected
def filter(data_processor, /, items):  # Bad - shadows built-in filter
    return data_processor.filter(items)

@injected
def map(transformer, /, values):  # Bad - shadows built-in map
    return transformer.map(values)

@injected
def zip(combiner, /, list1, list2):  # Bad - shadows built-in zip
    return combiner.zip(list1, list2)

@injected
def open(file_handler, /, path):  # Bad - shadows built-in open
    return file_handler.open(path)

@injected
def print(logger, /, message):  # Bad - shadows built-in print
    logger.log(message)

@injected
def input(ui_handler, /):  # Bad - shadows built-in input
    return ui_handler.get_input()
"""

    rule = PINJ013BuiltinShadowing()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect all 8 function shadows
    assert len(violations) == 8
    
    for violation in violations:
        assert violation.rule_id == "PINJ013"
        assert "shadows Python built-in" in violation.message


def test_pinj013_detects_async_shadows():
    """Test that PINJ013 detects shadows in async functions."""
    source = """
from pinjected import instance, injected

@instance
async def type():  # Bad - shadows built-in type
    return await get_type()

@instance
async def hash():  # Bad - shadows built-in hash
    return await compute_hash()

@injected
async def compile(compiler, /, source):  # Bad - shadows built-in compile
    return await compiler.compile(source)

@injected
async def eval(evaluator, /, expr):  # Bad - shadows built-in eval
    return await evaluator.eval(expr)
"""

    rule = PINJ013BuiltinShadowing()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect all 4 async shadows
    assert len(violations) == 4
    
    for violation in violations:
        assert violation.rule_id == "PINJ013"
        assert "shadows Python built-in" in violation.message


def test_pinj013_allows_non_shadowing_names():
    """Test that PINJ013 allows functions that don't shadow built-ins."""
    source = """
from pinjected import instance, injected

# Good - descriptive names
@instance
def config_dict():
    return {}

@instance
def item_list():
    return []

@instance
def user_type():
    return "admin"

@instance
def file_opener():
    return FileOpener()

# Good - action-based names for @injected
@injected
def filter_items(data_processor, /, items):
    return data_processor.filter(items)

@injected
def map_values(transformer, /, values):
    return transformer.map(values)

@injected
def open_file(file_handler, /, path):
    return file_handler.open(path)

@injected
def print_message(logger, /, message):
    logger.log(message)

# Good - async functions
@instance
async def async_type_checker():
    return await get_type_checker()

@injected
async def compile_source(compiler, /, source):
    return await compiler.compile(source)
"""

    rule = PINJ013BuiltinShadowing()
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


def test_pinj013_ignores_non_decorated_functions():
    """Test that PINJ013 ignores functions without @instance or @injected decorators."""
    source = """
from pinjected import instance

# These should be ignored - no decorators
def dict():
    return {}

def list():
    return []

async def open(path):
    return open_file(path)

class MyClass:
    def type(self):
        return "MyClass"
    
    # This should be detected - has decorator
    @instance
    def filter(self):  # Bad - shadows filter
        return lambda x: x

# Regular decorated function (not pinjected) - should be ignored
@some_other_decorator
def print(message):
    pass
"""

    rule = PINJ013BuiltinShadowing()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should only detect the @instance decorated method
    assert len(violations) == 1
    assert "'filter'" in violations[0].message


def test_pinj013_detects_less_common_builtins():
    """Test that PINJ013 detects less common built-in shadows."""
    source = """
from pinjected import instance, injected

@instance
def property():  # Bad - shadows built-in property
    return Property()

@instance
def super():  # Bad - shadows built-in super
    return SuperClass()

@instance
def object():  # Bad - shadows built-in object
    return Object()

@injected
def vars(inspector, /, obj):  # Bad - shadows built-in vars
    return inspector.get_vars(obj)

@injected
def globals(scope_manager, /):  # Bad - shadows built-in globals
    return scope_manager.get_globals()

@injected
def locals(scope_manager, /):  # Bad - shadows built-in locals
    return scope_manager.get_locals()
"""

    rule = PINJ013BuiltinShadowing()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect all 6 less common shadows
    assert len(violations) == 6
    
    shadow_names = {v.message.split("'")[1] for v in violations}
    expected_shadows = {"property", "super", "object", "vars", "globals", "locals"}
    assert shadow_names == expected_shadows


def test_pinj013_suggestions_in_message():
    """Test that PINJ013 provides helpful suggestions in error messages."""
    source = """
from pinjected import instance

@instance
def dict():
    return {}

@instance
def list():
    return []

@instance
def open():
    return FileOpener()
"""

    rule = PINJ013BuiltinShadowing()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Check that suggestions are provided
    for violation in violations:
        assert violation.suggestion is not None
        assert "Consider using a more descriptive name" in violation.suggestion
        
        # Check specific suggestions
        if "'dict'" in violation.message:
            assert "config_dict" in violation.suggestion or "settings_dict" in violation.suggestion
        elif "'list'" in violation.message:
            assert "item_list" in violation.suggestion or "_list" in violation.suggestion
        elif "'open'" in violation.message:
            assert "open_file" in violation.suggestion or "file_opener" in violation.suggestion


if __name__ == "__main__":
    test_pinj013_detects_common_type_shadows()
    test_pinj013_detects_common_function_shadows()
    test_pinj013_detects_async_shadows()
    test_pinj013_allows_non_shadowing_names()
    test_pinj013_ignores_non_decorated_functions()
    test_pinj013_detects_less_common_builtins()
    test_pinj013_suggestions_in_message()
    print("All PINJ013 tests passed!")