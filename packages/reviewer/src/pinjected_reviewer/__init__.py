from pathlib import Path

import loguru
from pinjected import *
import pinjected

__version__ = "0.1.0"

from pinjected_reviewer.reviewer_def import ReviewerDefinition
from pinjected_reviewer.loader import reviewer_definitions, find_reviewer_markdown_files

default_design = design(
    cache_root_path=Path("~/.cache/pinjected_reviewer").expanduser(),
) + providers(
    logger=lambda: loguru.logger,
    repo_root=lambda: Path.cwd(),  # Default to current directory
)
__meta_design__ = instances(
    overrides=default_design
)
