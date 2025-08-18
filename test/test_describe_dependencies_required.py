from unittest.mock import MagicMock

import pytest

from pinjected.run_helpers.run_injected import generate_dependency_graph_description
from pinjected import EmptyDesign


class TestObjectWithoutDependencies:
    """Test class without dependencies method."""


def test_describe_requires_dependencies():
    """Test that describe command requires dependencies method."""
    mock_cxt = MagicMock()
    mock_cxt.var = TestObjectWithoutDependencies()
    mock_cxt.src_var_spec.var_path = "test_obj"

    with pytest.raises(AttributeError) as excinfo:
        generate_dependency_graph_description("test_obj", None, mock_cxt, EmptyDesign)

    assert "must have a dependencies() method to use the describe command" in str(excinfo.value)
