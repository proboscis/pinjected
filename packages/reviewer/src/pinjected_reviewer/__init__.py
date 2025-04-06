"""
pinjected-reviewer - A git pre-commit hook for reviewing code with pinjected.
"""
from pathlib import Path

from injected_utils import async_cached, lzma_sqlite
from pinjected import design, instance, injected, Injected

__version__ = "0.3.1"

from pinjected_reviewer.__pinjected__ import __pinjected_reviewer_default_design


from pinjected_reviewer import entrypoint

__meta_design__ = design(
    overrides=__pinjected_reviewer_default_design
)
