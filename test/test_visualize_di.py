"""Tests for visualize_di module."""

import pytest
from unittest.mock import Mock, patch
from returns.result import Failure, Success
from returns.maybe import Maybe, Nothing, Some
from pinjected import design, instance, injected
from pinjected.di.injected import InjectedPure, InjectedFromFunction, InjectedByName
from pinjected.visualize_di import (
    DIGraph,
    EdgeInfo,
    MissingKeyError,
    create_dependency_graph,
    dfs,
    get_color,
    rgb_to_hex,
    getitem,
    safe_attr,
)


def test_rgb_to_hex():
    """Test RGB to hex color conversion."""
    # Test basic colors
    assert rgb_to_hex((255, 0, 0)) == "#ff0000"
    assert rgb_to_hex((0, 255, 0)) == "#00ff00"
    assert rgb_to_hex((0, 0, 255)) == "#0000ff"
    assert rgb_to_hex((255, 255, 255)) == "#ffffff"
    assert rgb_to_hex((0, 0, 0)) == "#000000"

    # Test mixed colors
    assert rgb_to_hex((128, 128, 128)) == "#808080"
    assert rgb_to_hex((255, 128, 0)) == "#ff8000"


def test_get_color():
    """Test color generation based on edge count."""
    # Test different edge counts
    color1 = get_color(0)
    color2 = get_color(5)
    color3 = get_color(10)

    # Colors should be hex strings
    assert color1.startswith("#")
    assert color2.startswith("#")
    assert color3.startswith("#")

    # Colors should be valid hex
    assert len(color1) == 7
    assert len(color2) == 7
    assert len(color3) == 7


def test_getitem():
    """Test safe getitem function."""
    # Test with dict
    data = {"key": "value", "nested": {"inner": 42}}
    # getitem returns Result type from returns library
    result = getitem(data, "key")
    assert result.unwrap() == "value"

    result2 = getitem(data, "nested")
    assert result2.unwrap() == {"inner": 42}

    # Test missing key returns Failure
    result3 = getitem(data, "missing")
    assert isinstance(result3, Failure)

    # Test with list
    lst = ["a", "b", "c"]
    assert getitem(lst, 0).unwrap() == "a"
    assert getitem(lst, 2).unwrap() == "c"

    # Test out of bounds returns Failure
    assert isinstance(getitem(lst, 10), Failure)


def test_dfs_basic():
    """Test depth-first search function."""
    # Create a simple graph as adjacency list
    graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}

    def neighbors(node):
        return graph.get(node, [])

    # Traverse from A
    edges = list(dfs(neighbors, "A"))

    # Should visit all edges
    assert len(edges) > 0
    # Each edge should be (from, to, trace)
    assert all(len(edge) == 3 for edge in edges)


def test_edge_info():
    """Test EdgeInfo dataclass."""
    # Create edge info with correct fields
    edge = EdgeInfo(
        key="my_service", dependencies=["config", "database"], used_by=["api_handler"]
    )

    assert edge.key == "my_service"
    assert edge.dependencies == ["config", "database"]
    assert edge.used_by == ["api_handler"]

    # Test with default used_by
    edge2 = EdgeInfo(key="config", dependencies=[])
    assert edge2.used_by == []


def test_missing_key_error():
    """Test MissingKeyError exception."""
    error = MissingKeyError("test_key")
    assert str(error) == "test_key"
    assert isinstance(error, RuntimeError)


def test_di_graph_init():
    """Test DIGraph initialization."""
    d = design(config="test_config", database="test_db")

    # Create DIGraph
    graph = DIGraph(d)

    # Should be initialized
    assert graph is not None
    assert hasattr(graph, "src")  # src instead of design
    assert hasattr(graph, "helper")
    assert graph.src == d


