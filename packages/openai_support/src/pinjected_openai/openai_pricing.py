"""OpenAI model pricing and cost tracking implementation."""

from typing import Protocol
from pydantic import BaseModel
from decimal import Decimal
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from pinjected import instance


class LoggerProtocol(Protocol):
    def debug(self, message: str) -> None: ...
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def success(self, message: str) -> None: ...


class OpenAIModelPricing(BaseModel):
    """Pricing information for an OpenAI model (per 1M tokens)."""

    prompt: Decimal  # Cost per 1M input tokens
    completion: Decimal  # Cost per 1M output tokens
    cached_prompt: Decimal | None = None  # Cost for cached input tokens (if applicable)

    def calc_cost(self, usage: dict) -> dict:
        """Calculate cost from usage dictionary."""
        # Convert from per 1M tokens to per token (divide by 1,000,000)
        prompt_cost = (
            float(usage.get("prompt_tokens", 0)) * float(self.prompt) / 1_000_000
        )
        completion_cost = (
            float(usage.get("completion_tokens", 0))
            * float(self.completion)
            / 1_000_000
        )

        # Handle cached tokens if present
        cached_cost = 0.0
        if self.cached_prompt and "prompt_tokens_details" in usage:
            details = usage["prompt_tokens_details"]
            cached_tokens = details.get("cached_tokens", 0)
            non_cached_tokens = usage["prompt_tokens"] - cached_tokens

            # Recalculate prompt cost with cached pricing
            prompt_cost = (
                float(non_cached_tokens) * float(self.prompt) / 1_000_000
                + float(cached_tokens) * float(self.cached_prompt) / 1_000_000
            )
            cached_cost = float(cached_tokens) * float(self.cached_prompt) / 1_000_000

        # Handle reasoning tokens for GPT-5 (billed as completion tokens)
        reasoning_cost = 0.0
        if "completion_tokens_details" in usage:
            details = usage["completion_tokens_details"]
            reasoning_tokens = details.get("reasoning_tokens", 0)
            if reasoning_tokens > 0:
                reasoning_cost = (
                    float(reasoning_tokens) * float(self.completion) / 1_000_000
                )

        return {
            "prompt": prompt_cost,
            "completion": completion_cost,
            "cached": cached_cost,
            "reasoning": reasoning_cost,
            "total": prompt_cost + completion_cost,
        }


class OpenAIModel(BaseModel):
    """OpenAI model information."""

    id: str
    name: str
    pricing: OpenAIModelPricing
    context_length: int
    max_output_tokens: int | None = None
    supports_vision: bool = False
    supports_function_calling: bool = True
    supports_json_mode: bool = False
    supports_structured_output: bool = False

    def supports_json_output(self) -> bool:
        """Check if model supports JSON output."""
        return self.supports_json_mode or self.supports_structured_output


class OpenAIModelTable(BaseModel):
    """Table of OpenAI models with pricing information."""

    data: list[OpenAIModel]

    def get_model(self, model_id: str) -> OpenAIModel | None:
        """Get a model by its ID."""
        for model in self.data:
            if model.id == model_id:
                return model
        return None

    def get_pricing(self, model_id: str) -> OpenAIModelPricing | None:
        """Get pricing for a model."""
        model = self.get_model(model_id)
        return model.pricing if model else None

    def supports_json_output(self, model_id: str) -> bool:
        """Check if a model supports JSON output."""
        model = self.get_model(model_id)
        return model.supports_json_output() if model else False


def _create_model(
    id: str,
    name: str,
    prompt_cost: str,
    completion_cost: str,
    cached_cost: str | None = None,
    context_length: int = 128000,
    max_output_tokens: int = 16384,
    supports_vision: bool = True,
    supports_json_mode: bool = True,
    supports_structured_output: bool = True,
) -> OpenAIModel:
    """Helper function to create an OpenAI model with pricing."""
    pricing = OpenAIModelPricing(
        prompt=Decimal(prompt_cost),
        completion=Decimal(completion_cost),
        cached_prompt=Decimal(cached_cost) if cached_cost else None,
    )
    return OpenAIModel(
        id=id,
        name=name,
        pricing=pricing,
        context_length=context_length,
        max_output_tokens=max_output_tokens,
        supports_vision=supports_vision,
        supports_json_mode=supports_json_mode,
        supports_structured_output=supports_structured_output,
    )


