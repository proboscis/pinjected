"""Check GPT-5 availability in OpenRouter."""

import pytest
from pinjected.test import injected_pytest


@pytest.mark.asyncio
@injected_pytest
async def test_gpt5_availability(
    openrouter_model_table,
    logger,
    /,
):
    """Check GPT-5 availability in OpenRouter."""

    # Check if GPT-5 is in the model table
    model = openrouter_model_table.get_model("openai/gpt-5")
    if model:
        logger.info(f"GPT-5 found in model table:")
        logger.info(f"  ID: {model.id}")
        logger.info(f"  Name: {model.name}")
        if hasattr(model, "created"):
            logger.info(f"  Created: {model.created}")
        logger.info(f"  Supported parameters: {model.supported_parameters}")
        logger.info(f"  Supports JSON: {model.supports_json_output()}")

        # Check additional fields
        if hasattr(model, "per_request_limits"):
            logger.info(f"  Per request limits: {model.per_request_limits}")
    else:
        logger.info("GPT-5 not found in model table")

    # Check what OpenAI models are available
    logger.info("\nAvailable OpenAI models in OpenRouter:")
    openai_models = [
        m for m in openrouter_model_table.data if m.id.startswith("openai/")
    ]
    logger.info(f"Found {len(openai_models)} OpenAI models")

    # Show GPT models only
    logger.info("\nGPT models:")
    gpt_models = [m for m in openai_models if "gpt" in m.id.lower()]
    for m in gpt_models:
        supports_json = "✓" if m.supports_json_output() else "✗"
        logger.info(f"  [{supports_json}] {m.id} - {m.name}")

    # Specifically look for GPT-5 variants
    logger.info("\nLooking for GPT-5 variants:")
    gpt5_models = [
        m
        for m in openrouter_model_table.data
        if "gpt-5" in m.id.lower() or "gpt5" in m.id.lower()
    ]
    if gpt5_models:
        for m in gpt5_models:
            logger.info(f"  Found: {m.id} - {m.name}")
            logger.info(f"    Created: {m.created if hasattr(m, 'created') else 'N/A'}")
            logger.info(f"    Supported params: {m.supported_parameters}")
    else:
        logger.info("  No GPT-5 variants found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