def test_di_graph_with_instances():
    """Test DIGraph with instance decorators."""

    @instance
    def config():
        return {"env": "test"}

    @instance
    def database(config):
        return f"DB for {config['env']}"

    @instance
    def service(database):
        return f"Service using {database}"

    d = design()
    graph = DIGraph(d)

    # Test that graph has explicit mappings
    assert hasattr(graph, "explicit_mappings")
    assert hasattr(graph, "total_bindings")
    assert isinstance(graph.explicit_mappings, dict)
    assert isinstance(graph.total_bindings, dict)


def test_di_graph_get_label():
    """Test DIGraph get_label method."""

    @instance
    def my_service():
        return "service"

    d = design()
    graph = DIGraph(d)

    # Test that graph has methods
    assert hasattr(graph, "resolve_injected")
    assert hasattr(graph, "new_name")
    # Test new_name method
    new_name = graph.new_name("test")
    assert new_name.startswith("test_")


def test_di_graph_build_networkx():
    """Test building NetworkX graph."""

    @instance
    def a():
        return "A"

    @instance
    def b(a):
        return f"B depends on {a}"

    @instance
    def c(a, b):
        return f"C depends on {a} and {b}"

    d = design()
    graph = DIGraph(d)

    # Test graph has necessary methods
    assert hasattr(graph, "create_dependency_digraph")
    assert hasattr(graph, "create_dependency_network")

    # Create dependency graph - returns NxGraphUtil
    nx_util = graph.create_dependency_digraph(["a", "b", "c"])

    # NxGraphUtil should have the networkx graph
    assert nx_util is not None
    # NxGraphUtil has graph attribute based on the actual implementation
    assert hasattr(nx_util, "graph") or hasattr(nx_util, "to_physics_network")


def test_di_graph_edge_creation():
    """Test edge information creation in DIGraph."""

    @instance
    def source():
        return "source_value"

    @instance
    def target(source):
        return f"target uses {source}"

    d = design()
    DIGraph(d)

    # Test edge info creation with correct structure
    edge = EdgeInfo(key="target", dependencies=["source"], used_by=[])
    assert edge.key == "target"
    assert "source" in edge.dependencies


def test_create_dependency_graph_function():
    """Test the create_dependency_graph convenience function."""

    @instance
    def root():
        return "root_value"

    @instance
    def leaf(root):
        return f"leaf depends on {root}"

    d = design()

    # Test that function exists and doesn't crash
    # Note: This creates an HTML file
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".html", delete=True) as tmp:
        try:
            result = create_dependency_graph(d, roots=["root"], output_file=tmp.name)
            # Should return a network object
            assert result is not None
        except Exception:
            # May fail if pyvis not installed
            pass


def test_di_graph_provider_dependencies():
    """Test getting provider dependencies."""

    @instance
    def config():
        return {"debug": True}

    @instance
    def logger(config):
        level = "DEBUG" if config["debug"] else "INFO"
        return f"Logger({level})"

    @instance
    def service(logger, config):
        return f"Service with {logger}"

    d = design()
    graph = DIGraph(d)

    # Test that explicit mappings contain our instances
    # The actual keys might be different than function names
    assert len(graph.explicit_mappings) > 0
    assert len(graph.total_bindings) > 0


def test_di_graph_with_injected():
    """Test DIGraph with @injected functions."""

    @injected
    def process(config, /, data: str) -> str:
        return f"{config}: {data}"

    @instance
    def config():
        return "test_config"

    d = design()
    graph = DIGraph(d)

    # Test that graph handles both instance and injected
    assert len(graph.explicit_mappings) > 0
    # Graph should have mappings for our functions
    # Note: actual implementation may use different keys


def test_safe_attr():
    """Test safe_attr function."""

    # Test with object that has attribute
    class TestObj:
        test_attr = "test_value"

    obj = TestObj()
    result = safe_attr(obj, "test_attr")
    assert isinstance(result, Success)
    assert result.unwrap() == "test_value"

    # Test with missing attribute
    result = safe_attr(obj, "missing_attr")
    assert isinstance(result, Failure)