def _get_gpt5_models() -> list[OpenAIModel]:
    """Get all GPT-5 model configurations."""
    return [
        _create_model(
            "gpt-5",
            "GPT-5",
            "1.25",
            "10.00",
            "0.125",
            context_length=400000,
            max_output_tokens=128000,
        ),
        _create_model(
            "gpt-5-mini",
            "GPT-5 Mini",
            "0.25",
            "2.00",
            "0.025",
            context_length=400000,
            max_output_tokens=128000,
        ),
        _create_model(
            "gpt-5-nano",
            "GPT-5 Nano",
            "0.05",
            "0.40",
            "0.005",
            context_length=400000,
            max_output_tokens=128000,
        ),
        _create_model(
            "gpt-5-chat-latest",
            "GPT-5 Chat Latest",
            "1.25",
            "10.00",
            "0.125",
            context_length=400000,
            max_output_tokens=128000,
        ),
    ]


def _get_gpt41_models() -> list[OpenAIModel]:
    """Get all GPT-4.1 model configurations."""
    return [
        _create_model("gpt-4.1", "GPT-4.1", "2.00", "8.00", "0.50"),
        _create_model("gpt-4.1-mini", "GPT-4.1 Mini", "0.40", "1.60", "0.10"),
        _create_model("gpt-4.1-nano", "GPT-4.1 Nano", "0.10", "0.40", "0.025"),
    ]


def _get_o1_models() -> list[OpenAIModel]:
    """Get all o1 reasoning model configurations."""
    return [
        _create_model(
            "o1",
            "o1",
            "15.00",
            "60.00",
            "7.50",
            context_length=200000,
            max_output_tokens=100000,
            supports_json_mode=False,
            supports_structured_output=False,
        ),
        _create_model(
            "o1-pro",
            "o1 Pro",
            "150.00",
            "600.00",
            None,
            context_length=200000,
            max_output_tokens=100000,
            supports_json_mode=False,
            supports_structured_output=False,
        ),
        _create_model(
            "o1-mini",
            "o1 Mini",
            "3.00",
            "12.00",
            "1.50",
            max_output_tokens=65536,
            supports_vision=False,
            supports_json_mode=False,
            supports_structured_output=False,
        ),
    ]


def _get_o3_models() -> list[OpenAIModel]:
    """Get all o3 model configurations."""
    return [
        _create_model(
            "o3-pro",
            "o3 Pro",
            "20.00",
            "80.00",
            None,
            context_length=200000,
            max_output_tokens=100000,
            supports_json_mode=False,
            supports_structured_output=False,
        ),
        _create_model(
            "o3",
            "o3",
            "2.00",
            "8.00",
            "0.50",
            context_length=200000,
            max_output_tokens=100000,
            supports_json_mode=False,
            supports_structured_output=False,
        ),
        _create_model(
            "o3-deep-research",
            "o3 Deep Research",
            "10.00",
            "40.00",
            "2.50",
            context_length=200000,
            max_output_tokens=100000,
            supports_json_mode=False,
            supports_structured_output=False,
        ),
        _create_model(
            "o3-mini",
            "o3 Mini",
            "1.10",
            "4.40",
            "0.55",
            max_output_tokens=65536,
            supports_vision=False,
            supports_json_mode=False,
            supports_structured_output=False,
        ),
    ]


def _get_o4_models() -> list[OpenAIModel]:
    """Get all o4 model configurations."""
    return [
        _create_model(
            "o4-mini",
            "o4 Mini",
            "1.10",
            "4.40",
            "0.275",
            max_output_tokens=65536,
            supports_vision=False,
            supports_json_mode=False,
            supports_structured_output=False,
        ),
        _create_model(
            "o4-mini-deep-research",
            "o4 Mini Deep Research",
            "2.00",
            "8.00",
            "0.50",
            max_output_tokens=65536,
            supports_vision=False,
            supports_json_mode=False,
            supports_structured_output=False,
        ),
    ]


