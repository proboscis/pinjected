"""Test PINJ014: Missing .pyi stub file."""

import ast
import tempfile
from pathlib import Path

from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.rules.pinj014_missing_stub_file import PINJ014MissingStubFile
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj014_detects_missing_stub_file():
    """Test that PINJ014 detects missing .pyi stub file for modules with @injected functions."""
    source = '''
from pinjected import injected

@injected
def fetch_user(db, /, user_id: str):
    return db.get_user(user_id)

@injected
def update_user(db, /, user_id: str, data: dict):
    return db.update_user(user_id, data)

def regular_function():
    return "not injected"
'''
    
    rule = PINJ014MissingStubFile()
    tree = ast.parse(source)
    
    # Mock file path that doesn't have a corresponding .pyi file
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "services" / "user_service.py"
        file_path.parent.mkdir(parents=True)
        file_path.write_text(source)
        
        context = RuleContext(
            file_path=file_path,
            source=source,
            tree=tree,
            symbol_table=SymbolTable(),
            config={},
        )
        
        violations = rule.check(context)
        
        # Should detect 1 violation
        assert len(violations) == 1
        
        violation = violations[0]
        assert violation.rule_id == "PINJ014"
        assert "2 @injected function(s)" in violation.message
        assert ".pyi stub file found" in violation.message
        assert violation.severity == Severity.WARNING
        assert violation.suggestion is not None
        assert "Create a stub file at:" in violation.suggestion
        assert "user_service.pyi" in violation.suggestion
        assert "@injected" in violation.suggestion
        assert "def fetch_user(" in violation.suggestion


def test_pinj014_no_violation_with_stub_file():
    """Test that PINJ014 doesn't report violation when .pyi file exists."""
    source = '''
from pinjected import injected

@injected
def process_data(transformer, /, data):
    return transformer.process(data)
'''
    
    rule = PINJ014MissingStubFile()
    tree = ast.parse(source)
    
    # Create both .py and .pyi files
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "processor.py"
        stub_path = Path(tmpdir) / "processor.pyi"
        
        file_path.write_text(source)
        stub_path.write_text("# Stub file")
        
        context = RuleContext(
            file_path=file_path,
            source=source,
            tree=tree,
            symbol_table=SymbolTable(),
            config={},
        )
        
        violations = rule.check(context)
        
        # Should detect no violations
        assert len(violations) == 0


def test_pinj014_no_violation_without_injected():
    """Test that PINJ014 doesn't report violation for modules without @injected functions."""
    source = '''
from pinjected import instance

@instance
def database():
    return Database()

def regular_function():
    return "not injected"

class MyClass:
    def method(self):
        pass
'''
    
    rule = PINJ014MissingStubFile()
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


def test_pinj014_async_injected_functions():
    """Test that PINJ014 detects async @injected functions."""
    source = '''
from pinjected import injected

@injected
async def a_fetch_data(api, /, endpoint: str):
    return await api.get(endpoint)

@injected
async def a_process_data(processor, /, data):
    return await processor.process(data)
'''
    
    rule = PINJ014MissingStubFile()
    tree = ast.parse(source)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "async_service.py"
        file_path.write_text(source)
        
        context = RuleContext(
            file_path=file_path,
            source=source,
            tree=tree,
            symbol_table=SymbolTable(),
            config={},
        )
        
        violations = rule.check(context)
        
        # Should detect 1 violation
        assert len(violations) == 1
        
        violation = violations[0]
        assert "2 @injected function(s)" in violation.message
        assert "async def a_fetch_data" in violation.suggestion


def test_pinj014_respects_min_injected_functions_config():
    """Test that PINJ014 respects min_injected_functions configuration."""
    source = '''
from pinjected import injected

@injected
def single_function(dep, /):
    return dep.do_something()
'''
    
    # Test with min_injected_functions = 2
    rule = PINJ014MissingStubFile(config={"min_injected_functions": 2})
    tree = ast.parse(source)
    
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={"min_injected_functions": 2},
    )
    
    violations = rule.check(context)
    
    # Should detect no violations (only 1 function, minimum is 2)
    assert len(violations) == 0
    
    # Test with min_injected_functions = 1 (default)
    rule = PINJ014MissingStubFile()
    violations = rule.check(context)
    
    # Should detect 1 violation
    assert len(violations) == 1


