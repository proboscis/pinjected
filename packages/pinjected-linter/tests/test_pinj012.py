"""Test PINJ012: Dependency cycles detection."""

import ast
from pathlib import Path

from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.rules.pinj012_dependency_cycles import PINJ012DependencyCycles
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj012_detects_simple_cycle():
    """Test that PINJ012 detects simple A → B → A cycles."""
    source = """
from pinjected import injected

@injected
def service_a(service_b, /):
    return f"A uses {service_b()}"

@injected
def service_b(service_a, /):
    return f"B uses {service_a()}"
"""

    rule = PINJ012DependencyCycles()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect the cycle
    assert len(violations) >= 1
    
    violation = violations[0]
    assert violation.rule_id == "PINJ012"
    assert "Circular dependency detected" in violation.message
    assert "service_a → service_b → service_a" in violation.message
    assert violation.severity == Severity.ERROR


def test_pinj012_detects_complex_cycle():
    """Test that PINJ012 detects complex multi-step cycles."""
    source = """
from pinjected import injected

@injected
def auth_service(user_service, /, request):
    user = user_service(request.user_id)
    return validate_auth(user)

@injected
def user_service(database_service, /, user_id):
    return database_service(f"SELECT * FROM users WHERE id={user_id}")

@injected
def database_service(logger_service, /, query):
    logger_service(f"Executing: {query}")
    return execute_query(query)

@injected
def logger_service(auth_service, /, message):
    if auth_service.is_admin():
        log_admin_action(message)
    return log(message)
"""

    rule = PINJ012DependencyCycles()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect the complex cycle
    assert len(violations) >= 1
    
    violation = violations[0]
    assert violation.rule_id == "PINJ012"
    assert "Circular dependency detected" in violation.message
    # The cycle should be reported (order might vary based on detection algorithm)
    assert "auth_service" in violation.message
    assert "user_service" in violation.message
    assert "database_service" in violation.message
    assert "logger_service" in violation.message


def test_pinj012_detects_self_reference():
    """Test that PINJ012 detects self-referencing functions."""
    source = """
from pinjected import injected

@injected
def recursive_service(recursive_service, /, data):
    if data:
        return recursive_service(data[1:])
    return []
"""

    rule = PINJ012DependencyCycles()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect self-reference
    assert len(violations) >= 1
    
    violation = violations[0]
    assert violation.rule_id == "PINJ012"
    assert "Circular dependency detected" in violation.message
    assert "recursive_service → recursive_service" in violation.message


def test_pinj012_detects_multiple_cycles():
    """Test that PINJ012 detects multiple independent cycles."""
    source = """
from pinjected import injected

# First cycle: A → B → A
@injected
def service_a(service_b, /):
    return service_b()

@injected
def service_b(service_a, /):
    return service_a()

# Second cycle: X → Y → Z → X
@injected
def service_x(service_y, /):
    return service_y()

@injected
def service_y(service_z, /):
    return service_z()

@injected
def service_z(service_x, /):
    return service_x()

# No cycle
@injected
def service_independent(data):
    # No slash means all args are runtime args, no dependencies
    return data
"""

    rule = PINJ012DependencyCycles()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect both cycles
    assert len(violations) >= 2
    
    # Check that both cycles are reported
    messages = [v.message for v in violations]
    cycles_found = []
    
    for msg in messages:
        if "service_a" in msg and "service_b" in msg:
            cycles_found.append("AB")
        elif "service_x" in msg and "service_y" in msg and "service_z" in msg:
            cycles_found.append("XYZ")
    
    assert "AB" in cycles_found
    assert "XYZ" in cycles_found


