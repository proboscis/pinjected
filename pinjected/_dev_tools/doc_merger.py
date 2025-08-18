"""Documentation merging functionality for dev tools."""

from pathlib import Path
from typing import TYPE_CHECKING

from pinjected import instance

if TYPE_CHECKING:
    from loguru import Logger


@instance
def generate_merged_doc(logger: "Logger"):
    """Merge all markdown documentation files into a single file."""
    docs = sorted(list(Path("docs").rglob("*.md")))
    logger.info(docs)
    merged_text = "\n".join([doc.read_text() for doc in docs])
    Path("merged_doc.md").write_text(merged_text)
