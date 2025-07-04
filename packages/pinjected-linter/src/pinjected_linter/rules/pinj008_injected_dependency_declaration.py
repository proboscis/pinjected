"""PINJ008: Injected function dependency declaration rule."""

import ast
from typing import Dict, List, Set

from ..models import Position, RuleContext, Severity, Violation
from ..utils.ast_utils import has_decorator
from .base import BaseRule


class InjectedDependencyChecker(ast.NodeVisitor):
    """Visitor for checking @injected function dependency declarations."""
    
    def __init__(self, symbol_table):
        self.symbol_table = symbol_table
        self.injected_functions: Dict[str, Set[str]] = {}  # func_name -> declared_deps
        self.violations = []
        self.current_function = None
        self.current_dependencies = set()
        
    def visit_Module(self, node):
        """First pass: collect all @injected functions and their dependencies."""
        # First pass: collect function info
        for item in ast.walk(node):
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and has_decorator(item, "injected"):
                    deps = self._extract_dependencies(item)
                    self.injected_functions[item.name] = deps
        
        # Second pass: check for violations
        self.generic_visit(node)
    
    def _extract_dependencies(self, node):
        """Extract dependency names from function signature (before slash)."""
        dependencies = set()
        args = node.args
        
        # Find the position of the slash (/)
        slash_pos = None
        for i, arg in enumerate(args.posonlyargs):
            # In Python 3.8+, position-only args are in posonlyargs
            dependencies.add(arg.arg)
            slash_pos = i
        
        # If no posonlyargs, check regular args for pattern
        if slash_pos is None and args.args:
            # Look for pattern where dependencies come before runtime args
            # This is a heuristic - in practice, the slash is explicit in AST
            for _arg in args.args:
                # We'll treat all args as potential dependencies for now
                # Real implementation would need more sophisticated parsing
                pass
        
        return dependencies
    
    def visit_FunctionDef(self, node):
        """Track current function context."""
        if has_decorator(node, "injected"):
            old_func = self.current_function
            old_deps = self.current_dependencies
            
            self.current_function = node.name
            self.current_dependencies = self._extract_dependencies(node)
            
            self.generic_visit(node)
            
            self.current_function = old_func
            self.current_dependencies = old_deps
        else:
            self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        """Track current async function context."""
        if has_decorator(node, "injected"):
            old_func = self.current_function
            old_deps = self.current_dependencies
            
            self.current_function = node.name
            self.current_dependencies = self._extract_dependencies(node)
            
            self.generic_visit(node)
            
            self.current_function = old_func
            self.current_dependencies = old_deps
        else:
            self.generic_visit(node)
    
    def visit_Call(self, node):
        """Check for calls to @injected functions."""
        if self.current_function is None:
            self.generic_visit(node)
            return
        
        # Check if calling an @injected function
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                func_name = node.func.value.id
        
        if func_name and func_name in self.injected_functions and func_name not in self.current_dependencies:
                self._add_violation(
                    node,
                    f"@injected function '{self.current_function}' calls "
                    f"@injected function '{func_name}' without declaring it as a dependency. "
                    f"Add '{func_name}' to the dependencies (before the '/')."
                )
        
        self.generic_visit(node)
    
    def _add_violation(self, node: ast.AST, message: str):
        """Add a violation."""
        position = Position(
            line=node.lineno if hasattr(node, "lineno") else 0,
            column=node.col_offset if hasattr(node, "col_offset") else 0,
            end_line=node.end_lineno if hasattr(node, "end_lineno") else None,
            end_column=node.end_col_offset if hasattr(node, "end_col_offset") else None,
        )
        
        violation = Violation(
            rule_id="PINJ008",
            message=message,
            file_path=self.symbol_table.file_path if hasattr(self.symbol_table, 'file_path') else None,
            position=position,
            severity=Severity.ERROR,
        )
        
        self.violations.append(violation)


class PINJ008InjectedDependencyDeclaration(BaseRule):
    """Rule for checking @injected function dependency declarations."""
    
    rule_id = "PINJ008"
    name = "Injected function dependency declaration"
    description = "@injected functions must declare other @injected functions they call as dependencies"
    severity = Severity.ERROR
    category = "dependencies"
    auto_fixable = False  # Requires understanding the function logic
    
    def check(self, context: RuleContext) -> List[Violation]:
        """Check for undeclared @injected dependencies."""
        checker = InjectedDependencyChecker(context.symbol_table)
        # Add file_path to symbol_table for violation reporting
        context.symbol_table.file_path = context.file_path
        checker.visit(context.tree)
        return checker.violations