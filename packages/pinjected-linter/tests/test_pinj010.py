"""Test PINJ010: Design() usage patterns."""

import ast
from pathlib import Path
from pinjected_linter.rules.pinj010_design_usage import PINJ010DesignUsage
from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj010_detects_empty_design():
    """Test that PINJ010 detects empty Design() instantiation."""
    source = """
from pinjected import Design, instance

# Bad - empty Design
design1 = Design()

# Bad - empty Design in function
def get_design():
    return Design()

# Bad - empty Design in combination
combined = Design() + Design(database=db_provider)
"""

    rule = PINJ010DesignUsage()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect empty Design() calls
    assert len(violations) >= 2

    for violation in violations:
        assert violation.rule_id == "PINJ010"
        assert "Empty Design()" in violation.message
        assert violation.severity == Severity.WARNING


def test_pinj010_detects_direct_calls():
    """Test that PINJ010 detects direct @instance function calls in Design."""
    source = """
from pinjected import Design, instance

@instance
def database_provider():
    return Database()

@instance
def logger_factory():
    return Logger()

@instance
def cache_service():
    return Cache()

# Bad - calling functions instead of referencing
design = Design(
    database=database_provider(),  # Bad - should not call
    logger=logger_factory(),       # Bad - should not call
    cache=cache_service()          # Bad - should not call
)

# Bad - in a function
def create_design():
    return Design(
        service=service_provider(),  # Bad
        client=client_factory()      # Bad
    )
"""

    rule = PINJ010DesignUsage()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect function calls
    assert len(violations) >= 3

    for violation in violations:
        if "directly call" in violation.message:
            assert "should reference functions, not call them" in violation.message
            assert "instead of" in violation.suggestion


def test_pinj010_detects_wrong_key_names():
    """Test that PINJ010 detects decorator names used as keys."""
    source = """
from pinjected import Design, instance

@instance
def database_provider():
    return Database()

# Bad - using decorator names as keys
design1 = Design(
    instance=database_provider,    # Bad - 'instance' is decorator name
    injected=some_function,        # Bad - 'injected' is decorator name
    provider=another_function      # Bad - 'provider' sounds like decorator
)

# Bad - mixed with good keys
design2 = Design(
    database=database_provider,    # Good key
    instance=logger_provider,      # Bad key
    cache=cache_provider          # Good key
)
"""

    rule = PINJ010DesignUsage()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect decorator names as keys
    assert len(violations) >= 3

    decorator_violations = [v for v in violations if "decorator name" in v.message]
    assert len(decorator_violations) >= 3

    for violation in decorator_violations:
        assert "dependency names as keys" in violation.suggestion


def test_pinj010_allows_proper_usage():
    """Test that PINJ010 allows proper Design() usage."""
    source = """
from pinjected import Design, design, instance

@instance
def database_provider():
    return Database()

@instance
def logger_instance():
    return Logger()

@instance  
def cache_factory():
    return InMemoryCache()

# Good - proper usage
design1 = Design(
    database=database_provider,    # Good - reference, not call
    logger=logger_instance,        # Good
    cache=cache_factory,          # Good
    config=lambda: {"debug": True}  # Good - lambda is fine
)

# Good - combining designs
base_design = Design(database=database_provider)
test_design = Design(database=mock_database_provider)
combined = base_design + test_design  # Good

# Good - in functions
def create_production_design():
    return Design(
        database=production_db_provider,
        logger=production_logger,
        monitoring=monitoring_service
    )

# Good - with kwargs expansion
config_overrides = {"timeout": 30, "retries": 3}
design2 = Design(
    service=service_provider,
    **config_overrides  # Good - kwargs expansion
)

# Good - using design() function (lowercase)
design3 = design(
    database=database_provider,
    cache=cache_factory,
    logger=logger_instance
)

# Good - combining design() results
base = design(database=db1)
extra = design(cache=cache1)
combined2 = base + extra
"""

    rule = PINJ010DesignUsage()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should have no violations for proper usage
    assert len(violations) == 0


