"""Command-line interface for Pinjected linter."""

import sys
from pathlib import Path
from typing import List, Optional

import click
from loguru import logger

from .analyzer import PinjectedAnalyzer
from .models import Severity
from .reporter import Reporter

# Configure logger to not output to stderr unless verbose
logger.remove()  # Remove default handler


def show_configuration_docs():
    """Display configuration documentation for pyproject.toml."""
    docs = """
Pinjected Linter Configuration Documentation
============================================

The pinjected linter can be configured in your pyproject.toml file under the
[tool.pinjected-linter] section.

Example Configuration:
----------------------

[tool.pinjected-linter]
# Enable specific rules (if not specified, all rules are enabled)
enable = [
    "PINJ001",  # Instance naming convention
    "PINJ002",  # Instance defaults
    "PINJ003",  # Async instance naming
    # ... add more rules as needed
]

# Or disable specific rules
disable = ["PINJ001", "PINJ005"]

# Configure specific rules
[tool.pinjected-linter.rules.PINJ014]
min_injected_functions = 3
stub_search_paths = ["stubs", "typings", "types"]
ignore_patterns = ["**/tests/**", "**/test_*.py"]

# Exclude paths from linting
exclude = [".venv", "venv", ".git", "__pycache__", "build", "dist"]

# Additional configuration options
max_line_length = 120
check_docstrings = true

Available Rules:
----------------
- PINJ001: Instance naming convention (@instance functions should be nouns)
- PINJ002: Instance defaults (check default parameter usage)
- PINJ003: Async instance naming (a_ prefix for async @instance)
- PINJ004: Direct instance call (avoid calling @instance functions directly)
- PINJ005: Injected function naming (should be verbs/actions)
- PINJ006: Async injected naming (a_ prefix for async @injected)
- PINJ007: Slash separator position (proper / placement)
- PINJ008: Injected dependency declaration (dependencies before /)
- PINJ009: No await in injected (except for declared dependencies)
- PINJ010: Design usage (proper design() function usage)
- PINJ011: IProxy annotations (not for injected dependencies)
- PINJ012: Dependency cycles detection
- PINJ013: Builtin shadowing (avoid shadowing builtins)
- PINJ014: Missing stub file (.pyi for @injected functions)
- PINJ015: Missing slash (require / in @injected functions)

Configuration Precedence:
-------------------------
1. Command line options (--enable, --disable) override all
2. Explicit config file specified with --config
3. pyproject.toml [tool.pinjected-linter] section
4. Default configuration (all rules enabled)

For more information, visit: https://github.com/pinjected/pinjected
"""
    click.echo(docs)


