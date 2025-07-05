"""PINJ009: No await in injected AST building rule."""

import ast
from typing import Set

from ..models import RuleContext, Severity
from ..utils.ast_utils import find_await_calls, has_decorator
from .base import ASTRuleBase, BaseNodeVisitor


class PINJ009Visitor(BaseNodeVisitor):
    """Visitor for checking await usage in @injected functions."""
    
    def __init__(self, rule, context):
        super().__init__(rule, context)
        self.symbol_table = context.symbol_table
        self.injected_functions = self._get_injected_functions()
        self.current_injected_function = None
    
    def _get_injected_functions(self) -> Set[str]:
        """Get all @injected function names from symbol table."""
        return {func.name for func in self.symbol_table.get_injected_functions()}
    
    def visit_FunctionDef(self, node):
        """Check function definitions."""
        self._check_function(node)
    
    def visit_AsyncFunctionDef(self, node):
        """Check async function definitions."""
        self._check_function(node)
    
    def _check_function(self, node):
        """Process function definition."""
        if has_decorator(node, "injected"):
            old_function = self.current_injected_function
            self.current_injected_function = node.name
            
            # Check for await expressions in the function body
            self._check_awaits_in_body(node)
            
            self.current_injected_function = old_function
        else:
            # Still visit children for nested functions
            self.generic_visit(node)
    
    def _check_awaits_in_body(self, function_node):
        """Check for improper await usage in function body."""
        await_calls = find_await_calls(function_node)
        
        for await_node in await_calls:
            # Check if the awaited expression is a call to an @injected function
            if self._is_await_on_injected_call(await_node.value):
                self.add_violation(
                    await_node,
                    f"@injected function '{self.current_injected_function}' uses 'await' on a call "
                    f"to another @injected function. Inside @injected functions, you're building "
                    f"an AST, not executing code. Remove the 'await'.",
                    suggestion="Remove 'await' - you're building an AST, not executing",
                )
    
    def _is_await_on_injected_call(self, node) -> bool:
        """Check if a node is a call to an @injected function."""
        if not isinstance(node, ast.Call):
            return False
        
        # Direct function call: injected_func(args)
        if isinstance(node.func, ast.Name):
            return node.func.id in self.injected_functions
        
        # Handle cases like a_fetch_data() where a_ prefix indicates async injected
        if isinstance(node.func, ast.Name) and node.func.id.startswith('a_'):
            # Check if the non-prefixed version exists as injected
            base_name = node.func.id[2:]
            if base_name in self.injected_functions:
                return True
            # Or if the prefixed version itself is injected
            return node.func.id in self.injected_functions
        
        return False


class PINJ009NoAwaitInInjected(ASTRuleBase):
    """Rule for checking improper await usage in @injected functions.
    
    Inside @injected functions, you're building an Abstract Syntax Tree (AST),
    not executing code directly. Using 'await' on calls to other @injected
    functions is incorrect because the actual execution happens later when
    the dependency graph is resolved.
    """
    
    rule_id = "PINJ009"
    name = "No await in injected AST building"
    description = "Don't use await when calling @injected functions inside other @injected functions"
    severity = Severity.ERROR
    category = "injection"
    auto_fixable = False  # Removing await requires understanding the context
    
    def get_visitor(self, context: RuleContext) -> ast.NodeVisitor:
        """Get the AST visitor for this rule."""
        return PINJ009Visitor(self, context)