"""Test if JSON support detection works."""

import pytest
from pinjected.test import injected_pytest
from loguru import logger


@pytest.mark.asyncio
@injected_pytest
async def test_json_support_detection(
    openrouter_model_table,
    /,
):
    """Test if JSON support is properly detected."""

    # Test OpenAI models
    openai_models = [
        "openai/gpt-4o-mini",
        "openai/gpt-4o",
        "openai/gpt-3.5-turbo",
    ]

    for model_id in openai_models:
        model = openrouter_model_table.get_model(model_id)
        if model:
            supports = model.supports_json_output()
            logger.info(f"Model {model_id}: supports_json_output = {supports}")

            # Check via table method too
            table_supports = openrouter_model_table.supports_json_output(model_id)
            logger.info(f"  Table says: {table_supports}")
        else:
            logger.warning(f"Model {model_id} not found in table")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
