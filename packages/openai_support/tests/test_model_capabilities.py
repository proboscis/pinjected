"""Test to see what capabilities are reported by the API."""

import pytest
from pinjected.test import injected_pytest
from loguru import logger
import json


@pytest.mark.asyncio
@injected_pytest
async def test_model_capabilities_detail(
    openrouter_model_table,
    /,
):
    """Test to see detailed capabilities."""

    # Check gpt-4o-mini specifically
    model_id = "openai/gpt-4o-mini"
    model = openrouter_model_table.get_model(model_id)

    if model:
        logger.info(f"Model: {model_id}")
        logger.info(f"  Name: {model.name}")
        logger.info(f"  ID: {model.id}")

        if model.architecture:
            logger.info(f"  Architecture name: {model.architecture.name}")
            if model.architecture.capabilities:
                # Log the raw capabilities dict
                caps_dict = model.architecture.capabilities.model_dump()
                logger.info(f"  Capabilities (raw): {json.dumps(caps_dict, indent=2)}")
                logger.info(
                    f"  Capabilities.json_output: {model.architecture.capabilities.json_output}"
                )

                # Try to access via alias
                try:
                    json_value = getattr(model.architecture.capabilities, "json", None)
                    logger.info(f"  Capabilities.json (via getattr): {json_value}")
                except AttributeError:
                    pass
            else:
                logger.info("  No capabilities")
        else:
            logger.info("  No architecture")
    else:
        logger.info(f"Model {model_id} not found in table")

    # Also test if the model table data is actually populated
    all_models = openrouter_model_table.data
    logger.info(f"Total models in table: {len(all_models)}")

    # Check first few models
    for i, model in enumerate(all_models[:3]):
        logger.info(f"Model {i}: {model.id}")
        if model.architecture and model.architecture.capabilities:
            logger.info(
                f"  Has capabilities: {model.architecture.capabilities.model_dump()}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
