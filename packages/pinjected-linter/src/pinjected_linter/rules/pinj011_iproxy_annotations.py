"""PINJ011: IProxy type annotations rule."""

import ast

from ..models import RuleContext, Severity
from ..utils.ast_utils import has_decorator
from .base import ASTRuleBase, BaseNodeVisitor


class PINJ011Visitor(BaseNodeVisitor):
    """Visitor for checking IProxy type annotations."""

    def __init__(self, rule, context):
        super().__init__(rule, context)
        self.has_iproxy_import = False
        self.iproxy_alias = None

    def visit_ImportFrom(self, node):
        """Track IProxy imports."""
        if node.module == "pinjected":
            for alias in node.names:
                if alias.name == "IProxy":
                    self.has_iproxy_import = True
                    self.iproxy_alias = alias.asname or "IProxy"
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """Check function definitions."""
        self._check_function(node)

    def visit_AsyncFunctionDef(self, node):
        """Check async function definitions."""
        self._check_function(node)

    def _check_function(self, node):
        """Check function for IProxy usage patterns."""
        # Check if this is an @injected function
        if has_decorator(node, "injected"):
            self._check_injected_function(node)
        # Check if this is an @instance function
        elif has_decorator(node, "instance"):
            self._check_instance_function(node)

        self.generic_visit(node)

    def _check_injected_function(self, node):
        """Check @injected functions for IProxy usage."""
        # In Python AST, positional-only args (before /) are in posonlyargs
        # Regular args (after /) are in args

        if not node.args.posonlyargs:
            # No positional-only args means no dependencies (no slash or slash at beginning)
            return

        # Check injected parameters (positional-only args before slash)
        for arg in node.args.posonlyargs:
            annotation = arg.annotation

            # Check if the parameter looks like a dependency that should use IProxy
            if self._should_use_iproxy(arg.arg, annotation):
                self.add_violation(
                    arg,
                    f"Parameter '{arg.arg}' in @injected function '{node.name}' should use IProxy[T] annotation. "
                    f"Dependencies that are injected should be typed with IProxy for proper type checking.",
                    suggestion=f"Change type annotation to IProxy[{self._get_inner_type(annotation)}]",
                )

    def _check_instance_function(self, node):
        """Check @instance function return types."""
        # @instance functions that provide entry points should return IProxy
        return_annotation = node.returns

        if (
            return_annotation
            and self._is_service_type(return_annotation)
            and not self._is_iproxy_annotation(return_annotation)
        ):
            self.add_violation(
                node,
                f"@instance function '{node.name}' returns a service type but doesn't use IProxy. "
                f"Entry point services should return IProxy[T] for proper dependency tracking.",
                suggestion=f"Change return type to IProxy[{self._get_annotation_string(return_annotation)}]",
            )

    def _should_use_iproxy(self, param_name: str, annotation) -> bool:
        """Check if a parameter should use IProxy based on naming and type."""
        # Skip if already using IProxy
        if annotation and self._is_iproxy_annotation(annotation):
            return False

        # Only suggest IProxy if there's a type annotation that looks like a service
        if not annotation:
            return False

        # Check type annotation
        annotation_str = self._get_annotation_string(annotation)

        # Service type patterns in annotations
        service_patterns = [
            "Service",
            "Client",
            "Repository",
            "Manager",
            "Factory",
            "Provider",
            "Handler",
            "Processor",
            "Validator",
            "Logger",
            "Database",
            "Cache",
            "Gateway",
            "Controller",
        ]

        # Check if the annotation looks like a service type
        return any(pattern in annotation_str for pattern in service_patterns)

    def _is_service_type(self, annotation) -> bool:
        """Check if the type looks like a service/component."""
        if not annotation:
            return False

        annotation_str = self._get_annotation_string(annotation)
        service_patterns = [
            "Service",
            "Client",
            "Repository",
            "Manager",
            "Handler",
            "Controller",
            "Gateway",
            "Adapter",
            "Provider",
        ]

        return any(pattern in annotation_str for pattern in service_patterns)

    def _is_iproxy_annotation(self, annotation) -> bool:
        """Check if the annotation is IProxy[T] or just IProxy."""
        if isinstance(annotation, ast.Name):
            # Check for bare IProxy
            return annotation.id == (self.iproxy_alias or "IProxy")
        elif isinstance(annotation, ast.Subscript) and isinstance(
            annotation.value, ast.Name
        ):
            return annotation.value.id == (self.iproxy_alias or "IProxy")
        return False

    def _get_annotation_string(self, annotation) -> str:
        """Get string representation of annotation."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Subscript):
            return self._get_annotation_string(annotation.value)
        elif isinstance(annotation, ast.Attribute):
            value = self._get_annotation_string(annotation.value)
            return f"{value}.{annotation.attr}"
        return "Any"

    def _get_inner_type(self, annotation) -> str:
        """Get the inner type for IProxy suggestion."""
        if annotation:
            return self._get_annotation_string(annotation)
        return "Any"


class PINJ011IProxyAnnotations(ASTRuleBase):
    """Rule for checking IProxy type annotations.

    IProxy[T] should be used for:
    1. Type annotations of injected dependencies in @injected functions
    2. Return types of @instance functions that provide entry points
    3. References to dependencies that are resolved through injection

    This helps with:
    - Type safety in dependency injection
    - Clear distinction between injected and runtime values
    - Better IDE support and type checking
    """

    rule_id = "PINJ011"
    name = "IProxy type annotations"
    description = "Dependencies should use IProxy[T] type annotations"
    severity = Severity.WARNING
    category = "typing"
    auto_fixable = False  # Type changes require careful consideration

    def get_visitor(self, context: RuleContext) -> ast.NodeVisitor:
        """Get the AST visitor for this rule."""
        return PINJ011Visitor(self, context)
