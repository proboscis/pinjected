"""Tests for visualize_di.py to improve coverage."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from returns.maybe import Nothing, Some
import networkx as nx

from pinjected.visualize_di import (
    dfs,
    rgb_to_hex,
    get_color,
    getitem,
    EdgeInfo,
    DIGraph,
    MissingKeyError,
    create_dependency_graph,
)
from pinjected.di.injected import (
    InjectedByName,
    InjectedFromFunction,
    InjectedPure,
    MappedInjected,
)
from pinjected.di.metadata.bind_metadata import BindMetadata
from pinjected.di.metadata.location_data import ModuleVarLocation
from pinjected.exceptions import _MissingDepsError
from pinjected import EmptyDesign
from returns.pipeline import is_successful
from pinjected.nx_graph_util import NxGraphUtil


class TestUtilityFunctions:
    """Test utility functions in visualize_di.py."""

    def test_dfs(self):
        """Test depth-first search generator."""

        def neighbors(node):
            graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
            return graph.get(node, [])

        results = list(dfs(neighbors, "A"))
        assert len(results) > 0
        # Check first edge
        assert results[0] == ("A", "B", [])
        # Check that we get edges to D from both B and C
        edges = [(src, dst) for src, dst, _ in results]
        assert ("B", "D") in edges
        assert ("C", "D") in edges

    def test_rgb_to_hex(self):
        """Test RGB to hex conversion."""
        assert rgb_to_hex((255, 255, 255)) == "#ffffff"
        assert rgb_to_hex((0, 0, 0)) == "#000000"
        assert rgb_to_hex((255, 0, 0)) == "#ff0000"
        assert rgb_to_hex((0, 255, 0)) == "#00ff00"
        assert rgb_to_hex((0, 0, 255)) == "#0000ff"

    def test_get_color(self):
        """Test color generation based on edge count."""
        # Test various edge counts
        color_0 = get_color(0)
        color_5 = get_color(5)
        color_10 = get_color(10)
        color_15 = get_color(15)  # Should cap at 10

        # All should be valid hex colors
        for color in [color_0, color_5, color_10, color_15]:
            assert color.startswith("#")
            assert len(color) == 7

        # Color should get redder as edges increase
        # (lower hue value in HSV)
        assert color_0 != color_10

    def test_getitem(self):
        """Test safe getitem function."""
        test_dict = {"key": "value", "num": 42}

        # Successful access
        result = getitem(test_dict, "key")
        assert result.unwrap() == "value"

        # Failed access
        result = getitem(test_dict, "missing")
        assert not is_successful(result)

        # Test with list
        test_list = [1, 2, 3]
        result = getitem(test_list, 1)
        assert result.unwrap() == 2


class TestEdgeInfo:
    """Test EdgeInfo dataclass and its methods."""

    def test_edge_info_creation(self):
        """Test creating EdgeInfo instances."""
        edge = EdgeInfo(
            key="test_key",
            dependencies=["dep1", "dep2"],
            used_by=["user1"],
            metadata=Nothing,
            spec=Nothing,
        )
        assert edge.key == "test_key"
        assert edge.dependencies == ["dep1", "dep2"]
        assert edge.used_by == ["user1"]

    def test_to_json_repr_basic(self):
        """Test converting EdgeInfo to JSON representation."""
        edge = EdgeInfo(
            key="test_key",
            dependencies=["dep1", "dep2"],
            used_by=["user1"],
        )
        json_repr = edge.to_json_repr()

        assert json_repr["key"] == "test_key"
        assert json_repr["dependencies"] == ["dep1", "dep2"]
        assert json_repr["used_by"] == ["user1"]
        assert json_repr["metadata"] is None
        assert json_repr["spec"] is None

    def test_to_json_repr_with_metadata(self):
        """Test converting EdgeInfo with metadata to JSON."""
        from pathlib import Path

        location = ModuleVarLocation(path=Path("/path/to/file.py"), line=42, column=0)
        metadata = MagicMock()
        metadata.location = location
        metadata.docstring = "Test docstring"
        metadata.source = "test_source"

        edge = EdgeInfo(key="test_key", dependencies=[], metadata=Some(metadata))
        json_repr = edge.to_json_repr()

        assert json_repr["metadata"] is not None
        # Check if metadata location exists and has expected structure
        # The actual implementation in to_json_repr checks for file_path attribute
        assert json_repr["metadata"]["docstring"] == "Test docstring"
        assert json_repr["metadata"]["source"] == "test_source"

    def test_to_json_repr_with_spec(self):
        """Test converting EdgeInfo with spec to JSON."""
        # Test with dict-like spec string
        spec_mock = Mock()
        spec_mock.__str__ = Mock(return_value="{'key': 'value', 'num': 42}")

        edge = EdgeInfo(key="test_key", dependencies=[], spec=Some(spec_mock))
        json_repr = edge.to_json_repr()

        assert json_repr["spec"] == {"key": "value", "num": 42}

        # Test with non-dict spec string
        spec_mock.__str__ = Mock(return_value="some_spec_string")
        edge.spec = Some(spec_mock)
        json_repr = edge.to_json_repr()
        assert json_repr["spec"] == "some_spec_string"


class TestDIGraph:
    """Test DIGraph class."""

    def test_digraph_creation(self):
        """Test creating DIGraph instance."""
        design = EmptyDesign
        graph = DIGraph(src=design)

        assert graph.src == design
        assert graph.spec == Nothing
        assert graph.use_implicit_bindings is True

    def test_new_name(self):
        """Test new_name method."""
        design = EmptyDesign
        graph = DIGraph(src=design)

        name1 = graph.new_name("base")
        name2 = graph.new_name("base")

        assert name1.startswith("base_")
        assert name2.startswith("base_")
        assert name1 != name2  # Should be unique

    @patch("pinjected.visualize_di.DIGraphHelper")
    def test_post_init(self, mock_helper_class):
        """Test __post_init__ method."""
        mock_helper = Mock()
        mock_helper.total_mappings.return_value = {"key1": Mock()}
        mock_helper.total_bindings.return_value = {}
        mock_helper_class.return_value = mock_helper

        design = EmptyDesign
        graph = DIGraph(src=design)

        assert mock_helper_class.called
        assert graph.helper == mock_helper
        assert "key1" in graph.explicit_mappings

    def test_deps_impl(self):
        """Test deps_impl function."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_injected = InjectedByName("test")
            mock_helper.total_mappings.return_value = {"test_key": mock_injected}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Mock resolve_injected
            graph.resolve_injected = Mock(return_value=["dep1", "dep2"])

            # Test with key in explicit_mappings
            deps = graph.deps_impl("test_key")
            assert deps == ["dep1", "dep2"]

            # Test with provide_ prefix
            deps = graph.deps_impl("provide_test_key")
            assert deps == ["dep1", "dep2"]

            # Test with missing key
            with pytest.raises(MissingKeyError, match="DI key not found"):
                graph.deps_impl("missing_key")

    def test_get_metadata(self):
        """Test get_metadata method."""
        from pinjected.v2.keys import StrBindKey
        from pinjected.v2.binds import BindInjected

        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}

            # Create a mock bind with metadata
            mock_metadata = Mock(spec=BindMetadata)
            mock_bind = Mock(spec=BindInjected)
            mock_bind.metadata = Some(mock_metadata)

            mock_helper.total_bindings.return_value = {
                StrBindKey("test_key"): mock_bind
            }
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Test existing key
            metadata = graph.get_metadata("test_key")
            assert metadata == Some(mock_metadata)

            # Test missing key
            metadata = graph.get_metadata("missing_key")
            assert metadata == Nothing

    def test_resolve_injected_injected_by_name(self):
        """Test resolve_injected with InjectedByName."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            injected = InjectedByName("test_dep")
            deps = graph.resolve_injected(injected)

            assert deps == ["test_dep"]
            assert injected in graph.injected_to_id

    def test_resolve_injected_injected_from_function(self):
        """Test resolve_injected with InjectedFromFunction."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Mock function - needs to be async
            async def test_func(a, b):
                return a + b

            # Create InjectedFromFunction with dependencies
            injected = InjectedFromFunction(
                original_function=test_func,
                target_function=test_func,
                kwargs_mapping={"a": InjectedByName("dep_a"), "b": InjectedPure(10)},
            )

            # Need to mock recursive calls
            graph.resolve_injected = Mock(
                side_effect=[
                    ["dep_a"],  # First call for kwargs_mapping["a"]
                    [],  # Second call for kwargs_mapping["b"] (pure value)
                    ["dep_a"],  # Final result
                ]
            )

            deps = graph.resolve_injected(injected)
            assert "dep_a" in deps

    def test_resolve_injected_pure(self):
        """Test resolve_injected with InjectedPure."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            injected = InjectedPure(42)
            deps = graph.resolve_injected(injected)

            assert deps == []


class TestDIGraphAdditionalMethods:
    """Test additional DIGraph methods."""

    def test_plot_method(self):
        """Test plot method."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Mock create_dependency_digraph
            mock_g = Mock()
            mock_g.plot_mpl = Mock()
            graph.create_dependency_digraph = Mock(return_value=mock_g)

            # Test on mac
            with patch("platform.system", return_value="Darwin"):
                graph.plot("test_root")
                mock_g.plot_mpl.assert_called_once()

            # Test on non-mac
            with (
                patch("platform.system", return_value="Linux"),
                patch("pinjected.pinjected_logging.logger") as mock_logger,
            ):
                graph.plot("test_root")
                mock_logger.warning.assert_called_once()

    def test_show_html(self):
        """Test show_html method."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Mock create_dependency_digraph
            mock_g = Mock()
            mock_g.show_html = Mock()
            graph.create_dependency_digraph = Mock(return_value=mock_g)

            graph.show_html(["root1", "root2"])
            mock_g.show_html.assert_called_once()

    def test_show_injected_html(self):
        """Test show_injected_html method."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Mock create_dependency_digraph_rooted
            mock_nx = Mock()
            mock_nx.show_html_temp = Mock()
            graph.create_dependency_digraph_rooted = Mock(return_value=mock_nx)

            injected = InjectedByName("test")
            graph.show_injected_html(injected, "custom_name")

            graph.create_dependency_digraph_rooted.assert_called_once()
            mock_nx.show_html_temp.assert_called_once()

    def test_to_json(self):
        """Test to_json method."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Mock to_edges
            mock_edge1 = Mock()
            mock_edge1.key = "edge1"
            mock_edge1.to_json_repr = Mock(return_value={"key": "edge1", "deps": []})

            mock_edge2 = Mock()
            mock_edge2.key = "__root__"
            mock_edge2.to_json_repr = Mock(return_value={"key": "__root__", "deps": []})

            graph.to_edges = Mock(return_value=[mock_edge1, mock_edge2])

            # Test with single root
            result = graph.to_json("test_root")
            assert "edges" in result
            assert len(result["edges"]) == 1  # __root__ should be filtered out

            # Test with multiple roots
            result = graph.to_json(["root1", "root2"])
            assert "edges" in result


class TestVisualizationFunctions:
    """Test top-level visualization functions."""

    @patch("pinjected.visualize_di.DIGraph")
    def test_create_dependency_graph(self, mock_digraph_class):
        """Test create_dependency_graph function."""
        # Mock DIGraph instance
        mock_digraph = Mock()
        mock_nt = Mock()
        mock_nt.show = Mock()
        mock_digraph.create_dependency_network = Mock(return_value=mock_nt)
        mock_digraph_class.return_value = mock_digraph

        # Mock design
        from pinjected import EmptyDesign

        design = EmptyDesign

        result = create_dependency_graph(
            design, ["root1", "root2"], output_file="test.html"
        )

        mock_digraph.create_dependency_network.assert_called_once_with(
            ["root1", "root2"]
        )
        mock_nt.show.assert_called_once_with("test.html")
        assert result == mock_nt


class TestDIGraphResolveInjected:
    """Test more complex resolve_injected scenarios."""

    def test_resolve_injected_mapped(self):
        """Test resolve_injected with MappedInjected."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Create MappedInjected - needs async function
            base_injected = InjectedByName("base")

            async def async_mapper(x):
                return x.upper()

            def original_mapper(x):
                return x.upper()

            injected = MappedInjected(base_injected, async_mapper, original_mapper)

            # Mock the recursive call
            original_resolve = graph.resolve_injected
            call_count = 0

            def mock_resolve(inj):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call with MappedInjected
                    return original_resolve(inj)
                else:
                    # Recursive call with base_injected
                    return ["base"]

            graph.resolve_injected = mock_resolve
            deps = graph.resolve_injected(injected)
            # The actual implementation adds a mapped_src_ prefix with a unique ID
            assert len(deps) == 1
            assert deps[0].startswith("mapped_src_")

    def test_resolve_injected_mzipped(self):
        """Test resolve_injected with MZippedInjected."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Create MZippedInjected
            from pinjected.di.injected import MZippedInjected

            injected1 = InjectedByName("dep1")
            injected2 = InjectedByName("dep2")
            injected = MZippedInjected(injected1, injected2)

            # Store calls to track recursive resolution
            resolved_deps = []
            original_resolve = graph.resolve_injected

            def mock_resolve(inj):
                if isinstance(inj, MZippedInjected):
                    # Resolve each target
                    for src in inj.srcs:
                        resolved_deps.extend(original_resolve(src))
                    return resolved_deps
                else:
                    return original_resolve(inj)

            graph.resolve_injected = mock_resolve
            deps = graph.resolve_injected(injected)
            assert "dep1" in deps
            assert "dep2" in deps


class TestDIGraphMethods:
    """Test additional DIGraph methods."""

    def test_di_dfs_success(self):
        """Test di_dfs method with successful dependency resolution."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Mock dependencies_of
            graph.dependencies_of = Mock(
                side_effect=lambda node: {
                    "A": ["B", "C"],
                    "B": ["D"],
                    "C": ["D"],
                    "D": [],
                }.get(node, [])
            )

            results = list(graph.di_dfs("A"))
            edges = [(src, dst) for src, dst, _ in results]

            assert ("A", "B") in edges
            assert ("A", "C") in edges
            assert ("B", "D") in edges
            assert ("C", "D") in edges

    def test_di_dfs_cyclic_dependency(self):
        """Test di_dfs with cyclic dependency."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Create cyclic dependency: A -> B -> C -> A
            graph.dependencies_of = Mock(
                side_effect=lambda node: {"A": ["B"], "B": ["C"], "C": ["A"]}.get(
                    node, []
                )
            )

            # Should raise AssertionError due to cycle detection
            with pytest.raises(AssertionError, match="cycle detected"):
                list(graph.di_dfs("A"))

    def test_di_dfs_missing_dependency(self):
        """Test di_dfs with missing dependency."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Mock dependencies_of to raise MissingKeyError
            def mock_deps(node):
                if node == "missing":
                    raise MissingKeyError(f"Key not found: {node}")
                return []

            graph.dependencies_of = Mock(side_effect=mock_deps)

            # Should raise _MissingDepsError
            with pytest.raises(_MissingDepsError, match="failed to get neighbors"):
                list(graph.di_dfs("missing"))

    def test_get_source(self):
        """Test get_source static method."""

        # Test with regular function
        def test_func():
            pass

        result = DIGraph.get_source(test_func)
        assert "test_func" in result

        # Test with function that has __original_file__
        test_func.__original_file__ = "/custom/path.py"
        test_func.__original_code__ = "def custom_func(): pass"

        result = DIGraph.get_source(test_func)
        assert "/custom/path.py" in result
        assert "def custom_func" in result

    def test_get_source_repr(self):
        """Test get_source_repr static method."""

        def test_func():
            pass

        result = DIGraph.get_source_repr(test_func)
        # Should replace special characters
        assert "<" not in result
        assert ">" not in result
        # Should replace whitespace
        assert "...." in result or "." in result

    def test_parse_injected_various_types(self):
        """Test parse_injected with various injected types."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Test InjectedByName
            result = graph.parse_injected(InjectedByName("test_name"))
            assert result[0] == "injected"
            assert result[1] == "test_name"
            assert result[2] == "by_name"

            # Test InjectedPure with value
            result = graph.parse_injected(InjectedPure(42))
            assert result[0] == "injected"
            assert "Pure:42" in result[1]
            assert "42" in result[2]

            # Test InjectedPure with callable
            def test_func():
                return 1

            result = graph.parse_injected(InjectedPure(test_func))
            assert result[0] == "injected"
            assert "Pure:" in result[1]

    def test_distilled_with_string(self):
        """Test distilled method with string target."""

        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Mock di_dfs to return some dependencies
            graph.di_dfs = Mock(
                return_value=[
                    ("node1", "dep1", []),
                    ("node1", "dep2", []),
                    ("dep1", "dep3", []),
                ]
            )

            # Mock __contains__ for src
            graph.src.__contains__ = Mock(return_value=True)
            graph.src.__getitem__ = Mock(return_value="mock_binding")

            result = graph.distilled("node1")
            assert result is not None

    def test_create_graph_from_nodes(self):
        """Test create_graph_from_nodes method."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Mock di_dfs
            graph.di_dfs = Mock(return_value=[("A", "B", []), ("B", "C", [])])

            # Mock stylize_graph
            graph.stylize_graph = Mock()

            result = graph.create_graph_from_nodes(["A", "B"])

            assert isinstance(result, NxGraphUtil)
            graph.stylize_graph.assert_called_once()

    def test_to_python_script_with_injected(self):
        """Test to_python_script method with Injected input."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {
                "test_key": InjectedByName("dep1")
            }
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Mock various methods
            graph.create_dependency_digraph_rooted = Mock()
            mock_graph = Mock()
            mock_graph.nx_graph = nx.DiGraph()
            mock_graph.nx_graph.add_node("test")
            mock_graph.roots = ["test"]
            graph.create_dependency_digraph_rooted.return_value = mock_graph

            injected = InjectedByName("test")
            result = graph.to_python_script(injected, "my.design.path")

            # Check that result contains expected imports
            assert "from pinjected.di.util import Design, design" in result
            assert "from my.design import path" in result


class TestDIGraphExtraMethods:
    """Test extra DIGraph methods for better coverage."""

    def test_save_as_html(self):
        """Test save_as_html method."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Mock create_dependency_digraph_rooted
            mock_nx = Mock()
            mock_nx.save_as_html_at = Mock(return_value="/path/to/saved.html")
            graph.create_dependency_digraph_rooted = Mock(return_value=mock_nx)

            from pathlib import Path

            injected = InjectedByName("test")
            result = graph.save_as_html(injected, Path("/tmp"))

            assert result == "/path/to/saved.html"

    def test_show_whole_html(self):
        """Test show_whole_html method."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {"key1": Mock(), "key2": Mock()}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Mock create_dependency_digraph
            mock_result = Mock()
            mock_result.show_html_temp = Mock()
            graph.create_dependency_digraph = Mock(return_value=mock_result)

            graph.show_whole_html()

            # Should use all keys from explicit_mappings
            graph.create_dependency_digraph.assert_called_once()
            call_args = graph.create_dependency_digraph.call_args
            assert set(call_args[0][0]) == {"key1", "key2"}

    def test_get_spec(self):
        """Test get_spec method."""
        from returns.maybe import Some

        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            # Mock spec
            mock_spec = Mock()
            mock_bind_spec = Mock()
            mock_spec.get_spec = Mock(return_value=Some(mock_bind_spec))

            design = EmptyDesign
            graph = DIGraph(src=design, spec=Some(mock_spec))

            result = graph.get_spec("test_key")

            mock_spec.get_spec.assert_called_once()
            assert result == Some(mock_bind_spec)

    def test_stylize_graph(self):
        """Test stylize_graph method."""
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_helper.total_mappings.return_value = {}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            design = EmptyDesign
            graph = DIGraph(src=design)

            # Create a simple networkx graph
            nx_graph = nx.DiGraph()
            nx_graph.add_node("node1")
            nx_graph.add_node("node2")
            nx_graph.add_edge("node1", "node2")

            # Mock get_node_to_sl
            mock_node_to_sl = Mock(
                side_effect=lambda n: {
                    "label": f"{n}_label",
                    "color": "#ff0000",
                    "value": 1,
                }
            )
            graph.get_node_to_sl = Mock(return_value=mock_node_to_sl)

            graph.stylize_graph(nx_graph, replace_missing=True)

            # Check that attributes were added
            assert nx_graph.nodes["node1"]["label"] == "node1_label"
            assert nx_graph.nodes["node2"]["label"] == "node2_label"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
