from pathlib import Path

import loguru
from pinjected import *
import pinjected

__version__ = "0.1.0"

default_design = design(
    cache_root_path=Path("~/.cache/pinjected_reviewer").expanduser(),
) + providers(
    logger=lambda: loguru.logger,
)
__meta_design__ = instances(
    overrides=default_design
)
