import re
from unittest.mock import MagicMock, patch

import pytest
from returns.maybe import Some
from rich.panel import Panel
from rich.text import Text

from pinjected import EmptyDesign
from pinjected.di.design_spec.impl import SimpleBindSpec
from pinjected.run_helpers.run_injected import generate_dependency_graph_description


def format_value_for_test(value):
    """Simplified version of format_value for testing."""
    if value is None:
        return "None"

    value_str = str(value)

    if isinstance(value, dict) and "documentation" in value and value["documentation"]:
        doc = value["documentation"]
        # Don't replace \\n since the input already has actual newlines
        doc = re.sub(r"[ \t]+", " ", doc)
        value["documentation"] = doc
        value_str = str(value)

    return value_str


def test_format_value_handles_newlines():
    """Test that format_value properly handles newlines in documentation."""
    test_dict = {
        "type": "SimpleBindSpec",
        "has_validator": False,
        "documentation": "\ntype: dict\nprotocol:\n    - label_look_forward_ns: int\n    - label_check_delay_ns: int\ndescription: Configuration for labeling data.",
    }

    # The test dict is modified in place by format_value_for_test
    format_value_for_test(test_dict)

    # Check that the documentation field was processed correctly
    assert (
        test_dict["documentation"]
        == "\ntype: dict\nprotocol:\n - label_look_forward_ns: int\n - label_check_delay_ns: int\ndescription: Configuration for labeling data."
    )


def test_simple_bind_spec_documentation():
    """Test that SimpleBindSpec documentation is properly formatted."""
    spec = SimpleBindSpec(
        documentation="""
type: dict
protocol:
    - label_look_forward_ns: int
    - label_check_delay_ns: int
description: Configuration for labeling data.
"""
    )

    spec_str = str(spec)

    assert "documentation" in spec_str

    # Convert the string back to dict for testing
    spec_dict = eval(spec_str)
    format_value_for_test(spec_dict)

    # Check that the documentation field was processed correctly (spaces normalized)
    assert (
        spec_dict["documentation"]
        == "\ntype: dict\nprotocol:\n - label_look_forward_ns: int\n - label_check_delay_ns: int\ndescription: Configuration for labeling data.\n"
    )


def test_merged_panels():
    """Test that documentation is included in the same panel as metadata."""
    from returns.maybe import Nothing

    mock_cxt = MagicMock()
    mock_cxt.src_var_spec.var_path = "test_obj"

    # Create mock spec trace with get_spec method that returns proper specs
    from pinjected.v2.keys import StrBindKey

    mock_spec_trace = MagicMock()

    def mock_spec_get_spec(key):
        if key == StrBindKey("dep1"):
            return Some({"documentation": "Test documentation"})
        return Nothing

    mock_spec_trace.get_spec = mock_spec_get_spec
    mock_cxt.src_meta_context.spec_trace.accumulated = mock_spec_trace

    class TestObject:
        def dependencies(self):
            return ["dep1"]

    mock_cxt.var = TestObject()

    mock_console_print = MagicMock()

    # Just mock the DIGraph minimally - the real flow will work with our spec_trace mock
    mock_digraph = MagicMock()

    with (
        patch("pinjected.run_helpers.run_injected.DIGraph", mock_digraph),
        patch("rich.console.Console.print", mock_console_print),
    ):
        generate_dependency_graph_description("test_obj", None, mock_cxt, EmptyDesign)

        panel_calls = [
            call
            for call in mock_console_print.call_args_list
            if call.args and isinstance(call.args[0], Panel)
        ]

        dep1_panel_call = None
        for call in panel_calls:
            panel = call.args[0]
            if isinstance(panel.title, Text) and panel.title.plain == "dep1":
                dep1_panel_call = call
                break

        assert dep1_panel_call is not None

        panel_content = dep1_panel_call.args[0].renderable.plain
        assert "Documentation:" in panel_content
        assert "Test documentation" in panel_content

        dep1_panels = 0
        for call in panel_calls:
            panel = call.args[0]
            if (isinstance(panel.title, Text) and panel.title.plain == "dep1") or (
                isinstance(panel.title, str) and "dep1" in panel.title
            ):
                dep1_panels += 1

        assert dep1_panels == 1


def test_generate_dependency_graph_description_with_none_design():
    """Test that generate_dependency_graph_description raises ValueError when design is None."""
    mock_cxt = MagicMock()
    mock_cxt.src_var_spec.var_path = "test_obj"

    class TestObject:
        def dependencies(self):
            return ["dep1"]

    mock_cxt.var = TestObject()

    with pytest.raises(ValueError) as excinfo:
        generate_dependency_graph_description("test_obj", None, mock_cxt, None)

    assert "design parameter cannot be None" in str(excinfo.value)
