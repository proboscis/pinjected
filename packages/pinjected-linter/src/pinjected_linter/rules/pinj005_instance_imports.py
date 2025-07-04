"""PINJ005: Instance function imports rule."""

import ast

from ..models import RuleContext, Severity
from ..utils.ast_utils import has_decorator
from .base import ASTRuleBase, BaseNodeVisitor


class PINJ005Visitor(BaseNodeVisitor):
    """Visitor for checking imports inside @instance functions."""

    def __init__(self, rule, context):
        super().__init__(rule, context)
        self.inside_instance = False
        self.current_function = None

    def visit_FunctionDef(self, node):
        """Check function definitions."""
        self._check_function(node)

    def visit_AsyncFunctionDef(self, node):
        """Check async function definitions."""
        self._check_function(node)

    def _check_function(self, node):
        """Process function definition."""
        old_inside = self.inside_instance
        old_function = self.current_function

        if has_decorator(node, "instance"):
            self.inside_instance = True
            self.current_function = node.name

        self.generic_visit(node)

        self.inside_instance = old_inside
        self.current_function = old_function

    def visit_Import(self, node):
        """Check import statements."""
        if self.inside_instance:
            self.add_violation(
                node,
                f"@instance function '{self.current_function}' contains import statement. "
                f"Imports should be at module level, not inside @instance functions.",
                suggestion="Move the import to the module level",
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Check from-import statements."""
        if self.inside_instance:
            module_name = node.module if node.module else "relative import"
            self.add_violation(
                node,
                f"@instance function '{self.current_function}' contains import from '{module_name}'. "
                f"Imports should be at module level, not inside @instance functions.",
                suggestion="Move the import to the module level",
            )
        self.generic_visit(node)


class PINJ005InstanceImports(ASTRuleBase):
    """Rule for checking imports inside @instance functions.

    @instance functions should not contain import statements. All imports
    should be at the module level to ensure:
    - Predictable behavior
    - No runtime import errors
    - Clear dependencies
    - Better performance (imports happen once)
    """

    rule_id = "PINJ005"
    name = "Instance function imports"
    description = "@instance functions should not contain import statements"
    severity = Severity.ERROR
    category = "imports"
    auto_fixable = False  # Moving imports requires careful consideration

    def get_visitor(self, context: RuleContext) -> ast.NodeVisitor:
        """Get the AST visitor for this rule."""
        return PINJ005Visitor(self, context)
