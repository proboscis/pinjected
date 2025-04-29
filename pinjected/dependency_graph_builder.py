from collections import defaultdict
from dataclasses import dataclass

from pinjected.visualize_di import EdgeInfo


@dataclass
class DependencyGraphBuilder:
    """
    A class to build and manage dependency graphs for the pinjected framework.
    This class provides methods to collect, process, and format dependency relationships
    and their documentation for visualization and inspection.
    """

    def __init__(self, digraph):
        """
        Initialize the DependencyGraphBuilder with a DIGraph instance.

        Args:
            digraph: The DIGraph instance to use for dependency resolution
        """
        self.digraph = digraph

    def collect_dependencies(self, deps: list[str]) -> dict[str, list[str]]:
        """
        Collect all dependencies for the given list of dependency keys.

        Args:
            deps: List of dependency keys to collect dependencies for

        Returns:
            A dictionary mapping dependency keys to their dependencies
        """
        deps_map = defaultdict(list)
        all_keys = set()

        for root in deps:
            for a, b, _ in self.digraph.di_dfs(root, replace_missing=True):
                deps_map[a].append(b)
                all_keys.add(a)
                all_keys.add(b)

        for key in all_keys:
            if key not in deps_map:
                deps_map[key] = []

        return deps_map

    def create_edge_info(
        self, key: str, dependencies: list[str], used_by: list[str] = None
    ) -> EdgeInfo:
        """
        Create an EdgeInfo object for a dependency key.

        Args:
            key: The dependency key
            dependencies: List of dependencies for this key
            used_by: List of keys that use this key

        Returns:
            An EdgeInfo object with metadata and spec information
        """
        return EdgeInfo(
            key=key,
            dependencies=sorted(set(dependencies)),
            used_by=sorted(set(used_by or [])),
            metadata=self.digraph.get_metadata(key),
            spec=self.digraph.get_spec(key),
        )

    def collect_used_by(self, deps_map: dict[str, list[str]]) -> dict[str, list[str]]:
        """
        Collect all keys that use each dependency.

        Args:
            deps_map: Dictionary mapping keys to their dependencies

        Returns:
            A dictionary mapping dependency keys to the keys that use them
        """
        used_by_map = defaultdict(list)
        for key, dependencies in deps_map.items():
            for dep in dependencies:
                used_by_map[dep].append(key)
        return used_by_map

    def build_edges(self, root_name: str, deps: list[str]) -> list[EdgeInfo]:
        """
        Build a list of EdgeInfo objects for the given root name and dependencies.

        Args:
            root_name: The name of the root node
            deps: List of direct dependencies

        Returns:
            A list of EdgeInfo objects representing the dependency graph
        """
        edges = []
        keys = set()

        deps_map = self.collect_dependencies(deps)

        for dep in deps:
            if root_name not in deps_map:
                deps_map[root_name] = []
            if dep not in deps_map[root_name]:
                deps_map[root_name].append(dep)

        used_by_map = self.collect_used_by(deps_map)

        for dep in deps:
            edges.append(
                self.create_edge_info(
                    dep, deps_map.get(dep, []), used_by_map.get(dep, [])
                )
            )
            keys.add(dep)

        for key, dependencies in deps_map.items():
            if key not in keys:
                edges.append(
                    self.create_edge_info(key, dependencies, used_by_map.get(key, []))
                )
                keys.add(key)

        if root_name not in keys:
            edges.append(
                EdgeInfo(
                    key=root_name,
                    dependencies=sorted(set(deps)),
                    used_by=sorted(set(used_by_map.get(root_name, []))),
                    metadata=self.digraph.get_metadata(root_name),
                    spec=self.digraph.get_spec(root_name),
                )
            )

        return edges
