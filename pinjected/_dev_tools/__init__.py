"""Dev tools package."""

from pinjected import design, instance
from pinjected._dev_tools.doc_merger import generate_merged_doc

__all__ = ["design", "generate_merged_doc", "instance"]

__design__ = design(overrides=design())