def test_pinj012_allows_valid_hierarchy():
    """Test that PINJ012 allows valid dependency hierarchies without cycles."""
    source = """
from pinjected import injected

# Layer 1: Core utilities (no dependencies)
@injected
def logger(message):
    # No dependencies - all runtime args
    print(f"[LOG] {message}")

@injected
def config(key):
    # No dependencies - all runtime args
    return get_config(key)

# Layer 2: Services using core utilities
@injected
def database(logger, config, /, query):
    logger(f"Query: {query}")
    db_config = config("database")
    return execute_query(query, db_config)

# Layer 3: Business logic using services
@injected
def user_service(database, logger, /, user_id):
    logger(f"Fetching user {user_id}")
    return database(f"SELECT * FROM users WHERE id={user_id}")

@injected
def auth_service(database, logger, /, token):
    logger(f"Validating token")
    return database(f"SELECT * FROM tokens WHERE token='{token}'")

# Layer 4: API using business logic
@injected
def api_handler(user_service, auth_service, logger, /, request):
    logger(f"API request from {request.ip}")
    if auth_service(request.token):
        return user_service(request.user_id)
    return {"error": "Unauthorized"}
"""

    rule = PINJ012DependencyCycles()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should have no violations - this is a valid hierarchy
    assert len(violations) == 0


def test_pinj012_handles_no_dependencies():
    """Test that PINJ012 handles functions with no dependencies."""
    source = """
from pinjected import injected

@injected
def standalone_service(data):
    # No dependencies - all runtime args
    return process(data)

@injected
def another_standalone(x, y):
    # No dependencies - all runtime args
    return x + y

# All runtime args, no dependencies
@injected
def pure_function(a, b, c):
    return a + b + c
"""

    rule = PINJ012DependencyCycles()
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


def test_pinj012_handles_async_functions():
    """Test that PINJ012 handles async @injected functions."""
    source = """
from pinjected import injected

@injected
async def a_service_a(a_service_b, /, data):
    result = a_service_b(data)
    return result

@injected  
async def a_service_b(a_service_a, /, data):
    result = a_service_a(data)
    return result
"""

    rule = PINJ012DependencyCycles()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect cycle in async functions
    assert len(violations) >= 1
    
    violation = violations[0]
    assert "a_service_a" in violation.message
    assert "a_service_b" in violation.message


def test_pinj012_ignores_non_injected_functions():
    """Test that PINJ012 ignores functions without @injected decorator."""
    source = """
from pinjected import injected, instance

# Regular functions - should be ignored
def func_a(func_b):
    return func_b()

def func_b(func_a):
    return func_a()

# @instance functions - should be ignored
@instance
def instance_a(instance_b):
    return instance_b

@instance
def instance_b(instance_a):
    return instance_a

# Valid @injected function
@injected
def service(data):
    # No dependencies - all runtime args
    return data
"""

    rule = PINJ012DependencyCycles()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should have no violations - cycles in non-@injected functions are ignored
    assert len(violations) == 0


def test_pinj012_handles_partial_cycles():
    """Test detection of cycles that don't include all functions."""
    source = """
from pinjected import injected

@injected
def entry_point(service_a, /, request):
    # entry_point depends on service_a but is not part of the cycle
    return service_a(request)

@injected
def service_a(service_b, /, data):
    return service_b(data)

@injected
def service_b(service_c, /, data):
    return service_c(data)

@injected
def service_c(service_a, /, data):
    # Creates cycle: A → B → C → A
    return service_a(data)

@injected
def unrelated_service(data):
    # Not part of any cycle - no dependencies
    return data
"""

    rule = PINJ012DependencyCycles()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect the A → B → C → A cycle
    assert len(violations) >= 1
    
    violation = violations[0]
    assert "service_a" in violation.message
    assert "service_b" in violation.message
    assert "service_c" in violation.message
    # entry_point should not be part of the reported cycle
    assert "entry_point" not in violation.message


if __name__ == "__main__":
    test_pinj012_detects_simple_cycle()
    test_pinj012_detects_complex_cycle()
    test_pinj012_detects_self_reference()
    test_pinj012_detects_multiple_cycles()
    test_pinj012_allows_valid_hierarchy()
    test_pinj012_handles_no_dependencies()
    test_pinj012_handles_async_functions()
    test_pinj012_ignores_non_injected_functions()
    test_pinj012_handles_partial_cycles()
    print("All PINJ012 tests passed!")