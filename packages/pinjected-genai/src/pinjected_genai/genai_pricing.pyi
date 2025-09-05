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

# Additional symbols:
class GenAIState:
    cumulative_cost: float
    total_cost_usd: float
    cost_breakdown: Dict[str, float]
    total_text_input_tokens: int
    total_text_output_tokens: int
    total_image_input_tokens: int
    total_image_output_tokens: int
    request_count: int
    def to_dict(self) -> dict: ...
    def update_from_usage(self, usage: dict, cost_dict: dict) -> "GenAIState": ...

# Additional symbols:
class CostBreakdown:
    text_input: float
    text_output: float
    image_input: float
    image_output: float
    def add(self, other: "CostBreakdown") -> "CostBreakdown": ...
    def to_dict(self) -> Dict[str, float]: ...
