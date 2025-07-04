"""PINJ009: Injected function async prefix rule."""

import ast

from ..models import Fix, Position, RuleContext, Severity
from ..utils.ast_utils import has_decorator
from .base import ASTRuleBase, BaseNodeVisitor


class PINJ009Visitor(BaseNodeVisitor):
    """Visitor for checking async @injected function naming."""

    def visit_AsyncFunctionDef(self, node):
        """Check async function definitions."""
        if has_decorator(node, "injected") and not node.name.startswith("a_"):
            fix = self._create_fix(node)
            self.add_violation(
                node,
                f"Async @injected function '{node.name}' should have 'a_' prefix. "
                f"This helps distinguish async from sync functions.",
                suggestion=f"Consider renaming to 'a_{node.name}'",
                fix=fix,
            )
        self.generic_visit(node)

    def _create_fix(self, node: ast.AsyncFunctionDef) -> Fix:
        """Create a fix to add the 'a_' prefix."""
        old_name = node.name
        new_name = f"a_{old_name}"

        start_pos = Position(
            line=node.lineno,
            column=node.col_offset + 10,  # 'async def ' is 10 characters
        )
        end_pos = Position(
            line=node.lineno,
            column=node.col_offset + 10 + len(old_name),
        )

        return Fix(
            start_pos=start_pos,
            end_pos=end_pos,
            replacement=new_name,
            description=f"Add 'a_' prefix to '{old_name}'",
        )


class PINJ009InjectedAsyncPrefix(ASTRuleBase):
    """Rule for checking async @injected function naming convention.

    Async @injected functions should have the 'a_' prefix to clearly
    distinguish them from synchronous functions. This is important because:
    - It makes async boundaries visible in the code
    - It helps prevent accidentally mixing sync/async calls
    - It follows Pinjected's naming conventions

    Note: This is the opposite of PINJ003, which prevents @instance
    functions from having the 'a_' prefix.
    """

    rule_id = "PINJ009"
    name = "Injected async function prefix"
    description = "Async @injected functions should have 'a_' prefix"
    severity = Severity.ERROR
    category = "naming"
    auto_fixable = True

    def get_visitor(self, context: RuleContext) -> ast.NodeVisitor:
        """Get the AST visitor for this rule."""
        return PINJ009Visitor(self, context)
