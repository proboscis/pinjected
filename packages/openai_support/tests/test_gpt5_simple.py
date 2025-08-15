"""Simple test to reproduce GPT-5 non-cached issue."""

import pytest
from pinjected.test import injected_pytest
from pydantic import BaseModel


class A(BaseModel):
    random_text: str


@pytest.mark.asyncio
@injected_pytest
async def test_gpt5_non_cached(
    a_openrouter_chat_completion,
    openrouter_model_table,
    logger,
    /,
):
    """Test non-cached GPT-5 with response_format - this should fail."""

    # Check if GPT-5 supports JSON
    model = openrouter_model_table.get_model("openai/gpt-5")
    if model:
        logger.info(f"GPT-5 found")
        logger.info(f"Supported parameters: {model.supported_parameters}")
        logger.info(f"Supports JSON output: {model.supports_json_output()}")

        # Check architecture capabilities
        if model.architecture.capabilities:
            logger.info(
                f"Architecture capabilities json_output: {model.architecture.capabilities.json_output}"
            )
    else:
        logger.warning("GPT-5 not found in model table")

    # Try to call directly (non-cached)
    try:
        logger.info("Attempting non-cached call with response_format...")
        result = await a_openrouter_chat_completion(
            prompt="Say hello and provide some random text",
            model="openai/gpt-5",
            response_format=A,
            max_tokens=100,
            temperature=0,
        )
        logger.info(f"Success! Result: {result}")
        assert isinstance(result, A)
    except Exception as e:
        logger.error(f"Non-cached failed with error: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback

        logger.error(f"Traceback:\n{traceback.format_exc()}")
        raise


@pytest.mark.asyncio
@injected_pytest
async def test_gpt4o_mini_comparison(
    a_openrouter_chat_completion,
    openrouter_model_table,
    logger,
    /,
):
    """Compare with GPT-4o-mini which we know works."""

    # Check GPT-4o-mini
    model = openrouter_model_table.get_model("openai/gpt-4o-mini")
    if model:
        logger.info(f"GPT-4o-mini found")
        logger.info(f"Supported parameters: {model.supported_parameters}")
        logger.info(f"Supports JSON output: {model.supports_json_output()}")

    # This should work
    result = await a_openrouter_chat_completion(
        prompt="Say hello and provide some random text",
        model="openai/gpt-4o-mini",
        response_format=A,
        max_tokens=100,
        temperature=0,
    )
    logger.info(f"GPT-4o-mini result: {result}")
    assert isinstance(result, A)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
