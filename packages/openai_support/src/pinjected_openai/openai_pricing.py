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


def get_openai_model_table() -> OpenAIModelTable:
    """
    Get OpenAI model pricing table.

    Note: OpenAI doesn't provide a public API for pricing, so we hardcode
    the current prices. These should be updated periodically.

    Prices are in USD per 1M tokens as of January 2025.
    """
    models = [
        # GPT-4o models
        OpenAIModel(
            id="gpt-4o",
            name="GPT-4o",
            pricing=OpenAIModelPricing(
                prompt=Decimal("2.50"),
                completion=Decimal("10.00"),
                cached_prompt=Decimal("1.25"),  # 50% discount for cached
            ),
            context_length=128000,
            max_output_tokens=16384,
            supports_vision=True,
            supports_json_mode=True,
            supports_structured_output=True,
        ),
        OpenAIModel(
            id="gpt-4o-2024-11-20",
            name="GPT-4o (2024-11-20)",
            pricing=OpenAIModelPricing(
                prompt=Decimal("2.50"),
                completion=Decimal("10.00"),
                cached_prompt=Decimal("1.25"),
            ),
            context_length=128000,
            max_output_tokens=16384,
            supports_vision=True,
            supports_json_mode=True,
            supports_structured_output=True,
        ),
        OpenAIModel(
            id="gpt-4o-mini",
            name="GPT-4o mini",
            pricing=OpenAIModelPricing(
                prompt=Decimal("0.15"),
                completion=Decimal("0.60"),
                cached_prompt=Decimal("0.075"),
            ),
            context_length=128000,
            max_output_tokens=16384,
            supports_vision=True,
            supports_json_mode=True,
            supports_structured_output=True,
        ),
        # GPT-5 models (reasoning models)
        OpenAIModel(
            id="gpt-5",
            name="GPT-5",
            pricing=OpenAIModelPricing(
                prompt=Decimal("15.00"),
                completion=Decimal("60.00"),
                cached_prompt=Decimal("7.50"),
            ),
            context_length=128000,
            max_output_tokens=32768,
            supports_vision=True,
            supports_json_mode=True,
            supports_structured_output=True,
        ),
        OpenAIModel(
            id="gpt-5-mini",
            name="GPT-5 mini",
            pricing=OpenAIModelPricing(
                prompt=Decimal("3.00"),
                completion=Decimal("12.00"),
                cached_prompt=Decimal("1.50"),
            ),
            context_length=128000,
            max_output_tokens=65536,
            supports_vision=True,
            supports_json_mode=True,
            supports_structured_output=True,
        ),
        OpenAIModel(
            id="gpt-5-nano",
            name="GPT-5 nano",
            pricing=OpenAIModelPricing(
                prompt=Decimal("0.60"),
                completion=Decimal("2.40"),
                cached_prompt=Decimal("0.30"),
            ),
            context_length=128000,
            max_output_tokens=16384,
            supports_vision=True,
            supports_json_mode=True,
            supports_structured_output=True,
        ),
        # GPT-4 Turbo
        OpenAIModel(
            id="gpt-4-turbo",
            name="GPT-4 Turbo",
            pricing=OpenAIModelPricing(
                prompt=Decimal("10.00"),
                completion=Decimal("30.00"),
            ),
            context_length=128000,
            max_output_tokens=4096,
            supports_vision=True,
            supports_json_mode=True,
            supports_structured_output=False,
        ),
        OpenAIModel(
            id="gpt-4-turbo-preview",
            name="GPT-4 Turbo Preview",
            pricing=OpenAIModelPricing(
                prompt=Decimal("10.00"),
                completion=Decimal("30.00"),
            ),
            context_length=128000,
            max_output_tokens=4096,
            supports_json_mode=True,
            supports_structured_output=False,
        ),
        # GPT-4
        OpenAIModel(
            id="gpt-4",
            name="GPT-4",
            pricing=OpenAIModelPricing(
                prompt=Decimal("30.00"),
                completion=Decimal("60.00"),
            ),
            context_length=8192,
            max_output_tokens=4096,
            supports_json_mode=False,
            supports_structured_output=False,
        ),
        OpenAIModel(
            id="gpt-4-32k",
            name="GPT-4 32K",
            pricing=OpenAIModelPricing(
                prompt=Decimal("60.00"),
                completion=Decimal("120.00"),
            ),
            context_length=32768,
            max_output_tokens=4096,
            supports_json_mode=False,
            supports_structured_output=False,
        ),
        # GPT-3.5 Turbo
        OpenAIModel(
            id="gpt-3.5-turbo",
            name="GPT-3.5 Turbo",
            pricing=OpenAIModelPricing(
                prompt=Decimal("0.50"),
                completion=Decimal("1.50"),
            ),
            context_length=16385,
            max_output_tokens=4096,
            supports_json_mode=True,
            supports_structured_output=False,
        ),
        OpenAIModel(
            id="gpt-3.5-turbo-16k",
            name="GPT-3.5 Turbo 16K",
            pricing=OpenAIModelPricing(
                prompt=Decimal("3.00"),
                completion=Decimal("4.00"),
            ),
            context_length=16385,
            max_output_tokens=4096,
            supports_json_mode=False,
            supports_structured_output=False,
        ),
    ]

    return OpenAIModelTable(data=models)


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
