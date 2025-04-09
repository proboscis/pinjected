from pathlib import Path

import loguru
from pinjected import *
import pinjected

from pinjected_openai.clients import async_openai_client, openai_api_key

__version__ = "0.4.24"

default_design = design(
    cache_root_path=Path("~/.cache/pinjected_openai").expanduser(),
)
