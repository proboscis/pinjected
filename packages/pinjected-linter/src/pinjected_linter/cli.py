"""Command-line interface for Pinjected linter."""

import sys
from pathlib import Path
from typing import List, Optional

import click
from loguru import logger

# Configure logger to not output to stderr unless verbose
logger.remove()  # Remove default handler

from .analyzer import PinjectedAnalyzer
from .models import Severity
from .reporter import Reporter


@click.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration file (.pinjected-lint.toml)",
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
):
    """Pinjected linter - Check your code for Pinjected best practices.
    
    If no paths are provided, the current directory is checked recursively.
    """
    # Configure logging based on verbose flag
    if verbose:
        logger.add(sys.stderr, level="INFO")
        logger.info("Starting Pinjected linter")
    
    # Collect Python files
    file_paths = collect_python_files(paths or ["."])
    if not file_paths:
        logger.warning("No Python files found")
        return
    
    if verbose:
        logger.info(f"Found {len(file_paths)} Python files to analyze")
    
    # Build configuration
    config_dict = {}
    if config:
        config_dict = load_config(config)
    
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


def collect_python_files(paths: List[str]) -> List[Path]:
    """Collect all Python files from given paths."""
    python_files = []
    
    for path_str in paths:
        path = Path(path_str).resolve()
        
        if path.is_file() and path.suffix == ".py":
            python_files.append(path)
        elif path.is_dir():
            # Recursively find Python files
            python_files.extend(path.rglob("*.py"))
    
    # Filter out common directories to ignore
    ignored_dirs = {".venv", "venv", "__pycache__", ".git", ".tox", "build", "dist"}
    python_files = [
        f for f in python_files
        if not any(ignored in f.parts for ignored in ignored_dirs)
    ]
    
    return sorted(set(python_files))


def load_config(config_path: str) -> dict:
    """Load configuration from TOML file."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        import tomli as tomllib  # Fallback for older Python
    
    path = Path(config_path)
    if not path.exists():
        logger.warning(f"Configuration file not found: {config_path}")
        return {}
    
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return {}


if __name__ == "__main__":
    main()