def show_rule_documentation(rule_id: str):
    """Display documentation for a specific rule."""
    # Normalize rule ID (ensure uppercase and remove any leading/trailing whitespace)
    rule_id = rule_id.strip().upper()

    # Try multiple possible locations for documentation
    possible_locations = [
        # Installed package location
        Path(__file__).parent.parent / "docs" / "rules",
        # Development source location
        Path(__file__).parent.parent.parent.parent / "docs" / "rules",
        # Relative to the current working directory
        Path.cwd() / "packages" / "pinjected-linter" / "docs" / "rules",
        # Direct path from repo root
        Path.cwd() / "docs" / "rules",
    ]

    doc_file = None
    for rule_docs_dir in possible_locations:
        if rule_docs_dir.exists():
            doc_files = list(rule_docs_dir.glob(f"{rule_id.lower()}_*.md"))
            if doc_files:
                doc_file = doc_files[0]
                break

    if not doc_file:
        click.echo(f"Error: No documentation found for rule {rule_id}", err=True)
        click.echo("Use --show-config-docs to see available rules.", err=True)
        sys.exit(1)

    # Read and display the documentation
    try:
        with open(doc_file, encoding="utf-8") as f:
            content = f.read()
        click.echo(content)
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error reading documentation: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration file (.pinjected-linter.toml)",
)
@click.option(
    "--output-format",
    "-f",
    type=click.Choice(["terminal", "json", "github"]),
    default="terminal",
    help="Output format",
)
@click.option(
    "--disable",
    "-d",
    multiple=True,
    help="Disable specific rules (can be used multiple times)",
)
@click.option(
    "--enable",
    "-e",
    multiple=True,
    help="Enable only specific rules (can be used multiple times)",
)
@click.option(
    "--no-parallel",
    is_flag=True,
    help="Disable parallel processing",
)
@click.option(
    "--show-source/--no-show-source",
    default=True,
    help="Show source code in violations",
)
@click.option(
    "--color/--no-color",
    default=True,
    help="Enable/disable colored output",
)
@click.option(
    "--severity",
    "-s",
    type=click.Choice(["error", "warning", "info"]),
    help="Minimum severity level to report",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
@click.option(
    "--show-config-docs",
    is_flag=True,
    help="Show documentation for pyproject.toml configuration",
)
@click.option(
    "--show-rule-doc",
    type=str,
    help="Show detailed documentation for a specific rule (e.g., PINJ001)",
)
def main(
    paths: tuple,
    config: Optional[str],
    output_format: str,
    disable: tuple,
    enable: tuple,
    no_parallel: bool,
    show_source: bool,
    color: bool,
    severity: Optional[str],
    verbose: bool,
    show_config_docs: bool,
    show_rule_doc: Optional[str],
):
    """Pinjected linter - Check your code for Pinjected best practices.

    If no paths are provided, the current directory is checked recursively.
    """
    # Show configuration documentation if requested
    if show_config_docs:
        show_configuration_docs()
        return

    # Show rule documentation if requested
    if show_rule_doc:
        show_rule_documentation(show_rule_doc)
        return

    # Configure logging based on verbose flag
    if verbose:
        logger.add(sys.stderr, level="INFO")
        logger.info("Starting Pinjected linter")

    # Build configuration
    # Always try to load config, even if no explicit path provided
    config_dict = load_config(config)

    # Get exclude patterns from config
    exclude_patterns = config_dict.get("exclude", [])

    # Collect Python files
    file_paths = collect_python_files(paths or ["."], exclude_patterns=exclude_patterns)
    if not file_paths:
        logger.warning("No Python files found")
        return

    if verbose:
        logger.info(f"Found {len(file_paths)} Python files to analyze")

    # Apply CLI overrides
    if disable:
        config_dict["disable"] = list(disable)
    if enable:
        config_dict["enable"] = list(enable)

    # Create analyzer
    analyzer = PinjectedAnalyzer(
        config=config_dict,
        parallel=not no_parallel,
    )

    # Analyze files
    if verbose:
        logger.info("Analyzing files...")
    violations = analyzer.analyze_files(file_paths)

    # Filter by severity if requested
    if severity:
        severity_order = {Severity.ERROR: 3, Severity.WARNING: 2, Severity.INFO: 1}
        min_severity = getattr(Severity, severity.upper())
        min_level = severity_order[min_severity]
        violations = [v for v in violations if severity_order[v.severity] >= min_level]

    # Create reporter
    reporter = Reporter(
        output_format=output_format,
        show_source=show_source,
        color=color,
    )

    # Print report
    reporter.print_report(violations)

    # Exit with error code if violations found
    if violations and any(v.severity == Severity.ERROR for v in violations):
        sys.exit(1)


def collect_python_files(
    paths: List[str], exclude_patterns: Optional[List[str]] = None
) -> List[Path]:
    """Collect all Python files from given paths.

    Args:
        paths: List of paths to search for Python files
        exclude_patterns: List of glob patterns to exclude

    Returns:
        List of Python file paths
    """
    import fnmatch

    python_files = []

    for path_str in paths:
        path = Path(path_str).resolve()

        if path.is_file() and path.suffix == ".py":
            python_files.append(path)
        elif path.is_dir():
            # Recursively find Python files
            python_files.extend(path.rglob("*.py"))

    # Default ignored directories
    default_ignored_dirs = {
        ".venv",
        "venv",
        "__pycache__",
        ".git",
        ".tox",
        "build",
        "dist",
    }

    # Additional exclusions from config
    exclude_patterns = exclude_patterns or []

    filtered_files = []
    for f in python_files:
        # Check default ignored directories
        if any(ignored in f.parts for ignored in default_ignored_dirs):
            continue

        # Check exclude patterns
        excluded = False
        for pattern in exclude_patterns:
            # Get relative path from current working directory
            try:
                rel_path = f.relative_to(Path.cwd())
                rel_path_str = str(rel_path)
            except ValueError:
                # File is outside current working directory, use absolute path
                rel_path_str = str(f)

            # Convert path separators for consistent matching
            rel_path_posix = rel_path_str.replace("\\", "/")

            # Check various pattern styles
            if (
                fnmatch.fnmatch(rel_path_posix, pattern)  # Full path match
                or fnmatch.fnmatch(f.name, pattern)  # Filename match
            ):
                excluded = True
                break

            # Check directory patterns
            if (
                "/" in pattern
                and "**" not in pattern
                and fnmatch.fnmatch(rel_path_posix, pattern)
            ):
                # For patterns like "excluded/*" or "tests/file.py"
                excluded = True
                break

            # Special handling for ** patterns (glob style)
            if "**" in pattern:
                import re

                # For patterns like **/tests/**, we need to check if the path contains the pattern
                # Remove the ** and check if the remaining pattern is in the path
                if pattern.startswith("**/") and pattern.endswith("/**"):
                    # Pattern like **/tests/** - check if 'tests' is in the path
                    middle_part = pattern[
                        3:-3
                    ]  # Remove **/ from start and /** from end
                    if (
                        f"/{middle_part}/" in f"/{rel_path_posix}/"
                        or rel_path_posix.startswith(f"{middle_part}/")
                    ):
                        excluded = True
                        break
                elif pattern.startswith("**/"):
                    # Pattern like **/tests - check if path ends with pattern
                    suffix = pattern[3:]  # Remove **/
                    if (
                        rel_path_posix.endswith(suffix)
                        or f"/{suffix}/" in rel_path_posix
                    ):
                        excluded = True
                        break
                elif pattern.endswith("/**"):
                    # Pattern like tests/** - check if path starts with pattern
                    prefix = pattern[:-3]  # Remove /**
                    if rel_path_posix.startswith(f"{prefix}/"):
                        excluded = True
                        break
                else:
                    # General ** pattern matching
                    pattern_regex = pattern.replace("**", ".*").replace("*", "[^/]*")
                    if re.match(pattern_regex, rel_path_posix):
                        excluded = True
                        break

        if not excluded:
            filtered_files.append(f)

    return sorted(set(filtered_files))


def load_config(config_path: Optional[str] = None) -> dict:
    """Load configuration from TOML file.

    If no config_path is provided, searches for:
    1. .pinjected-linter.toml in current directory
    2. pyproject.toml with [tool.pinjected-linter] section
    """
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        import tomli as tomllib  # Fallback for older Python

    # If explicit path provided, use it
    if config_path:
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"Configuration file not found: {config_path}")
            return {}

        try:
            with open(path, "rb") as f:
                config = tomllib.load(f)
                # If it's pyproject.toml, extract the tool.pinjected-linter section
                if (
                    path.name == "pyproject.toml"
                    and "tool" in config
                    and "pinjected-linter" in config["tool"]
                ):
                    return config["tool"]["pinjected-linter"]
                return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return {}

    # Otherwise, search for config files
    # First try .pinjected-linter.toml in current directory
    pinjected_config = Path(".pinjected-linter.toml")
    if pinjected_config.exists():
        try:
            with open(pinjected_config, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            logger.error(f"Failed to load .pinjected-linter.toml: {e}")

    # Then try pyproject.toml
    pyproject = Path("pyproject.toml")
    if pyproject.exists():
        try:
            with open(pyproject, "rb") as f:
                config = tomllib.load(f)
                if "tool" in config and "pinjected-linter" in config["tool"]:
                    return config["tool"]["pinjected-linter"]
        except Exception as e:
            logger.error(f"Failed to load pyproject.toml: {e}")

    return {}


if __name__ == "__main__":
    main()
