from pathlib import Path

from pinjected import *

__version__ = "0.1.0"

default_design = design(
    cache_root_path=Path("~/.cache/pinjected_rate_limit").expanduser(),
)
