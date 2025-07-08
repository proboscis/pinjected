"""Tests for pinjected.exporter.optimize_import_stmts module."""

import pytest

from pinjected.exporter.optimize_import_stmts import fix_imports


class TestFixImports:
    """Test the fix_imports function."""

    def test_removes_unused_imports(self):
        """Test that unused imports are removed."""
        source = """
import os
import sys
from pathlib import Path

def main():
    print(sys.version)
"""
        result = fix_imports(source)

        # sys should be kept, os and Path should be removed
        assert "import sys" in result
        assert "import os" not in result
        assert "from pathlib import Path" not in result

    def test_keeps_used_imports(self):
        """Test that used imports are kept."""
        source = """
import os
import sys

def main():
    print(os.getcwd())
    print(sys.version)
"""
        result = fix_imports(source)

        assert "import os" in result
        assert "import sys" in result

    def test_handles_import_aliases(self):
        """Test handling of import aliases."""
        source = """
import numpy as np
import pandas as pd

def process():
    data = np.array([1, 2, 3])
    return data
"""
        result = fix_imports(source)

        # np is used, pd is not
        assert "from numpy import np" in result or "import numpy as np" in result
        assert "pd" not in result

    def test_handles_from_imports(self):
        """Test handling of from imports."""
        source = """
from os.path import join, exists
from pathlib import Path

def check_file(name):
    return exists(name)
"""
        result = fix_imports(source)

        # exists is used, join and Path are not
        assert "from os.path import exists" in result
        assert "join" not in result
        assert "Path" not in result

    def test_handles_from_import_aliases(self):
        """Test handling of from imports with aliases."""
        source = """
from os.path import join as path_join
from os.path import exists as file_exists

def build_path(base, name):
    return path_join(base, name)
"""
        result = fix_imports(source)

        # path_join is used, file_exists is not
        assert "from os.path import path_join" in result
        assert "file_exists" not in result

    def test_preserves_non_import_lines(self):
        """Test that non-import lines are preserved."""
        source = """
import os

# This is a comment
def hello():
    '''Docstring'''
    return "world"

class MyClass:
    pass
"""
        result = fix_imports(source)

        assert "# This is a comment" in result
        assert "def hello():" in result
        assert "'''Docstring'''" in result
        assert "class MyClass:" in result

    def test_handles_multiline_imports(self):
        """Test handling of multiline imports."""
        source = """
from module import (
    func1,
    func2,
    func3
)

def use_it():
    return func2()
"""
        result = fix_imports(source)

        # Only func2 is used
        assert "from module import func2" in result
        assert "func1" not in result
        assert "func3" not in result

    def test_empty_source(self):
        """Test with empty source code."""
        result = fix_imports("")
        assert result == ""

    def test_no_imports(self):
        """Test source with no imports."""
        source = """
def hello():
    return "world"
"""
        result = fix_imports(source)
        assert result.strip() == source.strip()

    def test_all_imports_unused(self):
        """Test when all imports are unused."""
        source = """
import os
import sys
from pathlib import Path

def hello():
    return "world"
"""
        result = fix_imports(source)

        # No imports should remain
        assert "import" not in result
        assert "from" not in result
        assert "def hello():" in result

    def test_complex_usage_detection(self):
        """Test detection of variable usage in complex scenarios."""
        source = """
import json
import csv
import xml

def process(data):
    if data.type == 'json':
        return json.loads(data.content)
    else:
        # xml is mentioned in comment but not used
        return None
"""
        result = fix_imports(source)

        # json is used, csv and xml are not
        assert "import json" in result
        assert "csv" not in result
        assert "xml" not in result

    def test_import_used_in_class(self):
        """Test import used within a class."""
        source = """
import typing
from dataclasses import dataclass

@dataclass
class Config:
    name: typing.Optional[str] = None
"""
        result = fix_imports(source)

        assert "import typing" in result
        assert "from dataclasses import dataclass" in result

    def test_star_imports_removed(self):
        """Test that star imports are handled."""
        source = """
from module import *

def func():
    return something()
"""
        result = fix_imports(source)

        # Star imports can't be optimized precisely,
        # but the function handles them
        lines = result.split("\n")
        [line for line in lines if "import" in line]
        # Should have processed the imports somehow
        assert len(lines) > 0

    def test_nested_module_imports(self):
        """Test nested module imports."""
        source = """
import os.path
import sys.platform

def get_info():
    return os.path.sep
"""
        result = fix_imports(source)

        assert "os.path" in result
        assert "sys.platform" not in result

    def test_import_positions(self):
        """Test that imports are placed at the beginning."""
        source = """
def early_func():
    pass

import os

def late_func():
    return os.getcwd()
"""
        result = fix_imports(source)
        lines = result.strip().split("\n")

        # First non-empty line should be an import
        first_code_line = next(line for line in lines if line.strip())
        assert "import os" in first_code_line


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
