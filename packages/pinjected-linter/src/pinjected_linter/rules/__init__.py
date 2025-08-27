"""Linter rules for Pinjected."""

from .base import ASTRuleBase, BaseNodeVisitor, BaseRule

# Note: Python rule implementations have been moved to Rust
# This package now serves as the dynamic linter infrastructure

# Rule registry (empty for now as rules are implemented in Rust)
RULE_CLASSES = []

RULES_BY_ID = {}

__all__ = [
    "RULES_BY_ID",
    "RULE_CLASSES",
    "ASTRuleBase",
    "BaseNodeVisitor",
    "BaseRule",
]
