"""Test PINJ015: Missing slash in injected."""

import ast
from pathlib import Path

from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.rules.pinj015_missing_slash import PINJ015MissingSlash
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj015_detects_missing_slash():
    """Test that PINJ015 detects @injected functions missing the slash separator."""
    source = '''
from pinjected import injected

@injected
def process_data(logger, transformer, data):
    # Without slash, ALL args (logger, transformer, data) are runtime args
    # This means NO dependencies will be injected!
    logger.info("Processing data")
    return transformer.process(data)

@injected
def analyze_results(database, cache, analyzer, results):
    # Without slash, these are ALL runtime args - no injection
    cache.set("key", results)
    return analyzer.analyze(results)

@injected
async def a_fetch_data(client, a_prepare_dataset, input_path):
    # Async with no slash - all args are runtime args
    dataset = a_prepare_dataset(input_path)
    return await client.fetch(dataset)

@injected
def only_runtime_args(input_data, output_format):
    # Even though these don't look like dependencies,
    # without slash they're runtime args (which they already would be)
    return format_data(input_data, output_format)
'''
    
    rule = PINJ015MissingSlash()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )
    
    violations = rule.check(context)
    
    # Should detect 4 violations - ANY @injected with args but no slash
    assert len(violations) == 4
    
    # Check violations
    for violation in violations:
        assert violation.rule_id == "PINJ015"
        assert "missing the '/' separator" in violation.message
        assert "ALL arguments are treated as runtime arguments" in violation.message
        assert violation.severity == Severity.ERROR


def test_pinj015_allows_proper_slash_usage():
    """Test that PINJ015 allows @injected functions with proper slash usage."""
    source = '''
from pinjected import injected

@injected
def process_data(logger, transformer, /, data):
    # Good - slash properly separates dependencies from runtime args
    logger.info("Processing data")
    return transformer.process(data)

@injected
def only_runtime(request):
    # No dependencies - just runtime args (warning expected but valid use case)
    return {"status": "ok", "data": request}

@injected
def only_dependencies(logger, database, /):
    # Good - only dependencies, no runtime args
    logger.info("Initialized")
    return database.connect()

@injected
async def a_complex_handler(
    logger,
    cache,
    a_fetch_data,
    a_process_data,
    /,
    request_id: str,
    options: dict
):
    # Good - multiple dependencies and runtime args properly separated
    data = await a_fetch_data(request_id)
    return await a_process_data(data, options)
'''
    
    rule = PINJ015MissingSlash()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )
    
    violations = rule.check(context)
    
    # Should detect 1 violation - only_runtime has args but no slash
    assert len(violations) == 1
    assert "only_runtime" in violations[0].message


def test_pinj015_ignores_non_injected_functions():
    """Test that PINJ015 ignores functions without @injected decorator."""
    source = '''
from pinjected import instance

def regular_function(logger, data):
    # Not @injected, no slash needed
    return data

@instance
def database_connection(host, port):
    # @instance functions don't need slash
    return Database(host, port)

class MyClass:
    def method(self, logger, data):
        # Class methods don't need slash
        return self.process(data)
'''
    
    rule = PINJ015MissingSlash()
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


def test_pinj015_handles_edge_cases():
    """Test that PINJ015 handles edge cases correctly."""
    source = '''
from pinjected import injected

@injected
def no_args():
    # No arguments at all - should not trigger
    return "result"

@injected
def keyword_only_args(*, key1, key2):
    # Keyword-only args without slash - should trigger
    return process(key1, key2)

@injected
def mixed_case(Logger, Database, userData):
    # Without slash, ALL are runtime args - should trigger
    return Database.save(userData)

@injected
def single_arg(logger):
    # Even single arg needs slash if it's meant to be injected
    logger.info("Hello")
    return True
'''
    
    rule = PINJ015MissingSlash()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )
    
    violations = rule.check(context)
    
    # Should detect 3 violations (all with args but no slash)
    assert len(violations) == 3
    
    # Check specific functions
    violation_funcs = {v.message.split("'")[1] for v in violations}
    assert violation_funcs == {"keyword_only_args", "mixed_case", "single_arg"}


if __name__ == "__main__":
    test_pinj015_detects_missing_slash()
    test_pinj015_allows_proper_slash_usage()
    test_pinj015_ignores_non_injected_functions()
    test_pinj015_handles_edge_cases()
    print("All PINJ015 tests passed!")