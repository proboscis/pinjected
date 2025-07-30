#!/usr/bin/env python3
"""Test cases for PINJ046: Mutable attribute naming"""

import subprocess
import sys
import tempfile
import os


def run_linter(code: str, rule: str = "PINJ046") -> tuple[int, str, str]:
    """Run the linter on the given code and return (exit_code, stdout, stderr)"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()

        # Run the Rust binary directly
        linter_path = "./target/release/pinjected-linter"
        if not os.path.exists(linter_path):
            linter_path = "./target/debug/pinjected-linter"

        cmd = [linter_path, f.name, "-e", rule]
        result = subprocess.run(cmd, capture_output=True, text=True)

        os.unlink(f.name)
        return result.returncode, result.stdout, result.stderr


def test_mutable_attribute_without_prefix():
    """Test detection of mutable attributes without proper prefix"""
    code = """
class MyClass:
    def __init__(self):
        self.value = 0
    
    def update(self):
        self.value = 1  # Should be mut_value
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code != 0
    assert "PINJ046" in stdout
    assert "'value'" in stdout
    assert "mut_" in stdout


def test_private_mutable_attribute_without_prefix():
    """Test detection of private mutable attributes without proper prefix"""
    code = """
class MyClass:
    def __init__(self):
        self._value = 0
    
    def update(self):
        self._value = 1  # Should be _mut_value
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code != 0
    assert "PINJ046" in stdout
    assert "'_value'" in stdout
    assert "_mut" in stdout


def test_properly_named_mutable_attributes():
    """Test that properly named mutable attributes don't trigger violations"""
    code = """
class MyClass:
    def __init__(self):
        self.mut_counter = 0
        self._mut_state = None
    
    def update(self):
        self.mut_counter += 1
        self._mut_state = "updated"
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code == 0
    assert "PINJ046" not in stdout


def test_immutable_attributes_in_init():
    """Test that attributes only assigned in __init__ are not flagged"""
    code = """
class MyClass:
    def __init__(self):
        self.name = "test"
        self._config = {}
        self.items = []
    
    def get_name(self):
        return self.name
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code == 0
    assert "PINJ046" not in stdout


def test_post_init_assignments():
    """Test that __post_init__ assignments are treated like __init__"""
    code = """
class MyClass:
    def __init__(self):
        self.x = 0
    
    def __post_init__(self):
        self.y = 0
        self.z = 0
    
    def update(self):
        self.z = 1  # Only this should be flagged
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code != 0
    assert "PINJ046" in stdout
    assert "'z'" in stdout
    assert "'x'" not in stdout
    assert "'y'" not in stdout


def test_multiple_mutable_attributes():
    """Test detection of multiple mutable attributes"""
    code = """
class MyClass:
    def __init__(self):
        self.x = 0
        self.y = 0
    
    def move(self):
        self.x += 1
        self.y += 1
    
    def reset(self):
        self.x = 0
        self.y = 0
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code != 0
    assert "PINJ046" in stdout
    # Should have violations for both x and y
    assert stdout.count("PINJ046") >= 2


def test_nested_assignments():
    """Test detection of assignments in nested contexts"""
    code = """
class MyClass:
    def __init__(self):
        self.flag = False
        self.counter = 0
    
    def process(self):
        if True:
            self.flag = True
        
        for i in range(3):
            self.counter = i
        
        while self.counter > 0:
            self.counter -= 1
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code != 0
    assert "PINJ046" in stdout


def test_dunder_attributes_ignored():
    """Test that dunder attributes are not checked"""
    code = """
class MyClass:
    def __init__(self):
        self.__private = 0
    
    def update(self):
        self.__private = 1
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code == 0
    assert "PINJ046" not in stdout


def test_annotated_assignments():
    """Test detection with type annotations"""
    code = """
class MyClass:
    def __init__(self):
        self.value: int = 0
    
    def update(self):
        self.value: int = 1
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code != 0
    assert "PINJ046" in stdout
    assert "annotated assignment" in stdout


def test_augmented_assignments():
    """Test detection with augmented assignments"""
    code = """
class MyClass:
    def __init__(self):
        self.count = 0
    
    def increment(self):
        self.count += 1  # Should be mut_count
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code != 0
    assert "PINJ046" in stdout
    assert "augmented assignment" in stdout


def test_class_without_init():
    """Test class without __init__ method"""
    code = """
class MyClass:
    def set_value(self, value):
        self.value = value  # Should be mut_value
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code != 0
    assert "PINJ046" in stdout


def test_complex_control_flow():
    """Test assignments in complex control flow"""
    code = """
class MyClass:
    def __init__(self):
        self.state = "initial"
    
    def process(self, data):
        try:
            if data:
                self.state = "processing"
            else:
                self.state = "empty"
        except Exception:
            self.state = "error"
        finally:
            self.state = "done"
"""
    exit_code, stdout, stderr = run_linter(code)
    assert exit_code != 0
    assert "PINJ046" in stdout


if __name__ == "__main__":
    tests = [
        test_mutable_attribute_without_prefix,
        test_private_mutable_attribute_without_prefix,
        test_properly_named_mutable_attributes,
        test_immutable_attributes_in_init,
        test_post_init_assignments,
        test_multiple_mutable_attributes,
        test_nested_assignments,
        test_dunder_attributes_ignored,
        test_annotated_assignments,
        test_augmented_assignments,
        test_class_without_init,
        test_complex_control_flow,
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
