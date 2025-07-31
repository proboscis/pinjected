from pathlib import Path

from pinjected_openai.clients import async_openai_client, openai_api_key

from pinjected import *

__version__ = "0.4.24"

__all__ = ["async_openai_client", "openai_api_key"]

default_design = design(
    cache_root_path=Path("~/.cache/pinjected_openai").expanduser(),
)
