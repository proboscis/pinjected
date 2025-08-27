from unittest.mock import MagicMock

from returns.maybe import Nothing

from pinjected.dependency_graph_builder import DependencyGraphBuilder


def test_collect_dependencies_includes_all_keys():
    """Test that collect_dependencies includes all keys in the dependency chain."""
    mock_digraph = MagicMock()

    def mock_di_dfs(src, replace_missing=False):
        if src == "service":
            yield "service", "middle1", ["service", "middle1"]
            yield "service", "middle2", ["service", "middle2"]
            yield "middle1", "leaf1", ["service", "middle1", "leaf1"]
            yield "middle2", "leaf2", ["service", "middle2", "leaf2"]
        elif src == "middle1":
            yield "middle1", "leaf1", ["middle1", "leaf1"]
        elif src == "middle2":
            yield "middle2", "leaf2", ["middle2", "leaf2"]

    mock_digraph.di_dfs = mock_di_dfs

    builder = DependencyGraphBuilder(mock_digraph)

    deps = ["service"]
    deps_map = builder.collect_dependencies(deps)

    assert "service" in deps_map, "service should be in deps_map"
    assert "middle1" in deps_map, "middle1 should be in deps_map"
    assert "middle2" in deps_map, "middle2 should be in deps_map"
    assert "leaf1" in deps_map, "leaf1 should be in deps_map"
    assert "leaf2" in deps_map, "leaf2 should be in deps_map"

    assert sorted(deps_map["service"]) == sorted(["middle1", "middle2"]), (
        "service should depend on middle1 and middle2"
    )
    assert deps_map["middle1"] == ["leaf1"], "middle1 should depend on leaf1"
    assert deps_map["middle2"] == ["leaf2"], "middle2 should depend on leaf2"
    assert deps_map["leaf1"] == [], "leaf1 should have no dependencies"
    assert deps_map["leaf2"] == [], "leaf2 should have no dependencies"


def test_build_edges_includes_all_keys():
    """Test that build_edges includes all keys in the dependency chain."""
    mock_digraph = MagicMock()

    builder = DependencyGraphBuilder(mock_digraph)

    deps_map = {
        "service": ["middle1", "middle2"],
        "middle1": ["leaf1"],
        "middle2": ["leaf2"],
        "leaf1": [],
        "leaf2": [],
    }
    builder.collect_dependencies = MagicMock(return_value=deps_map)

    mock_digraph.get_metadata.return_value = Nothing
    mock_digraph.get_spec.return_value = Nothing

    edges = builder.build_edges("root", ["service"])
    edge_dict = {edge.key: edge for edge in edges}

    expected_keys = {"root", "service", "middle1", "middle2", "leaf1", "leaf2"}
    assert set(edge_dict.keys()) == expected_keys, (
        f"Missing keys: {expected_keys - set(edge_dict.keys())}"
    )

    assert sorted(edge_dict["root"].dependencies) == ["service"], (
        "root should depend on service"
    )
    assert sorted(edge_dict["service"].dependencies) == sorted(
        ["middle1", "middle2"]
    ), "service should depend on middle1 and middle2"
    assert edge_dict["middle1"].dependencies == ["leaf1"], (
        "middle1 should depend on leaf1"
    )
    assert edge_dict["middle2"].dependencies == ["leaf2"], (
        "middle2 should depend on leaf2"
    )
    assert edge_dict["leaf1"].dependencies == [], "leaf1 should have no dependencies"
    assert edge_dict["leaf2"].dependencies == [], "leaf2 should have no dependencies"

    assert edge_dict["service"].used_by == ["root"], "service should be used by root"
    assert edge_dict["middle1"].used_by == ["service"], (
        "middle1 should be used by service"
    )
    assert edge_dict["middle2"].used_by == ["service"], (
        "middle2 should be used by service"
    )
    assert edge_dict["leaf1"].used_by == ["middle1"], "leaf1 should be used by middle1"
    assert edge_dict["leaf2"].used_by == ["middle2"], "leaf2 should be used by middle2"


def test_leaf_nodes_included_in_edges():
    """Test that leaf nodes (keys with no dependencies) are included in the edges."""

    mock_digraph = MagicMock()

    builder = DependencyGraphBuilder(mock_digraph)

    deps_map = {
        "service": ["middle1", "middle2"],
        "middle1": ["leaf1"],
        "middle2": ["leaf2"],
        "leaf1": [],
        "leaf2": [],
    }
    builder.collect_dependencies = MagicMock(return_value=deps_map)

    mock_digraph.get_metadata.return_value = Nothing
    mock_digraph.get_spec.return_value = Nothing

    edges = builder.build_edges("root", ["service"])

    assert len(edges) == 6, f"Expected 6 edges, got {len(edges)}"

    leaf_edges = [edge for edge in edges if not edge.dependencies]
    leaf_keys = {edge.key for edge in leaf_edges}
    expected_leaf_keys = {"leaf1", "leaf2"}
    assert leaf_keys == expected_leaf_keys, (
        f"Missing leaf keys: {expected_leaf_keys - leaf_keys}"
    )
