from collections import defaultdict

from pinjected.dependency_graph_builder import DependencyGraphBuilder
from pinjected.di.util import design
from pinjected.visualize_di import DIGraph


def test_used_by_with_actual_design_objects():
    """Test that used_by field correctly tracks multiple users with actual Design objects."""
    test_design = design(
        shared_dep="shared dependency",
        dep1="dependency 1",
        dep2="dependency 2",
        dep3="dependency 3",
        service1=lambda shared_dep, dep1: f"{shared_dep} and {dep1}",
        service2=lambda shared_dep, dep2: f"{shared_dep} and {dep2}",
        service3=lambda shared_dep, dep3: f"{shared_dep} and {dep3}",
        root=lambda service1, service2, service3: [service1, service2, service3],
    )

    digraph = DIGraph(test_design)

    builder = DependencyGraphBuilder(digraph)

    deps = ["service1", "service2", "service3"]
    deps_map = builder.collect_dependencies(deps)

    assert "service1" in deps_map, "service1 should be in deps_map"
    assert sorted(deps_map["service1"]) == sorted(["dep1", "shared_dep"]), (
        "service1 should depend on dep1 and shared_dep"
    )

    assert "service2" in deps_map, "service2 should be in deps_map"
    assert sorted(deps_map["service2"]) == sorted(["dep2", "shared_dep"]), (
        "service2 should depend on dep2 and shared_dep"
    )

    assert "service3" in deps_map, "service3 should be in deps_map"
    assert sorted(deps_map["service3"]) == sorted(["dep3", "shared_dep"]), (
        "service3 should depend on dep3 and shared_dep"
    )

    used_by_map = defaultdict(list)
    for key, dependencies in deps_map.items():
        for dep in dependencies:
            used_by_map[dep].append(key)

    assert "shared_dep" in used_by_map, "shared_dep should be in used_by_map"
    assert sorted(used_by_map["shared_dep"]) == sorted(
        ["service1", "service2", "service3"]
    ), "shared_dep should be used by service1, service2, and service3"

    assert "dep1" in used_by_map, "dep1 should be in used_by_map"
    assert used_by_map["dep1"] == ["service1"], "dep1 should be used by service1"

    assert "dep2" in used_by_map, "dep2 should be in used_by_map"
    assert used_by_map["dep2"] == ["service2"], "dep2 should be used by service2"

    assert "dep3" in used_by_map, "dep3 should be in used_by_map"
    assert used_by_map["dep3"] == ["service3"], "dep3 should be used by service3"

    edges = builder.build_edges("root", ["service1", "service2", "service3"])

    edge_dict = {edge.key: edge for edge in edges}

    assert "service1" in edge_dict, "service1 should be in the edges"
    assert "root" in edge_dict["service1"].used_by, "service1 should be used by root"

    assert "service2" in edge_dict, "service2 should be in the edges"
    assert "root" in edge_dict["service2"].used_by, "service2 should be used by root"

    assert "service3" in edge_dict, "service3 should be in the edges"
    assert "root" in edge_dict["service3"].used_by, "service3 should be used by root"


def test_used_by_in_dependency_graph_description():
    """Test that used_by field is correctly included in dependency graph description."""
    from unittest.mock import MagicMock, call, patch

    from returns.maybe import Nothing
    from rich.panel import Panel
    from rich.text import Text

    from pinjected.dependency_graph_description import (
        DependencyGraphDescriptionGenerator,
    )
    from pinjected.visualize_di import DIGraph, EdgeInfo

    mock_edges = [
        EdgeInfo(
            key="root",
            dependencies=["service1", "service2"],
            used_by=[],
            metadata=Nothing,
            spec=Nothing,
        ),
        EdgeInfo(
            key="service1",
            dependencies=["dep1", "shared_dep"],
            used_by=["root"],
            metadata=Nothing,
            spec=Nothing,
        ),
        EdgeInfo(
            key="service2",
            dependencies=["dep2", "shared_dep"],
            used_by=["root"],
            metadata=Nothing,
            spec=Nothing,
        ),
        EdgeInfo(
            key="dep1",
            dependencies=[],
            used_by=["service1"],
            metadata=Nothing,
            spec=Nothing,
        ),
        EdgeInfo(
            key="dep2",
            dependencies=[],
            used_by=["service2"],
            metadata=Nothing,
            spec=Nothing,
        ),
        EdgeInfo(
            key="shared_dep",
            dependencies=[],
            used_by=["service1", "service2"],
            metadata=Nothing,
            spec=Nothing,
        ),
    ]

    mock_digraph = MagicMock(spec=DIGraph)
    mock_digraph.to_edges.return_value = mock_edges

    generator = DependencyGraphDescriptionGenerator(
        digraph=mock_digraph, root_name="root", deps=["service1", "service2"]
    )

    with patch.object(generator, "console") as mock_console:
        generator.generate()

        panel_calls = [
            call
            for call in mock_console.print.call_args_list
            if call.args and isinstance(call.args[0], Panel)
        ]

        for key in ["shared_dep", "dep1", "dep2", "service1", "service2"]:
            panel_found = False
            for call in panel_calls:
                panel = call.args[0]
                if isinstance(panel.title, Text) and panel.title.plain == key:
                    panel_found = True
                    panel_content = panel.renderable.plain
                    assert "Used by:" in panel_content, (
                        f"Used by field missing for {key}"
                    )

                    if key == "shared_dep":
                        assert (
                            "service1" in panel_content and "service2" in panel_content
                        ), f"shared_dep should show it's used by service1 and service2"
                    elif key == "dep1":
                        assert "service1" in panel_content, (
                            f"dep1 should show it's used by service1"
                        )
                    elif key == "dep2":
                        assert "service2" in panel_content, (
                            f"dep2 should show it's used by service2"
                        )
                    elif key == "service1" or key == "service2":
                        assert "root" in panel_content, (
                            f"{key} should show it's used by root"
                        )
                    break

            assert panel_found, f"No panel found for {key}"
