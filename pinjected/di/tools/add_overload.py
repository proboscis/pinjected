import ast
import inspect
import textwrap
from typing import Any, overload

from pinjected import design, injected
from pinjected.pinjected_logging import logger


def process_file(file_path):
    with open(file_path) as file:
        source_code = file.read()
    tree = ast.parse(source_code)
    import_overload = False

    # Build parent map to track parent nodes
    parent_map = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parent_map[child] = parent

    # Process function nodes with their parents
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            parent = parent_map.get(node, tree)
            if has_injected_decorator(node):
                original_signature = get_function_signature(node)
                updated_signature = update_function_signature(original_signature)
                overload_signature = generate_overload_signature(
                    node.name, updated_signature
                )
                inject_overload_signature(parent, node, overload_signature)
                import_overload = True
            else:
                remove_overload_signature(parent, node)
    if import_overload:
        add_overload_import(tree)
    updated_source_code = ast.unparse(tree)
    with open(file_path, "w") as file:
        file.write(updated_source_code)


def add_overload_import(tree):
    for node in tree.body:
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "typing"
            and any(alias.name == "overload" for alias in node.names)
        ):
            return
    import_node = ast.ImportFrom(
        module="typing", names=[ast.alias(name="overload", asname=None)], level=0
    )
    tree.body.insert(0, import_node)


def has_injected_decorator(node):
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "injected":
            return True
    return False


def get_function_signature(node: ast.FunctionDef) -> inspect.Signature:
    args: ast.arguments = node.args
    pos_only_args: list[ast.arg] = args.posonlyargs
    pos_or_kw_args: list[ast.arg] = args.args
    kw_only_args: list[ast.arg] = args.kwonlyargs
    defaults: list[Any] = [ast.literal_eval(default) for default in args.defaults]
    kw_defaults: dict[str, Any] = {
        kw.arg: ast.literal_eval(kw.value) for kw in args.kw_defaults
    }
    num_non_defaults: int = len(pos_or_kw_args) - len(defaults)
    non_def_params: list[inspect.Parameter] = [
        inspect.Parameter(
            name=arg.arg,
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=arg.annotation.id if arg.annotation else inspect.Parameter.empty,
        )
        for arg in pos_or_kw_args[:num_non_defaults]
    ]
    def_params: list[inspect.Parameter] = [
        inspect.Parameter(
            name=arg.arg,
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=default,
            annotation=arg.annotation.id if arg.annotation else inspect.Parameter.empty,
        )
        for arg, default in zip(
            pos_or_kw_args[num_non_defaults:], defaults, strict=False
        )
    ]
    pos_only_params: list[inspect.Parameter] = [
        inspect.Parameter(
            name=arg.arg,
            kind=inspect.Parameter.POSITIONAL_ONLY,
            annotation=arg.annotation.id if arg.annotation else inspect.Parameter.empty,
        )
        for arg in pos_only_args
    ]
    kw_only_params: list[inspect.Parameter] = [
        inspect.Parameter(
            name=arg.arg,
            kind=inspect.Parameter.KEYWORD_ONLY,
            default=kw_defaults.get(arg.arg, inspect.Parameter.empty),
            annotation=arg.annotation.id if arg.annotation else inspect.Parameter.empty,
        )
        for arg in kw_only_args
    ]
    return_annotation = (
        node.returns.value
        if isinstance(node.returns, ast.Constant)
        else node.returns.id
        if node.returns
        else inspect.Signature.empty
    )
    sig: inspect.Signature = inspect.Signature(
        parameters=pos_only_params + non_def_params + def_params + kw_only_params,
        return_annotation=return_annotation,
    )
    logger.info(f"signature: {sig}")
    return sig


def update_function_signature(original_signature):
    logger.info(f"Original signature: {original_signature}")
    updated_parameters = []
    param_list = list(original_signature.parameters.values())

    for i, param in enumerate(param_list):
        # Keep 'self' parameter even if it's positional-only
        if (
            i == 0 and param.name == "self"
        ) or param.kind != inspect.Parameter.POSITIONAL_ONLY:
            updated_parameters.append(param)

    updated_signature = original_signature.replace(parameters=updated_parameters)
    logger.info(f"Updated signature: {updated_signature}")
    return updated_signature


def generate_overload_signature(func_name, signature):
    param_annotations = []
    for param in signature.parameters.values():
        logger.info(f"param:{param},{param.annotation}")
        if param.annotation == inspect.Parameter.empty:
            param_annotations.append(param.name)
        else:
            param_annotations.append(
                f"{param.name}: {get_annotation_string(param.annotation)}"
            )
    return_annotation = signature.return_annotation
    signature_str = f"@overload\ndef {func_name}({', '.join(param_annotations)})"
    if return_annotation != inspect.Signature.empty:
        signature_str += f" -> {get_annotation_string(return_annotation)}"
    signature_str += (
        ':\n    """Signature of the function after being injected."""\n    ...'
    )
    return signature_str


def get_annotation_string(annotation):
    if annotation is None:
        return "None"
    if isinstance(annotation, str):
        return annotation
    if isinstance(annotation, type) or hasattr(annotation, "__name__"):
        return annotation.__name__
    return str(annotation)


def inject_overload_signature(parent, node, overload_signature):
    overload_node = ast.parse(textwrap.dedent(overload_signature)).body[0]
    remove_overload_signature(parent, node)

    # Get the body attribute from parent (works for Module, ClassDef, etc.)
    body = parent.body
    body.insert(body.index(node), overload_node)


def remove_overload_signature(parent, node):
    # Get the body attribute from parent (works for Module, ClassDef, etc.)
    body = parent.body
    node_index = body.index(node)

    if node_index > 0:
        prev_node = body[node_index - 1]
        if (
            isinstance(prev_node, ast.FunctionDef)
            and prev_node.name == node.name
            and has_overload_decorator(prev_node)
        ):
            body.remove(prev_node)


def has_overload_decorator(node):
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "overload":
            return True
    return False


@overload
def add_overload(file_path: str) -> int:
    """Signature of the function after being injected."""


@injected
def add_overload(file_path: str) -> int:
    process_file(file_path)
    return 0


design_obj = design()
__design__ = design()