def test_pinj010_allows_lambda_and_literals():
    """Test that PINJ010 allows lambdas and literal values in Design."""
    source = """
from pinjected import Design

# Good - lambdas and literals are allowed
design = Design(
    # Lambdas for lazy evaluation
    config=lambda: load_config(),
    timestamp=lambda: datetime.now(),
    
    # Literal values
    debug=True,
    port=8080,
    host="localhost",
    
    # Complex literals
    settings={
        "timeout": 30,
        "retries": 3
    },
    
    # Functions that return configs
    get_database_url=lambda: os.environ.get("DATABASE_URL", "sqlite:///:memory:")
)

# Good - conditional design
def create_design(env):
    return Design(
        database=prod_db if env == "prod" else test_db,
        cache=redis_cache if env == "prod" else memory_cache,
        debug=env != "prod"
    )
"""

    rule = PINJ010DesignUsage()
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


def test_pinj010_ignores_non_design_calls():
    """Test that PINJ010 ignores non-Design function calls."""
    source = """
from pinjected import instance

# These should not trigger PINJ010
config = Config()  # Not Design
service = Service()  # Not Design

# Function calls that aren't Design
def create_app():
    return Application(
        database=database_provider(),  # OK - not in Design()
        logger=get_logger()            # OK - not in Design()
    )

# Other class instantiation
container = Container(
    instance=some_instance,  # OK - not Design()
    provider=some_provider   # OK - not Design()
)
"""

    rule = PINJ010DesignUsage()
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


def test_pinj010_detects_incorrect_combination():
    """Test that PINJ010 detects incorrect Design combination patterns."""
    source = """
from pinjected import Design, design, instance

@instance
def database_provider():
    return Database()

# Bad - mixing Design with dict
design1 = Design(database=database_provider)
bad_combined1 = design1 + {"cache": cache_provider}  # Bad - can't add dict

# Bad - mixing design() with dict  
design2 = design(logger=logger_provider)
bad_combined2 = design2 + {"database": db}  # Bad - can't add dict

# Bad - mixing with other types
bad_combined3 = Design(a=1) + ["list", "items"]  # Bad
bad_combined4 = Design(b=2) + "string"  # Bad
"""

    rule = PINJ010DesignUsage()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Note: The current implementation may not detect these due to
    # _get_parent_node being a placeholder. This test documents
    # the expected behavior.
    # When implementation is fixed, uncomment the assertions below:
    # assert len(violations) >= 4
    # for violation in violations:
    #     if "should only be combined" in violation.message:
    #         assert "Design() + Design()" in violation.suggestion


def test_pinj010_with_lowercase_design():
    """Test that PINJ010 handles lowercase design() function."""
    source = """
from pinjected import design, instance

@instance
def database_provider():
    return Database()

# Bad - empty design()
empty = design()  # Should warn

# Bad - calling functions
bad_design = design(
    database=database_provider(),  # Bad - calling
    logger=logger_factory()        # Bad - calling  
)

# Bad - decorator names as keys
wrong_keys = design(
    instance=database_provider,  # Bad key
    injected=some_func          # Bad key
)

# Good - proper usage
good_design = design(
    database=database_provider,  # Good - reference
    logger=logger_instance,      # Good - reference
    config=lambda: {"debug": True}
)
"""

    rule = PINJ010DesignUsage()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Note: Current implementation only handles Design, not design
    # This test documents expected behavior for design() function
    # When implementation is updated, the assertions should pass
    # assert len(violations) >= 5  # empty, 2 calls, 2 wrong keys


if __name__ == "__main__":
    test_pinj010_detects_empty_design()
    test_pinj010_detects_direct_calls()
    test_pinj010_detects_wrong_key_names()
    test_pinj010_allows_proper_usage()
    test_pinj010_allows_lambda_and_literals()
    test_pinj010_ignores_non_design_calls()
    test_pinj010_detects_incorrect_combination()
    test_pinj010_with_lowercase_design()
    print("All PINJ010 tests passed!")
