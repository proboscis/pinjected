"""Tests to boost coverage for pinjected.visualize_di module."""

from unittest.mock import Mock, patch
from returns.maybe import Nothing, Some
from pinjected.visualize_di import (
    DIGraph,
    create_dependency_graph,
    dfs,
    getitem,
    rgb_to_hex,
    get_color,
    MissingKeyError,
    EdgeInfo,
)


class TestDIGraphCoverage:
    """Tests to improve coverage of DIGraph class."""

    def test_digraph_init(self):
        """Test DIGraph initialization."""
        mock_design = Mock()
        mock_design.__str__ = Mock(return_value="MockDesign")
        mock_design.bindings = {}  # Empty bindings dict

        # Test basic initialization
        graph = DIGraph(mock_design)
        assert graph.src == mock_design
        assert graph.use_implicit_bindings is True  # default
        assert graph.spec == Nothing  # default is Nothing, not None

        # Test with parameters
        from returns.maybe import Some

        mock_spec = Mock()
        graph2 = DIGraph(mock_design, use_implicit_bindings=False, spec=Some(mock_spec))
        assert graph2.use_implicit_bindings is False
        assert graph2.spec == Some(mock_spec)

    def test_digraph_str(self):
        """Test DIGraph string representation."""
        mock_design = Mock()
        mock_design.__str__ = Mock(return_value="TestDesign")
        mock_design.bindings = {}

        graph = DIGraph(mock_design)
        str_repr = str(graph)
        assert "DIGraph" in str_repr
        assert "src=" in str_repr
        assert "spec=" in str_repr
        assert "use_implicit_bindings=True" in str_repr

    @patch("pinjected.visualize_di.DIGraphHelper")
    def test_digraph_helper_property(self, mock_helper_class):
        """Test helper property lazy initialization."""
        mock_design = Mock()
        mock_design.bindings = {}
        mock_helper = Mock()
        mock_helper.total_mappings.return_value = {}
        mock_helper.total_bindings.return_value = {}
        mock_helper_class.return_value = mock_helper

        graph = DIGraph(mock_design)

        # Access helper property multiple times
        helper1 = graph.helper
        helper2 = graph.helper

        # Should only create helper once (cached)
        assert helper1 == mock_helper
        assert helper2 == mock_helper
        mock_helper_class.assert_called_once_with(
            mock_design, use_implicit_bindings=True
        )

    def test_digraph_explicit_mappings(self):
        """Test explicit_mappings attribute is populated from helper."""
        mock_design = Mock()
        mock_design.bindings = {}

        # Patch DIGraphHelper to control what it returns
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_mappings = {"key1": "value1", "key2": "value2"}
            mock_helper.total_mappings.return_value = mock_mappings
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            graph = DIGraph(mock_design)

            # Check that explicit_mappings was set from helper.total_mappings()
            assert graph.explicit_mappings == mock_mappings
            mock_helper.total_mappings.assert_called_once()

    def test_digraph_resolve_injected_by_name(self):
        """Test resolve_injected with InjectedByName."""
        from pinjected.di.injected import InjectedByName

        mock_design = Mock()
        mock_design.bindings = {}
        graph = DIGraph(mock_design)

        injected = InjectedByName("test_key")
        result = graph.resolve_injected(injected)

        # resolve_injected returns a list of dependencies
        assert result == ["test_key"]

    def test_digraph_resolve_injected_mapped(self):
        """Test resolve_injected with mapped injected - should generate UUID for unknown injected."""
        from pinjected.di.injected import InjectedPure

        mock_design = Mock()
        mock_design.bindings = {}
        graph = DIGraph(mock_design)

        # Test with a non-InjectedByName injected
        injected = InjectedPure("some_value")
        result = graph.resolve_injected(injected)

        # Should return empty list since InjectedPure has no dependencies
        assert result == []

        # Should have assigned an ID to this injected
        assert injected in graph.injected_to_id

    def test_digraph_get_metadata_key_not_found(self):
        """Test get_metadata when key is not found."""
        mock_design = Mock()
        mock_design.bindings = {}
        graph = DIGraph(mock_design)

        metadata = graph.get_metadata("nonexistent_key")

        assert metadata == Nothing

    def test_digraph_get_metadata_key_found(self):
        """Test get_metadata when key is found."""
        from pinjected.di.metadata.bind_metadata import BindMetadata
        from pinjected.di.metadata.location_data import ModuleVarLocation
        from pinjected.v2.keys import StrBindKey

        mock_design = Mock()
        mock_design.bindings = {}
        graph = DIGraph(mock_design)

        # Create mock binding with metadata
        mock_binding = Mock()
        location = ModuleVarLocation("test.py", 10, 5)
        bind_metadata = BindMetadata(code_location=Some(location))
        mock_binding.metadata = Some(bind_metadata)

        # Manually set the binding in total_bindings
        bind_key = StrBindKey("test_key")
        graph.total_bindings[bind_key] = mock_binding

        metadata = graph.get_metadata("test_key")

        assert metadata == Some(bind_metadata)

    def test_digraph_deps_impl_missing_key(self):
        """Test deps_impl when key is not found."""
        import pytest

        mock_design = Mock()
        mock_design.bindings = {}
        graph = DIGraph(mock_design)

        # Should raise MissingKeyError for unknown key
        with pytest.raises(MissingKeyError) as exc_info:
            graph.deps_impl("unknown_key")

        assert "DI key not found!:unknown_key" in str(exc_info.value)

    def test_digraph_deps_impl_with_explicit_mapping(self):
        """Test deps_impl with explicit mappings."""
        from pinjected.di.injected import InjectedByName

        mock_design = Mock()
        mock_design.bindings = {}

        # Setup graph with explicit mapping
        with patch("pinjected.visualize_di.DIGraphHelper") as mock_helper_class:
            mock_helper = Mock()
            mock_injected = InjectedByName("dep1")
            mock_helper.total_mappings.return_value = {"test_key": mock_injected}
            mock_helper.total_bindings.return_value = {}
            mock_helper_class.return_value = mock_helper

            graph = DIGraph(mock_design)

            # deps_impl should return result of resolve_injected
            with patch.object(
                graph, "resolve_injected", return_value=["resolved_dep"]
            ) as mock_resolve:
                deps = graph.deps_impl("test_key")

                assert deps == ["resolved_dep"]
                mock_resolve.assert_called_once_with(mock_injected)


