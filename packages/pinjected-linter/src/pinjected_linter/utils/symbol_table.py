"""Symbol table for tracking definitions in Python code."""

import ast
from typing import Dict, List, Optional

from ..models import FunctionInfo


class SymbolTable:
    """Track function definitions and their decorators."""

    def __init__(self):
        self.functions: Dict[str, FunctionInfo] = {}
        self.classes: Dict[str, ast.ClassDef] = {}
        self.imports: Dict[str, str] = {}  # name -> module
        self.global_vars: Dict[str, ast.AST] = {}
        self._pinjected_decorators = {"instance", "injected", "injected_test", "test"}

    def add_function(self, node: ast.FunctionDef):
        """Add a function to the symbol table."""
        decorators = self._extract_decorators(node)
        is_async = isinstance(node, ast.AsyncFunctionDef)

        # Check for Pinjected decorators
        is_instance = "instance" in decorators
        is_injected = "injected" in decorators
        is_test = any(d in decorators for d in ["injected_test", "test"])

        # Check for slash separator in injected functions
        has_slash = False
        slash_index = None
        if is_injected:
            has_slash, slash_index = self._find_slash_separator(node)

        info = FunctionInfo(
            name=node.name,
            node=node,
            decorators=decorators,
            is_instance=is_instance,
            is_injected=is_injected,
            is_async=is_async,
            is_test=is_test,
            has_slash=has_slash,
            slash_index=slash_index,
        )

        self.functions[node.name] = info

    def add_class(self, node: ast.ClassDef):
        """Add a class to the symbol table."""
        self.classes[node.name] = node

    def add_import(self, name: str, module: str):
        """Add an import to the symbol table."""
        self.imports[name] = module

    def add_global_var(self, name: str, node: ast.AST):
        """Add a global variable to the symbol table."""
        self.global_vars[name] = node

    def get_function(self, name: str) -> Optional[FunctionInfo]:
        """Get function info by name."""
        return self.functions.get(name)

    def get_injected_functions(self) -> List[FunctionInfo]:
        """Get all functions decorated with @injected."""
        return [f for f in self.functions.values() if f.is_injected]

    def get_instance_functions(self) -> List[FunctionInfo]:
        """Get all functions decorated with @instance."""
        return [f for f in self.functions.values() if f.is_instance]

    def is_pinjected_function(self, name: str) -> bool:
        """Check if a function has any Pinjected decorator."""
        func = self.get_function(name)
        return func is not None and func.is_decorated

    def _extract_decorators(self, node: ast.FunctionDef) -> List[str]:
        """Extract decorator names from a function."""
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Call) and isinstance(
                decorator.func, ast.Name
            ):
                decorators.append(decorator.func.id)
        return decorators

    def _find_slash_separator(
        self, node: ast.FunctionDef
    ) -> tuple[bool, Optional[int]]:
        """Find the slash separator in function arguments."""
        args = node.args

        # Check if any argument is position-only (uses /)
        if hasattr(args, "posonlyargs") and args.posonlyargs:
            # Python 3.8+ position-only arguments
            return True, len(args.posonlyargs)

        # For older Python or when not using position-only syntax,
        # we'll need to check comments or other indicators
        return False, None

    def get_injected_deps_before_slash(self, func_info: FunctionInfo) -> List[str]:
        """Get parameter names before the slash separator."""
        if not func_info.is_injected or not func_info.has_slash:
            return []

        args = func_info.node.args
        if hasattr(args, "posonlyargs") and args.posonlyargs:
            return [arg.arg for arg in args.posonlyargs]

        # If no slash found, assume all args except last few are deps
        # This is a heuristic and may need refinement
        all_args = [arg.arg for arg in args.args]
        return all_args[: func_info.slash_index] if func_info.slash_index else []
