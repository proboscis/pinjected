import re
from unittest.mock import MagicMock, patch

from returns.maybe import Some
from rich.panel import Panel
from rich.text import Text

from pinjected.di.design_spec.impl import SimpleBindSpec
from pinjected.run_helpers.run_injected import generate_dependency_graph_description


def format_value_for_test(value):
    """Simplified version of format_value for testing."""
    if value is None:
        return "None"
    
    value_str = str(value)
    
    if isinstance(value, dict) and 'documentation' in value:
        if value['documentation']:
            doc = value['documentation']
            doc = doc.replace('\\n', '\n')
            doc = re.sub(r'[ \t]+', ' ', doc)
            value['documentation'] = doc
            value_str = str(value)
    
    return value_str

def test_format_value_handles_newlines():
    """Test that format_value properly handles newlines in documentation."""
    test_dict = {
        'type': 'SimpleBindSpec',
        'has_validator': False,
        'documentation': '\\ntype: dict\\nprotocol:\\n    - label_look_forward_ns: int\\n    - label_check_delay_ns: int\\ndescription: Configuration for labeling data.'
    }
    
    formatted = format_value_for_test(test_dict)
    
    assert '\\n' not in formatted
    assert '\ntype: dict\n' in formatted

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
    
    assert 'documentation' in spec_str
    
    formatted = format_value_for_test(eval(spec_str))
    
    assert '\\n' not in formatted
    assert '\ntype: dict\n' in formatted

def test_merged_panels():
    """Test that documentation is included in the same panel as metadata."""
    mock_cxt = MagicMock()
    mock_cxt.src_var_spec.var_path = "test_obj"
    
    class TestObject:
        def dependencies(self):
            return ["dep1"]
    
    mock_cxt.var = TestObject()
    
    mock_digraph = MagicMock()
    mock_edge = MagicMock()
    mock_edge.key = "dep1"
    mock_edge.dependencies = []
    mock_edge.metadata = None
    mock_edge.spec = Some({'documentation': 'Test documentation'})
    
    mock_digraph.return_value.to_edges.return_value = [
        MagicMock(key="test_obj", dependencies=["dep1"], metadata=None, spec=None),
        mock_edge
    ]
    
    mock_console_print = MagicMock()
    
    with patch('pinjected.run_helpers.run_injected.DIGraph', mock_digraph), \
         patch('rich.console.Console.print', mock_console_print):
        
        generate_dependency_graph_description("test_obj", None, mock_cxt, None)
        
        panel_calls = [call for call in mock_console_print.call_args_list 
                       if call.args and isinstance(call.args[0], Panel)]
        
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
            if (isinstance(panel.title, Text) and panel.title.plain == "dep1") or \
               (isinstance(panel.title, str) and "dep1" in panel.title):
                dep1_panels += 1
        
        assert dep1_panels == 1
