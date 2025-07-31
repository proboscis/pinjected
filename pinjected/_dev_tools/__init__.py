"""Dev tools package."""

from pinjected import design
from pinjected._dev_tools.doc_merger import generate_merged_doc

__all__ = ["generate_merged_doc"]

__design__ = design(overrides=design())
