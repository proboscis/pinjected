"""Test the OpenRouter model table."""

import pytest
from pinjected.test import injected_pytest
from loguru import logger


@pytest.mark.asyncio
@injected_pytest
async def test_model_table_json_support(
    openrouter_model_table,
    /,
):
    """Test which models support JSON output."""

    # Models that should support JSON
    json_models = [
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
        "openai/gpt-4-turbo",
        "openai/gpt-3.5-turbo",
    ]

    for model_id in json_models:
        supports = openrouter_model_table.supports_json_output(model_id)
        logger.info(f"Model {model_id} supports JSON: {supports}")

        # Get detailed model info
        model = openrouter_model_table.get_model(model_id)
        if model:
            logger.info(f"  - Name: {model.name}")
            logger.info(
                f"  - Architecture: {model.architecture.name if model.architecture else 'None'}"
            )
            if model.architecture and model.architecture.capabilities:
                logger.info(
                    f"  - Capabilities.json: {model.architecture.capabilities.json}"
                )
            else:
                logger.info(f"  - No capabilities found")

    # Models that might not support JSON
    non_json_models = [
        "meta-llama/llama-3-8b-instruct",
        "google/gemini-pro",
    ]

    for model_id in non_json_models:
        supports = openrouter_model_table.supports_json_output(model_id)
        logger.info(f"Model {model_id} supports JSON: {supports}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
