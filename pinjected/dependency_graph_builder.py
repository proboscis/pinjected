import inspect
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Set, Any, Optional

from returns.maybe import Maybe, Nothing

from pinjected.di.design_spec.protocols import BindSpec
from pinjected.di.metadata.bind_metadata import BindMetadata
from pinjected.pinjected_logging import logger
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
        
    def collect_dependencies(self, deps: list[str]) -> Dict[str, List[str]]:
        """
        Collect all dependencies for the given list of dependency keys.
        
        Args:
            deps: List of dependency keys to collect dependencies for
            
        Returns:
            A dictionary mapping dependency keys to their dependencies
        """
        deps_map = defaultdict(list)
        
        for root in deps:
            for a, b, _ in self.digraph.di_dfs(root, replace_missing=True):
                deps_map[a].append(b)
                
        return deps_map
    
    def create_edge_info(self, key: str, dependencies: List[str], used_by: List[str] = None) -> EdgeInfo:
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
            dependencies=list(sorted(set(dependencies))),
            used_by=used_by,
            metadata=self.digraph.get_metadata(key),
            spec=self.digraph.get_spec(key)
        )
    
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
        
        used_by_map = defaultdict(list)
        for key, dependencies in deps_map.items():
            for dep in dependencies:
                used_by_map[dep].append(key)
        
        for dep in deps:
            edges.append(self.create_edge_info(dep, deps_map.get(dep, [])))
            keys.add(dep)
        
        for key, dependencies in deps_map.items():
            if key not in keys:
                edges.append(self.create_edge_info(key, dependencies))
                keys.add(key)
        
        if root_name not in keys:
            edges.append(EdgeInfo(
                key=root_name,
                dependencies=list(sorted(set(deps))),
                used_by=list(sorted(set(used_by_map.get(root_name, [])))),
                metadata=self.digraph.get_metadata(root_name),
                spec=self.digraph.get_spec(root_name)
            ))
        
        for edge in edges:
            if edge.used_by is None:  # Only update if not already set
                edge.used_by = list(sorted(set(used_by_map.get(edge.key, []))))
            
        return edges
