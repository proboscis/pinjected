"""Pricing module for Google Gen AI models with cost tracking.

This module provides pricing information and cost calculation for Google's Gemini models.
Cost tracking is performed per API call and cumulatively.

Token usage counts are extracted from the Gen AI API responses via usage_metadata.
Both text and image tokens are tracked separately for accurate cost calculation.
"""

from dataclasses import dataclass, field
from typing import ClassVar, Dict, Optional, Protocol

from pinjected import instance


@dataclass(frozen=True)
class CostBreakdown:
    """Immutable breakdown of costs by modality type."""

    text_input: float = 0.0
    text_output: float = 0.0
    image_input: float = 0.0
    image_output: float = 0.0

    def add(self, other: "CostBreakdown") -> "CostBreakdown":
        """Add costs from another breakdown and return a new instance."""
        return CostBreakdown(
            text_input=self.text_input + other.text_input,
            text_output=self.text_output + other.text_output,
            image_input=self.image_input + other.image_input,
            image_output=self.image_output + other.image_output,
        )

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for backward compatibility."""
        return {
            "text_input": self.text_input,
            "text_output": self.text_output,
            "image_input": self.image_input,
            "image_output": self.image_output,
        }


@dataclass
class ModelPricing:
    """Pricing information for a Gen AI model.

    All prices are per million tokens. Token counts are extracted from
    the API response's usage_metadata for both text and image modalities.
    """

    # Prices per million tokens
    text_input: float  # Per million input tokens
    text_output: float  # Per million output tokens
    image_input: float  # Per million input tokens for images
    image_output: float  # Per million output tokens for image generation

    def calc_cost(self, usage: dict) -> dict:
        """Calculate cost based on usage metrics.

        Args:
            usage: Dictionary containing usage metrics:
                - text_input_tokens: Number of input tokens (required)
                - text_output_tokens: Number of output tokens (required)
                - image_input_tokens: Number of input tokens for images
                - image_output_tokens: Number of output tokens for image generation

        Returns:
            Dictionary with cost breakdown:
                - text_input: Cost for text input
                - text_output: Cost for text output
                - image_input: Cost for input images
                - image_output: Cost for output images
                - total: Total cost
        """
        # Get token counts - require actual token counts, no character fallback
        if "text_input_tokens" not in usage:
            raise ValueError(
                "Missing required field 'text_input_tokens' in usage dictionary"
            )
        if "text_output_tokens" not in usage:
            raise ValueError(
                "Missing required field 'text_output_tokens' in usage dictionary"
            )

        text_in_tokens = usage["text_input_tokens"]
        text_out_tokens = usage["text_output_tokens"]

        # Get image token counts directly from API response
        image_in_tokens = usage.get("image_input_tokens", 0)
        image_out_tokens = usage.get("image_output_tokens", 0)

        # Calculate costs per million tokens
        text_in_cost = (text_in_tokens / 1_000_000) * self.text_input
        text_out_cost = (text_out_tokens / 1_000_000) * self.text_output
        img_in_cost = (image_in_tokens / 1_000_000) * self.image_input
        img_out_cost = (image_out_tokens / 1_000_000) * self.image_output

        return {
            "text_input": text_in_cost,
            "text_output": text_out_cost,
            "image_input": img_in_cost,
            "image_output": img_out_cost,
            "total": text_in_cost + text_out_cost + img_in_cost + img_out_cost,
        }


class GenAIModelTable:
    """Table of Gen AI model pricing information.

    Pricing information is hardcoded as the Gen AI SDK
    does not provide pricing via API. Token counts are obtained
    from API responses.
    """

    # Pricing as of January 2025 (prices in USD per million tokens)
    # Source: https://cloud.google.com/vertex-ai/generative-ai/pricing
    MODELS: ClassVar[Dict[str, ModelPricing]] = {
        # Gemini 2.5 Flash - Fast and efficient text-only model
        "gemini-2.5-flash": ModelPricing(
            text_input=0.30,  # $0.30/1M tokens (≤200K tokens)
            text_output=2.50,  # $2.50/1M tokens (≤200K tokens)
            image_input=0.00,  # Free for input images (can process images)
            image_output=0.00,  # Does not support image generation
        ),
        # Gemini 2.5 Flash Image Preview - Supports image generation
        # Also known internally as "nano-banana"
        "gemini-2.5-flash-image-preview": ModelPricing(
            text_input=0.30,  # $0.30/1M tokens (≤200K tokens)
            text_output=2.50,  # $2.50/1M tokens for text output
            image_input=0.30,  # $0.30/1M tokens for input images
            image_output=30.0,  # $30 per million tokens for image generation
        ),
        # Gemini 2.5 Pro - More capable text-only model
        "gemini-2.5-pro": ModelPricing(
            text_input=12.50,  # $12.50/1M tokens (≤200K tokens)
            text_output=150.0,  # $150/1M tokens (≤200K tokens)
            image_input=0.00,  # Free for input images (can process images)
            image_output=0.00,  # Does not support image generation
        ),
        # Gemini 2.0 Flash - Newer generation
        "gemini-2.0-flash": ModelPricing(
            text_input=1.25,  # Original pricing
            text_output=10.0,  # Original pricing
            image_input=0.00,  # Free for input images
            image_output=0.00,  # Does not support image generation
        ),
        # Gemini 1.5 Flash
        "gemini-1.5-flash": ModelPricing(
            text_input=1.25,  # Original pricing
            text_output=10.0,  # Original pricing
            image_input=0.00,  # Free for input images
            image_output=0.00,  # Does not support image generation
        ),
        # Gemini 1.5 Pro
        "gemini-1.5-pro": ModelPricing(
            text_input=12.50,  # Similar to 2.5 Pro
            text_output=150.0,  # Similar to 2.5 Pro
            image_input=0.00,  # Free for input images
            image_output=0.00,  # Does not support image generation
        ),
    }

    def get_pricing(self, model: str) -> Optional[ModelPricing]:
        """Get pricing information for a model.

        Args:
            model: Model name

        Returns:
            ModelPricing object or None if model not found
        """
        return self.MODELS.get(model)


class LoggerProtocol(Protocol):
    """Protocol for logger interface."""

    def info(self, message: str) -> None:
        """Log info message."""
        ...

    def warning(self, message: str) -> None:
        """Log warning message."""
        ...


@dataclass
class GenAIState:
    """State for tracking Gen AI API usage and costs."""

    # Cost tracking
    cumulative_cost: float = 0.0
    total_cost_usd: float = 0.0  # Alias for cumulative_cost for backward compatibility

    # Cost breakdown by type
    cost_breakdown: CostBreakdown = field(default_factory=CostBreakdown)

    # Token counts
    total_text_input_tokens: int = 0
    total_text_output_tokens: int = 0
    total_image_input_tokens: int = 0
    total_image_output_tokens: int = 0

    # Request tracking
    request_count: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility."""
        return {
            "cumulative_cost": self.cumulative_cost,
            "total_cost_usd": self.total_cost_usd,
            "cost_breakdown": self.cost_breakdown.to_dict(),
            "total_text_input_tokens": self.total_text_input_tokens,
            "total_text_output_tokens": self.total_text_output_tokens,
            "total_image_input_tokens": self.total_image_input_tokens,
            "total_image_output_tokens": self.total_image_output_tokens,
            "request_count": self.request_count,
        }

    def update_from_usage(self, usage: dict, cost_dict: dict) -> "GenAIState":
        """Create new state with updated values from usage and cost.

        Args:
            usage: Dictionary with token counts
            cost_dict: Dictionary with cost breakdown

        Returns:
            New GenAIState instance with updated values
        """
        new_cumulative = self.cumulative_cost + cost_dict.get("total", 0.0)

        new_breakdown = CostBreakdown(
            text_input=self.cost_breakdown.text_input
            + cost_dict.get("text_input", 0.0),
            text_output=self.cost_breakdown.text_output
            + cost_dict.get("text_output", 0.0),
            image_input=self.cost_breakdown.image_input
            + cost_dict.get("image_input", 0.0),
            image_output=self.cost_breakdown.image_output
            + cost_dict.get("image_output", 0.0),
        )

        return GenAIState(
            cumulative_cost=new_cumulative,
            total_cost_usd=new_cumulative,
            cost_breakdown=new_breakdown,
            total_text_input_tokens=self.total_text_input_tokens
            + usage.get("text_input_tokens", 0),
            total_text_output_tokens=self.total_text_output_tokens
            + usage.get("text_output_tokens", 0),
            total_image_input_tokens=self.total_image_input_tokens
            + usage.get("image_input_tokens", 0),
            total_image_output_tokens=self.total_image_output_tokens
            + usage.get("image_output_tokens", 0),
            request_count=self.request_count + 1,
        )