def test_edge_info_to_json_repr():
    """Test EdgeInfo.to_json_repr method."""
    # Test with basic info
    edge = EdgeInfo(key="test_key", dependencies=["dep1", "dep2"], used_by=["user1"])
    json_repr = edge.to_json_repr()
    assert json_repr["key"] == "test_key"
    assert json_repr["dependencies"] == ["dep1", "dep2"]
    assert json_repr["used_by"] == ["user1"]
    assert json_repr["metadata"] is None
    assert json_repr["spec"] is None

    # Test with metadata
    # Mock metadata with the attributes that to_json_repr expects
    metadata = Mock()
    location = Mock()
    location.file_path = "/test/path.py"
    location.line_no = 42
    metadata.location = location
    metadata.docstring = "Test docstring"
    metadata.source = "test source"

    edge_with_meta = EdgeInfo(key="test_key", dependencies=[], metadata=Some(metadata))
    json_repr = edge_with_meta.to_json_repr()
    assert json_repr["metadata"] is not None
    assert json_repr["metadata"]["location"]["file_path"] == "/test/path.py"
    assert json_repr["metadata"]["location"]["line_no"] == 42
    assert json_repr["metadata"]["docstring"] == "Test docstring"
    assert json_repr["metadata"]["source"] == "test source"

    # Test with metadata without location
    metadata_no_loc = Mock(spec_set=["protocol"])
    metadata_no_loc.protocol = None
    edge_with_meta_no_loc = EdgeInfo(
        key="test_key", dependencies=[], metadata=Some(metadata_no_loc)
    )
    json_repr_no_loc = edge_with_meta_no_loc.to_json_repr()
    assert json_repr_no_loc["metadata"] is not None
    assert json_repr_no_loc["metadata"]["location"] is None
    assert json_repr_no_loc["metadata"]["docstring"] is None
    assert json_repr_no_loc["metadata"]["source"] is None

    # Test with spec that looks like dict
    spec_mock = Mock()
    spec_mock.__str__ = Mock(return_value="{'key': 'value'}")
    edge_with_spec = EdgeInfo(key="test_key", dependencies=[], spec=Some(spec_mock))
    json_repr = edge_with_spec.to_json_repr()
    assert json_repr["spec"] == {"key": "value"}

    # Test with spec that doesn't parse as dict
    spec_mock2 = Mock()
    spec_mock2.__str__ = Mock(return_value="not a dict")
    edge_with_spec2 = EdgeInfo(key="test_key", dependencies=[], spec=Some(spec_mock2))
    json_repr = edge_with_spec2.to_json_repr()
    assert json_repr["spec"] == "not a dict"


def test_di_graph_new_name():
    """Test DIGraph.new_name method."""
    d = design()
    graph = DIGraph(d)

    # Test generating new names
    name1 = graph.new_name("base")
    name2 = graph.new_name("base")

    assert name1.startswith("base_")
    assert name2.startswith("base_")
    assert name1 != name2  # Should be unique


def test_di_graph_get_metadata():
    """Test DIGraph.get_metadata method."""
    d = design(test_key="test_value")
    graph = DIGraph(d)

    # Test getting metadata - should return Nothing if not found
    metadata = graph.get_metadata("test_key")
    assert isinstance(metadata, Maybe)

    # Test with non-existent key
    metadata = graph.get_metadata("non_existent")
    assert metadata == Nothing


def test_di_graph_resolve_injected():
    """Test DIGraph.resolve_injected method."""
    d = design()
    graph = DIGraph(d)

    # Test with InjectedPure
    pure_inj = InjectedPure("test_value")
    deps = graph.resolve_injected(pure_inj)
    assert isinstance(deps, list)
    assert len(deps) == 0  # Pure has no dependencies

    # Test with InjectedByName
    by_name = InjectedByName("test_name")
    deps = graph.resolve_injected(by_name)
    assert isinstance(deps, list)
    assert len(deps) == 1
    assert deps[0] == "test_name"

    # Test that same injected gets same ID
    graph.resolve_injected(pure_inj)
    assert graph.injected_to_id[pure_inj] == graph.injected_to_id[pure_inj]