def _get_gpt4o_models() -> list[OpenAIModel]:
    """Get all GPT-4o model configurations."""
    return [
        _create_model("gpt-4o", "GPT-4o", "2.50", "10.00", "1.25"),
        _create_model(
            "gpt-4o-2024-05-13", "GPT-4o (2024-05-13)", "5.00", "15.00", None
        ),
        _create_model(
            "gpt-4o-audio-preview", "GPT-4o Audio Preview", "2.50", "10.00", None
        ),
        _create_model(
            "gpt-4o-realtime-preview",
            "GPT-4o Realtime Preview",
            "5.00",
            "20.00",
            "2.50",
        ),
        _create_model("gpt-4o-mini", "GPT-4o Mini", "0.15", "0.60", "0.075"),
        _create_model(
            "gpt-4o-mini-audio-preview",
            "GPT-4o Mini Audio Preview",
            "0.15",
            "0.60",
            None,
        ),
        _create_model(
            "gpt-4o-mini-realtime-preview",
            "GPT-4o Mini Realtime Preview",
            "0.60",
            "2.40",
            "0.30",
        ),
        _create_model(
            "gpt-4o-mini-search-preview",
            "GPT-4o Mini Search Preview",
            "0.15",
            "0.60",
            None,
        ),
        _create_model(
            "gpt-4o-search-preview", "GPT-4o Search Preview", "2.50", "10.00", None
        ),
    ]


def _get_specialized_models() -> list[OpenAIModel]:
    """Get specialized model configurations (codex, computer-use, image)."""
    return [
        _create_model(
            "codex-mini-latest",
            "Codex Mini Latest",
            "1.50",
            "6.00",
            "0.375",
            supports_vision=False,
        ),
        _create_model(
            "computer-use-preview",
            "Computer Use Preview",
            "3.00",
            "12.00",
            None,
            supports_json_mode=False,
            supports_structured_output=False,
        ),
        _create_model(
            "gpt-image-1",
            "GPT Image 1",
            "5.00",
            "0.00",
            "1.25",
            max_output_tokens=0,
            supports_json_mode=False,
            supports_structured_output=False,
        ),
    ]


def _get_legacy_gpt4_models() -> list[OpenAIModel]:
    """Get legacy GPT-4 model configurations."""
    return [
        _create_model(
            "gpt-4-turbo",
            "GPT-4 Turbo",
            "10.00",
            "30.00",
            None,
            max_output_tokens=4096,
            supports_structured_output=False,
        ),
        _create_model(
            "gpt-4-turbo-preview",
            "GPT-4 Turbo Preview",
            "10.00",
            "30.00",
            None,
            max_output_tokens=4096,
            supports_vision=False,
            supports_structured_output=False,
        ),
        _create_model(
            "gpt-4",
            "GPT-4",
            "30.00",
            "60.00",
            None,
            context_length=8192,
            max_output_tokens=4096,
            supports_vision=False,
            supports_json_mode=False,
            supports_structured_output=False,
        ),
        _create_model(
            "gpt-4-32k",
            "GPT-4 32K",
            "60.00",
            "120.00",
            None,
            context_length=32768,
            max_output_tokens=4096,
            supports_vision=False,
            supports_json_mode=False,
            supports_structured_output=False,
        ),
    ]


def _get_gpt35_models() -> list[OpenAIModel]:
    """Get GPT-3.5 model configurations."""
    return [
        _create_model(
            "gpt-3.5-turbo",
            "GPT-3.5 Turbo",
            "0.50",
            "1.50",
            None,
            context_length=16385,
            max_output_tokens=4096,
            supports_vision=False,
            supports_structured_output=False,
        ),
        _create_model(
            "gpt-3.5-turbo-16k",
            "GPT-3.5 Turbo 16K",
            "3.00",
            "4.00",
            None,
            context_length=16385,
            max_output_tokens=4096,
            supports_vision=False,
            supports_json_mode=False,
            supports_structured_output=False,
        ),
    ]


