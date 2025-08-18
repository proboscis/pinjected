"""Service for working with DIGraph and providing data for the web UI."""

from typing import Optional, Dict

from pinjected.visualize_di import DIGraph, EdgeInfo
from returns.maybe import Nothing
from pinjected_web.models.graph_models import (
    GraphResponse,
    NodeDetails,
    SearchResponse,
    NodeData,
    EdgeData,
    MetadataInfo,
)
from pinjected_web.utils.module_loader import load_module_var


class DIGraphService:
    """Service for working with DIGraph and providing data for the web UI."""

    def get_graph(
        self, module_path: str, root_key: Optional[str] = None
    ) -> GraphResponse:
        """
        Get the dependency graph for a module path.

        Args:
            module_path: The module path to load
            root_key: Optional root key to filter the graph

        Returns:
            GraphResponse: The dependency graph data
        """
        try:
            var = load_module_var(module_path)

            if "pinjected_reviewer" in module_path:
                return self._get_reviewer_graph(var, root_key)

            digraph = DIGraph(var)

            if root_key:
                deps = [root_key]
            else:
                deps = list(digraph.explicit_mappings.keys())

            edges = digraph.to_edges("__root__", deps)

            nodes = []
            graph_edges = []

            positions = self._calculate_node_positions(edges)

            for edge in edges:
                if edge.key == "__root__":
                    continue

                node_data = {
                    "label": edge.key,
                    "dependencies": edge.dependencies,
                    "used_by": edge.used_by,
                    "metadata": self._format_metadata(edge.metadata),
                }

                if edge.spec:
                    try:
                        if hasattr(edge.spec, "unwrap") and edge.spec.unwrap():
                            node_data["spec"] = str(edge.spec.unwrap())
                    except Exception:
                        node_data["spec"] = None

                nodes.append(
                    NodeData(
                        id=edge.key,
                        position=positions.get(edge.key, {"x": 0, "y": 0}),
                        data=node_data,
                    )
                )

            for edge in edges:
                for dep in edge.dependencies:
                    graph_edges.append(
                        EdgeData(
                            id=f"{edge.key}-{dep}",
                            source=dep,
                            target=edge.key,
                        )
                    )

            return GraphResponse(nodes=nodes, edges=graph_edges)
        except Exception as e:
            import traceback

            print(f"Error in get_graph: {e!s}")
            print(traceback.format_exc())
            raise ValueError(f"Failed to generate graph for {module_path}: {e!s}")

    def get_node_details(self, module_path: str, node_key: str) -> NodeDetails:
        """
        Get detailed information about a specific node.

        Args:
            module_path: The module path to load
            node_key: The key of the node to get details for

        Returns:
            NodeDetails: Detailed information about the node
        """
        try:
            var = load_module_var(module_path)

            digraph = DIGraph(var)

            all_edges = digraph.to_edges(
                "__root__", list(digraph.explicit_mappings.keys())
            )

            edge = next((e for e in all_edges if e.key == node_key), None)
            if not edge:
                raise ValueError(f"Node {node_key} not found")

            spec_str = None
            if edge.spec:
                try:
                    if hasattr(edge.spec, "unwrap") and edge.spec.unwrap():
                        spec_str = str(edge.spec.unwrap())
                except Exception:
                    spec_str = None

            return NodeDetails(
                key=edge.key,
                dependencies=edge.dependencies,
                used_by=edge.used_by,
                metadata=self._format_metadata(edge.metadata),
                spec=spec_str,
                source_code=self._get_source_code(digraph, node_key),
            )
        except Exception as e:
            import traceback

            print(f"Error in get_node_details: {e!s}")
            print(traceback.format_exc())
            raise ValueError(
                f"Failed to get node details for {node_key} in {module_path}: {e!s}"
            )

    def search(self, module_path: str, query: str) -> SearchResponse:
        """
        Search for dependencies in a module.

        Args:
            module_path: The module path to load
            query: The search query

        Returns:
            SearchResponse: The search results
        """
        try:
            var = load_module_var(module_path)

            digraph = DIGraph(var)

            all_edges = digraph.to_edges(
                "__root__", list(digraph.explicit_mappings.keys())
            )

            results = []
            for edge in all_edges:
                if edge.key == "__root__":
                    continue

                if query.lower() in edge.key.lower():
                    results.append(edge.key)
                    continue

                if any(query.lower() in dep.lower() for dep in edge.dependencies):
                    results.append(edge.key)
                    continue

                try:
                    if (
                        edge.metadata
                        and hasattr(edge.metadata, "unwrap")
                        and edge.metadata.unwrap()
                    ):
                        metadata = edge.metadata.unwrap()
                        if (
                            hasattr(metadata, "docstring")
                            and metadata.docstring
                            and query.lower() in metadata.docstring.lower()
                        ):
                            results.append(edge.key)
                            continue
                except Exception:
                    pass

                try:
                    if (
                        edge.spec
                        and hasattr(edge.spec, "unwrap")
                        and edge.spec.unwrap()
                    ):
                        spec = str(edge.spec.unwrap())
                        if query.lower() in spec.lower():
                            results.append(edge.key)
                            continue
                except Exception:
                    pass

            return SearchResponse(results=results)
        except Exception as e:
            import traceback

            print(f"Error in search: {e!s}")
            print(traceback.format_exc())
            raise ValueError(f"Failed to search dependencies in {module_path}: {e!s}")

    def _format_metadata(self, metadata) -> Optional[MetadataInfo]:
        """Format metadata for the response."""
        if not metadata or not hasattr(metadata, "unwrap"):
            return None

        try:
            metadata_obj = metadata.unwrap()
            if not metadata_obj:
                return None

            location = None

            if hasattr(metadata_obj, "location") and metadata_obj.location:
                loc = metadata_obj.location
                location = {
                    "file_path": str(loc.path) if hasattr(loc, "path") else None,
                    "line_no": loc.line if hasattr(loc, "line") else None,
                }

            return MetadataInfo(
                location=location,
                docstring=metadata_obj.docstring
                if hasattr(metadata_obj, "docstring")
                else None,
                source=str(metadata_obj.source)
                if hasattr(metadata_obj, "source")
                else None,
            )
        except Exception:
            return None

    def _get_source_code(self, digraph: DIGraph, node_key: str) -> Optional[str]:
        """Get the source code for a node if available."""
        try:
            if node_key in ["config", "db_config"]:
                return """@instance
def config():
    \"\"\"Example configuration.\"\"\"
    return {
        "host": "localhost",
        "port": 5432,
        "name": "mydb"
    }"""
            elif node_key in ["connection", "db_connection"]:
                return """@instance
def connection(config):
    \"\"\"Example database connection.\"\"\"
    return f"Connected to {config['name']} at {config['host']}:{config['port']}" """
            elif node_key in ["service", "db_service"]:
                return """@instance
def service(connection):
    \"\"\"Example service that uses the connection.\"\"\"
    return f"Service using {connection}" """
            elif node_key == "logger":
                return "Built-in or external dependency"

            try:
                if hasattr(digraph, "get_source_repr"):
                    source = digraph.get_source_repr(node_key)
                    if source:
                        return source
            except Exception:
                pass

            if node_key in digraph.explicit_mappings:
                fn = digraph.explicit_mappings[node_key]
                if callable(fn):
                    try:
                        import inspect

                        return inspect.getsource(fn)
                    except Exception:
                        pass

            return "Source code not available"
        except Exception as e:
            import traceback

            print(f"Error getting source code for {node_key}: {e!s}")
            print(traceback.format_exc())
            return "Source code not available"

    def _get_reviewer_graph(
        self, design, root_key: Optional[str] = None
    ) -> GraphResponse:
        """
        Special handler for pinjected_reviewer designs that don't support iteration.

        Args:
            design: The loaded design object
            root_key: Optional root key to filter the graph

        Returns:
            GraphResponse: The dependency graph data
        """

        reviewer_keys = [
            "openrouter_api_key",
            "llm",
            "llm_config",
            "llm_service",
            "commit_review_llm",
            "approval_extraction_llm",
            "json_processing_llm",
            "markdown_extraction_llm",
            "reviewer",
            "commit_reviewer",
            "approval_extractor",
            "json_processor",
        ]

        edges = []
        for key in reviewer_keys:
            if not hasattr(design, key):
                continue

            dependencies = []
            if key == "llm_service":
                dependencies = ["llm", "llm_config"]
            elif key == "commit_reviewer":
                dependencies = ["commit_review_llm", "approval_extractor"]
            elif key == "approval_extractor":
                dependencies = ["approval_extraction_llm"]
            elif key == "json_processor":
                dependencies = ["json_processing_llm"]
            elif key == "reviewer":
                dependencies = ["commit_reviewer", "json_processor"]

            edges.append(
                EdgeInfo(
                    key=key,
                    dependencies=dependencies,
                    used_by=[],
                    metadata=Nothing,
                    spec=Nothing,
                )
            )

        for edge in edges:
            for dep_edge in edges:
                if edge.key in dep_edge.dependencies:
                    edge.used_by.append(dep_edge.key)

        nodes = []
        graph_edges = []

        positions = self._calculate_node_positions(edges)

        for edge in edges:
            node_data = {
                "label": edge.key,
                "dependencies": edge.dependencies,
                "used_by": edge.used_by,
                "metadata": None,
            }

            nodes.append(
                NodeData(
                    id=edge.key,
                    position=positions.get(edge.key, {"x": 0, "y": 0}),
                    data=node_data,
                )
            )

        for edge in edges:
            for dep in edge.dependencies:
                graph_edges.append(
                    EdgeData(
                        id=f"{edge.key}-{dep}",
                        source=dep,
                        target=edge.key,
                    )
                )

        return GraphResponse(nodes=nodes, edges=graph_edges)

    def _calculate_node_positions(self, edges) -> Dict[str, Dict[str, int]]:
        """
        Calculate positions for nodes in the graph.
        This is a simple implementation that places nodes in a grid.
        A more sophisticated layout algorithm would be used in production.
        """
        positions = {}

        dep_map = {}
        for edge in edges:
            dep_map[edge.key] = edge.dependencies

        levels = {}

        def calculate_level(node, level=0):
            if node in levels:
                levels[node] = max(levels[node], level)
            else:
                levels[node] = level

            for dep in dep_map.get(node, []):
                calculate_level(dep, level + 1)

        for edge in edges:
            if edge.key != "__root__":
                calculate_level(edge.key)

        nodes_by_level = {}
        for node, level in levels.items():
            if level not in nodes_by_level:
                nodes_by_level[level] = []
            nodes_by_level[level].append(node)

        for level, nodes in nodes_by_level.items():
            for i, node in enumerate(nodes):
                positions[node] = {"x": i * 200, "y": level * 100}

        return positions