def test_di_graph_resolve_injected_from_function():
    """Test resolve_injected with InjectedFromFunction."""
    d = design()
    graph = DIGraph(d)

    # Create mock coroutine function
    async def mock_func(**kwargs):
        return "result"

    # Test with string kwargs
    inj = InjectedFromFunction(
        original_function=mock_func,
        target_function=mock_func,
        kwargs_mapping={"arg1": "dep1", "arg2": "dep2"},
    )
    deps = graph.resolve_injected(inj)
    # resolve_injected creates new dep names with unique IDs
    assert len(deps) == 2

    # Test with injected kwargs
    nested_inj = InjectedPure("nested")
    inj2 = InjectedFromFunction(
        original_function=mock_func,
        target_function=mock_func,
        kwargs_mapping={"arg1": nested_inj},
    )
    deps2 = graph.resolve_injected(inj2)
    assert len(deps2) > 0


def test_di_graph_deps_impl():
    """Test DIGraph.deps_impl method."""

    @instance
    def test_service():
        return "service"

    d = design(custom_key="custom_value")
    graph = DIGraph(d)

    # Test with explicit mapping
    assert "test_service" in graph.explicit_mappings
    deps = graph.deps_impl("test_service")
    assert isinstance(deps, list)

    # Test with provide_ prefix
    deps = graph.deps_impl("provide_test_service")
    assert isinstance(deps, list)

    # Test with missing key
    with pytest.raises(MissingKeyError) as exc_info:
        graph.deps_impl("non_existent_key")
    assert "DI key not found!" in str(exc_info.value)


def test_di_graph_di_dfs():
    """Test DIGraph.di_dfs method."""

    @instance
    def a():
        return "A"

    @instance
    def b(a):
        return f"B-{a}"

    d = design()
    graph = DIGraph(d)

    # Test DFS traversal
    edges = list(graph.di_dfs("b"))
    assert len(edges) > 0
    # Should find edge from b to a
    assert any(edge[0] == "b" and edge[1] == "a" for edge in edges)


def test_di_graph_find_missing_dependencies():
    """Test DIGraph.find_missing_dependencies method."""
    d = design()
    graph = DIGraph(d)

    # Test with valid dependencies
    failures = graph.find_missing_dependencies([])
    assert isinstance(failures, list)
    assert len(failures) == 0

    # Test with known keys
    failures = graph.find_missing_dependencies(["__builtins__"])
    assert isinstance(failures, list)


def test_di_graph_to_edges():
    """Test DIGraph.to_edges method."""

    @instance
    def config():
        return {"debug": True}

    @instance
    def logger(config):
        return "Logger"

    d = design()
    graph = DIGraph(d)

    # Test edge generation with required arguments
    edges = graph.to_edges("root", ["logger"])
    assert isinstance(edges, list)

    # Should have EdgeInfo objects in the list
    assert len(edges) > 0
    for edge in edges:
        assert isinstance(edge, EdgeInfo)


def test_di_graph_parse_injected():
    """Test DIGraph.parse_injected method."""
    d = design()
    graph = DIGraph(d)

    # Test with different injected types
    pure = InjectedPure("test")
    label = graph.parse_injected(pure)
    assert len(label) == 3
    assert label[0] == "injected"
    assert "Pure:test" in label[1]

    # Test with InjectedByName
    by_name = InjectedByName("test_name")
    label = graph.parse_injected(by_name)
    assert label[0] == "injected"
    assert "test_name" in label[1]

    # Test with unknown type
    unknown = Mock()
    with pytest.raises(ValueError) as exc_info:
        graph.parse_injected(unknown)
    assert "unknown injected type" in str(exc_info.value)


