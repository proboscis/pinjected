from pathlib import Path

from pinjected import *


@instance
def generate_merged_doc(logger):
    docs = list(sorted(list(Path("docs_md").rglob("*.md"))))
    logger.info(docs)
    merged_text = "\n".join([doc.read_text() for doc in docs])
    Path("merged_doc.md").write_text(merged_text)


__meta_design__ = design(
    overrides=design(
    )
)
