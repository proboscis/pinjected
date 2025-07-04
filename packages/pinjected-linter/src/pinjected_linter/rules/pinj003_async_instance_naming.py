"""PINJ003: Async instance naming rule."""

import ast

from ..models import Fix, Position, RuleContext, Severity
from ..utils.ast_utils import has_decorator
from .base import ASTRuleBase, BaseNodeVisitor


class PINJ003Visitor(BaseNodeVisitor):
    """Visitor for checking async instance naming."""
    
    def visit_AsyncFunctionDef(self, node):
        """Check async function definitions."""
        if has_decorator(node, "instance") and node.name.startswith("a_"):
                fix = self._create_fix(node)
                self.add_violation(
                    node,
                    f"Async @instance function '{node.name}' should not have 'a_' prefix. "
                    f"The 'a_' prefix is only for @injected functions.",
                    suggestion=f"Consider renaming to '{node.name[2:]}'",
                    fix=fix,
                )
        self.generic_visit(node)
    
    def _create_fix(self, node: ast.AsyncFunctionDef) -> Fix:
        """Create a fix to remove the 'a_' prefix."""
        old_name = node.name
        new_name = old_name[2:]  # Remove 'a_' prefix
        
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
            description=f"Remove 'a_' prefix from '{old_name}'",
        )


class PINJ003AsyncInstanceNaming(ASTRuleBase):
    """Rule for checking async instance naming convention."""
    
    rule_id = "PINJ003"
    name = "Async instance naming"
    description = "Async @instance functions should NOT have 'a_' prefix"
    severity = Severity.ERROR
    category = "naming"
    auto_fixable = True
    
    def get_visitor(self, context: RuleContext) -> ast.NodeVisitor:
        """Get the AST visitor for this rule."""
        return PINJ003Visitor(self, context)