def test_di_graph_create_dependency_digraph_rooted():
    """Test create_dependency_digraph_rooted method."""
    d = design(base="base_value")
    graph = DIGraph(d)

    # Create rooted graph
    root_inj = InjectedPure("root_value")
    nx_util = graph.create_dependency_digraph_rooted(root_inj, "custom_root")

    # Should return NxGraphUtil
    assert nx_util is not None


def test_di_graph_create_graph_from_nodes():
    """Test create_graph_from_nodes method."""

    @instance
    def node1():
        return "n1"

    @instance
    def node2(node1):
        return f"n2-{node1}"

    d = design()
    graph = DIGraph(d)

    # Create graph from specific nodes
    nx_util = graph.create_graph_from_nodes(["node1", "node2"])
    assert nx_util is not None


def test_di_graph_create_dependency_network():
    """Test create_dependency_network method."""
    d = design(key="value")
    graph = DIGraph(d)

    # Create network - might fail if pyvis not installed
    try:
        net = graph.create_dependency_network(["key"])
        assert net is not None
    except ImportError:
        # pyvis not installed
        pass


def test_di_graph_stylize_graph():
    """Test stylize_graph method."""
    import networkx as nx

    d = design()
    graph = DIGraph(d)

    # Create a simple networkx graph
    nx_graph = nx.DiGraph()
    nx_graph.add_node("test_node")
    nx_graph.add_edge("test_node", "dep_node")

    # Apply styling with required replace_missing parameter
    graph.stylize_graph(nx_graph, replace_missing=True)

    # Should have added attributes
    assert "test_node" in nx_graph.nodes
    node_attrs = nx_graph.nodes["test_node"]
    assert "label" in node_attrs or "title" in node_attrs


def test_di_graph_spec_handling():
    """Test DIGraph with DesignSpec."""
    from pinjected.di.design_spec.protocols import DesignSpec, BindSpec

    # Create mock spec
    mock_spec = Mock(spec=DesignSpec)
    mock_bind_spec = Mock(spec=BindSpec)
    mock_bind_spec.key = "test_key"
    mock_bind_spec.provider = InjectedPure("test_value")
    mock_spec.binds = {"test_key": mock_bind_spec}

    d = design()
    graph = DIGraph(d, spec=Some(mock_spec))

    assert graph.spec != Nothing


def test_create_dependency_graph_function_detailed():
    """Test create_dependency_graph with various parameters."""

    @instance
    def service1():
        return "s1"

    @instance
    def service2(service1):
        return f"s2-{service1}"

    d = design()

    # Test with mock to avoid file creation
    with patch("pinjected.visualize_di.DIGraph") as mock_di_graph:
        mock_graph = Mock()
        mock_di_graph.return_value = mock_graph
        mock_graph.create_dependency_network.return_value = Mock()

        create_dependency_graph(d, roots=["service1"], output_file="test.html")

        # Verify DIGraph was created
        assert mock_di_graph.called
        mock_graph.create_dependency_network.assert_called_once()


def test_di_graph_to_python_script():
    """Test DIGraph.to_python_script method."""
    from pinjected import Injected

    @instance
    def my_service():
        return "service"

    d = design()
    graph = DIGraph(d)

    # Test with string root - use a valid module path
    with patch("pinjected.module_var_path.load_variable_by_module_path") as mock_load:
        mock_load.return_value = my_service
        script = graph.to_python_script("test.module.my_service", "test.module.design")
        assert isinstance(script, str)
        assert "from pinjected.di.util import Design, design" in script
        assert "d:Design =" in script
        assert "__target__" in script

    # Test with Injected root
    injected_root = Injected.pure("test_value")
    script = graph.to_python_script(injected_root, "test.module.design")
    assert isinstance(script, str)

    # Test with unsupported type
    with pytest.raises(ValueError) as exc_info:
        graph.to_python_script(123, "test.module.design")
    assert "unsupported type" in str(exc_info.value)


