import json
import pytest
from io import StringIO
import sys
from contextlib import redirect_stdout

from pinjected import design, Injected, injected, DesignSpec, SimpleBindSpec
from pinjected.test.injected_pytest import injected_pytest
from pinjected.visualize_di import DIGraph
from pinjected.main_impl import describe
from pinjected.v2.keys import StrBindKey
from returns.maybe import Nothing, Some


@injected
def dep3():
    """A simple dependency with documentation."""
    return "dep3_value"


@injected
def dep2(dep3, /):
    """A dependency that depends on dep3."""
    return f"dep2_value_with_{dep3()}"


@injected
def dep1(dep2, dep3, /):
    """A dependency that depends on dep2 and dep3."""
    return f"dep1_value_with_{dep2()}_and_{dep3()}"


@injected
def main_target(dep1, dep2, /):
    """The main target that depends on dep1 and dep2."""
    return f"main_with_{dep1()}_and_{dep2()}"


test_design = design(
    dep1=dep1,
    dep2=dep2,
    dep3=dep3,
    main_target=main_target
)

test_design_spec = DesignSpec.new(
    dep1=SimpleBindSpec(documentation="Dependency 1 with detailed documentation"),
    dep2=SimpleBindSpec(documentation="Dependency 2 with detailed documentation"),
    dep3=SimpleBindSpec(documentation="Dependency 3 with detailed documentation"),
    main_target=SimpleBindSpec(documentation="Main target with detailed documentation")
)


@injected_pytest
def test_describe_command_output():
    """Test that the describe command correctly visualizes dependencies with documentation."""
    digraph = DIGraph(
        test_design,
        spec=Some(test_design_spec)
    )
    
    root_name = "main_target"
    edges = digraph.to_edges(root_name, ["dep1", "dep2"])
    
    assert len(edges) > 0, "Should have at least one edge"
    
    main_edge = next((edge for edge in edges if edge.key == "main_target"), None)
    assert main_edge is not None, "Should find the main_target edge"
    
    assert "dep1" in main_edge.dependencies, "main_target should depend on dep1"
    assert "dep2" in main_edge.dependencies, "main_target should depend on dep2"
    
    dep1_edge = next((edge for edge in edges if edge.key == "dep1"), None)
    assert dep1_edge is not None, "Should find the dep1 edge"
    
    assert "dep2" in dep1_edge.dependencies, "dep1 should depend on dep2"
    assert "dep3" in dep1_edge.dependencies, "dep1 should depend on dep3"


@pytest.mark.asyncio
async def test_describe_command_with_docs():
    """Test that the describe command correctly includes documentation from design specs."""
    test_design_with_docs = design(
        dep1=dep1,
        dep2=dep2,
        dep3=dep3,
        main_target=main_target,
        __design_spec__=test_design_spec
    )
    
    digraph = DIGraph(
        test_design_with_docs,
        spec=Some(test_design_spec)
    )
    
    root_name = "main_target"
    edges = digraph.to_edges(root_name, ["dep1", "dep2"])
    
    assert len(edges) > 0, "Should have at least one edge"
    
    main_edge = next((edge for edge in edges if edge.key == "main_target"), None)
    assert main_edge is not None, "Should find the main_target edge"
    assert "dep1" in main_edge.dependencies, "main_target should depend on dep1"
    assert "dep2" in main_edge.dependencies, "main_target should depend on dep2"


def test_describe_command_with_none_var_path():
    """Test that the describe command provides a helpful error message when var_path is None."""
    from pinjected.main_impl import describe
    
    captured_output = StringIO()
    with redirect_stdout(captured_output):
        describe(var_path=None)
    
    output = captured_output.getvalue()
    assert "Error: You must provide a variable path" in output
    assert "Examples:" in output
    assert "pinjected describe my_module.my_submodule.my_variable" in output
    assert "pinjected describe --var_path=my_module.my_submodule.my_variable" in output


def test_describe_command_with_invalid_path():
    """Test that the describe command handles invalid paths properly."""
    from pinjected.main_impl import describe
    
    with pytest.raises(ValueError) as excinfo:
        describe(var_path="module_with_no_dots")
    
    assert "Empty module name" == str(excinfo.value)
    
    with pytest.raises(ImportError) as excinfo:
        describe(var_path="non.existent.module.path")
    
    assert "Could not import module" in str(excinfo.value)
    assert "Please ensure the module exists" in str(excinfo.value)
    
    from unittest.mock import patch, MagicMock
    from io import StringIO
    import sys
    
    with patch('pinjected.helpers.find_default_design_paths', return_value=[]):
        with patch('sys.stdout', new=StringIO()) as fake_out:
            describe(var_path="pinjected.test_package.child.module1.test_runnable")
            
            output = fake_out.getvalue()
            assert "Dependency Graph Description" in output
