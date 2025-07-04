"""Test all implemented rules together."""

import ast
from pathlib import Path
from pinjected_linter.analyzer import PinjectedAnalyzer
from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.utils.symbol_table import SymbolTable


def test_all_rules_comprehensive():
    """Test all implemented rules with a comprehensive example."""
    source = '''
from pinjected import instance, injected, design

# PINJ001: Instance naming violations
@instance
def get_database():  # Bad - verb form
    return Database()

@instance
def create_connection():  # Bad - verb form
    return Connection()

# PINJ002: Instance default arguments
@instance
def cache(ttl=3600):  # Bad - has defaults
    return Cache(ttl)

# PINJ003: Async instance naming
@instance
async def a_redis_client():  # Bad - has a_ prefix
    return await create_redis()

# PINJ004: Direct instance call
db = get_database()  # Bad - direct call to @instance

# PINJ008: Injected dependency not declared
@injected
def process_data(transformer, /):
    return transformer.process()

@injected
def workflow(logger, /):
    # Bad - calling process_data without declaring it
    result = process_data("test")
    return result

# PINJ015: Missing slash
@injected
def analyze(database, analyzer, results):  # Bad - missing slash
    return analyzer.analyze(results)

# Good examples that should NOT trigger violations
@instance
def database_connection():  # Good - noun form
    return Database()

@instance
def model():  # Good - noun form
    return Model()

@instance
async def cache_client():  # Good - no a_ prefix
    return await create_cache()

@injected
def good_workflow(logger, process_data, /, data):  # Good - declared dependency
    result = process_data(data)
    return result

@injected
def proper_function(database, /, query):  # Good - has slash
    return database.execute(query)

# Good - using design
config = design(
    db=database_connection,  # Good - not direct call
    model=model,
)
'''
    
    # Create a temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(source)
        temp_path = Path(f.name)
    
    try:
        analyzer = PinjectedAnalyzer()
        violations = analyzer.analyze_file(temp_path)
    finally:
        temp_path.unlink()  # Clean up
    
    # Count violations by rule
    violations_by_rule = {}
    for v in violations:
        violations_by_rule[v.rule_id] = violations_by_rule.get(v.rule_id, 0) + 1
    
    # We should have violations from each rule
    assert "PINJ001" in violations_by_rule  # Instance naming
    assert "PINJ002" in violations_by_rule  # Instance defaults
    assert "PINJ003" in violations_by_rule  # Async instance naming
    assert "PINJ004" in violations_by_rule  # Direct instance call
    assert "PINJ008" in violations_by_rule  # Injected dependency
    assert "PINJ015" in violations_by_rule  # Missing slash
    
    # Check specific counts
    assert violations_by_rule["PINJ001"] == 2  # get_database, create_connection
    assert violations_by_rule["PINJ002"] == 1  # cache with ttl=3600
    assert violations_by_rule["PINJ003"] == 1  # a_redis_client
    assert violations_by_rule["PINJ004"] == 1  # direct call to get_database
    assert violations_by_rule["PINJ008"] == 1  # workflow calling process_data
    assert violations_by_rule["PINJ015"] == 1  # analyze missing slash
    
    print(f"Total violations found: {len(violations)}")
    for rule_id, count in sorted(violations_by_rule.items()):
        print(f"  {rule_id}: {count} violations")


def test_no_false_positives():
    """Test that good code doesn't trigger violations."""
    source = '''
from pinjected import instance, injected, design

# All good examples
@instance
def database():
    return Database()

@instance
def cache_manager():
    return CacheManager()

@instance
async def async_service():
    return await create_service()

@injected
def process(transformer, /, data):
    return transformer.process(data)

@injected
def workflow(logger, process, /, input_data):
    result = process(input_data)
    logger.info(f"Processed: {result}")
    return result

# Using design properly
config = design(
    db=database,
    cache=cache_manager,
    service=async_service,
)

# Regular functions are fine
def regular_function():
    return "regular"

result = regular_function()  # OK - not @instance
'''
    
    # Create a temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(source)
        temp_path = Path(f.name)
    
    try:
        analyzer = PinjectedAnalyzer()
        violations = analyzer.analyze_file(temp_path)
        
        # Should have no violations
        assert len(violations) == 0
        print("No false positives - all good code passed!")
    finally:
        temp_path.unlink()  # Clean up


if __name__ == "__main__":
    # Need to mock file reading for the analyzer
    import tempfile
    import os
    
    # Create temporary files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write test files
        test_all_path = Path(tmpdir) / "test_all.py"
        test_good_path = Path(tmpdir) / "test_good.py"
        
        # Get source from the test functions
        test_all_source = test_all_rules_comprehensive.__code__.co_consts[1]
        test_good_source = test_no_false_positives.__code__.co_consts[1]
        
        test_all_path.write_text(test_all_source)
        test_good_path.write_text(test_good_source)
        
        # Run analyzer on files
        analyzer = PinjectedAnalyzer()
        
        print("Testing all rules with violations...")
        violations = analyzer.analyze_file(test_all_path)
        violations_by_rule = {}
        for v in violations:
            violations_by_rule[v.rule_id] = violations_by_rule.get(v.rule_id, 0) + 1
        
        print(f"Total violations found: {len(violations)}")
        for rule_id, count in sorted(violations_by_rule.items()):
            print(f"  {rule_id}: {count} violations")
        
        print("\nTesting good code (no violations expected)...")
        violations = analyzer.analyze_file(test_good_path)
        print(f"Violations in good code: {len(violations)}")
        
    print("\nAll tests passed!")