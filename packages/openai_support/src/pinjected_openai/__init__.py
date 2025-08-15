from pathlib import Path

from pinjected_openai.clients import async_openai_client, openai_api_key
from pinjected_openai.direct_openai import (
    a_sllm_openai,
    a_structured_llm_openai,
    a_sllm_gpt4o_direct,
    a_sllm_gpt5_nano_direct,
    a_sllm_gpt5_direct,
)

from pinjected import *

__version__ = "0.4.24"

__all__ = [
    "a_sllm_gpt4o_direct",
    "a_sllm_gpt5_direct",
    "a_sllm_gpt5_nano_direct",
    "a_sllm_openai",
    "a_structured_llm_openai",
    "async_openai_client",
    "openai_api_key",
]

default_design = design(
    cache_root_path=Path("~/.cache/pinjected_openai").expanduser(),
)
