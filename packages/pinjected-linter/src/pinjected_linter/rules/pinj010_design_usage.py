"""PINJ010: Design() usage patterns rule."""

import ast
from typing import Optional

from ..models import RuleContext, Severity
from .base import ASTRuleBase, BaseNodeVisitor


class PINJ010Visitor(BaseNodeVisitor):
    """Visitor for checking Design() usage patterns."""

    def __init__(self, rule, context):
        super().__init__(rule, context)
        self.has_design_import = False
        self.design_alias = None
        self.has_design_func_import = False
        self.design_func_alias = None

    def visit_ImportFrom(self, node):
        """Track Design and design imports."""
        if node.module == "pinjected":
            for alias in node.names:
                if alias.name == "Design":
                    self.has_design_import = True
                    self.design_alias = alias.asname or "Design"
                elif alias.name == "design":
                    self.has_design_func_import = True
                    self.design_func_alias = alias.asname or "design"
        self.generic_visit(node)

    def visit_Call(self, node):
        """Check Design() instantiation patterns."""
        if self._is_design_call(node):
            self._check_design_usage(node)
        self.generic_visit(node)

    def _is_design_call(self, node) -> bool:
        """Check if this is a Design() or design() call."""
        if isinstance(node.func, ast.Name):
            # Check for Design class
            if node.func.id == (self.design_alias or "Design"):
                return True
            # Check for design function
            if node.func.id == (self.design_func_alias or "design"):
                return True
        return False

    def _check_design_usage(self, node):
        """Check specific Design()/design() usage patterns."""
        # Rule 1: Design()/design() should not be empty
        if not node.args and not node.keywords:
            func_name = "Design()" if isinstance(node.func, ast.Name) and node.func.id in (self.design_alias or "Design", "Design") else "design()"
            self.add_violation(
                node,
                f"Empty {func_name} instantiation. Design should contain configuration or overrides.",
                suggestion="Add configuration parameters or remove if not needed",
            )
            return

        # Rule 2: Check for proper keyword usage
        self._check_keywords(node)

        # Rule 3: Check for mixing with non-Design patterns
        self._check_combination_patterns(node)

    def _check_keywords(self, node):
        """Check keyword arguments in Design()."""
        for keyword in node.keywords:
            if keyword.arg is None:
                # This is **kwargs expansion
                continue

            # Check for common misuse patterns
            if keyword.arg in ["injected", "instance", "provider"]:
                self.add_violation(
                    keyword,
                    f"Design/design parameter '{keyword.arg}' looks like a decorator name. "
                    f"Design should map dependency names to their providers.",
                    suggestion="Use dependency names as keys, not decorator names",
                )

            # Check for direct instance calls as values
            self._check_instance_calls(keyword)

    def _check_instance_calls(self, keyword):
        """Check if keyword value is a direct instance call."""
        if isinstance(keyword.value, ast.Call):
            func_name = self._get_call_name(keyword.value)
            if (
                func_name
                and not func_name.startswith(("lambda", "_"))
                and self._looks_like_instance_call(func_name)
            ):
                self.add_violation(
                    keyword.value,
                    f"Design/design appears to directly call @instance function '{func_name}'. "
                    f"Design should reference functions, not call them.",
                    suggestion=f"Use '{keyword.arg}': {func_name} instead of '{keyword.arg}': {func_name}()",
                )

    def _check_combination_patterns(self, node):
        """Check Design() combination patterns."""
        parent = self._get_parent_node(node)
        if (
            isinstance(parent, ast.BinOp)
            and isinstance(parent.op, ast.Add)
            and not (
                self._is_design_node(parent.left) and self._is_design_node(parent.right)
            )
        ):
            self.add_violation(
                node,
                "Design/design should only be combined with other Design/design instances using +",
                suggestion="Use Design() + Design() or design() + design() for combining designs",
            )

    def _get_call_name(self, node) -> Optional[str]:
        """Extract the name of the called function."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None

    def _looks_like_instance_call(self, name: str) -> bool:
        """Check if the name looks like an @instance function."""
        # Common patterns for instance functions
        instance_patterns = [
            "_provider",
            "_factory",
            "_service",
            "_client",
            "_repository",
            "_manager",
            "_handler",
            "_instance",
        ]
        return any(name.endswith(pattern) for pattern in instance_patterns)

    def _is_design_node(self, node) -> bool:
        """Check if a node is a Design-related expression."""
        if isinstance(node, ast.Call):
            return self._is_design_call(node)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            # Recursive check for Design() + Design()
            return self._is_design_node(node.left) or self._is_design_node(node.right)
        return False

    def _get_parent_node(self, node):
        """Get the parent node (simplified version)."""
        # In a real implementation, we'd track parent nodes during traversal
        # For now, this is a placeholder
        return None


class PINJ010DesignUsage(ASTRuleBase):
    """Rule for checking Design() usage patterns.

    Design() class and design() function are used to configure and override
    dependencies in Pinjected. Common issues include:
    1. Empty Design()/design() with no configuration
    2. Calling @instance functions instead of referencing them
    3. Using decorator names as keys instead of dependency names
    4. Incorrect combination patterns

    Good:
        # Using Design class
        config1 = Design(
            database=database_provider,
            logger=logger_instance,
            config=lambda: {"debug": True}
        )
        
        # Using design function
        config2 = design(
            database=database_provider,
            cache=cache_provider
        )

    Bad:
        empty1 = Design()  # Empty
        empty2 = design()  # Empty
        bad1 = Design(instance=database_provider)  # Wrong key name
        bad2 = design(database=database_provider())  # Calling instead of referencing
    """

    rule_id = "PINJ010"
    name = "Design() usage patterns"
    description = "Design()/design() should be used correctly for dependency configuration"
    severity = Severity.WARNING
    category = "usage"
    auto_fixable = False  # Usage patterns require manual review

    def get_visitor(self, context: RuleContext) -> ast.NodeVisitor:
        """Get the AST visitor for this rule."""
        return PINJ010Visitor(self, context)
