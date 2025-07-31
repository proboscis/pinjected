#!/usr/bin/env python3
"""
Example of integrating the Rust linter with Python code.
This can be used in pre-commit hooks or build scripts.
"""

import json
import subprocess
import sys
from typing import Any, Dict, List


def run_rust_linter(
    path: str,
    rule: str | None = None,
    cache: bool = True,
    threads: int | None = None,
    skip_patterns: List[str] | None = None,
) -> Dict[str, Any]:
    """Run the Rust pinjected linter and parse results."""

    # Build command
    cmd = ["./target/release/pinjected-linter-rust", path]

    if rule:
        cmd.extend(["--rule", rule])

    if cache:
        cmd.append("--cache")

    if threads:
        cmd.extend(["-j", str(threads)])

    if skip_patterns:
        for pattern in skip_patterns:
            cmd.extend(["--skip", pattern])

    # Add timing to get stats
    cmd.append("--timing")

    # Run linter
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Parse output
    violations = []
    stats = {}

    for line in result.stdout.splitlines():
        if line.startswith("/") and ":" in line:
            # Parse violation line
            parts = line.split(":", 4)
            if len(parts) >= 5:
                violations.append(
                    {
                        "file": parts[0],
                        "line": int(parts[1]),
                        "column": int(parts[2]),
                        "rule": parts[3].strip(),
                        "message": parts[4].strip(),
                    }
                )
        elif "Analyzed" in line and "files in" in line:
            # Parse stats
            parts = line.split()
            stats["files_analyzed"] = int(parts[1])
            stats["time_seconds"] = float(parts[4].rstrip("s"))
        elif "Files/second:" in line:
            stats["files_per_second"] = float(line.split(":")[1].strip())

    return {
        "success": result.returncode == 0,
        "violations": violations,
        "stats": stats,
        "stderr": result.stderr,
    }


def main():
    """Example usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Python wrapper for Rust pinjected linter"
    )
    parser.add_argument("path", help="Path to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    # Run linter
    result = run_rust_linter(
        args.path, cache=True, skip_patterns=["test_", "__pycache__", ".venv"]
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        # Pretty print results
        if result["violations"]:
            print(f"Found {len(result['violations'])} violations:")
            for v in result["violations"]:
                print(
                    f"  {v['file']}:{v['line']}:{v['column']} {v['rule']}: {v['message']}"
                )
        else:
            print("✓ No issues found!")

        if result["stats"]:
            print(
                f"\nAnalyzed {result['stats']['files_analyzed']} files in {result['stats']['time_seconds']:.2f}s"
            )
            print(f"Speed: {result['stats']['files_per_second']:.0f} files/second")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
