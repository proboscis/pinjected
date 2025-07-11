"""
pinjected-reviewer - A git pre-commit hook for reviewing code with pinjected.
"""

from pinjected import design

__version__ = "0.3.1"

from pinjected_reviewer import entrypoint
from pinjected_reviewer.__pinjected__ import __pinjected_reviewer_default_design

__all__ = ["__design__", "__version__", "entrypoint"]

__design__ = design(overrides=__pinjected_reviewer_default_design)
