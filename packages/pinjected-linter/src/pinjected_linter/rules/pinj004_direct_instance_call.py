"""PINJ004: Direct instance call detection rule."""

import ast
from typing import Set

from ..models import Position, RuleContext, Severity, Violation
from ..utils.ast_utils import has_decorator
from .base import BaseRule


class DirectInstanceCallChecker(ast.NodeVisitor):
    """Visitor for checking direct calls to @instance functions."""
    
    def __init__(self, symbol_table):
        self.symbol_table = symbol_table
        self.instance_functions: Set[str] = set()
        self.violations = []
        self.current_function = None
        # Track if we're inside a design() call
        self.in_design_call = False
        self.design_level = 0
        
    def visit_Module(self, node):
        """First pass: collect all @instance function names."""
        # Collect @instance functions
        for item in ast.walk(node):
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and has_decorator(item, "instance"):
                    self.instance_functions.add(item.name)
        
        # Second pass: check for direct calls
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        """Track current function context."""
        old_func = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_func
    
    def visit_AsyncFunctionDef(self, node):
        """Track current async function context."""
        old_func = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_func
    
    def visit_Call(self, node):
        """Check for direct calls to @instance functions."""
        # Check if this is a design() call
        if isinstance(node.func, ast.Name) and node.func.id == "design":
            self.design_level += 1
            self.in_design_call = True
            self.generic_visit(node)
            self.design_level -= 1
            if self.design_level == 0:
                self.in_design_call = False
            return
        
        # Skip if we're inside a design() call
        if self.in_design_call:
            self.generic_visit(node)
            return
        
        # Check for direct instance function calls
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.instance_functions:
                # Direct call to @instance function
                self._add_violation(
                    node,
                    f"Direct call to @instance function '{func_name}'. "
                    f"@instance functions should be used in design() or as dependencies, not called directly."
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
            rule_id="PINJ004",
            message=message,
            file_path=self.symbol_table.file_path if hasattr(self.symbol_table, 'file_path') else None,
            position=position,
            severity=Severity.ERROR,
            suggestion="Use this function in design() or inject it as a dependency",
        )
        
        self.violations.append(violation)


class PINJ004DirectInstanceCall(BaseRule):
    """Rule for detecting direct calls to @instance functions."""
    
    rule_id = "PINJ004"
    name = "Direct instance call detection"
    description = "@instance decorated functions cannot be called directly"
    severity = Severity.ERROR
    category = "usage"
    auto_fixable = False  # Complex fix requires understanding the context
    
    def check(self, context: RuleContext) -> list[Violation]:
        """Check for direct instance calls."""
        checker = DirectInstanceCallChecker(context.symbol_table)
        # Add file_path to symbol_table for violation reporting
        context.symbol_table.file_path = context.file_path
        checker.visit(context.tree)
        return checker.violations