"""Base class for linter rules."""

import ast
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..models import Fix, RuleContext, Severity, Violation


class BaseRule(ABC):
    """Base class for all linter rules."""
    
    # These should be overridden by subclasses
    rule_id: str = ""
    name: str = ""
    description: str = ""
    severity: Severity = Severity.ERROR
    category: str = "general"
    auto_fixable: bool = False
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize rule with configuration."""
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
    
    @abstractmethod
    def check(self, context: RuleContext) -> List[Violation]:
        """Check for violations of this rule.
        
        Args:
            context: The rule context containing AST, symbol table, etc.
            
        Returns:
            List of violations found
        """
        pass
    
    def is_enabled(self) -> bool:
        """Check if this rule is enabled."""
        return self.enabled
    
    def get_severity(self) -> Severity:
        """Get the severity level for this rule."""
        # Allow override from config
        severity_str = self.config.get("severity", self.severity.value)
        try:
            return Severity(severity_str)
        except ValueError:
            return self.severity
    
    def can_fix(self, violation: Violation) -> bool:
        """Check if this violation can be auto-fixed."""
        return self.auto_fixable and violation.fix is not None
    
    def generate_fix(self, violation: Violation, source: str) -> Optional[Fix]:
        """Generate a fix for the violation.
        
        Default implementation returns None. Override in subclasses
        that support auto-fixing.
        """
        return None
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(rule_id={self.rule_id})"


class ASTRuleBase(BaseRule):
    """Base class for rules that use AST node visitors."""
    
    def check(self, context: RuleContext) -> List[Violation]:
        """Check for violations by visiting AST nodes."""
        visitor = self.get_visitor(context)
        visitor.visit(context.tree)
        return visitor.violations
    
    @abstractmethod
    def get_visitor(self, context: RuleContext) -> ast.NodeVisitor:
        """Get the AST node visitor for this rule.
        
        The visitor should have a 'violations' attribute that collects
        Violation objects.
        """
        pass


class BaseNodeVisitor(ast.NodeVisitor):
    """Base AST node visitor that collects violations."""
    
    def __init__(self, rule: BaseRule, context: RuleContext):
        self.rule = rule
        self.context = context
        self.violations: List[Violation] = []
    
    def add_violation(
        self,
        node: ast.AST,
        message: str,
        suggestion: Optional[str] = None,
        fix: Optional[Fix] = None,
    ):
        """Add a violation for the given node."""
        from ..models import Position
        
        position = Position(
            line=node.lineno if hasattr(node, "lineno") else 0,
            column=node.col_offset if hasattr(node, "col_offset") else 0,
            end_line=node.end_lineno if hasattr(node, "end_lineno") else None,
            end_column=node.end_col_offset if hasattr(node, "end_col_offset") else None,
        )
        
        violation = Violation(
            rule_id=self.rule.rule_id,
            message=message,
            file_path=self.context.file_path,
            position=position,
            severity=self.rule.get_severity(),
            suggestion=suggestion,
            fix=fix,
            source_line=self.context.get_line(node),
        )
        
        self.violations.append(violation)