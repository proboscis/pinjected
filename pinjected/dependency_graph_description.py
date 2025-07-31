import re
from dataclasses import dataclass

from returns.maybe import Nothing
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from pinjected.pinjected_logging import logger
from pinjected.visualize_di import DIGraph


@dataclass
class DependencyGraphDescriptionGenerator:
    """
    A class to generate human-readable descriptions of dependency graphs.
    This class handles the collection, formatting, and display of dependency
    relationships and their documentation.
    """

    def __init__(self, digraph: DIGraph, root_name: str, deps: list[str]):
        """
        Initialize the DependencyGraphDescriptionGenerator.

        Args:
            digraph: The DIGraph instance containing dependency information
            root_name: The name of the root node
            deps: List of direct dependencies
        """
        self.digraph = digraph
        self.root_name = root_name
        self.deps = deps
        self.edges = self.digraph.to_edges(root_name, deps)
        self.console = Console()
        self.processed_nodes = set()

        for edge in self.edges:
            logger.info(f"Edge key: {edge.key}, has spec: {edge.spec != Nothing}")
            if edge.spec != Nothing:
                logger.info(f"Edge spec: {edge.spec}")

    def format_maybe(self, value):
        """Format Maybe objects (Some/Nothing) to clean representation."""
        if value == Nothing:
            return "None"
        if hasattr(value, "unwrap"):  # Check if it's a Some instance
            return self.format_value(value.unwrap())
        return self.format_value(value)

    def format_value(self, value):
        """Format values to clean representation."""
        if value is None:
            return "None"

        value_str = str(value)

        if (
            isinstance(value, dict)
            and "documentation" in value
            and value["documentation"]
        ):
            doc = value["documentation"]
            doc = doc.replace("\\n", "\n")
            doc = re.sub(r"[ \t]+", " ", doc)
            value["documentation"] = doc
            value_str = str(value)

        return value_str

    def add_node_to_tree(self, parent_tree, edge):
        """Add a node and its dependencies to the tree."""
        if edge.key in self.processed_nodes:
            return

        self.processed_nodes.add(edge.key)

        metadata_text = ""
        if edge.metadata:
            metadata_text = f"\n[dim]Metadata:[/dim] {self.format_maybe(edge.metadata)}"

        spec_text = ""
        if edge.spec:
            spec_text = f"\n[dim]Spec:[/dim] {self.format_maybe(edge.spec)}"

        node_text = f"[bold green]{edge.key}[/bold green]{metadata_text}{spec_text}"

        node_tree = parent_tree.add(node_text)

        for dep in edge.dependencies:
            node_tree.add(f"[yellow]→ {dep}[/yellow]")

            for child_edge in self.edges:
                if child_edge.key == dep:
                    self.add_node_to_tree(node_tree, child_edge)

    def build_dependency_tree(self):
        """Build and return a tree representation of the dependency graph."""
        root_tree = Tree(f"[bold blue]{self.root_name}[/bold blue]")

        for edge in self.edges:
            if edge.key == self.root_name:
                for dep in edge.dependencies:
                    root_tree.add(f"[yellow]→ {dep}[/yellow]")

                    for child_edge in self.edges:
                        if child_edge.key == dep:
                            self.add_node_to_tree(root_tree, child_edge)

        return root_tree

    def display_edge_details(self, edge):
        """Display detailed information about an edge."""
        title = Text(edge.key, style="bold green")
        content = Text()

        content.append("\nDependencies: ")
        if edge.dependencies:
            content.append(", ".join(edge.dependencies), style="yellow")
        else:
            content.append("None", style="dim")

        content.append("\nUsed by: ")
        if edge.used_by and len(edge.used_by) > 0:
            content.append(", ".join(edge.used_by), style="cyan")
        else:
            content.append("None", style="dim")

        if edge.metadata:
            content.append("\nMetadata: ")
            content.append(self.format_maybe(edge.metadata))

        if edge.spec:
            content.append("\nSpec: ")
            spec_value = self.format_maybe(edge.spec)

            if "documentation" in spec_value:
                try:
                    import ast

                    try:
                        spec_dict = ast.literal_eval(spec_value)
                    except (ValueError, SyntaxError):
                        import re

                        doc_match = re.search(
                            r"'documentation':\s*'([^']*)'", spec_value
                        )
                        if doc_match:
                            doc = doc_match.group(1)
                            clean_spec = re.sub(
                                r"'documentation':\s*'[^']*'", "", spec_value
                            )
                            content.append(clean_spec)

                            content.append("\n\nDocumentation: ")
                            content.append(doc, style="blue")
                            self.console.print(Panel(content, title=title))
                            return
                        logger.debug(
                            f"Failed to extract documentation with regex from: {spec_value}"
                        )
                        raise ValueError("Could not extract documentation with regex")
                    else:
                        doc = spec_dict.get("documentation", "")

                        if doc:
                            clean_spec = {
                                k: v
                                for k, v in spec_dict.items()
                                if k != "documentation"
                            }
                            content.append(str(clean_spec))

                            content.append("\n\nDocumentation: ")
                            content.append(doc, style="blue")
                            self.console.print(Panel(content, title=title))
                            return
                except Exception as e:
                    logger.debug(f"Failed to parse documentation: {e}")
                    logger.debug(f"Spec value: {spec_value}")

            content.append(spec_value)

        self.console.print(Panel(content, title=title))

    def generate(self):
        """Generate and display the complete dependency graph description."""
        self.console.print("\n[bold]Dependency Graph Description:[/bold]")
        self.console.print(self.build_dependency_tree())

        self.console.print("\n[bold]Edge Details:[/bold]")

        self.console.print(
            Panel(f"[bold blue]{self.root_name}[/bold blue]", title="Root Node")
        )

        for edge in self.edges:
            if edge.key != self.root_name:  # Skip root as it's already shown
                self.display_edge_details(edge)
