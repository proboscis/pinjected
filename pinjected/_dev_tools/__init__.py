from pathlib import Path

from pinjected import *


@instance
def generate_merged_doc(logger):
    docs = sorted(list(Path("docs").rglob("*.md")))
    logger.info(docs)
    merged_text = "\n".join([doc.read_text() for doc in docs])
    Path("merged_doc.md").write_text(merged_text)


__design__ = design(overrides=design())
