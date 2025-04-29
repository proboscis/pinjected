from unittest.mock import MagicMock, patch

from returns.maybe import Nothing
from rich.panel import Panel
from rich.text import Text

from pinjected.dependency_graph_builder import DependencyGraphBuilder
from pinjected.run_helpers.run_injected import generate_dependency_graph_description


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

def test_collect_used_by_with_multiple_users():
    """Test that collect_used_by correctly identifies multiple users for a dependency."""
    mock_digraph = MagicMock()
    builder = DependencyGraphBuilder(mock_digraph)
    
    deps_map = {
        'service1': ['shared_dep', 'dep1'],
        'service2': ['shared_dep', 'dep2'],
        'service3': ['shared_dep', 'dep3'],
        'dep1': [],
        'dep2': ['dep4'],
        'dep3': ['dep4'],
        'dep4': [],
        'shared_dep': []
    }
    
    used_by_map = builder.collect_used_by(deps_map)
    
    assert sorted(used_by_map['shared_dep']) == sorted(['service1', 'service2', 'service3']), \
        "shared_dep should be used by service1, service2, and service3"
    assert used_by_map['dep1'] == ['service1'], "dep1 should be used by service1"
    assert used_by_map['dep2'] == ['service2'], "dep2 should be used by service2"
    assert used_by_map['dep3'] == ['service3'], "dep3 should be used by service3"
    assert sorted(used_by_map['dep4']) == sorted(['dep2', 'dep3']), \
        "dep4 should be used by dep2 and dep3"

def test_build_edges_with_complex_dependency_graph():
    """Test that build_edges correctly populates used_by with multiple users in a complex graph."""
    mock_digraph = MagicMock()
    
    deps_map = {
        'root': ['service1', 'service2', 'service3'],
        'service1': ['shared_dep', 'dep1'],
        'service2': ['shared_dep', 'dep2'],
        'service3': ['shared_dep', 'dep3'],
        'dep1': [],
        'dep2': ['dep4'],
        'dep3': ['dep4'],
        'dep4': [],
        'shared_dep': []
    }
    
    builder = DependencyGraphBuilder(mock_digraph)
    builder.collect_dependencies = MagicMock(return_value=deps_map)
    
    edges = builder.build_edges('root', ['service1', 'service2', 'service3'])
    
    edge_dict = {edge.key: edge for edge in edges}
    
    assert sorted(edge_dict['shared_dep'].used_by) == sorted(['service1', 'service2', 'service3']), \
        "shared_dep should be used by service1, service2, and service3"
    assert edge_dict['dep1'].used_by == ['service1'], "dep1 should be used by service1"
    assert edge_dict['dep2'].used_by == ['service2'], "dep2 should be used by service2"
    assert edge_dict['dep3'].used_by == ['service3'], "dep3 should be used by service3"
    assert sorted(edge_dict['dep4'].used_by) == sorted(['dep2', 'dep3']), \
        "dep4 should be used by dep2 and dep3"
    assert sorted(edge_dict['service1'].used_by) == ['root'], "service1 should be used by root"
    assert sorted(edge_dict['service2'].used_by) == ['root'], "service2 should be used by root"
    assert sorted(edge_dict['service3'].used_by) == ['root'], "service3 should be used by root"
