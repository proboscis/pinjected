from pathlib import Path

from pinjected_genai.clients import (
    GenAIAuthClient,
    genai_auth_client,
    genai_auth_client_adc,
    genai_client,
    genai_location,
)
from pinjected_genai.image_generation import (
    GeneratedImage,
    GenerationResult,
    a_describe_image__genai,
    a_edit_image__genai,
    a_generate_image__genai,
)
from pinjected_genai.genai_pricing import (
    CostBreakdown,
    GenAIModelTable,
    GenAIState,
    ModelPricing,
    log_generation_cost,
    genai_state,
)

from pinjected import *

__version__ = "0.1.0"

__all__ = [
    "CostBreakdown",
    "GenAIAuthClient",
    "GenAIModelTable",
    "GenAIState",
    "GeneratedImage",
    "GenerationResult",
    "ModelPricing",
    "a_describe_image__genai",
    "a_edit_image__genai",
    "a_generate_image__genai",
    "genai_auth_client",
    "genai_auth_client_adc",
    "genai_client",
    "genai_location",
    "genai_state",
    "log_generation_cost",
]

default_design = design(
    cache_root_path=Path("~/.cache/pinjected_genai").expanduser(),
    genai_model_table=GenAIModelTable(),
    genai_state=genai_state,
)
