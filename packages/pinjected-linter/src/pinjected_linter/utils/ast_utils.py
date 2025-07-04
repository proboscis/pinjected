"""AST utility functions for analyzing Python code."""

import ast
from typing import List, Optional, Set, Tuple


def has_decorator(node: ast.FunctionDef, decorator_name: str) -> bool:
    """Check if a function has a specific decorator."""
    return decorator_name in get_decorator_names(node)


def get_decorator_names(node: ast.FunctionDef) -> List[str]:
    """Extract decorator names from a function."""
    decorators = []
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name):
            decorators.append(decorator.id)
        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            decorators.append(decorator.func.id)
    return decorators


def find_slash_position(args: ast.arguments) -> Optional[int]:
    """Find the position of the slash separator in function arguments.
    
    Returns the index where the slash appears, or None if no slash.
    """
    # Python 3.8+ position-only arguments use posonlyargs
    if hasattr(args, "posonlyargs") and args.posonlyargs:
        return len(args.posonlyargs)
    
    # For compatibility, we might need to parse comments or use other heuristics
    # In real implementation, this would need more sophisticated handling
    return None


def get_function_params_before_slash(node: ast.FunctionDef) -> List[str]:
    """Get parameter names before the slash separator."""
    slash_pos = find_slash_position(node.args)
    if slash_pos is None:
        return []
    
    params = []
    if hasattr(node.args, "posonlyargs"):
        params.extend(arg.arg for arg in node.args.posonlyargs)
    
    return params


def get_function_params_after_slash(node: ast.FunctionDef) -> List[str]:
    """Get parameter names after the slash separator."""
    slash_pos = find_slash_position(node.args)
    if slash_pos is None:
        # No slash, all params are after
        return [arg.arg for arg in node.args.args]
    
    # Return regular args (not position-only)
    return [arg.arg for arg in node.args.args]


def is_function_call(node: ast.AST, function_name: str) -> bool:
    """Check if a node is a call to a specific function."""
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            return node.func.id == function_name
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr == function_name
    return False


def find_all_names(node: ast.AST) -> Set[str]:
    """Find all Name nodes in an AST subtree."""
    names = set()
    
    class NameCollector(ast.NodeVisitor):
        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load):
                names.add(node.id)
            self.generic_visit(node)
    
    NameCollector().visit(node)
    return names


def get_call_names(node: ast.AST) -> Set[str]:
    """Get all function names that are called in an AST subtree."""
    calls = set()
    
    class CallCollector(ast.NodeVisitor):
        def visit_Call(self, node):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                # For method calls, we might want the attribute name
                calls.add(node.func.attr)
            self.generic_visit(node)
    
    CallCollector().visit(node)
    return calls


def find_await_calls(node: ast.AST) -> List[ast.Await]:
    """Find all await expressions in an AST subtree."""
    awaits = []
    
    class AwaitCollector(ast.NodeVisitor):
        def visit_Await(self, node):
            awaits.append(node)
            self.generic_visit(node)
    
    AwaitCollector().visit(node)
    return awaits


def get_string_value(node: ast.AST) -> Optional[str]:
    """Extract string value from an AST node if it's a string literal."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    elif isinstance(node, ast.Str):  # For Python < 3.8
        return node.s
    return None


def is_design_call(node: ast.AST) -> bool:
    """Check if a node is a call to design() function."""
    return is_function_call(node, "design")


def is_iproxy_type_annotation(node: ast.AST) -> bool:
    """Check if a type annotation is IProxy or IProxy[...]."""
    if isinstance(node, ast.Name):
        return node.id == "IProxy"
    elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        return node.value.id == "IProxy"
    return False


def extract_function_defaults(node: ast.FunctionDef) -> List[Tuple[str, ast.AST]]:
    """Extract parameter names and their default values."""
    defaults = []
    args = node.args
    
    # Handle regular arguments with defaults
    if args.defaults:
        # defaults align with the end of args
        num_args = len(args.args)
        num_defaults = len(args.defaults)
        start_idx = num_args - num_defaults
        
        for i, default in enumerate(args.defaults):
            arg = args.args[start_idx + i]
            defaults.append((arg.arg, default))
    
    # Handle keyword-only arguments with defaults
    if args.kw_defaults:
        for arg, default in zip(args.kwonlyargs, args.kw_defaults):
            if default is not None:
                defaults.append((arg.arg, default))
    
    return defaults


def is_print_call(node: ast.AST) -> bool:
    """Check if a node is a call to print() function."""
    return is_function_call(node, "print")