"""Simple tests for dependency_graph_builder.py module to improve coverage."""

import pytest
from unittest.mock import Mock
from dataclasses import is_dataclass

from pinjected.dependency_graph_builder import DependencyGraphBuilder
from pinjected.visualize_di import EdgeInfo


class TestDependencyGraphBuilder:
    """Test the DependencyGraphBuilder class."""

    def test_dependency_graph_builder_is_dataclass(self):
        """Test that DependencyGraphBuilder is a dataclass."""
        assert is_dataclass(DependencyGraphBuilder)

    def test_dependency_graph_builder_init(self):
        """Test DependencyGraphBuilder initialization."""
        mock_digraph = Mock()

        builder = DependencyGraphBuilder(mock_digraph)

        assert builder.digraph is mock_digraph

    def test_collect_dependencies(self):
        """Test collect_dependencies method."""
        mock_digraph = Mock()

        # Mock di_dfs to return some edges
        mock_digraph.di_dfs.return_value = [
            ("A", "B", {}),
            ("B", "C", {}),
            ("A", "D", {}),
            ("D", "E", {}),
        ]

        builder = DependencyGraphBuilder(mock_digraph)
        deps_map = builder.collect_dependencies(["A"])

        # Check the dependency map
        assert "A" in deps_map
        assert "B" in deps_map["A"]
        assert "D" in deps_map["A"]
        assert "C" in deps_map["B"]
        assert "E" in deps_map["D"]

        # Check that all keys exist even if they have no dependencies
        assert "C" in deps_map
        assert "E" in deps_map
        assert deps_map["C"] == []
        assert deps_map["E"] == []

    def test_collect_dependencies_multiple_roots(self):
        """Test collect_dependencies with multiple root nodes."""
        mock_digraph = Mock()

        # Mock di_dfs to return different edges for different roots
        def mock_dfs(root, replace_missing=True):
            if root == "X":
                return [("X", "Y", {}), ("Y", "Z", {})]
            elif root == "A":
                return [("A", "B", {}), ("B", "C", {})]
            return []

        mock_digraph.di_dfs.side_effect = mock_dfs

        builder = DependencyGraphBuilder(mock_digraph)
        deps_map = builder.collect_dependencies(["X", "A"])

        # Check dependencies from both roots
        assert "X" in deps_map
        assert "Y" in deps_map["X"]
        assert "A" in deps_map
        assert "B" in deps_map["A"]
        assert "Z" in deps_map["Y"]
        assert "C" in deps_map["B"]

    def test_create_edge_info(self):
        """Test create_edge_info method."""
        mock_digraph = Mock()
        mock_metadata = {"source": "test.py"}
        mock_spec = {"type": "function"}

        mock_digraph.get_metadata.return_value = mock_metadata
        mock_digraph.get_spec.return_value = mock_spec

        builder = DependencyGraphBuilder(mock_digraph)

        edge_info = builder.create_edge_info(
            key="test_key",
            dependencies=["dep1", "dep2", "dep1"],  # Duplicate to test deduplication
            used_by=["user1", "user2", "user1"],  # Duplicate to test deduplication
        )

        assert isinstance(edge_info, EdgeInfo)
        assert edge_info.key == "test_key"
        assert edge_info.dependencies == ["dep1", "dep2"]  # Sorted and deduplicated
        assert edge_info.used_by == ["user1", "user2"]  # Sorted and deduplicated
        assert edge_info.metadata == mock_metadata
        assert edge_info.spec == mock_spec

        # Verify calls
        mock_digraph.get_metadata.assert_called_once_with("test_key")
        mock_digraph.get_spec.assert_called_once_with("test_key")

    def test_create_edge_info_no_used_by(self):
        """Test create_edge_info with no used_by list."""
        mock_digraph = Mock()
        mock_digraph.get_metadata.return_value = None
        mock_digraph.get_spec.return_value = None

        builder = DependencyGraphBuilder(mock_digraph)

        edge_info = builder.create_edge_info(
            key="test_key", dependencies=["dep1"], used_by=None
        )

        assert edge_info.used_by == []

    def test_collect_used_by(self):
        """Test collect_used_by method."""
        mock_digraph = Mock()
        builder = DependencyGraphBuilder(mock_digraph)

        deps_map = {"A": ["B", "C"], "B": ["D"], "C": ["D", "E"], "E": []}

        used_by_map = builder.collect_used_by(deps_map)

        # Check reverse dependencies
        # If A depends on B and C, then B and C are used by A
        assert "A" in used_by_map["B"]
        assert "A" in used_by_map["C"]
        assert "B" in used_by_map["D"]
        assert "C" in used_by_map["D"]
        assert "C" in used_by_map["E"]
        assert len(used_by_map["D"]) == 2  # Used by both B and C

        # A and E should not have anything in their used_by lists
        assert used_by_map.get("A", []) == []

    def test_build_edges(self):
        """Test build_edges method."""
        mock_digraph = Mock()

        # Mock di_dfs
        mock_digraph.di_dfs.return_value = [
            ("dep1", "sub_dep1", {}),
            ("dep1", "sub_dep2", {}),
            ("dep2", "sub_dep3", {}),
        ]

        # Mock get_metadata and get_spec
        mock_digraph.get_metadata.return_value = {"meta": "data"}
        mock_digraph.get_spec.return_value = {"spec": "info"}

        builder = DependencyGraphBuilder(mock_digraph)

        edges = builder.build_edges("root", ["dep1", "dep2"])

        # Check that edges are created for all nodes
        edge_keys = {edge.key for edge in edges}
        assert "root" in edge_keys
        assert "dep1" in edge_keys
        assert "dep2" in edge_keys
        assert "sub_dep1" in edge_keys
        assert "sub_dep2" in edge_keys
        assert "sub_dep3" in edge_keys

        # Find root edge
        root_edge = next(e for e in edges if e.key == "root")
        assert set(root_edge.dependencies) == {"dep1", "dep2"}

        # Find dep1 edge
        dep1_edge = next(e for e in edges if e.key == "dep1")
        assert set(dep1_edge.dependencies) == {"sub_dep1", "sub_dep2"}
        assert "root" in dep1_edge.used_by

        # Find dep2 edge
        dep2_edge = next(e for e in edges if e.key == "dep2")
        assert set(dep2_edge.dependencies) == {"sub_dep3"}
        assert "root" in dep2_edge.used_by

    def test_build_edges_no_dependencies(self):
        """Test build_edges with no dependencies."""
        mock_digraph = Mock()
        mock_digraph.di_dfs.return_value = []
        mock_digraph.get_metadata.return_value = None
        mock_digraph.get_spec.return_value = None

        builder = DependencyGraphBuilder(mock_digraph)

        edges = builder.build_edges("root", [])

        # Should still have root edge
        assert len(edges) == 1
        assert edges[0].key == "root"
        assert edges[0].dependencies == []
        assert edges[0].used_by == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
