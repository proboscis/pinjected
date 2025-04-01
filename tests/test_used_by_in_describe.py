import pytest
from unittest.mock import MagicMock, patch, call
from pinjected.run_helpers.run_injected import generate_dependency_graph_description
from rich.panel import Panel
from rich.text import Text
from returns.maybe import Some, Nothing

def test_used_by_in_edge_details():
    """Test that 'used_by' information is included in edge details."""
    mock_cxt = MagicMock()
    mock_cxt.src_var_spec.var_path = "test_obj"
    
    class TestObject:
        def dependencies(self):
            return ["dep1", "dep2"]
    
    mock_cxt.var = TestObject()
    
    mock_edges = [
        MagicMock(key="test_obj", dependencies=["dep1", "dep2"], used_by=[], metadata=Nothing, spec=Nothing),
        MagicMock(key="dep1", dependencies=[], used_by=["test_obj"], metadata=Nothing, spec=Nothing),
        MagicMock(key="dep2", dependencies=["dep3"], used_by=["test_obj"], metadata=Nothing, spec=Nothing),
        MagicMock(key="dep3", dependencies=[], used_by=["dep2"], metadata=Nothing, spec=Nothing)
    ]
    
    mock_digraph = MagicMock()
    mock_digraph.return_value.to_edges.return_value = mock_edges
    
    mock_console_print = MagicMock()
    
    with patch('pinjected.run_helpers.run_injected.DIGraph', mock_digraph), \
         patch('rich.console.Console.print', mock_console_print):
        
        generate_dependency_graph_description("test_obj", None, mock_cxt, None)
        
        panel_calls = [call for call in mock_console_print.call_args_list 
                      if call.args and isinstance(call.args[0], Panel)]
        
        for edge in mock_edges:
            if edge.key != "test_obj":  # Skip root node
                edge_panel_call = None
                for call in panel_calls:
                    panel = call.args[0]
                    if isinstance(panel.title, Text) and panel.title.plain == edge.key:
                        edge_panel_call = call
                        break
                
                assert edge_panel_call is not None, f"No panel found for {edge.key}"
                
                panel_content = edge_panel_call.args[0].renderable.plain
                assert "Used by:" in panel_content
                
                if edge.used_by:
                    for user in edge.used_by:
                        assert user in panel_content
                else:
                    assert "Used by: None" in panel_content
