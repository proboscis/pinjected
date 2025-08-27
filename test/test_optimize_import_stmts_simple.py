"""Simple tests for exporter/optimize_import_stmts.py module to improve coverage."""

import pytest
from pinjected.exporter.optimize_import_stmts import fix_imports


class TestFixImports:
    """Test the fix_imports function."""

    def test_fix_imports_removes_unused_imports(self):
        """Test that unused imports are removed."""
        source = """import os
import sys
import json
from pathlib import Path

def main():
    print(sys.version)
    return Path("test")
"""

        result = fix_imports(source)

        # Should keep sys and Path, remove os and json
        assert "import sys" in result
        assert "from pathlib import Path" in result
        assert "import os" not in result
        assert "import json" not in result

        # Should have the function intact
        assert "def main():" in result
        assert "print(sys.version)" in result

    def test_fix_imports_handles_aliased_imports(self):
        """Test handling of aliased imports."""
        source = """import numpy as np
import pandas as pd
from datetime import datetime as dt

def process():
    data = np.array([1, 2, 3])
    return data
"""

        result = fix_imports(source)

        # Should keep numpy as np, remove pandas and datetime
        assert "from numpy import np" in result
        assert "pandas" not in result
        assert "datetime" not in result
        assert "def process():" in result

    def test_fix_imports_handles_from_imports(self):
        """Test handling of from imports."""
        source = """from os.path import join, dirname, exists
from collections import defaultdict, Counter

def build_path():
    return join(dirname(__file__), "data")
"""

        result = fix_imports(source)

        # Should keep join and dirname, remove exists, defaultdict, Counter
        assert "from os.path import join" in result
        assert "from os.path import dirname" in result
        assert "exists" not in result
        assert "defaultdict" not in result
        assert "Counter" not in result

    def test_fix_imports_preserves_direct_module_usage(self):
        """Test that direct module imports are preserved when used."""
        source = """import os
import sys

def get_info():
    print(os.name)
    return sys.platform
"""

        result = fix_imports(source)

        # Should keep both os and sys
        assert "import os" in result
        assert "import sys" in result

    def test_fix_imports_empty_source(self):
        """Test fix_imports with empty source."""
        source = ""
        result = fix_imports(source)

        # Should return empty or just newline
        assert result.strip() == ""

    def test_fix_imports_no_imports(self):
        """Test fix_imports with no imports."""
        source = """def hello():
    return "Hello, World!"

print(hello())
"""

        result = fix_imports(source)

        # Should preserve the code
        assert "def hello():" in result
        assert 'return "Hello, World!"' in result
        assert "print(hello())" in result

    def test_fix_imports_multiple_import_styles(self):
        """Test with multiple import styles mixed."""
        source = """import json
from typing import List, Dict, Optional
import re as regex
from datetime import datetime
import os.path

def parse_data(data: List[Dict]) -> Optional[str]:
    if not data:
        return None
    return json.dumps(data)
"""

        result = fix_imports(source)

        # Should keep json, List, Dict, Optional, remove others
        assert "import json" in result
        assert "from typing import List" in result
        assert "from typing import Dict" in result
        assert "from typing import Optional" in result
        assert "regex" not in result
        assert "datetime" not in result
        assert "os.path" not in result

    def test_fix_imports_preserves_code_structure(self):
        """Test that non-import code structure is preserved."""
        source = """import os
import sys

# This is a comment
CONSTANT = 42

def func1():
    '''Docstring'''
    return sys.version

class MyClass:
    def method(self):
        pass
"""

        result = fix_imports(source)

        # Should preserve all non-import code
        assert "# This is a comment" in result
        assert "CONSTANT = 42" in result
        assert "def func1():" in result
        assert "'''Docstring'''" in result
        assert "class MyClass:" in result

    def test_fix_imports_handles_nested_usage(self):
        """Test variable usage in nested scopes."""
        source = """import json
import os

def outer():
    def inner():
        return json.loads('{}')
    return inner()
"""

        result = fix_imports(source)

        # Should keep json (used in inner function), remove os
        assert "import json" in result
        assert "import os" not in result

    def test_fix_imports_multiline_imports(self):
        """Test handling of imports on multiple lines."""
        source = """from module import (
    func1,
    func2,
    func3
)

result = func2()
"""

        result = fix_imports(source)

        # Should only keep func2
        assert "from module import func2" in result
        assert "func1" not in result or "func1" not in result.split("result")[0]
        assert "func3" not in result or "func3" not in result.split("result")[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
