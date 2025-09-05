"""Pricing module for Google Gen AI models with cost tracking.

This module provides pricing information and cost calculation for Google's Gemini models.
Cost tracking is performed per API call and cumulatively.

Note: The Gen AI SDK does not currently provide token usage counts in API responses.
Text token counts are estimated from character counts (4 chars ≈ 1 token).
Image token counts cannot be accurately calculated without API support.
"""

from dataclasses import dataclass
from typing import ClassVar, Dict, Optional, Protocol

from pinjected import instance


@dataclass
class ModelPricing:
    """Pricing information for a Gen AI model.

    All prices are per million tokens. For text, we estimate tokens from
    character count (4 chars ≈ 1 token). For images, actual token counts
    must be provided by the API (currently not available in Gen AI SDK).
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
                - text_input_tokens: Number of input tokens (or text_input_chars to convert)
                - text_output_tokens: Number of output tokens (or text_output_chars to convert)
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
        # Get token counts - support both tokens and chars (converting chars to tokens)
        text_in_tokens = usage.get("text_input_tokens", 0)
        if text_in_tokens == 0 and "text_input_chars" in usage:
            # Convert chars to tokens (4 chars ≈ 1 token)
            text_in_tokens = usage["text_input_chars"] / 4

        text_out_tokens = usage.get("text_output_tokens", 0)
        if text_out_tokens == 0 and "text_output_chars" in usage:
            # Convert chars to tokens (4 chars ≈ 1 token)
            text_out_tokens = usage["text_output_chars"] / 4

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

    Note: Pricing information must be hardcoded as the Gen AI SDK
    does not provide pricing via API.
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


def calculate_cumulative_cost(genai_state: dict, cost_dict: dict) -> dict:
    """Calculate new state with updated cumulative cost.

    Args:
        genai_state: Current state dictionary
        cost_dict: Cost breakdown for current call

    Returns:
        Updated state dictionary
    """
    current_total = genai_state.get("cumulative_cost", 0.0)
    current_breakdown = genai_state.get(
        "cost_breakdown",
        {
            "text_input": 0.0,
            "text_output": 0.0,
            "image_input": 0.0,
            "image_output": 0.0,
        },
    )

    # Update total
    new_total = current_total + cost_dict.get("total", 0.0)

    # Update breakdown
    new_breakdown = {
        "text_input": current_breakdown["text_input"]
        + cost_dict.get("text_input", 0.0),
        "text_output": current_breakdown["text_output"]
        + cost_dict.get("text_output", 0.0),
        "image_input": current_breakdown["image_input"]
        + cost_dict.get("image_input", 0.0),
        "image_output": current_breakdown["image_output"]
        + cost_dict.get("image_output", 0.0),
    }

    # Increment request count
    request_count = genai_state.get("request_count", 0) + 1

    return {
        **genai_state,
        "cumulative_cost": new_total,
        "cost_breakdown": new_breakdown,
        "request_count": request_count,
    }


def log_generation_cost(
    usage: dict,
    model: str,
    genai_model_table: GenAIModelTable,
    genai_state: dict,
    logger: LoggerProtocol,
) -> dict:
    """Calculate and log generation costs, returning updated state.

    Args:
        usage: Usage metrics dictionary
        model: Model name used
        genai_model_table: Model pricing table
        genai_state: Current state
        logger: Logger instance

    Returns:
        Updated state dictionary with new costs
    """
    pricing = genai_model_table.get_pricing(model)

    if not pricing:
        logger.warning(f"No pricing information available for model: {model}")
        return genai_state

    cost_dict = pricing.calc_cost(usage)
    new_state = calculate_cumulative_cost(genai_state, cost_dict)

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
        f"Cumulative: ${new_state['cumulative_cost']:.6f}"
    )

    # Log detailed breakdown periodically
    if new_state.get("request_count", 0) % 10 == 0:
        breakdown = new_state["cost_breakdown"]
        logger.info(
            f"Cost breakdown - "
            f"Text Input: ${breakdown['text_input']:.4f}, "
            f"Text Output: ${breakdown['text_output']:.4f}, "
            f"Image Input: ${breakdown['image_input']:.4f}, "
            f"Image Output: ${breakdown['image_output']:.4f}"
        )

    return new_state


@instance
def genai_state() -> dict:
    """Get initial Gen AI state for cost tracking.

    Returns:
        Initial state dictionary
    """
    return {
        "cumulative_cost": 0.0,
        "cost_breakdown": {
            "text_input": 0.0,
            "text_output": 0.0,
            "image_input": 0.0,
            "image_output": 0.0,
        },
        "request_count": 0,
    }