class TestVisualizeFunctions:
    """Tests for module-level visualization functions."""

    def test_create_dependency_graph_basic(self):
        """Test create_dependency_graph function."""
        from unittest.mock import MagicMock

        # Create a mock design that supports the + operator
        mock_design = MagicMock()
        combined_design = MagicMock()
        mock_design.__add__.return_value = combined_design

        with patch("pinjected.visualize_di.DIGraph") as mock_digraph_class:
            mock_digraph = Mock()
            mock_digraph_class.return_value = mock_digraph
            mock_network = Mock()
            mock_digraph.create_dependency_network.return_value = mock_network
            mock_network.show = Mock()

            result = create_dependency_graph(mock_design, roots=["test_root"])

            assert result == mock_network
            # Check that DIGraph was initialized with the combined design
            assert mock_digraph_class.called
            # The first arg to DIGraph should be the result of design + something
            call_args = mock_digraph_class.call_args[0]
            assert len(call_args) > 0  # Should have at least one argument

            mock_digraph.create_dependency_network.assert_called_once_with(
                ["test_root"]
            )
            mock_network.show.assert_called_once_with("dependencies.html")

    def test_dfs_function(self):
        """Test dfs function."""
        # Create a simple neighbors function
        graph = {"a": ["b", "c"], "b": ["d"], "c": ["e"], "d": [], "e": []}

        def neighbors(node):
            return graph.get(node, [])

        # Test DFS traversal
        visited = list(dfs(neighbors, "a"))

        # dfs yields (from_node, to_node, trace) tuples for edges
        # So for the graph a->b,c b->d c->e, we expect 4 edges
        assert len(visited) == 4

        # Check that all edges are present
        edges = [(v[0], v[1]) for v in visited]
        assert ("a", "b") in edges
        assert ("a", "c") in edges
        assert ("b", "d") in edges
        assert ("c", "e") in edges

    def test_getitem_function(self):
        """Test getitem function."""
        # Test with dict
        obj = {"key": "value"}
        result = getitem(obj, "key")
        assert result.unwrap() == "value"

        # Test with object attribute (note: getitem uses [], not getattr)
        # getitem is for subscript access, not attribute access
        # This test was incorrect - getitem won't work with attributes

        # Test with list
        obj = ["a", "b", "c"]
        result = getitem(obj, 1)
        assert result.unwrap() == "b"

    def test_rgb_to_hex(self):
        """Test rgb_to_hex function."""
        assert rgb_to_hex((255, 0, 0)) == "#ff0000"
        assert rgb_to_hex((0, 255, 0)) == "#00ff00"
        assert rgb_to_hex((0, 0, 255)) == "#0000ff"
        assert rgb_to_hex((128, 128, 128)) == "#808080"

    def test_get_color(self):
        """Test get_color function."""
        # Test various edge counts
        color1 = get_color(0)
        color2 = get_color(5)
        color3 = get_color(10)

        # Should return hex color strings
        assert color1.startswith("#")
        assert color2.startswith("#")
        assert color3.startswith("#")
        assert len(color1) == 7
        assert len(color2) == 7
        assert len(color3) == 7


class TestMiscClasses:
    """Tests for miscellaneous classes."""

    def test_missing_key_error(self):
        """Test MissingKeyError."""
        error = MissingKeyError("test_key")
        assert "test_key" in str(error)

    def test_edge_info_creation(self):
        """Test EdgeInfo dataclass."""
        edge = EdgeInfo(key="test_key", dependencies=["dep1", "dep2"])
        assert edge.key == "test_key"
        assert edge.dependencies == ["dep1", "dep2"]
        assert edge.used_by == []  # default value
