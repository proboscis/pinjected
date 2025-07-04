"""Test PinjectedAnalyzer functionality."""

import ast
import multiprocessing
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pinjected_linter.analyzer import PinjectedAnalyzer, SymbolTableBuilder
from pinjected_linter.models import RuleContext, Severity, Violation
from pinjected_linter.rules.base import BaseRule
from pinjected_linter.utils.symbol_table import SymbolTable


def test_symbol_table_builder_import():
    """Test SymbolTableBuilder handling import statements."""
    source = '''
import os
import sys as system
import pathlib.Path
'''
    tree = ast.parse(source)
    symbol_table = SymbolTable()
    builder = SymbolTableBuilder(symbol_table)
    builder.visit(tree)
    
    # Check imports were added
    assert "os" in symbol_table.imports
    assert symbol_table.imports["os"] == "os"
    assert "system" in symbol_table.imports
    assert symbol_table.imports["system"] == "sys"
    assert "pathlib.Path" in symbol_table.imports
    assert symbol_table.imports["pathlib.Path"] == "pathlib.Path"


def test_symbol_table_builder_import_from():
    """Test SymbolTableBuilder handling from-import statements."""
    source = '''
from os import path
from sys import exit as sys_exit
from pathlib import Path, PosixPath
'''
    tree = ast.parse(source)
    symbol_table = SymbolTable()
    builder = SymbolTableBuilder(symbol_table)
    builder.visit(tree)
    
    # Check imports were added
    assert "path" in symbol_table.imports
    assert symbol_table.imports["path"] == "os.path"
    assert "sys_exit" in symbol_table.imports
    assert symbol_table.imports["sys_exit"] == "sys.exit"
    assert "Path" in symbol_table.imports
    assert symbol_table.imports["Path"] == "pathlib.Path"
    assert "PosixPath" in symbol_table.imports
    assert symbol_table.imports["PosixPath"] == "pathlib.PosixPath"


def test_analyzer_syntax_error():
    """Test analyzer handling files with syntax errors."""
    analyzer = PinjectedAnalyzer()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("def invalid syntax")
        temp_path = Path(f.name)
    
    try:
        violations = analyzer.analyze_file(temp_path)
        assert violations == []  # Should return empty list on syntax error
    finally:
        temp_path.unlink()


def test_analyzer_unicode_error():
    """Test analyzer handling files with unicode errors."""
    analyzer = PinjectedAnalyzer()
    
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.py', delete=False) as f:
        # Write invalid UTF-8 bytes
        f.write(b'\xff\xfe invalid unicode')
        temp_path = Path(f.name)
    
    try:
        violations = analyzer.analyze_file(temp_path)
        assert violations == []  # Should return empty list on unicode error
    finally:
        temp_path.unlink()


class ErrorRule(BaseRule):
    """Test rule that raises an exception."""
    
    rule_id = "TEST001"
    name = "Error Rule"
    description = "Rule that always errors"
    severity = Severity.ERROR
    category = "test"
    
    def check(self, context: RuleContext):
        raise RuntimeError("Test error")


def test_analyzer_rule_error(capsys):
    """Test analyzer handling rule exceptions."""
    analyzer = PinjectedAnalyzer()
    
    # Monkey patch to include our error rule
    original_rules = analyzer.enabled_rules
    analyzer.enabled_rules = [ErrorRule]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("# Valid Python code\n")
        temp_path = Path(f.name)
    
    try:
        violations = analyzer.analyze_file(temp_path)
        assert violations == []  # Should return empty list when rule errors
        
        # Check error was printed
        captured = capsys.readouterr()
        assert "Error in rule TEST001: Test error" in captured.out
    finally:
        temp_path.unlink()
        analyzer.enabled_rules = original_rules


def test_analyzer_get_rule_config():
    """Test analyzer getting rule-specific configuration."""
    config = {
        "rules": {
            "PINJ001": {"enabled": False},
            "PINJ002": {"severity": "warning"},
        }
    }
    analyzer = PinjectedAnalyzer(config=config)
    
    # Test getting config for configured rule
    rule_config = analyzer._get_rule_config("PINJ001")
    assert rule_config == {"enabled": False}
    
    # Test getting config for unconfigured rule
    rule_config = analyzer._get_rule_config("PINJ999")
    assert rule_config == {}


def test_analyzer_parallel_mode():
    """Test analyzer parallel mode initialization."""
    # Test with parallel=True (default)
    analyzer1 = PinjectedAnalyzer()
    assert analyzer1.parallel == (multiprocessing.cpu_count() > 1)
    
    # Test with parallel=False
    analyzer2 = PinjectedAnalyzer(parallel=False)
    assert analyzer2.parallel is False
    
    # Test with parallel=True but single CPU
    with patch('multiprocessing.cpu_count', return_value=1):
        analyzer3 = PinjectedAnalyzer(parallel=True)
        assert analyzer3.parallel is False


def test_analyzer_analyze_files_single():
    """Test analyze_files with single file (no parallel)."""
    analyzer = PinjectedAnalyzer(parallel=False)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test file
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text("# Test file")
        
        violations = analyzer.analyze_files([test_file])
        assert isinstance(violations, list)


def test_analyzer_analyze_files_parallel():
    """Test analyze_files with multiple files in parallel mode."""
    analyzer = PinjectedAnalyzer(parallel=True)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create multiple test files
        files = []
        for i in range(3):
            test_file = Path(tmpdir) / f"test{i}.py"
            test_file.write_text(f"# Test file {i}")
            files.append(test_file)
        
        # Force parallel mode even with few files
        if multiprocessing.cpu_count() > 1:
            violations = analyzer.analyze_files(files)
            assert isinstance(violations, list)


def test_analyzer_analyze_files_parallel_error(capsys):
    """Test parallel analysis with file processing error."""
    analyzer = PinjectedAnalyzer(parallel=True)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a valid file and a non-existent file
        valid_file = Path(tmpdir) / "valid.py"
        valid_file.write_text("# Valid")
        invalid_file = Path(tmpdir) / "nonexistent.py"
        
        # Mock analyze_file to raise exception for invalid file
        original_analyze = analyzer.analyze_file
        
        def mock_analyze(path):
            if path == invalid_file:
                raise Exception("File not found")
            return original_analyze(path)
        
        analyzer.analyze_file = mock_analyze
        
        # This should handle the error gracefully
        violations = analyzer._analyze_files_parallel([valid_file, invalid_file])
        
        # Check error was printed
        captured = capsys.readouterr()
        assert "Error analyzing" in captured.out


def test_analyzer_severity_override():
    """Test severity override in configuration."""
    config = {
        "severity": {
            "PINJ001": "warning",
            "PINJ002": "info"
        }
    }
    analyzer = PinjectedAnalyzer(config=config)
    
    # Test severity override
    config1 = analyzer._get_rule_config("PINJ001")
    assert config1["severity"] == "warning"
    
    config2 = analyzer._get_rule_config("PINJ002")
    assert config2["severity"] == "info"
    
    # Test rule without override
    config3 = analyzer._get_rule_config("PINJ003")
    assert "severity" not in config3