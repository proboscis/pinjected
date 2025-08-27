"""Main analyzer for Pinjected linter.

This module serves as a compatibility layer. All analysis is now done by the Rust implementation.
Use the Rust CLI directly for best performance: pinjected-linter [paths...]
"""

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import Position, Severity, Violation


class SymbolTableBuilder:
    """Placeholder for compatibility - actual implementation in Rust."""
    
    def __init__(self):
        self.imports = {}
        self.functions = {}
        self.classes = {}
    
    def visit(self, node):
        """Placeholder visit method."""
        pass


class PinjectedAnalyzer:
    """Main analyzer for Pinjected code - now delegates to Rust implementation."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        parallel: bool = True,
    ):
        """Initialize analyzer.

        Args:
            config: Configuration dictionary
            parallel: Whether to use parallel processing
        """
        self.config = config or {}
        self.parallel = parallel

    def analyze_file(self, file_path: Path) -> List[Violation]:
        """Analyze a single Python file using Rust linter.

        Args:
            file_path: Path to the file to analyze

        Returns:
            List of violations found
        """
        return self.analyze_files([file_path])

    def analyze_files(self, file_paths: List[Path]) -> List[Violation]:
        """Analyze multiple Python files using Rust linter.

        Args:
            file_paths: List of file paths to analyze

        Returns:
            List of all violations found
        """
        if not file_paths:
            return []

        # Build command for Rust linter
        cmd = ["pinjected-linter", "--output-format", "json"]

        # Add config options
        if "disable" in self.config:
            for rule_id in self.config["disable"]:
                cmd.extend(["--disable", rule_id])

        if "enable" in self.config:
            for rule_id in self.config["enable"]:
                cmd.extend(["--enable", rule_id])

        if not self.parallel:
            cmd.append("--no-parallel")

        # Add file paths
        cmd.extend(str(p) for p in file_paths)

        try:
            # Run Rust linter
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode not in (0, 1):  # 0 = no violations, 1 = violations found
                print(f"Error running pinjected-linter: {result.stderr}", file=sys.stderr)
                return []

            # Parse JSON output
            import json
            output = json.loads(result.stdout)

            violations = []
            for v in output.get("violations", []):
                violation = Violation(
                    rule_id=v["rule"],
                    message=v["message"],
                    file_path=Path(v["file"]),
                    position=Position(
                        line=v["line"],
                        column=v["column"]
                    ),
                    severity=getattr(Severity, v["severity"].upper()),
                )
                violations.append(violation)

            return violations

        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError) as e:
            print(f"Error running Rust linter: {e}", file=sys.stderr)
            return []
