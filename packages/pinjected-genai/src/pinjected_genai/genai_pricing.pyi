"""Type stubs for Gen AI pricing module."""

from dataclasses import dataclass
from typing import Dict, Optional, Protocol
from pinjected import IProxy

@dataclass
class ModelPricing:
    text_input: float
    text_output: float
    image_input: float
    image_output: float

    def calc_cost(self, usage: dict) -> dict: ...

class GenAIModelTable:
    MODELS: Dict[str, ModelPricing]

    def get_pricing(self, model: str) -> Optional[ModelPricing]: ...

class LoggerProtocol(Protocol):
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...

def calculate_cumulative_cost(genai_state: dict, cost_dict: dict) -> dict: ...
def log_generation_cost(
    usage: dict,
    model: str,
    genai_model_table: GenAIModelTable,
    genai_state: dict,
    logger: LoggerProtocol,
) -> dict: ...
def genai_state() -> dict: ...

# IProxy definitions for dependency injection
genai_model_table: IProxy[GenAIModelTable]
genai_state: IProxy[dict]
