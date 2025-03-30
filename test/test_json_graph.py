import json
from pinjected import design, Injected, injected
from pinjected.visualize_di import DIGraph

@injected
def dep3():
    return "dep3_value"

@injected
def dep2(dep3, /):
    return f"dep2_value_with_{dep3()}"

@injected
def dep1(dep2, dep3, /):
    return f"dep1_value_with_{dep2()}_and_{dep3()}"

@injected
def main_target(dep1, dep2, /):
    return f"main_with_{dep1()}_and_{dep2()}"

test_design = design(
    dep1=dep1,
    dep2=dep2,
    dep3=dep3,
    main_target=main_target
)

def test_to_json_single_root():
    """Test that to_json works correctly with a single root node."""
    graph = DIGraph(test_design)
    json_output = graph.to_json("main_target")
    
    assert isinstance(json_output, dict)
    assert 'edges' in json_output
    
    edges = json_output['edges']
    assert isinstance(edges, list)
    
    main_target_edge = next((edge for edge in edges if edge['key'] == 'main_target'), None)
    assert main_target_edge is not None
    
    assert 'dependencies' in main_target_edge
    assert isinstance(main_target_edge['dependencies'], list)
    assert 'dep1' in main_target_edge['dependencies']
    assert 'dep2' in main_target_edge['dependencies']
    
    dep1_edge = next((edge for edge in edges if edge['key'] == 'dep1'), None)
    assert dep1_edge is not None
    
    assert 'dependencies' in dep1_edge
    assert isinstance(dep1_edge['dependencies'], list)
    assert 'dep2' in dep1_edge['dependencies']
    assert 'dep3' in dep1_edge['dependencies']

def test_to_json_multiple_roots():
    """Test that to_json works correctly with multiple root nodes."""
    graph = DIGraph(test_design)
    json_output = graph.to_json(["main_target", "dep1"])
    
    assert isinstance(json_output, dict)
    assert 'edges' in json_output
    
    edges = json_output['edges']
    assert isinstance(edges, list)
    
    keys = [edge['key'] for edge in edges]
    assert 'main_target' in keys
    assert 'dep1' in keys

def test_to_json_replace_missing():
    """Test that to_json works correctly with replace_missing=False."""
    graph = DIGraph(test_design)
    
    incomplete_design = design(
        dep2=dep2,
        main_target=main_target
    )
    
    graph = DIGraph(incomplete_design)
    
    json_output_with_replace = graph.to_json("main_target")
    
    json_output_without_replace = graph.to_json("main_target", replace_missing=False)
    
    assert len(json_output_with_replace['edges']) >= len(json_output_without_replace['edges'])
