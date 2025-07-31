#!/usr/bin/env python3
"""Test cases for PINJ047: Maximum mutable attributes per class"""

import subprocess
import sys
import tempfile
from pathlib import Path


def run_linter(
    code: str, rule: str = "PINJ047", pyproject_content: str | None = None
) -> tuple[int, str, str]:
    """Run the linter on the given code and return (exit_code, stdout, stderr)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Write the Python file
        py_file = tmpdir_path / "test.py"
        py_file.write_text(code)

        # Write pyproject.toml if provided
        if pyproject_content:
            pyproject_file = tmpdir_path / "pyproject.toml"
            pyproject_file.write_text(pyproject_content)

        # Run the Rust binary directly
        script_dir = Path(__file__).parent
        linter_path = script_dir / "target/release/pinjected-linter"
        if not linter_path.exists():
            linter_path = script_dir / "target/debug/pinjected-linter"

        cmd = [str(linter_path), str(py_file), "-e", rule]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=tmpdir)

        return result.returncode, result.stdout, result.stderr


def test_single_mutable_attribute_allowed():
    """Test that single mutable attribute is allowed by default"""
    code = """
class Counter:
    def __init__(self):
        self.mut_count = 0
    
    def increment(self):
        self.mut_count += 1
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code == 0
    assert "PINJ047" not in stdout


def test_multiple_mutable_attributes_violation():
    """Test detection of multiple mutable attributes exceeding default limit"""
    code = """
class GameState:
    def __init__(self):
        self.mut_score = 0
        self.mut_level = 1
        self.mut_lives = 3
    
    def update_score(self, points):
        self.mut_score += points
    
    def next_level(self):
        self.mut_level += 1
    
    def lose_life(self):
        self.mut_lives -= 1
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code != 0
    assert "PINJ047" in stdout
    assert "3 mutable attributes" in stdout
    assert "exceeding the limit of 1" in stdout


def test_custom_limit_via_config():
    """Test custom limit - currently configuration not supported, so skipping"""
    # TODO: Enable this test when rule-specific configuration is supported
    pass


def test_zero_mutable_attributes_allowed():
    """Test configuration allowing zero mutable attributes - currently configuration not supported"""
    # TODO: Enable this test when rule-specific configuration is supported
    pass


def test_init_only_attributes_not_counted():
    """Test that attributes only assigned in __init__ are not counted as mutable"""
    code = """
class Config:
    def __init__(self, data):
        self.host = data['host']
        self.port = data['port']
        self.timeout = data['timeout']
        self.mut_connection_count = 0
    
    def increment_connections(self):
        self.mut_connection_count += 1
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code == 0
    assert "PINJ047" not in stdout


def test_post_init_attributes_not_counted():
    """Test that __post_init__ attributes are treated like __init__"""
    code = """
class DataClass:
    def __init__(self):
        self.a = 1
    
    def __post_init__(self):
        self.b = 2
        self.c = 3
    
    def update(self):
        self.mut_d = 4  # Only mutable attribute
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code == 0
    assert "PINJ047" not in stdout


def test_attributes_in_different_methods():
    """Test detection of attributes assigned in different methods"""
    code = """
class BadClass:
    def __init__(self):
        self.x = 0
    
    def method1(self):
        self.y = 1  # First mutable
    
    def method2(self):
        self.z = 2  # Second mutable
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code != 0
    assert "PINJ047" in stdout
    assert "2 mutable attributes" in stdout
    assert "y, z" in stdout


def test_repeated_assignments_counted_once():
    """Test that repeated assignments to same attribute count as one"""
    code = """
class Counter:
    def __init__(self):
        self.mut_value = 0
    
    def increment(self):
        self.mut_value += 1
    
    def decrement(self):
        self.mut_value -= 1
    
    def reset(self):
        self.mut_value = 0
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code == 0
    assert "PINJ047" not in stdout


def test_class_without_init():
    """Test class without __init__ method"""
    code = """
class LazyClass:
    def set_value(self, value):
        self.mut_value = value
    
    def set_name(self, name):
        self.mut_name = name
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code != 0
    assert "PINJ047" in stdout
    assert "2 mutable attributes" in stdout


def test_complex_nested_assignments():
    """Test assignments in complex nested control flow"""
    code = """
class ComplexClass:
    def __init__(self):
        self.mut_state = "initial"
    
    def process(self, data):
        try:
            if data:
                for item in data:
                    if item > 0:
                        self.mut_positive_count = getattr(self, 'mut_positive_count', 0) + 1
                    else:
                        self.mut_negative_count = getattr(self, 'mut_negative_count', 0) + 1
        except Exception:
            self.mut_error_flag = True
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code != 0
    assert "PINJ047" in stdout
    assert (
        "3 mutable attributes" in stdout
    )  # mut_error_flag, mut_negative_count, mut_positive_count (mut_state is in __init__)


def test_multiple_classes_in_file():
    """Test multiple classes in same file"""
    code = """
class GoodClass:
    def __init__(self):
        self.mut_value = 0
    
    def update(self):
        self.mut_value = 1

class BadClass:
    def __init__(self):
        self.mut_a = 0
        self.mut_b = 0
    
    def update(self):
        self.mut_a = 1
        self.mut_b = 2
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code != 0
    assert "PINJ047" in stdout
    assert "BadClass" in stdout
    assert (
        "GoodClass" not in stdout.split("BadClass")[0]
    )  # GoodClass should not be in violation


def test_mutable_attributes_message_plural():
    """Test proper pluralization in error messages"""
    # Test with 2 attributes
    code = """
class TwoMutable:
    def update(self):
        self.a = 1
        self.b = 2
"""
    exit_code, stdout, stderr = run_linter(code)
    assert "2 mutable attributes" in stdout


if __name__ == "__main__":
    tests = [
        test_single_mutable_attribute_allowed,
        test_multiple_mutable_attributes_violation,
        # test_custom_limit_via_config,  # TODO: Enable when config is supported
        # test_zero_mutable_attributes_allowed,  # TODO: Enable when config is supported
        test_init_only_attributes_not_counted,
        test_post_init_attributes_not_counted,
        test_attributes_in_different_methods,
        test_repeated_assignments_counted_once,
        test_class_without_init,
        test_complex_nested_assignments,
        test_multiple_classes_in_file,
        test_mutable_attributes_message_plural,
    ]

    for test in tests:
        try:
            test()
            print(f"✓ {test.__name__}")
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"✗ {test.__name__}: Unexpected error: {e}")
            sys.exit(1)

    print(f"\nAll {len(tests)} tests passed!")