def log_generation_cost(
    usage: dict,
    model: str,
    genai_model_table: GenAIModelTable,
    genai_state: GenAIState,  # noqa: PINJ056
    logger: LoggerProtocol,
) -> GenAIState:
    """Calculate and log generation costs, mutating and returning the state.

    Args:
        usage: Usage metrics dictionary
        model: Model name used
        genai_model_table: Model pricing table
        genai_state: GenAIState instance to update (will be mutated)
        logger: Logger instance

    Returns:
        Same GenAIState instance with updated costs (mutated)
    """
    pricing = genai_model_table.get_pricing(model)

    if not pricing:
        error_msg = f"No pricing information available for model: {model}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    cost_dict = pricing.calc_cost(usage)

    # Mutate the state directly for accumulation
    genai_state.cumulative_cost += cost_dict.get("total", 0.0)  # noqa: PINJ056
    genai_state.total_cost_usd = genai_state.cumulative_cost  # noqa: PINJ056

    # Create a new CostBreakdown with the updated costs
    new_cost_breakdown = CostBreakdown(
        text_input=cost_dict.get("text_input", 0.0),
        text_output=cost_dict.get("text_output", 0.0),
        image_input=cost_dict.get("image_input", 0.0),
        image_output=cost_dict.get("image_output", 0.0),
    )
    genai_state.cost_breakdown = genai_state.cost_breakdown.add(new_cost_breakdown)  # noqa: PINJ056

    # Update token counts
    genai_state.total_text_input_tokens += usage.get("text_input_tokens", 0)  # noqa: PINJ056
    genai_state.total_text_output_tokens += usage.get("text_output_tokens", 0)  # noqa: PINJ056
    genai_state.total_image_input_tokens += usage.get("image_input_tokens", 0)  # noqa: PINJ056
    genai_state.total_image_output_tokens += usage.get("image_output_tokens", 0)  # noqa: PINJ056

    genai_state.request_count += 1  # noqa: PINJ056

    # Format cost string
    cost_parts = []
    if cost_dict["text_input"] > 0:
        cost_parts.append(f"text_input: ${cost_dict['text_input']:.6f}")
    if cost_dict["text_output"] > 0:
        cost_parts.append(f"text_output: ${cost_dict['text_output']:.6f}")
    if cost_dict["image_input"] > 0:
        cost_parts.append(f"image_input: ${cost_dict['image_input']:.6f}")
    if cost_dict["image_output"] > 0:
        cost_parts.append(f"image_output: ${cost_dict['image_output']:.6f}")

    cost_str = ", ".join(cost_parts) if cost_parts else "No cost"

    logger.info(
        f"GenAI Cost: {cost_str} | "
        f"Total: ${cost_dict['total']:.6f} | "
        f"Cumulative: ${genai_state.cumulative_cost:.6f}"
    )

    # Log detailed breakdown periodically
    if genai_state.request_count % 10 == 0:
        breakdown = genai_state.cost_breakdown
        logger.info(
            f"Cost breakdown - "
            f"Text Input: ${breakdown.text_input:.4f}, "
            f"Text Output: ${breakdown.text_output:.4f}, "
            f"Image Input: ${breakdown.image_input:.4f}, "
            f"Image Output: ${breakdown.image_output:.4f}"
        )

    return genai_state


@instance
def genai_state() -> GenAIState:
    """Get initial Gen AI state for cost tracking.

    Returns:
        Initial GenAIState instance
    """
    return GenAIState()
