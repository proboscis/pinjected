"""PINJ006: Async injected naming rule."""

import ast

from ..models import Fix, Position, RuleContext, Severity
from ..utils.ast_utils import has_decorator
from .base import ASTRuleBase, BaseNodeVisitor


class PINJ006Visitor(BaseNodeVisitor):
    """Visitor for checking async @injected function naming."""

    def visit_AsyncFunctionDef(self, node):
        """Check async function definitions."""
        if has_decorator(node, "injected") and not node.name.startswith("a_"):
            fix = self._create_fix(node)
            self.add_violation(
                node,
                f"Async @injected function '{node.name}' must have 'a_' prefix. "
                f"This helps distinguish async functions in dependency injection.",
                suggestion=f"Rename to 'a_{node.name}'",
                fix=fix,
            )
        self.generic_visit(node)

    def _create_fix(self, node: ast.AsyncFunctionDef) -> Fix:
        """Create a fix to add the 'a_' prefix."""
        old_name = node.name
        new_name = f"a_{old_name}"

        # The position after 'async def '
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


class PINJ006AsyncInjectedNaming(ASTRuleBase):
    """Rule for checking async @injected function naming convention.
    
    Async @injected functions MUST have 'a_' prefix to clearly indicate
    that they are asynchronous operations in Pinjected's dependency
    injection system.
    """
    
    rule_id = "PINJ006"
    name = "Async injected naming"
    description = "Async @injected functions must have 'a_' prefix"
    severity = Severity.ERROR
    category = "naming"
    auto_fixable = True
    
    def get_visitor(self, context: RuleContext) -> ast.NodeVisitor:
        """Get the AST visitor for this rule."""
        return PINJ006Visitor(self, context)