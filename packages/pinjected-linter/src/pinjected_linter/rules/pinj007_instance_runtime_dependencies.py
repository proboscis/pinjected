"""PINJ007: Instance function runtime dependencies rule."""

import ast

from ..models import RuleContext, Severity
from ..utils.ast_utils import has_decorator
from .base import ASTRuleBase, BaseNodeVisitor


class PINJ007Visitor(BaseNodeVisitor):
    """Visitor for checking runtime dependencies in @instance functions."""

    def visit_FunctionDef(self, node):
        """Check function definitions."""
        self._check_function(node)

    def visit_AsyncFunctionDef(self, node):
        """Check async function definitions."""
        self._check_function(node)

    def _check_function(self, node):
        """Check if @instance function has runtime dependencies."""
        if not has_decorator(node, "instance"):
            self.generic_visit(node)
            return

        # Check for any parameters
        all_args = []

        # Regular args
        all_args.extend(node.args.args)

        # Positional-only args
        all_args.extend(node.args.posonlyargs)

        # Keyword-only args
        all_args.extend(node.args.kwonlyargs)

        # Check for *args
        if node.args.vararg:
            all_args.append(node.args.vararg)

        # Check for **kwargs
        if node.args.kwarg:
            all_args.append(node.args.kwarg)

        # @instance functions should have no parameters
        if all_args:
            arg_names = [arg.arg for arg in all_args]
            self.add_violation(
                node,
                f"@instance function '{node.name}' accepts parameters: {', '.join(arg_names)}. "
                f"@instance functions should not accept any runtime parameters. "
                f"They should only construct and return dependency providers.",
                suggestion="Remove all parameters or convert to @injected if runtime parameters are needed",
            )

        self.generic_visit(node)


class PINJ007InstanceRuntimeDependencies(ASTRuleBase):
    """Rule for checking runtime dependencies in @instance functions.

    @instance functions are dependency providers that should not accept
    any runtime parameters. They should be pure factories that construct
    and return objects.

    If runtime parameters are needed, use @injected instead.

    Bad:
        @instance
        def database_connection(host: str, port: int):
            return Database(host=host, port=port)

    Good:
        @instance
        def database_connection():
            return Database(host="localhost", port=5432)

        # Or use @injected for runtime parameters
        @injected
        def create_connection(config, /, host: str, port: int):
            return Database(host=host, port=port)
    """

    rule_id = "PINJ007"
    name = "Instance function runtime dependencies"
    description = "@instance functions should not accept runtime parameters"
    severity = Severity.ERROR
    category = "design"
    auto_fixable = False  # Requires design decision

    def get_visitor(self, context: RuleContext) -> ast.NodeVisitor:
        """Get the AST visitor for this rule."""
        return PINJ007Visitor(self, context)
