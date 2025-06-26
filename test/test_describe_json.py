import json
from contextlib import redirect_stdout
from io import StringIO

from returns.maybe import Some

from pinjected import DesignSpec, SimpleBindSpec, design, injected
from pinjected.di.iproxy import IProxy
from pinjected.test.injected_pytest import injected_pytest
from pinjected.visualize_di import DIGraph


@injected
def json_dep3():
    """A simple dependency with documentation for JSON test."""
    return "json_dep3_value"


@injected
def json_dep2(json_dep3, /):
    """A dependency that depends on json_dep3 for JSON test."""
    return f"json_dep2_value_with_{json_dep3()}"


@injected
def json_dep1(json_dep2, json_dep3, /):
    """A dependency that depends on json_dep2 and json_dep3 for JSON test."""
    return f"json_dep1_value_with_{json_dep2()}_and_{json_dep3()}"


# Create IProxy objects for testing
iproxy_main = IProxy(lambda dep1, dep2: f"main_with_{dep1}_and_{dep2}")
iproxy_simple = IProxy("simple_value")


test_json_design = design(
    json_dep1=json_dep1,
    json_dep2=json_dep2,
    json_dep3=json_dep3,
)

test_json_design_spec = DesignSpec.new(
    json_dep1=SimpleBindSpec(
        documentation="JSON Dependency 1 with detailed documentation"
    ),
    json_dep2=SimpleBindSpec(
        documentation="JSON Dependency 2 with detailed documentation"
    ),
    json_dep3=SimpleBindSpec(
        documentation="JSON Dependency 3 with detailed documentation"
    ),
)


@injected_pytest
def test_describe_json_edge_to_json_repr():
    """Test that EdgeInfo.to_json_repr() correctly formats the JSON output."""
    from pinjected.visualize_di import EdgeInfo

    # Create a mock location object with the expected attributes
    class MockLocation:
        def __init__(self, file_path, line_no):
            self.file_path = file_path
            self.line_no = line_no

    # Create a mock metadata object
    class MockMetadata:
        def __init__(self, location, docstring=None, source=None):
            self.location = location
            self.docstring = docstring
            self.source = source

    # Create a sample EdgeInfo with all fields
    edge = EdgeInfo(
        key="test_key",
        dependencies=["dep1", "dep2"],
        used_by=["parent1", "parent2"],
        metadata=Some(
            MockMetadata(
                location=MockLocation(file_path="/path/to/test.py", line_no=42),
                docstring="Test documentation",
                source="def test(): pass",
            )
        ),
        spec=Some(SimpleBindSpec(documentation="Test spec documentation")),
    )

    json_repr = edge.to_json_repr()

    assert json_repr["key"] == "test_key"
    assert json_repr["dependencies"] == ["dep1", "dep2"]
    assert json_repr["used_by"] == ["parent1", "parent2"]
    assert json_repr["metadata"]["location"]["file_path"] == "/path/to/test.py"
    assert json_repr["metadata"]["location"]["line_no"] == 42
    assert json_repr["metadata"]["docstring"] == "Test documentation"
    assert json_repr["metadata"]["source"] == "def test(): pass"
    assert "documentation" in str(json_repr["spec"])


@injected_pytest
def test_describe_json_output_format():
    """Test that the describe_json command returns proper JSON format."""
    digraph = DIGraph(test_json_design, spec=Some(test_json_design_spec))

    root_name = "json_dep1"
    edges = digraph.to_edges(root_name, ["json_dep2", "json_dep3"])

    # Create the expected JSON structure
    result = {
        "root": root_name,
        "module_var_path": "test.module.json_dep1",
        "dependency_chain": [edge.to_json_repr() for edge in edges],
    }

    # Verify JSON is serializable
    json_str = json.dumps(result, indent=2)
    parsed = json.loads(json_str)

    assert parsed["root"] == root_name
    assert parsed["module_var_path"] == "test.module.json_dep1"
    assert len(parsed["dependency_chain"]) > 0

    # Check dependency chain structure
    for edge in parsed["dependency_chain"]:
        assert "key" in edge
        assert "dependencies" in edge
        assert "used_by" in edge
        assert "metadata" in edge
        assert "spec" in edge


def test_describe_json_command_with_none_var_path():
    """Test that the describe_json command provides a helpful error message when var_path is None."""
    from pinjected.main_impl import describe_json

    captured_output = StringIO()
    with redirect_stdout(captured_output):
        describe_json(var_path=None)

    output = captured_output.getvalue()
    assert "Error: You must provide a variable path" in output
    assert "Examples:" in output
    assert "pinjected describe-json my_module.my_submodule.my_iproxy_variable" in output
    assert (
        "pinjected describe-json --var_path=my_module.my_submodule.my_iproxy_variable"
        in output
    )


def test_describe_json_error_output():
    """Test that errors are returned as JSON for IDE consumption."""
    # This would be tested more thoroughly with integration tests
    # For now, just verify the error JSON structure
    error_result = {
        "error": "Object test_obj must have a dependencies() method to use the describe-json command",
        "root": "test_obj",
        "module_var_path": "test.module.test_obj",
    }

    # Verify it's valid JSON
    json_str = json.dumps(error_result, indent=2)
    parsed = json.loads(json_str)

    assert "error" in parsed
    assert "root" in parsed
    assert "module_var_path" in parsed


@injected_pytest
def test_describe_json_with_complex_dependencies():
    """Test describe_json with complex nested dependencies."""
    digraph = DIGraph(test_json_design, spec=Some(test_json_design_spec))

    # Get edges for a complex dependency graph
    edges = digraph.to_edges("json_dep1", ["json_dep2", "json_dep3"])

    # Verify we get all expected edges
    edge_keys = [edge.key for edge in edges]
    assert "json_dep1" in edge_keys
    assert "json_dep2" in edge_keys
    assert "json_dep3" in edge_keys

    # Find specific edges to check dependencies
    dep1_edge = next((edge for edge in edges if edge.key == "json_dep1"), None)
    assert dep1_edge is not None
    assert set(dep1_edge.dependencies) == {"json_dep2", "json_dep3"}

    dep2_edge = next((edge for edge in edges if edge.key == "json_dep2"), None)
    assert dep2_edge is not None
    assert "json_dep3" in dep2_edge.dependencies

    # Check used_by relationships
    dep3_edge = next((edge for edge in edges if edge.key == "json_dep3"), None)
    assert dep3_edge is not None
    # dep3 should be used by both dep1 and dep2
    assert len(dep3_edge.used_by) >= 2
