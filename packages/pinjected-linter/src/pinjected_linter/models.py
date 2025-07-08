"""Core data models for the Pinjected linter."""

import ast
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .utils.symbol_table import SymbolTable


class Severity(Enum):
    """Severity levels for violations."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Position:
    """Position in source code."""

    line: int
    column: int
    end_line: Optional[int] = None
    end_column: Optional[int] = None


@dataclass
class Fix:
    """Represents a fix that can be applied to source code."""

    start_pos: Position
    end_pos: Position
    replacement: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "start_line": self.start_pos.line,
            "start_column": self.start_pos.column,
            "end_line": self.end_pos.line,
            "end_column": self.end_pos.column,
            "replacement": self.replacement,
            "description": self.description,
        }


@dataclass
class Violation:
    """Represents a linting violation."""

    rule_id: str
    message: str
    file_path: Path
    position: Position
    severity: Severity
    suggestion: Optional[str] = None
    fix: Optional[Fix] = None
    source_line: Optional[str] = None

    @property
    def line(self) -> int:
        """Line number for backwards compatibility."""
        return self.position.line

    @property
    def column(self) -> int:
        """Column number for backwards compatibility."""
        return self.position.column

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "rule_id": self.rule_id,
            "message": self.message,
            "file": str(self.file_path),
            "line": self.line,
            "column": self.column,
            "severity": self.severity.value,
            "suggestion": self.suggestion,
            "fix": self.fix.to_dict() if self.fix else None,
            "source_line": self.source_line,
        }


@dataclass
class FunctionInfo:
    """Information about a function definition."""

    name: str
    node: ast.FunctionDef
    decorators: List[str]
    is_instance: bool = False
    is_injected: bool = False
    is_async: bool = False
    is_test: bool = False
    has_slash: bool = False
    slash_index: Optional[int] = None

    @property
    def is_decorated(self) -> bool:
        """Check if function has any Pinjected decorators."""
        return self.is_instance or self.is_injected


@dataclass
class RuleContext:
    """Context passed to rules for checking."""

    file_path: Path
    source: str
    tree: ast.AST
    symbol_table: "SymbolTable"
    config: Dict[str, Any]

    def get_line(self, node: ast.AST) -> str:
        """Get source line for a node."""
        if hasattr(node, "lineno"):
            lines = self.source.splitlines()
            if 0 < node.lineno <= len(lines):
                return lines[node.lineno - 1]
        return ""
