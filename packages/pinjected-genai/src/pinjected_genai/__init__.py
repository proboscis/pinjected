from pathlib import Path

from pinjected_genai.clients import (
    GenAIAuthClient,
    genai_auth_client,
    genai_auth_client_adc,
    genai_client,
    genai_location,
    genai_model_name,
)
from pinjected_genai.image_generation import (
    GeneratedImage,
    GenerationResult,
    a_describe_image__genai,
    a_edit_image__genai,
    a_generate_image__genai,
)

from pinjected import *

__version__ = "0.1.0"

__all__ = [
    "GenAIAuthClient",
    "GeneratedImage",
    "GenerationResult",
    "a_describe_image__genai",
    "a_edit_image__genai",
    "a_generate_image__genai",
    "genai_auth_client",
    "genai_auth_client_adc",
    "genai_client",
    "genai_location",
    "genai_model_name",
]

default_design = design(
    cache_root_path=Path("~/.cache/pinjected_genai").expanduser(),
)
