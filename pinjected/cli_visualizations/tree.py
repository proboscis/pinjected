import io

from rich.style import Style
from rich.text import Text
from rich.tree import Tree

from pinjected.di.app_injected import EvaledInjected
from pinjected.di.expr_util import show_expr
from pinjected.di.injected import (
    Injected,
    InjectedByName,
    InjectedFromFunction,
    InjectedPure,
    InjectedWithDefaultDesign,
    MappedInjected,
    MZippedInjected,
    PartialInjectedFunction,
    ZippedInjected,
)
from pinjected.visualize_di import DIGraph


def format_path_for_display(path: str, max_length: int = 50) -> str:
    """Format a file path for display, shortening if necessary.

    Args:
        path: The file path to format
        max_length: Maximum length before shortening

    Returns:
        Formatted path string
    """
    if len(path) <= max_length:
        return path

    parts = [p for p in path.split("/") if p]  # Remove empty strings
    if len(parts) > 3:
        return ".../" + "/".join(parts[-3:])
    return path


def get_binding_location_info(
    d: DIGraph, node: str, binding_sources: dict | None = None
) -> str:
    """Extract binding location information for a node.

    Args:
        d: The DIGraph containing metadata
        node: The node name to get location for
        binding_sources: Optional fallback binding sources

    Returns:
        Formatted location string (e.g., " [from path:line]") or empty string
    """
    from returns.maybe import Nothing
    from pinjected.di.metadata.location_data import ModuleVarPath, ModuleVarLocation

    # First check binding_sources (for backwards compatibility)
    if binding_sources:
        from pinjected.v2.keys import StrBindKey

        # Check if the binding_sources keys are IBindKey objects or strings
        for bind_key, source in binding_sources.items():
            if (isinstance(bind_key, StrBindKey) and bind_key.name == node) or (
                isinstance(bind_key, str) and bind_key == node
            ):
                # Shorten long paths for readability
                if source.startswith("/"):
                    source = format_path_for_display(source)
                return f" [from {source}]"

    # If no binding_sources or not found, try metadata
    metadata = d.get_metadata(node)

    if metadata != Nothing:
        meta = metadata.unwrap()
        if meta.code_location != Nothing:
            location = meta.code_location.unwrap()

            # Format location based on type
            if isinstance(location, ModuleVarPath):
                return f" [from {location.path}]"
            elif isinstance(location, ModuleVarLocation):
                source_path = format_path_for_display(str(location.path))
                return f" [from {source_path}:{location.line}]"

    return ""


def format_injected_for_tree(injected: Injected) -> str:
    """依存関係ツリー表示用にInjectedをフォーマットする"""
    if isinstance(injected, InjectedWithDefaultDesign):
        return format_injected_for_tree(injected.src)
    if isinstance(injected, InjectedFromFunction):
        try:
            return f"<function {injected.original_function.__name__}>"
        except:  # noqa: E722
            return "<function>"
    elif isinstance(injected, InjectedPure):
        v = injected.value
        if isinstance(v, str):
            return "<str instance>"
        if isinstance(v, type):
            return f"<class '{v.__name__}'>"
        if callable(v):
            try:
                return f"<function {v.__name__}>"
            except:  # noqa: E722
                return "<function>"
        else:
            return str(v)
    elif isinstance(injected, PartialInjectedFunction):
        return "Partial"
    elif isinstance(injected, MappedInjected):
        return "Mapped"
    elif isinstance(injected, ZippedInjected):
        return "Zipped"
    elif isinstance(injected, MZippedInjected):
        return "MZipped"
    elif isinstance(injected, InjectedByName):
        return f"ByName({injected.name})"
    elif isinstance(injected, EvaledInjected):
        return f"Eval({show_expr(injected.ast)})"
    else:
        return injected.__class__.__name__


def design_rich_tree(tgt_design, root, binding_sources=None):
    """依存関係をリッチなツリー形式で表示する

    Args:
        tgt_design: The design to visualize
        root: The root dependency to start from
        binding_sources: Optional dict mapping bind keys to their source locations
    """
    from pinjected import design
    from pinjected.di.injected import Injected

    enhanced_design = tgt_design + design(
        __design__=Injected.pure(tgt_design),
        __resolver__=Injected.pure("__resolver__"),
    )

    d = DIGraph(enhanced_design)
    g = d.create_dependency_digraph_rooted(root).graph

    def get_node_label(node):
        try:
            value = d[node]
            if isinstance(value, Injected):
                value_str = format_injected_for_tree(value)
            else:
                value_str = str(value)
            if len(value_str) > 50:
                value_str = value_str[:47] + "... (truncated)"
            typ = type(value)
            # if 'key' in node.lower() or 'secret' in node.lower():
            #     value_str = "********"

            # Add source information if available
            source_info = get_binding_location_info(d, node, binding_sources)

            return Text.assemble(
                (node, Style(color="cyan", bold=True)),
                (" -> ", Style(color="white")),
                (typ.__name__, Style(color="blue")),
                (" : ", Style(color="white")),
                (value_str, Style(color="yellow")),
                (source_info, Style(color="green", dim=True)),
            )
        except Exception as e:
            return Text(f"{node} (Error: {e!s})", style="red")

    root = Tree(Text("target", style="green bold"))
    trees = dict(__root__=root)
    for dep, item in g.edges:
        if item not in trees:
            trees[item] = Tree(get_node_label(item))
        if dep not in trees:
            trees[dep] = Tree(get_node_label(dep))
        trees[item].add(trees[dep])

    from rich.console import Console

    console = Console(file=io.StringIO())
    console.print(root)
    tree_str = console.file.getvalue()
    return tree_str