def test_pinj014_respects_ignore_patterns():
    """Test that PINJ014 respects ignore_patterns configuration."""
    source = '''
from pinjected import injected

@injected
def test_helper(mock, /):
    return mock.helper()
'''
    
    rule = PINJ014MissingStubFile(config={
        "ignore_patterns": ["**/tests/**", "**/migrations/**"]
    })
    tree = ast.parse(source)
    
    # Test file in tests directory
    context = RuleContext(
        file_path=Path("project/tests/test_utils.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={"ignore_patterns": ["**/tests/**", "**/migrations/**"]},
    )
    
    violations = rule.check(context)
    
    # Should detect no violations (file is in ignored pattern)
    assert len(violations) == 0
    
    # Test file in regular directory
    context.file_path = Path("project/src/utils.py")
    violations = rule.check(context)
    
    # Should detect 1 violation
    assert len(violations) == 1


def test_pinj014_checks_alternative_stub_paths():
    """Test that PINJ014 checks alternative stub directories."""
    source = '''
from pinjected import injected

@injected
def service(config, /):
    return Service(config)
'''
    
    rule = PINJ014MissingStubFile(config={
        "stub_search_paths": ["stubs", "typings"]
    })
    tree = ast.parse(source)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "src" / "service.py"
        file_path.parent.mkdir(parents=True)
        file_path.write_text(source)
        
        # Create stub in alternative location
        stub_dir = file_path.parent / "stubs"
        stub_dir.mkdir()
        stub_path = stub_dir / "service.pyi"
        stub_path.write_text("# Stub file")
        
        context = RuleContext(
            file_path=file_path,
            source=source,
            tree=tree,
            symbol_table=SymbolTable(),
            config={"stub_search_paths": ["stubs", "typings"]},
        )
        
        violations = rule.check(context)
        
        # Should detect no violations (stub found in alternative location)
        assert len(violations) == 0


def test_pinj014_suggestion_shows_multiple_functions():
    """Test that PINJ014 suggestion shows multiple function signatures."""
    source = '''
from pinjected import injected

@injected
def fetch_user(db, /, user_id: str):
    return db.get_user(user_id)

@injected
def update_user(db, /, user_id: str, data: dict):
    return db.update_user(user_id, data)

@injected
def delete_user(db, /, user_id: str):
    return db.delete_user(user_id)

@injected
def list_users(db, /, filter: dict = None):
    return db.list_users(filter)

@injected
async def a_get_user_stats(stats_api, /, user_id: str):
    return await stats_api.get_stats(user_id)
'''
    
    rule = PINJ014MissingStubFile()
    tree = ast.parse(source)
    
    context = RuleContext(
        file_path=Path("user_service.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )
    
    violations = rule.check(context)
    
    assert len(violations) == 1
    violation = violations[0]
    
    # Check suggestion content
    assert "def fetch_user(" in violation.suggestion
    assert "def update_user(" in violation.suggestion
    assert "def delete_user(" in violation.suggestion
    assert "... and 2 more @injected functions" in violation.suggestion
    assert "async def a_get_user_stats(" not in violation.suggestion  # Beyond first 3


def test_pinj014_empty_module():
    """Test that PINJ014 handles empty modules correctly."""
    source = ''
    
    rule = PINJ014MissingStubFile()
    tree = ast.parse(source)
    
    context = RuleContext(
        file_path=Path("empty.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )
    
    violations = rule.check(context)
    
    # Should detect no violations
    assert len(violations) == 0


def test_pinj014_mixed_decorators():
    """Test that PINJ014 only counts @injected functions, not @instance."""
    source = '''
from pinjected import injected, instance

@instance
def database():
    return Database()

@injected
def fetch_data(db, /, query):
    return db.execute(query)

@instance
def cache():
    return Cache()
'''
    
    rule = PINJ014MissingStubFile()
    tree = ast.parse(source)
    
    context = RuleContext(
        file_path=Path("mixed.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )
    
    violations = rule.check(context)
    
    # Should detect 1 violation (only 1 @injected function)
    assert len(violations) == 1
    assert "1 @injected function(s)" in violations[0].message


if __name__ == "__main__":
    test_pinj014_detects_missing_stub_file()
    test_pinj014_no_violation_with_stub_file()
    test_pinj014_no_violation_without_injected()
    test_pinj014_async_injected_functions()
    test_pinj014_respects_min_injected_functions_config()
    test_pinj014_respects_ignore_patterns()
    test_pinj014_checks_alternative_stub_paths()
    test_pinj014_suggestion_shows_multiple_functions()
    test_pinj014_empty_module()
    test_pinj014_mixed_decorators()
    print("All PINJ014 tests passed!")