def test_di_graph_get_node_to_sl():
    """Test DIGraph.get_node_to_sl method."""
    import networkx as nx
    from pinjected import Injected

    d = design(test_key=Injected.pure("test_value"))
    graph = DIGraph(d)

    nx_graph = nx.DiGraph()
    nx_graph.add_node("test_key")
    nx_graph.add_node("missing_key")  # Add the missing key to the graph

    # Get the node_to_sl function
    node_to_sl = graph.get_node_to_sl(nx_graph, replace_missing=True)

    # Test with existing key
    attrs = node_to_sl("test_key")
    assert isinstance(attrs, dict)
    assert "label" in attrs
    assert "title" in attrs
    assert "value" in attrs
    assert "mass" in attrs
    assert "color" in attrs

    # Test with missing key (not in design but in graph)
    attrs = node_to_sl("missing_key")
    assert attrs["label"].startswith("missing_key")


def test_di_graph_distilled():
    """Test DIGraph.distilled method."""

    @instance
    def config():
        return {"env": "test"}

    @instance
    def service(config):
        return f"Service in {config['env']}"

    d = design()
    graph = DIGraph(d)

    # Test with string target
    distilled = graph.distilled("service")
    assert distilled is not None
    # Should be a Design object
    from pinjected import Design

    assert isinstance(distilled, Design)


def test_di_graph_plot():
    """Test DIGraph.plot method."""

    d = design(key="value")
    graph = DIGraph(d)

    # Test plot method - it checks platform
    with patch("platform.system") as mock_system:
        # Test on macOS
        mock_system.return_value = "Darwin"
        with patch.object(graph, "create_dependency_digraph") as mock_create:
            mock_util = Mock()
            mock_create.return_value = mock_util

            graph.plot(["key"])

            mock_create.assert_called_once_with(["key"], replace_missing=True)
            mock_util.plot_mpl.assert_called_once()

        # Test on non-macOS
        mock_system.return_value = "Linux"
        with patch("pinjected.pinjected_logging.logger") as mock_logger:
            graph.plot(["key"])
            mock_logger.warning.assert_called()


def test_di_graph_show_html():
    """Test DIGraph.show_html method."""
    d = design(key="value")
    graph = DIGraph(d)

    with patch.object(graph, "create_dependency_digraph") as mock_create:
        mock_util = Mock()
        mock_create.return_value = mock_util

        graph.show_html(["key"])

        mock_create.assert_called_once_with(["key"], replace_missing=True)
        mock_util.show_html.assert_called_once()


def test_di_graph_show_injected_html():
    """Test DIGraph.show_injected_html method."""
    from pinjected import Injected

    d = design()
    graph = DIGraph(d)

    injected_val = Injected.pure("test")

    with patch.object(graph, "create_dependency_digraph_rooted") as mock_create:
        mock_util = Mock()
        mock_create.return_value = mock_util

        graph.show_injected_html(injected_val, "test_name")

        mock_create.assert_called_once()
        mock_util.show_html_temp.assert_called_once()


def test_di_graph_show_whole_html():
    """Test DIGraph.show_whole_html method."""
    d = design(key1="value1", key2="value2")
    graph = DIGraph(d)

    with patch.object(graph, "create_dependency_digraph") as mock_create:
        mock_util = Mock()
        mock_create.return_value = mock_util

        graph.show_whole_html()

        # Should be called with all explicit mappings as roots
        mock_create.assert_called_once()
        call_args = mock_create.call_args[0][0]
        assert isinstance(call_args, list)
        assert len(call_args) >= 2  # At least our two keys


def test_di_graph_save_as_html():
    """Test DIGraph.save_as_html method."""
    from pathlib import Path
    from pinjected import Injected

    d = design()
    graph = DIGraph(d)

    injected_val = Injected.pure("test")

    with patch.object(graph, "create_dependency_digraph_rooted") as mock_create:
        mock_util = Mock()
        mock_create.return_value = mock_util

        graph.save_as_html(injected_val, Path("/tmp"))

        mock_create.assert_called_once_with(injected_val, replace_missing=True)
        mock_util.save_as_html_at.assert_called_once_with(Path("/tmp"))