def get_openai_model_table() -> OpenAIModelTable:
    """
    Get OpenAI model pricing table.

    Note: OpenAI doesn't provide a public API for pricing, so we hardcode
    the current prices. These should be updated periodically.

    Prices are in USD per 1M tokens as of January 2025.
    Based on: https://platform.openai.com/docs/pricing
    """
    # Combine all model families using helper functions (DRY principle)
    all_models = []

    # Add each model family
    all_models.extend(_get_gpt5_models())
    all_models.extend(_get_gpt41_models())
    all_models.extend(_get_o1_models())
    all_models.extend(_get_o3_models())
    all_models.extend(_get_o4_models())
    all_models.extend(_get_gpt4o_models())
    all_models.extend(_get_specialized_models())
    all_models.extend(_get_legacy_gpt4_models())
    all_models.extend(_get_gpt35_models())

    return OpenAIModelTable(data=all_models)


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
)
async def fetch_openai_models(api_key: str) -> list[str]:
    """
    Fetch available models from OpenAI API.

    This returns model IDs but not pricing information.
    Pricing must be maintained separately.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response.raise_for_status()
        data = response.json()

        # Filter to chat models only
        chat_models = [
            model["id"] for model in data["data"] if "gpt" in model["id"].lower()
        ]

        return sorted(chat_models)


def calculate_cumulative_cost(openai_state: dict, cost_dict: dict) -> dict:
    """Calculate new state with updated cumulative cost."""
    current_total = openai_state.get("cumulative_cost", 0.0)
    current_breakdown = openai_state.get(
        "cost_breakdown",
        {
            "prompt": 0.0,
            "completion": 0.0,
            "cached": 0.0,
            "reasoning": 0.0,
        },
    )

    # Update total
    new_total = current_total + cost_dict.get("total", 0.0)

    # Update breakdown
    new_breakdown = {
        "prompt": current_breakdown["prompt"] + cost_dict.get("prompt", 0.0),
        "completion": current_breakdown["completion"]
        + cost_dict.get("completion", 0.0),
        "cached": current_breakdown["cached"] + cost_dict.get("cached", 0.0),
        "reasoning": current_breakdown["reasoning"] + cost_dict.get("reasoning", 0.0),
    }

    return {
        **openai_state,
        "cumulative_cost": new_total,
        "cost_breakdown": new_breakdown,
    }


def log_completion_cost(
    usage: dict,
    model: str,
    openai_model_table: OpenAIModelTable,
    openai_state: dict,
    logger: LoggerProtocol,
) -> dict:
    """Calculate and log completion costs, returning updated state."""
    pricing = openai_model_table.get_pricing(model)

    if not pricing:
        logger.warning(f"No pricing information available for model: {model}")
        return openai_state

    cost_dict = pricing.calc_cost(usage)
    new_state = calculate_cumulative_cost(openai_state, cost_dict)

    # Format cost string
    cost_parts = []
    if cost_dict["prompt"] > 0:
        cost_parts.append(f"prompt: ${cost_dict['prompt']:.6f}")
    if cost_dict["completion"] > 0:
        cost_parts.append(f"completion: ${cost_dict['completion']:.6f}")
    if cost_dict.get("cached", 0) > 0:
        cost_parts.append(f"cached: ${cost_dict['cached']:.6f}")
    if cost_dict.get("reasoning", 0) > 0:
        cost_parts.append(f"reasoning: ${cost_dict['reasoning']:.6f}")

    cost_str = ", ".join(cost_parts)

    logger.info(
        f"Cost: {cost_str} | "
        f"Total: ${cost_dict['total']:.6f} | "
        f"Cumulative: ${new_state['cumulative_cost']:.6f}"
    )

    # Log detailed breakdown periodically
    if new_state.get("request_count", 0) % 10 == 0:
        breakdown = new_state["cost_breakdown"]
        logger.info(
            f"Cost breakdown - "
            f"Prompt: ${breakdown['prompt']:.4f}, "
            f"Completion: ${breakdown['completion']:.4f}, "
            f"Cached: ${breakdown['cached']:.4f}, "
            f"Reasoning: ${breakdown['reasoning']:.4f}"
        )

    return new_state


# Injected instances
@instance
def openai_model_table() -> OpenAIModelTable:
    """Get the OpenAI model pricing table."""
    return get_openai_model_table()


@instance
def openai_state() -> dict:
    """Initial OpenAI state for cost tracking."""
    return {
        "cumulative_cost": 0.0,
        "cost_breakdown": {
            "prompt": 0.0,
            "completion": 0.0,
            "cached": 0.0,
            "reasoning": 0.0,
        },
        "request_count": 0,
    }
