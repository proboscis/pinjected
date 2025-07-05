"""PINJ007: Slash separator position rule."""

import ast
from typing import List, Set

from ..models import RuleContext, Severity
from ..utils.ast_utils import find_slash_position, has_decorator
from .base import ASTRuleBase, BaseNodeVisitor


class PINJ007Visitor(BaseNodeVisitor):
    """Visitor for checking slash separator position in @injected functions."""
    
    def __init__(self, rule, context):
        super().__init__(rule, context)
        self.symbol_table = context.symbol_table
        self.known_dependencies = self._get_known_dependencies()
    
    def _get_known_dependencies(self) -> Set[str]:
        """Get set of known dependency names from symbol table."""
        dependencies = set()
        
        # Get all @instance functions
        for func_info in self.symbol_table.get_instance_functions():
            dependencies.add(func_info.name)
        
        # Get all @injected functions
        for func_info in self.symbol_table.get_injected_functions():
            dependencies.add(func_info.name)
        
        return dependencies
    
    def visit_FunctionDef(self, node):
        """Check function definitions."""
        self._check_function(node)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        """Check async function definitions."""
        self._check_function(node)
        self.generic_visit(node)
    
    def _check_function(self, node):
        """Check if @injected function has correct slash position."""
        if not has_decorator(node, "injected"):
            return
        
        slash_pos = find_slash_position(node.args)
        if slash_pos is None:
            # No slash, this is handled by PINJ015
            return
        
        # Get parameters after the slash
        params_after_slash = self._get_params_after_slash(node.args, slash_pos)
        
        # Check each parameter after slash
        for param_name in params_after_slash:
            if self._is_likely_dependency(param_name, node):
                self.add_violation(
                    node,
                    f"@injected function '{node.name}' has dependency parameter '{param_name}' "
                    f"after the slash separator. Dependencies must be on the left side of '/'.",
                    suggestion=f"Move '{param_name}' before the '/' separator",
                )
    
    def _get_params_after_slash(self, args: ast.arguments, slash_pos: int) -> List[str]:
        """Get parameter names after the slash position."""
        params = []
        
        # In Python's AST, posonlyargs are the parameters before the slash
        # Regular args are the parameters after the slash (between / and *)
        for arg in args.args:
            params.append(arg.arg)
        
        # Also include kwonlyargs (they are always after slash and *)
        for arg in args.kwonlyargs:
            params.append(arg.arg)
        
        return params
    
    def _is_likely_dependency(self, param_name: str, function_node) -> bool:
        """Determine if a parameter is likely a dependency."""
        # Check if it's a known dependency name
        if param_name in self.known_dependencies:
            return True
        
        # Common dependency patterns
        dependency_patterns = {
            'logger', 'db', 'database', 'cache', 'redis', 'api', 'client',
            'service', 'repository', 'repo', 'manager', 'handler', 'processor',
            'transformer', 'validator', 'serializer', 'parser', 'formatter',
            'auth', 'authenticator', 'authorizer', 'session', 'store', 'storage',
            'queue', 'mq', 'broker', 'publisher', 'subscriber', 'dispatcher',
            'factory', 'builder', 'provider', 'injector', 'container',
            'config', 'settings', 'env', 'context', 'engine', 'driver',
            'connector', 'adapter', 'gateway', 'proxy', 'middleware',
            'monitor', 'metrics', 'tracer', 'profiler', 'debugger',
        }
        
        # Check if param name matches common patterns
        param_lower = param_name.lower()
        if param_lower in dependency_patterns:
            return True
        
        # Check if it ends with common dependency suffixes
        dependency_suffixes = ['_service', '_client', '_manager', '_handler', 
                               '_repository', '_repo', '_factory', '_provider',
                               '_api', '_db', '_cache', '_store', '_queue']
        
        for suffix in dependency_suffixes:
            if param_lower.endswith(suffix):
                return True
        
        # Check if parameter name starts with 'a_' (async dependency)
        if param_name.startswith('a_') and param_name[2:] in self.known_dependencies:
            return True
        
        # Additional heuristic: check if it's used as a method call in the function body
        return self._is_used_as_dependency_in_body(param_name, function_node)
    
    def _is_used_as_dependency_in_body(self, param_name: str, function_node) -> bool:
        """Check if parameter is used like a dependency in function body."""
        class DependencyUsageChecker(ast.NodeVisitor):
            def __init__(self):
                self.is_dependency = False
            
            def visit_Call(self, node):
                # Check for method calls like param.method()
                if (isinstance(node.func, ast.Attribute) and 
                    isinstance(node.func.value, ast.Name) and 
                    node.func.value.id == param_name):
                    self.is_dependency = True
                self.generic_visit(node)
        
        checker = DependencyUsageChecker()
        checker.visit(function_node)
        return checker.is_dependency


class PINJ007SlashSeparatorPosition(ASTRuleBase):
    """Rule for checking slash separator position in @injected functions.
    
    The slash separator (/) must correctly separate injected dependencies
    (left side) from runtime arguments (right side). Dependencies placed
    after the slash will not be injected and will cause runtime errors.
    """
    
    rule_id = "PINJ007"
    name = "Slash separator position"
    description = "/ must separate injected dependencies (left) from runtime args (right)"
    severity = Severity.ERROR
    category = "injection"
    auto_fixable = False  # Moving parameters requires careful consideration
    
    def get_visitor(self, context: RuleContext) -> ast.NodeVisitor:
        """Get the AST visitor for this rule."""
        return PINJ007Visitor(self, context)