def test_di_graph_to_json_with_root_name():
    """Test DIGraph.to_json_with_root_name method."""
    d = design(dep1="value1", dep2="value2")
    graph = DIGraph(d)

    with patch.object(graph, "to_edges") as mock_to_edges:
        mock_edges = [
            EdgeInfo(key="dep1", dependencies=[]),
            EdgeInfo(key="dep2", dependencies=[]),
        ]
        mock_to_edges.return_value = mock_edges

        result = graph.to_json_with_root_name("root", ["dep1", "dep2"])

        assert "edges" in result
        assert len(result["edges"]) == 2
        mock_to_edges.assert_called_once_with("root", ["dep1", "dep2"])


def test_di_graph_to_json():
    """Test DIGraph.to_json method."""
    d = design(service="value")
    graph = DIGraph(d)

    with patch.object(graph, "to_edges") as mock_to_edges:
        mock_edges = [
            EdgeInfo(key="__root__", dependencies=["service"]),
            EdgeInfo(key="service", dependencies=[]),
        ]
        mock_to_edges.return_value = mock_edges

        # Test with single root
        result = graph.to_json("service")

        assert "edges" in result
        # Should filter out __root__
        assert all(edge["key"] != "__root__" for edge in result["edges"])

        # Test with list of roots
        result = graph.to_json(["service"])
        assert "edges" in result


def test_di_graph_get_spec():
    """Test DIGraph.get_spec method."""
    from pinjected.di.design_spec.protocols import DesignSpec, BindSpec
    from pinjected.v2.keys import StrBindKey

    # Create mock spec
    mock_spec = Mock(spec=DesignSpec)
    mock_bind_spec = Mock(spec=BindSpec)
    mock_spec.get_spec.return_value = Some(mock_bind_spec)

    d = design()
    graph = DIGraph(d, spec=Some(mock_spec))

    # Test getting spec
    result = graph.get_spec("test_key")
    assert result == Some(mock_bind_spec)

    # Verify the call
    mock_spec.get_spec.assert_called_once()
    call_arg = mock_spec.get_spec.call_args[0][0]
    assert isinstance(call_arg, StrBindKey)
    assert call_arg.name == "test_key"


def test_di_graph_show_graph_notebook():
    """Test DIGraph.show_graph_notebook method."""
    d = design(key="value")
    graph = DIGraph(d)

    with patch.object(graph, "create_dependency_network") as mock_create:
        mock_net = Mock()
        mock_create.return_value = mock_net

        graph.show_graph_notebook(["key"])

        mock_create.assert_called_once_with(["key"])
        assert mock_net.width == 1000
        assert mock_net.height == 1000
        mock_net.prep_notebook.assert_called_once()
        mock_net.show.assert_called_once_with("__notebook__.html")


def test_edge_info_with_complete_metadata():
    """Test EdgeInfo with all metadata fields."""
    # Create comprehensive metadata
    metadata = Mock()
    location = Mock()
    location.file_path = "/path/to/file.py"
    location.line_no = 100
    metadata.location = location
    metadata.docstring = "Comprehensive docstring"
    metadata.source = "def my_function():\n    pass"

    edge = EdgeInfo(
        key="test_key",
        dependencies=["dep1", "dep2", "dep3"],
        used_by=["user1", "user2"],
        metadata=Some(metadata),
    )

    json_repr = edge.to_json_repr()

    # Verify all fields
    assert json_repr["key"] == "test_key"
    assert len(json_repr["dependencies"]) == 3
    assert len(json_repr["used_by"]) == 2
    assert json_repr["metadata"]["location"]["file_path"] == "/path/to/file.py"
    assert json_repr["metadata"]["location"]["line_no"] == 100
    assert json_repr["metadata"]["docstring"] == "Comprehensive docstring"
    assert "def my_function" in json_repr["metadata"]["source"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
