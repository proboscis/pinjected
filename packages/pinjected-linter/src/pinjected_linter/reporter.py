"""Reporter classes for formatting linter output."""

import json
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import ClassVar, List

from rich.console import Console

from .models import Severity, Violation


class OutputFormatter(ABC):
    """Base class for output formatters."""

    @abstractmethod
    def format(self, violations: List[Violation]) -> str:
        """Format violations for output."""
        pass


class TerminalFormatter(OutputFormatter):
    """Rich terminal output with colors and formatting."""

    def __init__(self, show_source: bool = True, color: bool = True):
        self.show_source = show_source
        self.console = Console(color_system="auto" if color else None)

    def format(self, violations: List[Violation]) -> str:
        """Format violations for terminal output."""
        if not violations:
            return "[green]✓ No issues found![/green]"

        # Group by file
        by_file = defaultdict(list)
        for violation in violations:
            by_file[violation.file_path].append(violation)

        output_parts = []

        for file_path, file_violations in by_file.items():
            output_parts.append(f"\n[bold]{file_path}[/bold]")

            for violation in sorted(file_violations, key=lambda v: (v.line, v.column)):
                output_parts.append(self._format_violation(violation))

        # Summary
        error_count = sum(1 for v in violations if v.severity == Severity.ERROR)
        warning_count = sum(1 for v in violations if v.severity == Severity.WARNING)
        info_count = sum(1 for v in violations if v.severity == Severity.INFO)

        output_parts.append("\n[bold]Summary:[/bold]")
        output_parts.append(f"  [red]Errors: {error_count}[/red]")
        output_parts.append(f"  [yellow]Warnings: {warning_count}[/yellow]")
        output_parts.append(f"  [blue]Info: {info_count}[/blue]")

        # Add help message for rule documentation
        output_parts.append(
            "\n[dim]💡 Use --show-rule-doc <RULE_ID> for detailed rule information and examples[/dim]"
        )
        output_parts.append(
            "[dim]   Example: pinjected-dynamic-linter --show-rule-doc PINJ001[/dim]"
        )

        return "\n".join(output_parts)

    def _format_violation(self, violation: Violation) -> str:
        """Format a single violation."""
        severity_color = {
            Severity.ERROR: "red",
            Severity.WARNING: "yellow",
            Severity.INFO: "blue",
        }[violation.severity]

        lines = []

        # Main violation line
        location = f"{violation.line}:{violation.column}"
        lines.append(
            f"  [{severity_color}]{location:>8}[/{severity_color}] "
            f"[bold]{violation.rule_id}[/bold] {violation.message}"
        )

        # Source line if requested
        if self.show_source and violation.source_line:
            lines.append(f"  {violation.line:>8} | {violation.source_line.rstrip()}")
            # Pointer to column
            spaces = " " * (len(str(violation.line)) + violation.column + 11)
            lines.append(f"{spaces}^")

        # Suggestion if available
        if violation.suggestion:
            lines.append(f"           [dim]💡 {violation.suggestion}[/dim]")

        return "\n".join(lines)


class JSONFormatter(OutputFormatter):
    """JSON output for programmatic consumption."""

    def format(self, violations: List[Violation]) -> str:
        """Format violations as JSON."""
        data = {
            "violations": [v.to_dict() for v in violations],
            "summary": {
                "total": len(violations),
                "errors": sum(1 for v in violations if v.severity == Severity.ERROR),
                "warnings": sum(
                    1 for v in violations if v.severity == Severity.WARNING
                ),
                "info": sum(1 for v in violations if v.severity == Severity.INFO),
                "fixable": sum(1 for v in violations if v.fix is not None),
            },
        }
        return json.dumps(data, indent=2)


class GitHubFormatter(OutputFormatter):
    """GitHub Actions annotation format."""

    def format(self, violations: List[Violation]) -> str:
        """Format violations for GitHub Actions."""
        lines = []
        for v in violations:
            level = {
                Severity.ERROR: "error",
                Severity.WARNING: "warning",
                Severity.INFO: "notice",
            }[v.severity]

            # GitHub annotation format
            lines.append(
                f"::{level} file={v.file_path},line={v.line},col={v.column}::"
                f"{v.rule_id}: {v.message}"
            )
        return "\n".join(lines)


class Reporter:
    """Main reporter class that handles different output formats."""

    FORMATTERS: ClassVar[dict[str, type[OutputFormatter]]] = {
        "terminal": TerminalFormatter,
        "json": JSONFormatter,
        "github": GitHubFormatter,
    }

    def __init__(self, output_format: str = "terminal", **kwargs):
        """Initialize reporter with specified format."""
        formatter_class = self.FORMATTERS.get(output_format, TerminalFormatter)

        # Only pass kwargs to formatters that accept them
        if formatter_class == TerminalFormatter:
            self.formatter = formatter_class(**kwargs)
        else:
            self.formatter = formatter_class()

    def report(self, violations: List[Violation]) -> str:
        """Report violations in the configured format."""
        return self.formatter.format(violations)

    def print_report(self, violations: List[Violation]):
        """Print violations to console."""
        output = self.report(violations)
        if isinstance(self.formatter, TerminalFormatter):
            self.formatter.console.print(output)
        else:
            print(output)
