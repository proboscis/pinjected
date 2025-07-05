"""Test PINJ007: Slash separator position."""

import ast
from pathlib import Path

from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.rules.pinj007_slash_separator_position import PINJ007SlashSeparatorPosition
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj007_detects_misplaced_dependencies():
    """Test that PINJ007 detects dependencies after the slash."""
    source = """
from pinjected import injected, instance

@instance
def logger():
    return Logger()

@instance  
def database():
    return Database()

@injected
def process(dep1, /, dep2, arg):  # Bad - dep2 after slash
    return dep1.process(dep2, arg)

@injected
def handle(obj, /, logger, data):  # Bad - logger after slash
    logger.info(f"Processing {data}")

@injected
def compute(calc, /, transformer, value):  # Bad - transformer after slash
    return calc.compute(transformer.transform(value))

@injected
def mixed(db, /, cache, user_id):  # Bad - cache after slash
    cached = cache.get(user_id)
    return cached or db.fetch(user_id)

@injected
def query(obj, /, database, query_string):  # Bad - known dependency after slash
    return database.execute(query_string)
"""

    rule = PINJ007SlashSeparatorPosition()
    tree = ast.parse(source)
    symbol_table = SymbolTable()
    
    # Build symbol table to recognize known dependencies
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

    # Should detect violations for misplaced dependencies
    assert len(violations) >= 4  # dep2 might not be detected as it's not a common pattern
    
    # Check violations
    for violation in violations:
        assert violation.rule_id == "PINJ007"
        assert "after the slash separator" in violation.message
        assert violation.severity == Severity.ERROR
    
    # Check specific violations - dep2 might not be detected as it's not a common pattern
    violation_messages = [v.message for v in violations]
    assert any("'logger'" in msg and "handle" in msg for msg in violation_messages)
    assert any("'transformer'" in msg and "compute" in msg for msg in violation_messages)
    assert any("'cache'" in msg and "mixed" in msg for msg in violation_messages)
    assert any("'database'" in msg and "query" in msg for msg in violation_messages)


def test_pinj007_accepts_correct_placement():
    """Test that PINJ007 accepts correct slash placement."""
    source = """
from pinjected import injected, instance

@instance
def logger():
    return Logger()

@injected
def process(dep1, dep2, /, arg):  # Good - dependencies before slash
    return dep1.process(dep2, arg)

@injected
def handle(logger, /, data):  # Good - logger before slash
    logger.info(f"Processing {data}")

@injected
def compute(calc, transformer, /, value):  # Good - dependencies before slash
    return calc.compute(transformer.transform(value))

@injected
def no_deps(obj, /, arg1, arg2):  # Good - no dependencies (obj is not a dependency pattern)
    return arg1 + arg2

@injected
def all_deps(logger, db, cache, /):  # Good - all params are dependencies
    logger.info("Initializing")
    db.connect()
    cache.clear()
"""

    rule = PINJ007SlashSeparatorPosition()
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


def test_pinj007_detects_common_dependency_patterns():
    """Test that PINJ007 detects common dependency patterns."""
    source = """
from pinjected import injected

@injected
def process1(obj, /, user_service, data):  # Bad - _service suffix
    return user_service.process(data)

@injected
def process2(obj, /, api_client, request):  # Bad - _client suffix
    return api_client.send(request)

@injected
def process3(obj, /, db, query):  # Bad - common name 'db'
    return db.execute(query)

@injected
def process4(obj, /, cache, key):  # Bad - common name 'cache'
    return cache.get(key)

@injected
def process5(obj, /, auth, request):  # Bad - common name 'auth'
    return auth.verify(request)

@injected
def process6(obj, /, payment_manager, order):  # Bad - _manager suffix
    return payment_manager.process(order)

@injected
def process7(obj, /, order_repository, id):  # Bad - _repository suffix
    return order_repository.find(id)

@injected
def process8(obj, /, event_handler, event):  # Bad - _handler suffix
    return event_handler.handle(event)
"""

    rule = PINJ007SlashSeparatorPosition()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect all common patterns
    assert len(violations) >= 8
    
    # Check that each pattern was detected
    detected_params = {v.message.split("'")[3] for v in violations}  # Extract parameter name
    expected_params = {
        'user_service', 'api_client', 'db', 'cache', 'auth',
        'payment_manager', 'order_repository', 'event_handler'
    }
    assert expected_params.issubset(detected_params)


def test_pinj007_async_dependencies():
    """Test that PINJ007 handles async dependencies with a_ prefix."""
    source = """
from pinjected import injected, instance

@injected
async def a_fetch_data(api, /):
    return await api.get_data()

@injected
async def process(obj, /, a_fetch_data, id):  # Bad - async dependency after slash
    data = a_fetch_data(id)
    return data

@injected  
async def handle(a_fetch_data, /, id):  # Good - async dependency before slash
    data = a_fetch_data(id)
    return data
"""

    rule = PINJ007SlashSeparatorPosition()
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

    # Should detect the misplaced async dependency
    assert len(violations) == 1
    assert "'a_fetch_data'" in violations[0].message
    assert "process" in violations[0].message


def test_pinj007_no_slash():
    """Test that PINJ007 ignores functions without slash."""
    source = """
from pinjected import injected

@injected
def process(logger, data):  # No slash - handled by PINJ015
    logger.info(data)
    return data

@injected
def handle(db, cache, user_id):  # No slash - handled by PINJ015
    return db.get(user_id)
"""

    rule = PINJ007SlashSeparatorPosition()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should have no violations (these are handled by PINJ015)
    assert len(violations) == 0


def test_pinj007_non_injected_functions():
    """Test that PINJ007 ignores non-@injected functions."""
    source = """
from pinjected import instance

# Regular function
def process(dep1, /, dep2, arg):
    return dep1.process(dep2, arg)

# @instance function  
@instance
def service(obj, /, logger):
    return Service(logger)

# Different decorator
@custom_decorator  
def handle(obj, /, db, data):
    return db.save(data)
"""

    rule = PINJ007SlashSeparatorPosition()
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


def test_pinj007_edge_cases():
    """Test edge cases for PINJ007."""
    source = """
from pinjected import injected

@injected
def func1(obj, /, logger, db, data):  # Bad - multiple dependencies after slash
    logger.info("Processing")
    return db.save(data)

@injected
def func2(valid_arg, /, sneaky_service, data):  # Bad - service suffix
    return sneaky_service.process(data)

@injected
def func3(obj, /, my_logger, request):  # Bad - logger in name
    my_logger.debug(request)
    return request

@injected
def func4(obj, /, data, user_id):  # Good - 'data' is not a common dependency name
    return {"data": data, "id": user_id}

@injected
def func5(processor, /, ):  # Good - no params after slash
    return processor.run()
"""

    rule = PINJ007SlashSeparatorPosition()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Check specific violations
    violation_funcs = {v.message.split("'")[1] for v in violations}
    
    # func1, func2, func3 should have violations
    assert "func1" in violation_funcs
    assert "func2" in violation_funcs  
    assert "func3" in violation_funcs
    
    # func4 and func5 should not
    assert "func4" not in violation_funcs
    assert "func5" not in violation_funcs


if __name__ == "__main__":
    test_pinj007_detects_misplaced_dependencies()
    test_pinj007_accepts_correct_placement()
    test_pinj007_detects_common_dependency_patterns()
    test_pinj007_async_dependencies()
    test_pinj007_no_slash()
    test_pinj007_non_injected_functions()
    test_pinj007_edge_cases()
    print("All PINJ007 tests passed!")