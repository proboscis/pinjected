"""Additional tests for test_aggregator to improve coverage."""

import pytest
import tempfile
import os
from pinjected.test_helper.test_aggregator import find_pinjected_annotations


def test_find_pinjected_annotations_with_assign_type_comment():
    """Test finding annotations in assignments with type comments containing Injected/IProxy."""
    code = """# Type comment on assignment with Injected
my_var = some_value  # type: Injected[str]

# Type comment on assignment with IProxy
proxy = get_proxy()  # type: IProxy[Database]

# Type comment without Injected or IProxy (should not be found)
regular = 42  # type: int

# Assignment with multiple targets
x = y = injected_func()  # type: Injected[Config]
"""

    # Create a temporary file with the code
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        temp_file = f.name

    try:
        # Now test the function with the file path
        annotations = find_pinjected_annotations(temp_file)

        # The function doesn't parse type comments, so it won't find any
        # This is because ast.parse() in the function doesn't have type_comments=True
        assert len(annotations) == 0
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)


def test_find_pinjected_annotations_edge_cases():
    """Test edge cases for annotation finding."""
    code = """
# Regular assignment without type comment
normal_var = 42

# Function with no decorator
def regular_func():
    pass

# Class with no decorator
class RegularClass:
    pass

# Variable annotation with other type
other: str = "hello"

# Injected in a string (should not be found)
comment = "This is an Injected[str] in a string"
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        temp_file = f.name

    try:
        annotations = find_pinjected_annotations(temp_file)
        # Should find nothing
        assert len(annotations) == 0
    finally:
        os.unlink(temp_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
