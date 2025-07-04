"""PINJ015: Missing slash in injected rule."""

import ast

from ..models import RuleContext, Severity
from ..utils.ast_utils import has_decorator
from .base import ASTRuleBase, BaseNodeVisitor


class PINJ015Visitor(BaseNodeVisitor):
    """Visitor for checking missing slash in @injected functions."""
    
    def visit_FunctionDef(self, node):
        """Check function definitions."""
        self._check_function(node)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        """Check async function definitions."""
        self._check_function(node)
        self.generic_visit(node)
    
    def _check_function(self, node):
        """Check if an @injected function is missing the slash separator."""
        if not has_decorator(node, "injected"):
            return
        
        args = node.args
        
        # Check if function has position-only args (indicating slash)
        has_slash = len(args.posonlyargs) > 0
        
        # If no slash and has arguments, warn because ALL args will be runtime args
        if not has_slash and (args.args or args.kwonlyargs):
            self.add_violation(
                node,
                f"@injected function '{node.name}' is missing the '/' separator. "
                f"Without '/', ALL arguments are treated as runtime arguments (not injected). "
                f"If you need dependency injection, add '/' after the dependencies.",
                suggestion=self._generate_suggestion(node),
            )
    
    def _generate_suggestion(self, node):
        """Generate suggestion for adding slash."""
        args = node.args
        if args.args:
            # We can't know which args are meant to be dependencies without user intent
            # So provide a generic example showing the pattern
            arg_names = [arg.arg for arg in args.args]
            
            # If it looks like the first args might be dependencies (common patterns)
            likely_deps = []
            likely_runtime = []
            
            for arg in args.args:
                arg_name = arg.arg.lower()
                # Common dependency names
                if any(pattern in arg_name for pattern in [
                    'logger', 'database', 'db', 'cache', 'client', 'service',
                    'repository', 'repo', 'manager', 'handler', 'processor',
                    'transformer', 'validator', 'analyzer', 'converter',
                    'factory', 'builder', 'provider', 'storage', 'queue',
                    'config', 'settings', 'session', 'connection', 'channel'
                ]) or arg.arg.startswith('a_'):
                    likely_deps.append(arg.arg)
                else:
                    likely_runtime.append(arg.arg)
            
            if likely_deps and likely_runtime:
                return (
                    f"If dependencies are {', '.join(likely_deps)}, "
                    f"use: def {node.name}({', '.join(likely_deps)}, /, {', '.join(likely_runtime)})"
                )
            elif likely_deps:
                # All args look like dependencies
                return (
                    f"If all arguments are dependencies, "
                    f"use: def {node.name}({', '.join(arg_names)}, /)"
                )
            else:
                # No clear dependencies
                return (
                    f"Add '/' after dependencies. Example: "
                    f"def {node.name}(dep1, dep2, /, {', '.join(arg_names)})"
                )
        return "Add '/' to separate dependencies from runtime arguments"


class PINJ015MissingSlash(ASTRuleBase):
    """Rule for checking missing slash in @injected functions.
    
    In Pinjected, the '/' separator is critical:
    - Arguments before '/' are positional-only and treated as dependencies (injected)
    - Arguments after '/' are runtime arguments (must be provided when calling)
    - Without '/', ALL arguments are treated as runtime arguments
    
    This rule warns when an @injected function has arguments but no '/',
    which means no dependencies will be injected.
    """
    
    rule_id = "PINJ015"
    name = "Missing slash in injected"
    description = "@injected functions need '/' to mark dependencies as positional-only"
    severity = Severity.ERROR
    category = "syntax"
    auto_fixable = False  # Requires understanding user intent
    
    def get_visitor(self, context: RuleContext) -> ast.NodeVisitor:
        """Get the AST visitor for this rule."""
        return PINJ015Visitor(self, context)