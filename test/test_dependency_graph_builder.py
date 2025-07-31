"""Tests for pinjected.dependency_graph_builder module."""

import pytest
from unittest.mock import Mock
from collections import defaultdict

from pinjected.dependency_graph_builder import DependencyGraphBuilder
from pinjected.visualize_di import EdgeInfo


class TestDependencyGraphBuilder:
    """Test the DependencyGraphBuilder class."""

    def test_init(self):
        """Test DependencyGraphBuilder initialization."""
        mock_digraph = Mock()
        builder = DependencyGraphBuilder(mock_digraph)

        assert builder.digraph is mock_digraph

    def test_collect_dependencies_empty(self):
        """Test collect_dependencies with empty list."""
        mock_digraph = Mock()
        mock_digraph.di_dfs.return_value = []

        builder = DependencyGraphBuilder(mock_digraph)
        result = builder.collect_dependencies([])

        assert isinstance(result, dict)
        assert len(result) == 0

    def test_collect_dependencies_single(self):
        """Test collect_dependencies with single dependency."""
        mock_digraph = Mock()
        # di_dfs returns tuples of (from, to, edge_data)
        mock_digraph.di_dfs.return_value = [("a", "b", {}), ("b", "c", {})]

        builder = DependencyGraphBuilder(mock_digraph)
        result = builder.collect_dependencies(["a"])

        assert "a" in result
        assert "b" in result
        assert "c" in result
        assert "b" in result["a"]
        assert "c" in result["b"]
        assert result["c"] == []  # c has no dependencies

    def test_collect_dependencies_multiple_roots(self):
        """Test collect_dependencies with multiple root dependencies."""
        mock_digraph = Mock()

        # Setup different paths for different roots
        def mock_di_dfs(root, replace_missing=False):
            if root == "root1":
                return [("root1", "dep1", {}), ("dep1", "common", {})]
            elif root == "root2":
                return [("root2", "dep2", {}), ("dep2", "common", {})]
            return []

        mock_digraph.di_dfs.side_effect = mock_di_dfs

        builder = DependencyGraphBuilder(mock_digraph)
        result = builder.collect_dependencies(["root1", "root2"])

        assert "root1" in result
        assert "root2" in result
        assert "dep1" in result["root1"]
        assert "dep2" in result["root2"]
        assert "common" in result["dep1"]
        assert "common" in result["dep2"]

    def test_create_edge_info_basic(self):
        """Test create_edge_info with basic inputs."""
        mock_digraph = Mock()
        mock_digraph.get_metadata.return_value = {"meta": "data"}
        mock_digraph.get_spec.return_value = {"spec": "info"}

        builder = DependencyGraphBuilder(mock_digraph)
        edge_info = builder.create_edge_info("key1", ["dep1", "dep2"])

        assert isinstance(edge_info, EdgeInfo)
        assert edge_info.key == "key1"
        assert edge_info.dependencies == ["dep1", "dep2"]
        assert edge_info.used_by == []
        assert edge_info.metadata == {"meta": "data"}
        assert edge_info.spec == {"spec": "info"}

    def test_create_edge_info_with_used_by(self):
        """Test create_edge_info with used_by list."""
        mock_digraph = Mock()
        mock_digraph.get_metadata.return_value = None
        mock_digraph.get_spec.return_value = None

        builder = DependencyGraphBuilder(mock_digraph)
        edge_info = builder.create_edge_info(
            "key1", ["dep1", "dep2"], ["parent1", "parent2"]
        )

        assert edge_info.key == "key1"
        assert edge_info.dependencies == ["dep1", "dep2"]
        assert edge_info.used_by == ["parent1", "parent2"]

    def test_create_edge_info_deduplicates_and_sorts(self):
        """Test that create_edge_info deduplicates and sorts lists."""
        mock_digraph = Mock()
        mock_digraph.get_metadata.return_value = None
        mock_digraph.get_spec.return_value = None

        builder = DependencyGraphBuilder(mock_digraph)
        edge_info = builder.create_edge_info(
            "key1",
            ["z", "a", "z", "b", "a"],  # duplicates and unsorted
            ["y", "x", "y"],  # duplicates and unsorted
        )

        assert edge_info.dependencies == ["a", "b", "z"]  # deduplicated and sorted
        assert edge_info.used_by == ["x", "y"]  # deduplicated and sorted

    def test_collect_used_by_empty(self):
        """Test collect_used_by with empty deps map."""
        mock_digraph = Mock()
        builder = DependencyGraphBuilder(mock_digraph)

        result = builder.collect_used_by({})

        assert isinstance(result, defaultdict)
        assert len(result) == 0

    def test_collect_used_by_simple(self):
        """Test collect_used_by with simple dependencies."""
        mock_digraph = Mock()
        builder = DependencyGraphBuilder(mock_digraph)

        deps_map = {"a": ["b", "c"], "b": ["c"], "d": ["a"]}

        result = builder.collect_used_by(deps_map)

        # If "d" depends on "a", then "a" is used by "d"
        assert "d" in result["a"]
        # If "a" depends on "b", then "b" is used by "a"
        assert "a" in result["b"]
        # If "a" depends on "c", then "c" is used by "a"
        assert "a" in result["c"]
        # If "b" depends on "c", then "c" is used by "b"
        assert "b" in result["c"]

    def test_collect_used_by_complex(self):
        """Test collect_used_by with complex dependency graph."""
        mock_digraph = Mock()
        builder = DependencyGraphBuilder(mock_digraph)

        deps_map = {
            "app": ["service1", "service2"],
            "service1": ["db", "cache"],
            "service2": ["db", "api"],
            "db": ["config"],
            "cache": ["config"],
            "api": [],
            "config": [],
        }

        result = builder.collect_used_by(deps_map)

        assert sorted(result["db"]) == ["service1", "service2"]
        assert sorted(result["config"]) == ["cache", "db"]
        assert result["service1"] == ["app"]
        assert result["service2"] == ["app"]

    def test_build_edges_simple(self):
        """Test build_edges with simple dependencies."""
        mock_digraph = Mock()
        mock_digraph.di_dfs.return_value = []
        mock_digraph.get_metadata.return_value = None
        mock_digraph.get_spec.return_value = None

        builder = DependencyGraphBuilder(mock_digraph)
        edges = builder.build_edges("root", ["dep1", "dep2"])

        # Should have edges for dep1, dep2, and root
        assert len(edges) >= 2

        # Find the root edge
        root_edge = next((e for e in edges if e.key == "root"), None)
        assert root_edge is not None
        assert sorted(root_edge.dependencies) == ["dep1", "dep2"]

    def test_build_edges_with_transitive_deps(self):
        """Test build_edges with transitive dependencies."""
        mock_digraph = Mock()

        def mock_di_dfs(root, replace_missing=False):
            if root == "dep1":
                return [("dep1", "subdep1", {}), ("subdep1", "subdep2", {})]
            elif root == "dep2":
                return [("dep2", "subdep2", {})]
            return []

        mock_digraph.di_dfs.side_effect = mock_di_dfs
        mock_digraph.get_metadata.return_value = None
        mock_digraph.get_spec.return_value = None

        builder = DependencyGraphBuilder(mock_digraph)
        edges = builder.build_edges("root", ["dep1", "dep2"])

        # Should have edges for all dependencies
        keys = {e.key for e in edges}
        assert "root" in keys
        assert "dep1" in keys
        assert "dep2" in keys
        assert "subdep1" in keys
        assert "subdep2" in keys

    def test_build_edges_preserves_metadata(self):
        """Test that build_edges preserves metadata and spec."""
        mock_digraph = Mock()
        mock_digraph.di_dfs.return_value = []

        # Different metadata for different keys
        def mock_get_metadata(key):
            return {"key": key, "type": "metadata"}

        def mock_get_spec(key):
            return {"key": key, "type": "spec"}

        mock_digraph.get_metadata.side_effect = mock_get_metadata
        mock_digraph.get_spec.side_effect = mock_get_spec

        builder = DependencyGraphBuilder(mock_digraph)
        edges = builder.build_edges("root", ["dep1"])

        for edge in edges:
            assert edge.metadata == {"key": edge.key, "type": "metadata"}
            assert edge.spec == {"key": edge.key, "type": "spec"}

    def test_build_edges_handles_cycles(self):
        """Test build_edges with cyclic dependencies."""
        mock_digraph = Mock()

        # Create a cycle: a -> b -> c -> a
        def mock_di_dfs(root, replace_missing=False):
            if root == "a":
                return [("a", "b", {}), ("b", "c", {}), ("c", "a", {})]
            return []

        mock_digraph.di_dfs.side_effect = mock_di_dfs
        mock_digraph.get_metadata.return_value = None
        mock_digraph.get_spec.return_value = None

        builder = DependencyGraphBuilder(mock_digraph)
        edges = builder.build_edges("root", ["a"])

        # Should handle the cycle without infinite loop
        keys = {e.key for e in edges}
        assert "a" in keys
        assert "b" in keys
        assert "c" in keys

    def test_build_edges_root_already_in_deps(self):
        """Test build_edges when root is already in dependencies."""
        mock_digraph = Mock()

        def mock_di_dfs(root, replace_missing=False):
            if root == "dep1":
                return [("dep1", "root", {})]  # dep1 depends on root
            return []

        mock_digraph.di_dfs.side_effect = mock_di_dfs
        mock_digraph.get_metadata.return_value = None
        mock_digraph.get_spec.return_value = None

        builder = DependencyGraphBuilder(mock_digraph)
        edges = builder.build_edges("root", ["dep1"])

        # Should handle circular dependency gracefully
        root_edge = next(e for e in edges if e.key == "root")
        dep1_edge = next(e for e in edges if e.key == "dep1")

        assert "dep1" in root_edge.dependencies
        assert "root" in dep1_edge.dependencies

    def test_dataclass_functionality(self):
        """Test that DependencyGraphBuilder works as a dataclass."""
        mock_digraph = Mock()
        builder = DependencyGraphBuilder(mock_digraph)

        # Should have standard dataclass features
        assert hasattr(builder, "__dataclass_fields__")

        # Test string representation
        str_repr = str(builder)
        assert "DependencyGraphBuilder" in str_repr

    def test_build_edges_root_not_in_keys(self):
        """Test build_edges when root is not in any dependency paths."""
        mock_digraph = Mock()

        # No dependencies found in di_dfs
        mock_digraph.di_dfs.return_value = []
        mock_digraph.get_metadata.return_value = {"root": "metadata"}
        mock_digraph.get_spec.return_value = {"root": "spec"}

        builder = DependencyGraphBuilder(mock_digraph)
        edges = builder.build_edges("isolated_root", ["dep1"])

        # Should still create an edge for the root
        root_edge = next(e for e in edges if e.key == "isolated_root")
        assert root_edge is not None
        assert root_edge.dependencies == ["dep1"]
        assert root_edge.metadata == {"root": "metadata"}
        assert root_edge.spec == {"root": "spec"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
