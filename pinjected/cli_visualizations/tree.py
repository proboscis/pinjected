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


def format_injected_for_tree(injected: Injected) -> str:  # noqa: C901, PLR0911, PLR0912
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
            return f"<str instance>"
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


def design_rich_tree(tgt_design, root, binding_sources=None):  # noqa: C901
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

    def get_node_label(node):  # noqa: C901, PLR0912
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
            source_info = ""
            if binding_sources:
                from pinjected.v2.keys import StrBindKey

                key = StrBindKey(node)
                if key in binding_sources:
                    source = binding_sources[key]
                    # Shorten long paths for readability
                    if source.startswith("/") and len(source) > 50:
                        # Show last part of path
                        parts = source.split("/")
                        if len(parts) > 3:
                            source = "..." + "/".join(parts[-3:])
                    source_info = f" [from {source}]"

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
