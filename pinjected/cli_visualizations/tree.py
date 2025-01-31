import io
from pinjected.di.injected import (
    Injected, InjectedWithDefaultDesign, InjectedFromFunction,
    InjectedPure, PartialInjectedFunction, MappedInjected,
    ZippedInjected, MZippedInjected, InjectedByName
)
from pinjected.di.app_injected import EvaledInjected
from pinjected.di.expr_util import show_expr
from pinjected.visualize_di import DIGraph
from rich.tree import Tree
from rich.text import Text
from rich.style import Style


def format_injected_for_tree(injected: Injected) -> str:
    """依存関係ツリー表示用にInjectedをフォーマットする"""
    if isinstance(injected, InjectedWithDefaultDesign):
        return format_injected_for_tree(injected.src)
    elif isinstance(injected, InjectedFromFunction):
        try:
            return f"<function {injected.original_function.__name__}>"
        except:
            return "<function>"
    elif isinstance(injected, InjectedPure):
        v = injected.value
        if isinstance(v, str):
            return f'{v}'
        elif isinstance(v, type):
            return f"<class '{v.__name__}'>"
        elif callable(v):
            try:
                return f"<function {v.__name__}>"
            except:
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


def design_rich_tree(tgt_design, root):
    """依存関係をリッチなツリー形式で表示する"""
    d = DIGraph(tgt_design)
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
            if 'key' in node.lower() or 'secret' in node.lower():
                value_str = "********"
            return Text.assemble(
                (node, Style(color="cyan", bold=True)),
                (" -> ", Style(color="white")),
                (typ.__name__, Style(color="blue")),
                (" : ", Style(color="white")),
                (value_str, Style(color="yellow"))
            )
        except Exception as e:
            return Text(f"{node} (Error: {str(e)})", style="red")

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