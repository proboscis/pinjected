"""PINJ006: Instance function side effects rule."""

import ast
from typing import ClassVar, Set

from ..models import RuleContext, Severity
from ..utils.ast_utils import has_decorator
from .base import ASTRuleBase, BaseNodeVisitor


class PINJ006Visitor(BaseNodeVisitor):
    """Visitor for checking side effects in @instance functions."""

    # Functions/methods that typically cause side effects
    SIDE_EFFECT_FUNCTIONS: ClassVar[Set[str]] = {
        # File I/O
        "open",
        "write",
        "read",
        "close",
        # Print/logging
        "print",
        "pprint",
        # OS operations
        "os.system",
        "os.popen",
        "os.remove",
        "os.mkdir",
        "os.makedirs",
        "os.rmdir",
        "os.rename",
        "os.environ",
        # Subprocess
        "subprocess.run",
        "subprocess.call",
        "subprocess.Popen",
        # Network
        "requests.get",
        "requests.post",
        "requests.put",
        "requests.delete",
        "urllib.request.urlopen",
        "socket.socket",
        # Database
        "connect",
        "execute",
        "commit",
        "rollback",
        # Global state
        "globals",
        "locals",
        "setattr",
        "delattr",
    }

    # Modules that typically involve side effects
    SIDE_EFFECT_MODULES: ClassVar[Set[str]] = {
        "requests",
        "urllib",
        "urllib2",
        "urllib3",
        "httpx",
        "aiohttp",
        "socket",
        "subprocess",
        "shutil",
        "tempfile",
        "sqlite3",
        "psycopg2",
        "pymongo",
        "redis",
    }

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

    def visit_Call(self, node):
        """Check function calls for side effects."""
        if not self.inside_instance:
            self.generic_visit(node)
            return

        func_name = self._get_call_name(node)
        self._check_for_side_effects(node, func_name)
        self.generic_visit(node)

    def _check_for_side_effects(self, node, func_name):
        """Check if the function call has side effects."""
        # Check for known side effect functions
        if func_name in self.SIDE_EFFECT_FUNCTIONS:
            operation = "print statement" if func_name == "print" else func_name
            if func_name == "open":
                operation = "file I/O operation"
            self._add_side_effect_violation(node, operation)
        # Check for logging
        elif self._is_logging_call(func_name):
            self._add_side_effect_violation(node, "logging operation")
        # Check for module-based side effects
        elif any(module in func_name for module in self.SIDE_EFFECT_MODULES):
            self._add_side_effect_violation(node, f"call to {func_name}")

    def visit_With(self, node):
        """Check with statements (often used for file I/O)."""
        if self.inside_instance:
            # Check if it's a file open
            for item in node.items:
                if isinstance(item.context_expr, ast.Call):
                    func_name = self._get_call_name(item.context_expr)
                    if func_name == "open":
                        self._add_side_effect_violation(
                            node, "file I/O with 'with open(...)'"
                        )
        self.generic_visit(node)

    def visit_Attribute(self, node):
        """Check attribute access for environment variables."""
        if self.inside_instance and (
            isinstance(node.value, ast.Name)
            and node.value.id == "os"
            and node.attr == "environ"
        ):
            self._add_side_effect_violation(node, "environment variable access")
        self.generic_visit(node)

    def _get_call_name(self, node) -> str:
        """Extract the name of the called function."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return ""

    def _is_logging_call(self, func_name: str) -> bool:
        """Check if the function call is a logging operation."""
        logging_patterns = [
            "logger.",
            "logging.",
            "log.",
            ".debug",
            ".info",
            ".warning",
            ".error",
            ".critical",
        ]
        return any(pattern in func_name for pattern in logging_patterns)

    def _add_side_effect_violation(self, node, operation: str):
        """Add a side effect violation."""
        self.add_violation(
            node,
            f"@instance function '{self.current_function}' contains {operation}. "
            f"@instance functions should be pure providers without side effects.",
            suggestion="Move side effects to @injected functions or regular methods",
        )


class PINJ006InstanceSideEffects(ASTRuleBase):
    """Rule for checking side effects in @instance functions.

    @instance functions should be pure providers that only construct and
    return objects. They should not have side effects such as:
    - File I/O operations
    - Network calls
    - Database operations
    - Print statements
    - Logging operations
    - Environment variable access
    - Global state modifications

    These operations should be done in @injected functions or regular methods.
    """

    rule_id = "PINJ006"
    name = "Instance function side effects"
    description = "@instance functions should not have side effects"
    severity = Severity.ERROR
    category = "purity"
    auto_fixable = False  # Side effects require manual refactoring

    def get_visitor(self, context: RuleContext) -> ast.NodeVisitor:
        """Get the AST visitor for this rule."""
        return PINJ006Visitor(self, context)
